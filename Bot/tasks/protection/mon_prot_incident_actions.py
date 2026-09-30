"""
tasks/protection/mon_prot_incident_actions.py

Monitor de Incident Actions (DMs e Invites bloqueados).

Responsabilidades:
  1. Task periódica (a cada 3 min) que verifica via API do Discord se as
     incident actions ainda estão ativas e, se não estiverem, reaaplica.
  2. Listener on_guild_update que detecta alterações em tempo real e
     reaaplica imediatamente.
  3. Logs detalhados para o canal configurado.
  4. Robusto a erros de rede, rate-limit e ausência de permissões.
"""

import asyncio
import datetime
import json
import traceback
from typing import Optional

import aiohttp
import disnake
from disnake.ext import commands, tasks

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.protecaogeral.incidentactions import helpers

DISCORD_API_BASE = "https://discord.com/api/v10"

# Cooldown entre tentativas de reaplicação por guild (segundos)
RETRY_COOLDOWN = 60
# Quantas tentativas consecutivas com falha antes de desativar automaticamente
MAX_FALHAS_CONSECUTIVAS = 5


def _get_bot_token() -> str:
    """Lê o token do bot do config.json."""
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
        return data["bot"]["token"]
    except Exception:
        return ""


class MonProtIncidentActions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # guild_id -> timestamp da última tentativa de reaplicação
        self._ultima_tentativa: dict[int, float] = {}

        # guild_id -> contagem de falhas consecutivas
        self._falhas_consecutivas: dict[int, int] = {}

        # guild_id -> set{"dms", "invites"} — itens que já foram logados como
        # "desativados externamente" para evitar spam de logs
        self._notificados: dict[int, set[str]] = {}

        self._scan_task.start()

    def cog_unload(self):
        self._scan_task.cancel()

    # ------------------------------------------------------------------
    # Helpers de API
    # ------------------------------------------------------------------

    async def _get_incident_actions(self, guild_id: int, token: str) -> Optional[dict]:
        """
        Busca o estado atual de incident-actions da guild.
        Retorna o dict JSON ou None em caso de erro.
        """
        headers = {"Authorization": f"Bot {token}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{DISCORD_API_BASE}/guilds/{guild_id}?with_counts=false",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "dms_disabled_until":     data.get("incidents_data", {}).get("dms_disabled_until"),
                            "invites_disabled_until": data.get("incidents_data", {}).get("invites_disabled_until"),
                        }
                    if resp.status == 429:
                        retry_after = float((await resp.json()).get("retry_after", 5))
                        await asyncio.sleep(retry_after)
                    return None
        except Exception:
            return None

    async def _aplicar_incident_actions(
        self,
        guild_id: int,
        token: str,
        dms_minutos: Optional[int],
        invites_minutos: Optional[int],
    ) -> tuple[bool, str]:
        """
        Aplica (ou limpa) incident-actions via API.
        Retorna (sucesso, mensagem).
        """
        payload: dict = {}

        if dms_minutos is not None:
            until = datetime.datetime.utcnow() + datetime.timedelta(minutes=dms_minutos)
            payload["dms_disabled_until"] = until.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        else:
            payload["dms_disabled_until"] = None

        if invites_minutos is not None:
            until = datetime.datetime.utcnow() + datetime.timedelta(minutes=invites_minutos)
            payload["invites_disabled_until"] = until.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        else:
            payload["invites_disabled_until"] = None

        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{DISCORD_API_BASE}/guilds/{guild_id}/incident-actions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        return True, "OK"
                    if resp.status == 429:
                        data = await resp.json()
                        retry_after = data.get("retry_after", 5)
                        return False, f"Rate limited — aguarde {retry_after:.1f}s"
                    texto = await resp.text()
                    return False, f"HTTP {resp.status}: {texto[:120]}"
        except asyncio.TimeoutError:
            return False, "Timeout na requisição à API do Discord"
        except aiohttp.ClientError as exc:
            return False, f"Erro de rede: {exc}"
        except Exception as exc:
            return False, f"Erro inesperado: {exc}"

    # ------------------------------------------------------------------
    # Lógica central de verificação
    # ------------------------------------------------------------------

    async def _verificar_guild(self, guild: disnake.Guild) -> None:
        """
        Verifica e reaaplica incident-actions para uma guild, se necessário.
        """
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})

        dms_ativado     = dados.get("dms_ativado", False)
        invites_ativado = dados.get("invites_ativado", False)

        # Se nenhum está ativo na config, nada a fazer
        if not dms_ativado and not invites_ativado:
            return

        token = _get_bot_token()
        if not token:
            return

        canal_logs = avancado.get("canal_logs")
        guild_id   = guild.id
        agora      = datetime.datetime.utcnow()

        # Cooldown entre tentativas
        import time as _time
        ultima = self._ultima_tentativa.get(guild_id, 0)
        if (_time.time() - ultima) < RETRY_COOLDOWN:
            return

        # Buscar estado atual via API
        estado_atual = await self._get_incident_actions(guild_id, token)
        if estado_atual is None:
            # Falha ao buscar — contar como falha
            self._registrar_falha(guild_id, dados, config, canal_logs, guild,
                                   motivo="Falha ao consultar API do Discord")
            return

        # Resetar falhas em caso de sucesso na consulta
        self._falhas_consecutivas[guild_id] = 0

        precisa_reaplicar_dms     = False
        precisa_reaplicar_invites = False

        # Checar DMs
        if dms_ativado:
            dms_until_str = estado_atual.get("dms_disabled_until")
            if not dms_until_str:
                precisa_reaplicar_dms = True
            else:
                try:
                    dms_until = datetime.datetime.fromisoformat(
                        dms_until_str.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    # Reaplicar se restar menos de 10 minutos (margem de segurança)
                    if (dms_until - agora).total_seconds() < 600:
                        precisa_reaplicar_dms = True
                except Exception:
                    precisa_reaplicar_dms = True

        # Checar Invites
        if invites_ativado:
            inv_until_str = estado_atual.get("invites_disabled_until")
            if not inv_until_str:
                precisa_reaplicar_invites = True
            else:
                try:
                    inv_until = datetime.datetime.fromisoformat(
                        inv_until_str.replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    if (inv_until - agora).total_seconds() < 600:
                        precisa_reaplicar_invites = True
                except Exception:
                    precisa_reaplicar_invites = True

        if not precisa_reaplicar_dms and not precisa_reaplicar_invites:
            # Limpar notificações antigas — tudo está OK
            self._notificados.pop(guild_id, None)
            return

        # Marcar timestamp da tentativa
        self._ultima_tentativa[guild_id] = _time.time()

        dms_minutos     = helpers.duracao_para_minutos(dados.get("duracao_dms", "1h"))     if precisa_reaplicar_dms     else None
        invites_minutos = helpers.duracao_para_minutos(dados.get("duracao_invites", "1h")) if precisa_reaplicar_invites else None

        ok, msg = await self._aplicar_incident_actions(guild_id, token, dms_minutos, invites_minutos)

        if ok:
            self._falhas_consecutivas[guild_id] = 0
            linhas = [f"{emoji.reload} **Incident Actions restauradas automaticamente**"]

            if precisa_reaplicar_dms:
                dur_label = helpers.formatar_duracao(dados.get("duracao_dms", "1h"))
                linhas.append(f"{emoji.warn} **DMs bloqueadas** renovadas por mais `{dur_label}`")

            if precisa_reaplicar_invites:
                dur_label = helpers.formatar_duracao(dados.get("duracao_invites", "1h"))
                linhas.append(f"{emoji.warn} **Invites bloqueados** renovados por mais `{dur_label}`")

            linhas.append(f"{emoji.calendar} **Detectado em:** <t:{int(_time.time())}:f>")
            await enviar_log(guild, canal_logs, "Incident Actions — Restauração Automática", linhas)

            # Limpar notificações — ação foi restaurada
            self._notificados.pop(guild_id, None)

        else:
            self._registrar_falha(guild_id, dados, config, canal_logs, guild, motivo=msg)

    def _registrar_falha(
        self,
        guild_id: int,
        dados: dict,
        config: dict,
        canal_logs: Optional[int],
        guild: disnake.Guild,
        motivo: str,
    ) -> None:
        """Incrementa falhas consecutivas e, se atingir o limite, desativa a proteção."""
        import time as _time

        self._falhas_consecutivas[guild_id] = self._falhas_consecutivas.get(guild_id, 0) + 1
        falhas = self._falhas_consecutivas[guild_id]

        if falhas >= MAX_FALHAS_CONSECUTIVAS:
            # Desativar automaticamente para não logar spam
            dados["dms_ativado"]     = False
            dados["invites_ativado"] = False
            config[helpers.CHAVE]   = dados
            helpers.salvar_config(config)
            self._falhas_consecutivas[guild_id] = 0

            asyncio.create_task(
                enviar_log(
                    guild,
                    canal_logs,
                    "Incident Actions — Proteção Desativada Automaticamente",
                    [
                        f"{emoji.wrong} **{MAX_FALHAS_CONSECUTIVAS} falhas consecutivas** ao reaplicar.",
                        f"{emoji.information} Motivo da última falha: `{motivo}`",
                        f"{emoji.warn} A proteção foi **desativada automaticamente** para evitar spam.",
                        f"-# Reative manualmente quando o problema for resolvido.",
                    ],
                )
            )

    # ------------------------------------------------------------------
    # Task periódica
    # ------------------------------------------------------------------

    @tasks.loop(minutes=3)
    async def _scan_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                await self._verificar_guild(guild)
            except Exception:
                print(f"[MonProtIncidentActions] Erro inesperado na guild {guild.id}:")
                traceback.print_exc()
            # Pequena pausa entre guilds para não sobrecarregar a API
            await asyncio.sleep(0.5)

    @_scan_task.before_loop
    async def _before_scan(self):
        await self.bot.wait_until_ready()
        # Aguardar 30s após o boot antes da primeira varredura
        await asyncio.sleep(30)

    @_scan_task.error
    async def _scan_task_error(self, error: Exception):
        print(f"[MonProtIncidentActions] Erro na task periódica: {error}")
        traceback.print_exc()
        # Reiniciar a task após 60s em caso de erro fatal
        await asyncio.sleep(60)
        if not self._scan_task.is_running():
            self._scan_task.start()

    # ------------------------------------------------------------------
    # Listener em tempo real
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_guild_update(self, before: disnake.Guild, after: disnake.Guild):
        """
        Detecta alterações em incidents_data e reaaplica imediatamente
        se a proteção estiver ativa.
        """
        config = helpers.carregar_config()
        dados  = config.get(helpers.CHAVE, {})
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})

        dms_ativado     = dados.get("dms_ativado", False)
        invites_ativado = dados.get("invites_ativado", False)

        if not dms_ativado and not invites_ativado:
            return

        # Capturar dados de incidents antes e depois
        before_incidents = getattr(before, "incidents_data", None) or {}
        after_incidents  = getattr(after, "incidents_data", None) or {}

        before_dms     = before_incidents.get("dms_disabled_until")     if isinstance(before_incidents, dict) else getattr(before_incidents, "dms_disabled_until", None)
        after_dms      = after_incidents.get("dms_disabled_until")      if isinstance(after_incidents, dict) else getattr(after_incidents, "dms_disabled_until", None)
        before_invites = before_incidents.get("invites_disabled_until") if isinstance(before_incidents, dict) else getattr(before_incidents, "invites_disabled_until", None)
        after_invites  = after_incidents.get("invites_disabled_until")  if isinstance(after_incidents, dict) else getattr(after_incidents, "invites_disabled_until", None)

        dms_desativado_externamente     = dms_ativado     and before_dms     and not after_dms
        invites_desativado_externamente = invites_ativado and before_invites and not after_invites

        if not dms_desativado_externamente and not invites_desativado_externamente:
            return

        # Tentar identificar o responsável via audit log
        await asyncio.sleep(1.5)
        executor_str = "Desconhecido"
        try:
            agora_dt = disnake.utils.utcnow()
            async for entry in after.audit_logs(action=disnake.AuditLogAction.guild_update, limit=5):
                if (agora_dt - entry.created_at).total_seconds() <= 30:
                    u = entry.user
                    if u:
                        executor_str = f"{u.mention} (`{u.id}`)"
                    break
        except Exception:
            pass

        canal_logs = avancado.get("canal_logs")
        token      = _get_bot_token()
        guild_id   = after.id

        linhas_log = [f"{emoji.warn} **Incident Action removida externamente por:** {executor_str}"]

        if dms_desativado_externamente:
            linhas_log.append(f"{emoji.message} **DMs bloqueadas** foram desativadas externamente")

        if invites_desativado_externamente:
            linhas_log.append(f"{emoji.link} **Invites bloqueados** foram desativados externamente")

        # Reaplicar imediatamente
        dms_min     = helpers.duracao_para_minutos(dados.get("duracao_dms", "1h"))     if dms_desativado_externamente     else None
        invites_min = helpers.duracao_para_minutos(dados.get("duracao_invites", "1h")) if invites_desativado_externamente else None

        ok, msg = await self._aplicar_incident_actions(guild_id, token, dms_min, invites_min)

        if ok:
            self._falhas_consecutivas[guild_id] = 0
            if dms_desativado_externamente:
                dur = helpers.formatar_duracao(dados.get("duracao_dms", "1h"))
                linhas_log.append(f"{emoji.reload} **DMs** restauradas por `{dur}`")
            if invites_desativado_externamente:
                dur = helpers.formatar_duracao(dados.get("duracao_invites", "1h"))
                linhas_log.append(f"{emoji.reload} **Invites** restaurados por `{dur}`")
            await enviar_log(after, canal_logs, "Incident Actions — Restauração em Tempo Real", linhas_log)
        else:
            linhas_log.append(f"{emoji.wrong} **Falha ao restaurar:** `{msg}`")
            linhas_log.append(f"-# A task periódica tentará novamente em até 3 minutos.")
            await enviar_log(after, canal_logs, "Incident Actions — Falha na Restauração", linhas_log)

            # Forçar cooldown zerado para a task tentar logo
            import time as _time
            self._ultima_tentativa[guild_id] = 0


def setup(bot: commands.Bot):
    bot.add_cog(MonProtIncidentActions(bot))
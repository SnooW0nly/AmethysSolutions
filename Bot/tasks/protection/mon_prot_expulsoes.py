import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.protecaogeral.expulsoes import helpers


class MonProtExpulsoes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Mapa: guild_id -> executor_id -> deque[timestamps]
        self._contadores: Dict[int, Dict[int, Deque[float]]] = defaultdict(lambda: defaultdict(lambda: deque()))
        # Mapa: guild_id -> executor_id -> deque[(timestamp, alvo_id)]
        self._alvos: Dict[int, Dict[int, Deque[tuple[float, int]]]] = defaultdict(lambda: defaultdict(lambda: deque()))

    # Config helpers
    @classmethod
    def _carregar_config(cls) -> dict:
        dados = db.get_document(cls.COLLECTION_NAME)
        base = dados.get("expulsoes") or {}
        avancado = dados.get("expulsoes_avancado") or {}
        ativado = bool(base.get("ativado", True))
        limite = int(base.get("limite", 2))
        intervalo = int(base.get("intervalo", 10))
        punicao = avancado.get("punicao", "ban")
        cargos_imunes = avancado.get("cargos_imunes", []) or []
        canal_logs = avancado.get("canal_logs")
        return {
            "ativado": ativado,
            "limite": limite,
            "intervalo": intervalo,
            "punicao": punicao,
            "cargos_imunes": cargos_imunes,
            "canal_logs": canal_logs,
        }

    # Log helpers
    @staticmethod
    def _criar_container_log(titulo: str, linhas: list[str]) -> disnake.ui.Container:
        linhas_filtradas = [l for l in linhas if l]
        corpo = "\n".join(linhas_filtradas) if linhas_filtradas else ""
        return disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# {titulo}"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(corpo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"{emoji.calendar} **Data:** <t:{int(time.time())}:f> (<t:{int(time.time())}:R>)"
            ),
        )

    # Punição
    @staticmethod
    async def _aplicar_punicao(guild: disnake.Guild, executor: Optional[disnake.Member], punicao: str, motivo: str) -> str:
        if executor is None:
            return "Executor desconhecido — sem punição"
        try:
            if punicao == "ban":
                await guild.ban(executor, reason=motivo)
                return "Aplicada"
            if punicao == "kick":
                await guild.kick(executor, reason=motivo)
                return "Aplicada"
            if punicao == "remover_cargos":
                roles_to_remove = [r for r in executor.roles if not r.is_default()]
                if roles_to_remove:
                    await executor.remove_roles(*roles_to_remove, reason=motivo)
                return "Aplicada"
            return "Sem punição (configurado como none)"
        except Exception:
            return "Falha ao punir (Verifique as permissões do bot)"

    def _add_executor_info(self, linhas: list[str], executor: Optional[disnake.Member]):
        if executor:
            info_executor = [
                f"{emoji.member} **Executor:** {executor.mention} ({executor.id})",
                f"{emoji.information} **Cargo mais alto:** {executor.top_role.mention}",
                f"{emoji.information} **Quantidade de cargos:** {len(executor.roles)}",
            ]
            if executor.joined_at:
                info_executor.append(f"{emoji.information} **Entrou em:** <t:{int(executor.joined_at.timestamp())}:f> (<t:{int(executor.joined_at.timestamp())}:R>)")
            if executor.created_at:
                info_executor.append(f"{emoji.information} **Conta criada em:** <t:{int(executor.created_at.timestamp())}:f> (<t:{int(executor.created_at.timestamp())}:R>)")
            linhas.extend(info_executor)
        else:
            linhas.append(f"{emoji.member} **Executor:** Desconhecido (N/A)")

    # Audit log: resolver executor de expulsão
    async def _resolver_executor_kick(self, guild: disnake.Guild, alvo: disnake.Member | disnake.User, limite_segundos: int = 120) -> Optional[disnake.Member]:
        for _ in range(8):
            try:
                agora = disnake.utils.utcnow()
                async for entry in guild.audit_logs(action=disnake.AuditLogAction.kick, limit=25):
                    if getattr(entry, "target", None) and getattr(entry.target, "id", 0) == getattr(alvo, "id", 0):
                        if (agora - entry.created_at).total_seconds() <= limite_segundos:
                            usuario = entry.user
                            membro = usuario if isinstance(usuario, disnake.Member) else guild.get_member(getattr(usuario, 'id', 0))
                            if membro and (not self.bot.user or membro.id != self.bot.user.id):
                                return membro
            except Exception:
                pass
            await asyncio.sleep(1.2)
        return None

    # Contador por janela
    def _incrementar_contador(self, guild_id: int, executor_id: int, intervalo: int) -> int:
        agora = time.time()
        fila = self._contadores[guild_id][executor_id]
        while fila and (agora - fila[0]) > intervalo:
            fila.popleft()
        fila.append(agora)
        return len(fila)

    def _registrar_alvo(self, guild_id: int, executor_id: int, alvo_id: int, intervalo: int) -> None:
        agora = time.time()
        fila = self._alvos[guild_id][executor_id]
        while fila and (agora - fila[0][0]) > intervalo:
            fila.popleft()
        fila.append((agora, int(alvo_id)))

    def _listar_alvos_mencionados(self, guild_id: int, executor_id: int, intervalo: int) -> list[str]:
        agora = time.time()
        fila = self._alvos[guild_id][executor_id]
        while fila and (agora - fila[0][0]) > intervalo:
            fila.popleft()
        return [f"<@{alvo_id}>," for _, alvo_id in list(fila)]

    @staticmethod
    def _executor_imune(executor: Optional[disnake.Member], config: dict) -> bool:
        if not executor:
            return False
        ids = set(config.get("cargos_imunes", []))
        if not ids:
            return False
        try:
            return any(r.id in ids for r in getattr(executor, "roles", []))
        except Exception:
            return False

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        # Detectar se foi expulsão (kick) pelo audit log
        guild = member.guild
        if not guild:
            return

        config = helpers.carregar_config()
        if not config:
            return

        try:
            await asyncio.sleep(0.75)
        except Exception:
            pass

        executor = await self._resolver_executor_kick(guild, member)
        if not executor:
            # Provável saída voluntária; não logar
            return

        dados_base = config.get(helpers.CHAVE, {})
        dados_avancados = config.get("expulsoes_avancado", {})

        # Carregar configurações
        ativado = dados_base.get("ativado", True)
        limite = dados_base.get("limite", 2)
        intervalo = dados_base.get("intervalo", 10)

        # Verificar se haverá lista de usuários afetados
        tem_lista_usuarios = False
        fila = self._alvos[guild.id][executor.id]
        agora = time.time()
        # Simular limpeza da fila para ver se há alvos
        alvos_validos = [(ts, alvo_id) for ts, alvo_id in fila if (agora - ts) <= intervalo]
        tem_lista_usuarios = len(alvos_validos) > 0

        # Linhas base
        linhas = []
        
        # Só mostrar usuário individual se não houver lista de usuários afetados
        if not tem_lista_usuarios:
            linhas.append(f"{emoji.member} **Alvo expulso:** <@{member.id}> ({member.id})")
        
        self._add_executor_info(linhas, executor)

        # Se desativado: ainda assim logar executor e alvos recentes
        if not ativado:
            self._registrar_alvo(guild.id, executor.id, member.id, intervalo)
            mencoes = self._listar_alvos_mencionados(guild.id, executor.id, intervalo)
            if mencoes:
                linhas.extend(mencoes)
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada")
            await enviar_log(guild, dados_avancados.get("canal_logs"), "Proteção de Expulsões - Logs", linhas)
            return

        # Contagem por executor
        contagem = self._incrementar_contador(guild.id, executor.id, intervalo)
        self._registrar_alvo(guild.id, executor.id, member.id, intervalo)
        linhas.append(f"{emoji.chart} **Contagem:** {contagem}/{limite} em {intervalo}s")
        mencoes = self._listar_alvos_mencionados(guild.id, executor.id, intervalo)
        if mencoes:
            linhas.extend(mencoes)

        # Imunidade
        executor_imune = self._executor_imune(executor, dados_avancados)
        excedeu = contagem > limite
        if excedeu:
            linhas.append(f"{emoji.warn} **Ação:** Limite excedido")
            if not executor_imune:
                punicao = dados_avancados.get("punicao", "ban")
                if punicao != "none":
                    resultado = await self._aplicar_punicao(
                        guild,
                        executor,
                        punicao,
                        motivo=f"Violou proteção de expulsões (limite excedido) ao expulsar <@{member.id}>"
                    )
                    linhas.append(f"{emoji.wand} **Punição:** {punicao.capitalize()} — {resultado}")
                else:
                    linhas.append(f"{emoji.wand} **Punição:** Nenhuma (configurado)")
            else:
                linhas.append(f"{emoji.shield} **Ação:** Executor imune — punição não aplicada")

            await enviar_log(guild, dados_avancados.get("canal_logs"), "Proteção de Expulsões - Logs", linhas)
            return

        # Não excedeu: apenas logar
        await enviar_log(guild, dados_avancados.get("canal_logs"), "Proteção de Expulsões - Logs", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(MonProtExpulsoes(bot))


"""
tasks/utilitarios/tsk_tagbio.py

Task periódica que verifica, para cada membro com o cargo configurado,
se ainda possui a tag/bio exigida — e remove o cargo se não tiver mais.
Também adiciona o cargo para quem passou a ter.

Fluxo:
  - A cada X minutos (cooldown_minutos), varre todos os membros do servidor.
  - Para cada membro:
    - Se TEM o cargo:
        • verifica tag (se tag_ativo) e bio (se bio_ativo)
        • se falhou → remove o cargo → log privado + log público (perdeu)
    - Se NÃO tem o cargo:
        • verifica tag e bio
        • se passou em tudo → adiciona cargo → log privado (ganhou)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import aiohttp
import disnake
from disnake.ext import commands, tasks

from functions.database import database as db
from functions.emoji import emoji

log = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"


# ─── Helpers locais (evitar importar o módulo inteiro desnecessariamente) ─────

def _carregar_config() -> dict:
    dados = db.get_document("utilitarios_tagbio") or {}
    if not isinstance(dados, dict):
        dados = {}
    return dados


def _get_bot_token() -> str | None:
    try:
        config = db.obter("config.json")
        return config.get("bot", {}).get("token")
    except Exception:
        pass
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f).get("bot", {}).get("token")
    except Exception:
        return None


def _get_user_tokens() -> list[dict]:
    """Retorna a lista de tokens de usuário cadastrados."""
    doc = db.get_document("tokens") or {}
    return doc.get("list", [])


def _get_any_user_token() -> str | None:
    tokens = _get_user_tokens()
    if tokens:
        return tokens[0].get("token")
    return None


def _get_user_token(user_id: int | str) -> str | None:
    uid = str(user_id)
    for t in _get_user_tokens():
        if str(t.get("user_id")) == uid:
            return t.get("token")
    return None


async def _fetch_bio(user_id: int, token: str) -> str | None:
    """Busca a bio do perfil Discord de um usuário via user token."""
    headers = {"Authorization": token}
    url = f"{DISCORD_API_BASE}/users/{user_id}/profile?with_mutual_guilds=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return (data.get("user_profile") or {}).get("bio") or ""
    except Exception:
        return None


def _check_tag(member: disnake.Member, tag_texto: str) -> bool:
    """Verifica se a tag/nome do membro contém o texto configurado."""
    display = member.display_name or ""
    name    = member.name or ""
    return (tag_texto.lower() in display.lower() or
            tag_texto.lower() in name.lower())


async def _check_bio(user_id: int, bio_texto: str) -> bool:
    """Verifica se a bio do usuário contém o texto configurado."""
    token = _get_user_token(user_id) or _get_any_user_token()
    if not token:
        return False
    bio = await _fetch_bio(user_id, token)
    if bio is None:
        return False
    return bio_texto.lower() in bio.lower()


async def _get_canal(bot: commands.Bot, canal_id: int | str | None) -> Optional[disnake.TextChannel]:
    if not canal_id:
        return None
    try:
        ch = bot.get_channel(int(canal_id))
        if isinstance(ch, disnake.TextChannel):
            return ch
    except Exception:
        pass
    return None


async def _send_log(canal: Optional[disnake.TextChannel], titulo: str, descricao: str, cor: disnake.Colour):
    """Envia um embed de log em um canal."""
    if not canal:
        return
    try:
        emb = disnake.Embed(title=titulo, description=descricao, color=cor)
        await canal.send(embed=emb)
    except Exception:
        pass


# ─── COG da task ──────────────────────────────────────────────────────────────

class TagBioTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot          = bot
        self._next_run_in = 0   # segundos restantes até próxima execução
        self._task_loop.start()

    def cog_unload(self):
        self._task_loop.cancel()

    @tasks.loop(minutes=1)
    async def _task_loop(self):
        """
        Roda a cada minuto para checar se chegou a hora de executar a verificação
        com base no cooldown_minutos configurado.
        """
        config = _carregar_config()

        if not config.get("ativado", False):
            return

        cooldown = max(1, int(config.get("cooldown_minutos", 60)))

        # Controle simples de tempo: usa um contador interno
        self._next_run_in -= 1
        if self._next_run_in > 0:
            return
        self._next_run_in = cooldown  # reseta para o próximo ciclo

        await self._executar_verificacao(config)

    @_task_loop.before_loop
    async def _before_task(self):
        await self.bot.wait_until_ready()
        # Primeira execução imediata ao iniciar
        config = _carregar_config()
        self._next_run_in = max(1, int(config.get("cooldown_minutos", 60)))

    async def _executar_verificacao(self, config: dict):
        """Varre todos os membros do servidor e verifica tag/bio."""
        cargo_id    = config.get("cargo_id")
        tag_ativo   = config.get("tag_ativo", False)
        bio_ativo   = config.get("bio_ativo", False)
        tag_texto   = config.get("tag_texto") or ""
        bio_texto   = config.get("bio_texto") or ""
        logs_pub_id = config.get("canal_logs_publico_id")
        logs_prv_id = config.get("canal_logs_privado_id")

        if not cargo_id:
            return

        if not tag_ativo and not bio_ativo:
            return

        # Pegar o guild (único servidor)
        guild: Optional[disnake.Guild] = None
        for g in self.bot.guilds:
            guild = g
            break

        if not guild:
            return

        role = guild.get_role(int(cargo_id))
        if not role:
            return

        canal_pub = await _get_canal(self.bot, logs_pub_id)
        canal_prv = await _get_canal(self.bot, logs_prv_id)

        ph_raw   = (db.get_document("custom_colors") or {}).get("primary", "#5865F2")
        cor_ok   = disnake.Colour(int(ph_raw.replace("#", ""), 16))
        cor_err  = disnake.Colour(int(
            (db.get_document("custom_colors") or {}).get("danger", "#dc3545").replace("#", ""), 16
        ))

        try:
            members = await guild.fetch_members(limit=None).flatten()
        except Exception as e:
            log.error(f"[TagBio Task] Erro ao buscar membros: {e}")
            return

        for member in members:
            if member.bot:
                continue

            tem_cargo  = role in member.roles
            tag_ok     = True
            bio_ok     = True

            if tag_ativo and tag_texto:
                tag_ok = _check_tag(member, tag_texto)

            if bio_ativo and bio_texto:
                bio_ok = await _check_bio(member.id, bio_texto)
                # Pequeno delay para não sobrecarregar a API
                await asyncio.sleep(0.3)

            passou = tag_ok and bio_ok

            if tem_cargo and not passou:
                # Remover cargo
                try:
                    await member.remove_roles(role, reason="TagBio: verificação falhou")
                except disnake.Forbidden:
                    log.warning(f"[TagBio Task] Sem permissão para remover cargo de {member.id}")
                    continue

                motivo_parts = []
                if tag_ativo and not tag_ok:
                    motivo_parts.append(f"tag `{tag_texto}` não encontrada")
                if bio_ativo and not bio_ok:
                    motivo_parts.append(f"bio `{bio_texto}` não encontrada")
                motivo = " | ".join(motivo_parts)

                # Log privado (detalhado)
                await _send_log(
                    canal_prv,
                    f"🔴 Cargo removido — {member.display_name}",
                    f"{member.mention} (`{member.id}`) **perdeu** o cargo {role.mention}.\n**Motivo:** {motivo}",
                    cor_err,
                )
                # Log público
                await _send_log(
                    canal_pub,
                    f"🔴 {member.display_name} perdeu o cargo",
                    f"{member.mention} perdeu o cargo {role.mention} pois não atende mais os requisitos.",
                    cor_err,
                )

            elif not tem_cargo and passou:
                # Adicionar cargo
                try:
                    await member.add_roles(role, reason="TagBio: verificação aprovada (task)")
                except disnake.Forbidden:
                    log.warning(f"[TagBio Task] Sem permissão para adicionar cargo a {member.id}")
                    continue

                # Log privado (detalhado)
                await _send_log(
                    canal_prv,
                    f"🟢 Cargo concedido — {member.display_name}",
                    f"{member.mention} (`{member.id}`) **recebeu** o cargo {role.mention} pela task automática.",
                    cor_ok,
                )
                # Nota: a task NÃO gera log público para quem GANHOU — só o botão gera.

            # Pequeno delay entre membros para não travar o event loop
            await asyncio.sleep(0.05)


def setup(bot: commands.Bot):
    bot.add_cog(TagBioTask(bot))
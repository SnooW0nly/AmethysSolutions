"""
tasks/utilitarios/tsk_familia.py

Task do Sistema de Família:
  - on_voice_state_update → rastreia tempo na call da família
  - loop 5 min           → flush de sessões ativas
  - loop 10 min          → atualiza mensagem de rank no canal configurado
  - loop 1 hora          → verifica inatividade e deleta famílias inativas
"""
from __future__ import annotations

import time
from datetime import datetime

import disnake
from disnake.ext import commands, tasks

from modules.utilitarios.comunidade.familia import helpers
from modules.utilitarios.comunidade.familia.helpers import (
    load_json, save_json, FAMILIAS_JSON, VOICE_JSON,
    accent, color, _mode, _primary_hex,
)
from modules.utilitarios.comunidade.familia.cog import _deletar_familia_completa


class FamiliaTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._rank_ticks = 0
        self._flush_and_rank_task.start()
        self._inatividade_task.start()

    def cog_unload(self):
        self._flush_and_rank_task.cancel()
        self._inatividade_task.cancel()

    # ── Reabre sessões ao reiniciar ───────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        """Reativa sessões para membros já em call ao reiniciar o bot."""
        familias = helpers.get_all_familias()
        for guild in self.bot.guilds:
            for fid, fdata in familias.items():
                voz_id = fdata.get("canal_voz_id")
                if not voz_id:
                    continue
                canal = guild.get_channel(int(voz_id))
                if not isinstance(canal, disnake.VoiceChannel):
                    continue
                for member in canal.members:
                    if member.bot:
                        continue
                    if member.id in fdata.get("membros", []):
                        helpers.open_voice_session(fid, member.id)

    # ── Voice state tracking ──────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after:  disnake.VoiceState,
    ):
        if member.bot:
            return

        fid, fdata = helpers.get_familia_by_membro(member.id)
        if not fdata:
            return

        voz_id = fdata.get("canal_voz_id")
        if not voz_id:
            return

        saiu_da_call   = before.channel and before.channel.id == voz_id and (
            not after.channel or after.channel.id != voz_id
        )
        entrou_na_call = after.channel and after.channel.id == voz_id and (
            not before.channel or before.channel.id != voz_id
        )

        if saiu_da_call:
            elapsed = helpers.close_voice_session(fid, member.id)
            if elapsed > 0:
                await helpers.enviar_log(
                    self.bot,
                    "Saiu da Call da Família",
                    f"{member.mention} saiu da call de **{fdata['nome']}** "
                    f"após {helpers.formatar_tempo(elapsed)}.",
                )

        if entrou_na_call:
            helpers.open_voice_session(fid, member.id)
            helpers.update_ultima_atividade(fid)
            await helpers.enviar_log(
                self.bot,
                "Entrou na Call da Família",
                f"{member.mention} entrou na call de **{fdata['nome']}**.",
            )

    # ── Loop 5 min: flush + rank update ──────────────────────────────────────

    @tasks.loop(minutes=5)
    async def _flush_and_rank_task(self):
        # 1. Flush sessões ativas (acumula tempo parcial sem fechar)
        voice    = load_json(VOICE_JSON)
        familias = helpers.get_all_familias()

        for fid, sessions in list(voice.items()):
            for uid_str in list(sessions.keys()):
                try:
                    uid    = int(uid_str)
                    guild  = self._get_guild_for_familia(fid, familias)
                    member = guild.get_member(uid) if guild else None
                    fdata  = familias.get(fid, {})
                    voz_id = fdata.get("canal_voz_id")

                    # Se não está mais na call → fechar sessão
                    if not member or not member.voice or (
                        voz_id and member.voice.channel and member.voice.channel.id != int(voz_id)
                    ) or (not member.voice.channel):
                        helpers.close_voice_session(fid, uid)
                    else:
                        helpers.flush_voice_session(fid, uid)
                except Exception:
                    pass

        # 2. Verificar se deve atualizar o rank (a cada 2 ticks = 10 min)
        self._rank_ticks += 1
        if self._rank_ticks >= 2:
            self._rank_ticks = 0
            await self._atualizar_rank()

    @_flush_and_rank_task.before_loop
    async def _before_flush(self):
        await self.bot.wait_until_ready()

    # ── Loop 1 hora: inatividade ──────────────────────────────────────────────

    @tasks.loop(hours=1)
    async def _inatividade_task(self):
        config = helpers.carregar_config()
        dias   = config.get("inatividade_dias", 0)
        if not dias:
            return

        limite_segundos = dias * 86400
        familias        = helpers.get_all_familias()
        now             = datetime.now()

        for fid, fdata in list(familias.items()):
            ultima = fdata.get("ultima_atividade")
            if not ultima:
                continue
            try:
                dt_ultima = datetime.fromisoformat(ultima)
                if (now - dt_ultima).total_seconds() >= limite_segundos:
                    guild = self._get_guild_for_familia(fid, familias)
                    if guild:
                        await _deletar_familia_completa(
                            self.bot, guild, fid, fdata,
                            motivo=f"Inatividade superior a {dias} dia(s)",
                        )
            except Exception:
                pass

    @_inatividade_task.before_loop
    async def _before_inatividade(self):
        await self.bot.wait_until_ready()

    # ── Rank ──────────────────────────────────────────────────────────────────

    async def _atualizar_rank(self):
        config  = helpers.carregar_config()
        rank_id = config.get("canal_rank_id")
        if not rank_id:
            return

        canal = self.bot.get_channel(int(rank_id))
        if not isinstance(canal, disnake.TextChannel):
            return

        familias  = helpers.get_all_familias()
        rank_txt  = helpers.build_rank_text(familias)
        mode      = _mode()
        ph        = _primary_hex()
        msg_id    = config.get("rank_message_id")
        timestamp = f"-# Atualizado em <t:{int(time.time())}:R>"

        try:
            if mode == "embed":
                emb = disnake.Embed(
                    title="🏆 Ranking de Famílias",
                    description=f"{rank_txt}\n\n{timestamp}",
                    color=color() or disnake.Colour.gold(),
                )
                if msg_id:
                    try:
                        msg = await canal.fetch_message(int(msg_id))
                        await msg.edit(embed=emb, components=[])
                        return
                    except (disnake.NotFound, disnake.HTTPException):
                        pass
                new_msg = await canal.send(embed=emb)
            else:
                kw       = accent(ph)
                comps    = [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# 🏆 Ranking de Famílias\n{rank_txt}\n\n{timestamp}"
                        ),
                        **kw,
                    )
                ]
                if msg_id:
                    try:
                        msg = await canal.fetch_message(int(msg_id))
                        await msg.edit(
                            components=comps,
                            flags=disnake.MessageFlags(is_components_v2=True),
                        )
                        return
                    except (disnake.NotFound, disnake.HTTPException):
                        pass
                new_msg = await canal.send(
                    components=comps,
                    flags=disnake.MessageFlags(is_components_v2=True),
                )

            # Salvar ID da nova mensagem
            config2 = helpers.carregar_config()
            config2["rank_message_id"] = str(new_msg.id)
            helpers.salvar_config(config2)

        except Exception:
            pass

    # ── Helper: descobrir guild de uma família ────────────────────────────────

    def _get_guild_for_familia(self, fid: str, familias: dict) -> disnake.Guild | None:
        fdata  = familias.get(fid, {})
        voz_id = fdata.get("canal_voz_id")
        cat_id = fdata.get("categoria_id")

        for guild in self.bot.guilds:
            if voz_id and guild.get_channel(int(voz_id)):
                return guild
            if cat_id and guild.get_channel(int(cat_id)):
                return guild
        return None


def setup(bot: commands.Bot):
    bot.add_cog(FamiliaTasks(bot))
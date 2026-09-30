from __future__ import annotations

import time

import disnake
from disnake.ext import commands, tasks

from modules.automations.temp_em_call import helpers


class TempCallTaskCog(commands.Cog):
    """
    Core do sistema Temp em Call:
      - Rastreia tempo de voz de cada membro
      - Concede cargos conforme thresholds configurados
      - Atualiza o ranking periodicamente
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        helpers.get_all_voice_data()  # garante que o arquivo exista
        self._update_sessions_task.start()
        self._update_ranking_task.start()
        self._cleanup_stale_task.start()

    def cog_unload(self):
        self._update_sessions_task.cancel()
        self._update_ranking_task.cancel()
        self._cleanup_stale_task.cancel()

    # ─── Reabrir sessões após restart ────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        cfg = helpers.carregar_config()
        if not cfg.get("ativado", False):
            return

        now      = time.time()
        all_data = helpers.get_all_voice_data()

        for guild in self.bot.guilds:
            gid = str(guild.id)
            all_data.setdefault(gid, {})
            for channel in guild.voice_channels:
                if not helpers.canal_valido(channel, cfg):
                    continue
                for member in channel.members:
                    if member.bot:
                        continue
                    uid   = str(member.id)
                    udata = all_data[gid].setdefault(uid, {
                        "total_seconds":  0,
                        "last_join":      None,
                        "assigned_roles": [],
                    })
                    if udata["last_join"] is None:
                        udata["last_join"] = now

        helpers.save_all_voice(all_data)

    # ─── on_voice_state_update ────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member:  disnake.Member,
        before:  disnake.VoiceState,
        after:   disnake.VoiceState,
    ):
        if member.bot:
            return

        cfg = helpers.carregar_config()
        if not cfg.get("ativado", False):
            return

        all_data = helpers.get_all_voice_data()
        gid  = str(member.guild.id)
        uid  = str(member.id)
        all_data.setdefault(gid, {})
        udata = all_data[gid].setdefault(uid, {
            "total_seconds":  0,
            "last_join":      None,
            "assigned_roles": [],
        })

        saiu    = before.channel and (not after.channel or before.channel.id != after.channel.id)
        entrou  = after.channel  and (not before.channel or before.channel.id != after.channel.id)
        # Mudança de estado sem trocar de canal (mute/deaf)
        mesmo_canal = (
            before.channel and after.channel
            and before.channel.id == after.channel.id
        )

        # ── Saiu de canal ────────────────────────────────────────────────────
        if saiu:
            helpers.close_session(udata)

        # ── Entrou em canal ──────────────────────────────────────────────────
        if entrou:
            if helpers.canal_valido(after.channel, cfg):
                if helpers.membro_deve_contar(member, after, cfg):
                    helpers.open_session(udata)
                else:
                    udata["last_join"] = None
            else:
                udata["last_join"] = None

        # ── Mesmo canal, mudança de mute/deaf ────────────────────────────────
        if mesmo_canal and not saiu and not entrou:
            deve_contar = helpers.membro_deve_contar(member, after, cfg)
            if not deve_contar and udata["last_join"] is not None:
                # Ficou muted/deafened e config manda parar de contar
                helpers.close_session(udata)
            elif deve_contar and udata["last_join"] is None:
                # Desmutou, volta a contar
                if after.channel and helpers.canal_valido(after.channel, cfg):
                    helpers.open_session(udata)

        helpers.save_all_voice(all_data)

        # Verificar cargos após qualquer update
        await self._check_and_assign_roles(member, udata, cfg)

    # ─── Verificação e concessão de cargos ──────────────────────────────────

    async def _check_and_assign_roles(
        self,
        member:    disnake.Member,
        user_data: dict,
        cfg:       dict,
    ) -> None:
        if member.bot:
            return

        total    = user_data.get("total_seconds", 0)
        assigned = user_data.setdefault("assigned_roles", [])
        changed  = False

        for threshold in helpers.get_sorted_thresholds(cfg):
            cargo_id = threshold.get("cargo_id")
            segundos = threshold.get("segundos", 0)
            if not cargo_id or not segundos:
                continue
            cargo_id = int(cargo_id)

            if total >= segundos and cargo_id not in assigned:
                role = member.guild.get_role(cargo_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="TempCall: threshold atingido")
                        assigned.append(cargo_id)
                        changed = True
                        await helpers.enviar_log_cargo(
                            self.bot, member.guild, member, role, threshold, cfg
                        )
                    except disnake.HTTPException:
                        pass

        if changed:
            all_data = helpers.get_all_voice_data()
            gid, uid = str(member.guild.id), str(member.id)
            if gid in all_data and uid in all_data[gid]:
                all_data[gid][uid]["assigned_roles"] = assigned
                helpers.save_all_voice(all_data)

    # ─── Task: atualizar sessões ativas (acumular parcial) ───────────────────

    @tasks.loop(minutes=5)
    async def _update_sessions_task(self):
        cfg = helpers.carregar_config()
        if not cfg.get("ativado", False):
            return

        all_data = helpers.get_all_voice_data()
        changed  = False

        for guild in self.bot.guilds:
            gid = str(guild.id)
            if gid not in all_data:
                continue
            for uid, udata in all_data[gid].items():
                if udata.get("last_join") is None:
                    continue
                member = guild.get_member(int(uid))
                if not member:
                    continue
                # Verificar se ainda está em canal válido
                if not member.voice or not member.voice.channel:
                    helpers.close_session(udata)
                    changed = True
                    continue
                if not helpers.canal_valido(member.voice.channel, cfg):
                    helpers.close_session(udata)
                    changed = True
                    continue
                # Acumula parcial e continua
                helpers.update_session(udata)
                changed = True
                await self._check_and_assign_roles(member, udata, cfg)

        if changed:
            helpers.save_all_voice(all_data)

    @_update_sessions_task.before_loop
    async def _before_update(self):
        await self.bot.wait_until_ready()

    # ─── Task: atualizar ranking ─────────────────────────────────────────────

    @tasks.loop(minutes=1)
    async def _update_ranking_task(self):
        cfg = helpers.carregar_config()
        if not cfg.get("ativado", False):
            return
        if not cfg.get("canal_ranking_id"):
            return

        # Respeita intervalo configurado (verifica no loop de 1 min)
        intervalo = max(1, int(cfg.get("ranking_intervalo_minutos", 5)))
        # Usa um contador simples via atributo do cog
        self._ranking_ticks = getattr(self, "_ranking_ticks", 0) + 1
        if self._ranking_ticks < intervalo:
            return
        self._ranking_ticks = 0

        for guild in self.bot.guilds:
            await helpers.enviar_ou_editar_ranking(self.bot, guild, cfg)

    @_update_ranking_task.before_loop
    async def _before_ranking(self):
        await self.bot.wait_until_ready()

    # ─── Task: cleanup de sessões quebradas (> 8h abertas) ───────────────────

    @tasks.loop(minutes=10)
    async def _cleanup_stale_task(self):
        cfg     = helpers.carregar_config()
        now     = time.time()
        all_data = helpers.get_all_voice_data()
        changed  = False

        for guild in self.bot.guilds:
            gid = str(guild.id)
            if gid not in all_data:
                continue
            for uid, udata in all_data[gid].items():
                last = udata.get("last_join")
                if last is None:
                    continue
                member = guild.get_member(int(uid))
                # Se membro não está em nenhum canal de voz, fecha sessão
                if not member or not member.voice or not member.voice.channel:
                    helpers.close_session(udata)
                    changed = True
                    continue
                # Sessão absurdamente longa (> 8h) → acumula parcial e continua
                if now - last > 8 * 3600:
                    helpers.update_session(udata)
                    changed = True
                    if member and cfg.get("ativado", False):
                        await self._check_and_assign_roles(member, udata, cfg)

        if changed:
            helpers.save_all_voice(all_data)

    @_cleanup_stale_task.before_loop
    async def _before_cleanup(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(TempCallTaskCog(bot))
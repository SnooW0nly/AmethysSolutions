"""
Task do sistema de afiliados.
Responsável por:
  - Rastrear convites e registrar relações afiliado → convidado
  - Enviar notificações de DM de comissão de forma assíncrona e segura
"""
import asyncio

import disnake
from disnake.ext import commands, tasks

from functions.database import database as db
from functions.emoji import emoji
from modules.loja.afiliados import helpers


class AfiliadosTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cache local de convites por guild_id
        self._invites: dict[int, list[disnake.Invite]] = {}

    # ──────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        await self.bot.wait_until_ready()
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return
        for guild in self.bot.guilds:
            await self._cache_guild_invites(guild)

        if not self._notificacoes_task.is_running():
            self._notificacoes_task.start()

    def cog_unload(self):
        self._notificacoes_task.cancel()

    # ──────────────────────────────────────────────────────
    # Cache de convites
    # ──────────────────────────────────────────────────────

    async def _cache_guild_invites(self, guild: disnake.Guild) -> None:
        try:
            self._invites[guild.id] = await guild.invites()
        except (disnake.Forbidden, disnake.HTTPException):
            self._invites[guild.id] = []

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: disnake.Guild):
        await self._cache_guild_invites(guild)

    @commands.Cog.listener("on_guild_remove")
    async def on_guild_remove(self, guild: disnake.Guild):
        self._invites.pop(guild.id, None)

    @commands.Cog.listener("on_invite_create")
    async def on_invite_create(self, invite: disnake.Invite):
        guild_id = getattr(invite.guild, "id", None)
        if guild_id and guild_id in self._invites:
            # Evitar duplicatas
            if not any(i.code == invite.code for i in self._invites[guild_id]):
                self._invites[guild_id].append(invite)

    @commands.Cog.listener("on_invite_delete")
    async def on_invite_delete(self, invite: disnake.Invite):
        guild_id = getattr(invite.guild, "id", None)
        if guild_id and guild_id in self._invites:
            self._invites[guild_id] = [
                i for i in self._invites[guild_id] if i.code != invite.code
            ]

    # ──────────────────────────────────────────────────────
    # Rastreamento de entrada/saída
    # ──────────────────────────────────────────────────────

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: disnake.Member):
        if member.bot:
            return

        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return

        try:
            old_invites = self._invites.get(member.guild.id, [])
            try:
                new_invites = await member.guild.invites()
            except (disnake.Forbidden, disnake.HTTPException):
                return

            self._invites[member.guild.id] = new_invites

            # Descobrir qual convite foi usado comparando os usos
            inviter_id: str | None = None
            for invite in new_invites:
                old = next((i for i in old_invites if i.code == invite.code), None)
                if old and invite.uses > old.uses:
                    if invite.inviter:
                        inviter_id = str(invite.inviter.id)
                    break

            if inviter_id:
                helpers.registrar_entrada(str(member.id), inviter_id)

        except Exception as e:
            print(f"[Afiliados] Erro ao processar entrada de {member}: {e}")

    @commands.Cog.listener("on_member_remove")
    async def on_member_remove(self, member: disnake.Member):
        """
        Mantém a relação ao sair.
        Se entrar novamente via outro convite, registrar_entrada irá atualizar.
        """
        pass

    # ──────────────────────────────────────────────────────
    # Task: enviar notificações DM de comissão
    # ──────────────────────────────────────────────────────

    @tasks.loop(seconds=30)
    async def _notificacoes_task(self):
        pending = helpers.pop_pending_notifications()
        if not pending:
            return

        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_hex = colors.get("primary")
        color = None
        if primary_hex:
            try:
                color = int(primary_hex.replace("#", ""), 16)
            except Exception:
                pass

        for notif in pending:
            try:
                user_id = notif.get("user_id")
                comissao = float(notif.get("comissao", 0))
                produto = notif.get("produto", "Produto")

                if not user_id or comissao <= 0:
                    continue

                # Verificar se notificações ainda estão ativas (usuário pode ter desativado)
                membro = helpers.get_membro(user_id)
                if not membro.get("notificar_dm", True):
                    continue

                try:
                    user = await self.bot.fetch_user(int(user_id))
                except (disnake.NotFound, disnake.HTTPException):
                    continue

                texto = (
                    f"💰 **Comissão de afiliado recebida!**\n\n"
                    f"Um membro que você convidou realizou uma compra.\n"
                    f"**Produto:** {produto}\n"
                    f"**Comissão recebida:** `R$ {comissao:.2f}`\n"
                    f"**Saldo atual:** `R$ {membro.get('saldo', 0.0):.2f}`\n\n"
                    f"-# Use `/afiliados` para ver seu saldo e solicitar saque."
                )

                try:
                    if mode == "embed":
                        embed = disnake.Embed(
                            title=f"{emoji.correct} Comissão de Afiliado!",
                            description=texto,
                            color=color or disnake.Color.green()
                        )
                        await user.send(embed=embed)
                    else:
                        container_kwargs = {}
                        if color:
                            container_kwargs["accent_colour"] = disnake.Colour(color)
                        await user.send(
                            components=[
                                disnake.ui.Container(
                                    disnake.ui.TextDisplay(texto),
                                    **container_kwargs
                                )
                            ],
                            flags=disnake.MessageFlags(is_components_v2=True)
                        )
                except disnake.Forbidden:
                    pass  # Usuário com DMs fechadas

                # Pequena pausa para evitar rate limit de DMs
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"[Afiliados] Erro ao enviar notificação: {e}")

    @_notificacoes_task.before_loop
    async def _before_notificacoes(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(AfiliadosTask(bot))
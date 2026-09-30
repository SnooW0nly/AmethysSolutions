import disnake
from disnake.ext import commands
from modules.automations.invite_tracker import helpers

class InviteTrackerTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except disnake.Forbidden:
                pass

    @commands.Cog.listener("on_guild_join")
    async def on_guild_join(self, guild: disnake.Guild):
        try:
            self.invites[guild.id] = await guild.invites()
        except disnake.Forbidden:
            pass

    @commands.Cog.listener("on_guild_remove")
    async def on_guild_remove(self, guild: disnake.Guild):
        if guild.id in self.invites:
            del self.invites[guild.id]

    @commands.Cog.listener("on_invite_create")
    async def on_invite_create(self, invite: disnake.Invite):
        if invite.guild.id in self.invites:
            self.invites[invite.guild.id].append(invite)

    @commands.Cog.listener("on_invite_delete")
    async def on_invite_delete(self, invite: disnake.Invite):
        if invite.guild.id in self.invites:
            self.invites[invite.guild.id] = [i for i in self.invites[invite.guild.id] if i.code != invite.code]

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: disnake.Member):
        # Ignorar bots - não contar como convite nem enviar mensagem
        if member.bot:
            return
        
        try:
            old_invites = self.invites.get(member.guild.id, [])
            new_invites = await member.guild.invites()
            self.invites[member.guild.id] = new_invites
        except disnake.Forbidden:
            return

        inviter = None
        used_invite = None
        is_vanity_url = False
        
        for invite in new_invites:
            found = next((i for i in old_invites if i.code == invite.code), None)
            if found and invite.uses > found.uses:
                inviter = invite.inviter
                used_invite = invite
                break

        # Se não encontrou nenhum invite usado, provavelmente entrou via Vanity URL
        # Se encontrou invite mas inviter é None, é um convite criado por usuário que saiu do servidor
        if not used_invite:
            is_vanity_url = True
            inviter_id_str = "Vanity Url"
        elif inviter is None:
            # Convite criado por usuário que não está mais no servidor
            # Não rastrear estatísticas, mas tratar como convite normal (não Vanity URL)
            inviter_id_str = None
            is_vanity_url = False
        else:
            inviter_id_str = str(inviter.id)
            is_vanity_url = False

        # Atualizar dados de convites apenas se temos um inviter válido ou é Vanity URL
        if inviter_id_str:
            invites_data = helpers.get_invites_data()
            guild_id_str = str(member.guild.id)
            member_id_str = str(member.id)

            if guild_id_str not in invites_data:
                invites_data[guild_id_str] = {"invites": {}, "members": {}}
            
            if inviter_id_str not in invites_data[guild_id_str]["invites"]:
                invites_data[guild_id_str]["invites"][inviter_id_str] = {"total": 0, "valid": 0, "fake": 0, "bonus": 0, "left": 0}

            inviter_data = invites_data[guild_id_str]["invites"][inviter_id_str]
            inviter_data["total"] += 1
            inviter_data["valid"] += 1
            
            invites_data[guild_id_str]["members"][member_id_str] = {
                "inviter": inviter_id_str,
                "code": used_invite.code if used_invite else "vanity_url"
            }
            helpers.save_invites_data(invites_data)
        else:
            # Convite criado por usuário que não está mais no servidor - não rastrear
            inviter_data = None

        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return

        channel_id = config.get("channel_id")
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        # Usar mensagem específica para Vanity URL ou mensagem normal
        if is_vanity_url:
            welcome_message = config.get("welcome_message_vanity", "")
            # Se não houver mensagem de vanity, usar a mensagem normal como fallback
            if not welcome_message:
                welcome_message = config.get("welcome_message", "")
            inviter_mention = "Vanity Url"
            inviter_name = "Vanity Url"
            entry_mode = "Vanity Url"
            # Para Vanity URL, mostrar o total de entradas (total) ao invés de valid
            total_invites = inviter_data["total"] if inviter_data else 0
        else:
            welcome_message = config.get("welcome_message", "")
            if inviter is None:
                # Convite criado por usuário que não está mais no servidor
                inviter_mention = "Usuário Desconhecido"
                inviter_name = "Usuário Desconhecido"
                total_invites = 0
            else:
                inviter_mention = inviter.mention
                inviter_name = inviter.display_name
                total_invites = inviter_data["valid"] if inviter_data else 0
            entry_mode = "Convite"
        
        # Se a mensagem estiver vazia, não enviar
        if not welcome_message or not welcome_message.strip():
            return
        
        try:
            message = welcome_message.format(
                member=member.mention,
                membername=member.display_name,
                inviter=inviter_mention,
                invitername=inviter_name,
                invites=total_invites,
                entry_mode=entry_mode
            )
        except KeyError:
            # Fallback para mensagens antigas que não usam todas as variáveis
            message = welcome_message.format(
                member=member.mention,
                membername=member.display_name
            )
        
        await channel.send(message)

        # ── Points Tracker: verificar recompensas disponíveis ─────────────────
        try:
            pt = helpers.get_points_config()
            if pt.get("ativado"):
                valid_after = helpers.get_member_invites_valid(str(member.guild.id), inviter_id_str) if inviter_id_str and inviter_id_str != "Vanity Url" else 0
                recompensas = pt.get("recompensas", [])
                novas = [r for r in recompensas if r["invites"] == valid_after]
                pt_channel_id = pt.get("channel_id")
                pt_channel = self.bot.get_channel(pt_channel_id) if pt_channel_id else None
                if novas and pt_channel and inviter:
                    nomes = ", ".join(f"**{r['nome']}**" for r in novas)
                    await pt_channel.send(
                        f"🎉 {inviter.mention} atingiu `{valid_after}` convites válidos e desbloqueou: {nomes}! Vá ao painel para resgatar.",
                        allowed_mentions=disnake.AllowedMentions(users=True),
                    )
        except Exception:
            pass


    @commands.Cog.listener("on_member_remove")
    async def on_member_remove(self, member: disnake.Member):
        # Ignorar bots - não enviar mensagem de saída
        if member.bot:
            return
        
        invites_data = helpers.get_invites_data()
        guild_id_str = str(member.guild.id)
        member_id_str = str(member.id)
        inviter_id_str = None
        inviter_data = None

        if guild_id_str in invites_data and member_id_str in invites_data[guild_id_str].get("members", {}):
            member_data = invites_data[guild_id_str]["members"].pop(member_id_str)
            if isinstance(member_data, dict):
                inviter_id_str = member_data.get("inviter")
            elif isinstance(member_data, str):
                inviter_id_str = member_data
            
            if inviter_id_str and inviter_id_str in invites_data[guild_id_str].get("invites", {}):
                inviter_data = invites_data[guild_id_str]["invites"][inviter_id_str]
                inviter_data["valid"] -= 1
                inviter_data["left"] += 1
            
            helpers.save_invites_data(invites_data)

        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return

        channel_id = config.get("channel_id")
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        leave_message = config.get("leave_message", "")
        
        # Se a mensagem estiver vazia, não enviar
        if not leave_message or not leave_message.strip():
            return
        
        message_to_send = ""
        
        inviter = None
        is_vanity_url = inviter_id_str == "Vanity Url"
        
        # Tentar buscar o usuário se não for Vanity URL
        if inviter_id_str and not is_vanity_url:
            try:
                inviter = await self.bot.fetch_user(int(inviter_id_str))
            except (disnake.NotFound, ValueError):
                pass

        try:
            if is_vanity_url:
                inviter_mention = "Vanity Url"
                inviter_name = "Vanity Url"
                entry_mode = "Vanity Url"
                # Para Vanity URL, mostrar o total de entradas (total) ao invés de valid
                vanity_invites = inviter_data.get("total", 0) if inviter_data else 0
            else:
                inviter_mention = inviter.mention if inviter else "Usuário Desconhecido"
                inviter_name = inviter.display_name if inviter else "Usuário Desconhecido"
                entry_mode = "Convite"
                vanity_invites = inviter_data.get("valid", 0) if inviter_data else 0
            
            format_args = {
                "member": member.mention,
                "membername": member.display_name,
                "inviter": inviter_mention,
                "invitername": inviter_name,
                "invites": vanity_invites,
                "entry_mode": entry_mode
            }
            message_to_send = leave_message.format(**format_args)
        except KeyError:
            # Fallback for old message formats that don't use all the new variables
            message_to_send = leave_message.format(
                member=member.mention,
                membername=member.display_name
            )

        if message_to_send:
            await channel.send(message_to_send)

def setup(bot: commands.Bot):
    bot.add_cog(InviteTrackerTask(bot))

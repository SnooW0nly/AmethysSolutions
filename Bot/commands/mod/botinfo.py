import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.utils import utils

class BotInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot:
            return

        is_mention = self.bot.user in message.mentions
        contains_name = "amethys" in message.content.lower()

        if message.reference and message.reference.resolved and message.reference.resolved.author == self.bot.user:
            is_explicit_mention = f'<@{self.bot.user.id}>' in message.content or f'<@!{self.bot.user.id}>' in message.content
            if not is_explicit_mention:
                is_mention = False

        if is_mention:
            if not message.guild or message.guild.id != utils.obter_server_principal():
                return

            config = db.obter("config.json")
            mode_data = db.get_document("custom_mode")
            color_data = db.get_document("custom_colors")

            mode = mode_data.get("mode", "components")
            primary_color_hex = color_data.get("primary")

            info_text_list = [
                f"{emoji.chevron} **Bot desenvolvido pela [Amethys](https://amethys.solutions)**",
                f"{emoji.robot} **Versão:** `{config['version']}`",
                f"{emoji.location} **Exclusivo para o servidor `{message.guild.name}`**",
                f"{emoji.thunder} **Tempo de resposta:** `{round(self.bot.latency * 1000)}ms`",
            ]

            buttons = disnake.ui.ActionRow(
                disnake.ui.Button(label="Dashboard", url=f"https://amethys.solutions"),
                disnake.ui.Button(label="Servidor de Suporte", url=f"https://amethys.solutions/socials/discord"),
            )
            
            badge_button = disnake.ui.ActionRow(
                disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, custom_id="botinfo_delete", disabled=True),
            )

            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title=f"Informações do bot",
                    description="\n".join(info_text_list),
                    **embed_kwargs,
                    # timestamp=disnake.utils.utcnow()
                )
                # embed.set_footer(text=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                
                await message.reply(embed=embed, components=[buttons, badge_button], delete_after=30)
            
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Informações do sistema**"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay("\n".join(info_text_list)),
                    disnake.ui.Separator(),
                    buttons,
                    **container_kwargs
                )
                
                await message.reply(components=[container, badge_button], flags=disnake.MessageFlags(is_components_v2=True), delete_after=30)

        elif contains_name:
            if not message.guild or message.guild.id != utils.obter_server_principal():
                return
            
            try:
                await message.add_reaction(emoji.amethys)
            except disnake.HTTPException:
                pass

def setup(bot):
    bot.add_cog(BotInfo(bot))
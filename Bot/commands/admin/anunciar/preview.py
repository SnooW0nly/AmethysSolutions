import disnake
from disnake.ext import commands
from .builder import Builder


class Preview(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_Visualizar":
            # Defer primeiro para ganhar tempo durante o build (pode ter download de imagem)
            await inter.response.defer(ephemeral=True)

            built = await Builder.build()

            if built["mode"] == "v2":
                await inter.followup.send(
                    components=built["components"],
                    flags=built["flags"],
                    ephemeral=True,
                    allowed_mentions=disnake.AllowedMentions.none(),
                )
            else:
                kwargs = {"ephemeral": True, "allowed_mentions": disnake.AllowedMentions.none()}
                if built.get("content") is not None:
                    kwargs["content"] = built["content"]
                if built.get("embed") is not None:
                    kwargs["embed"] = built["embed"]
                if built.get("components"):
                    kwargs["components"] = built["components"]
                if built.get("files"):
                    kwargs["files"] = built["files"]
                await inter.followup.send(**kwargs)


def setup(bot: commands.Bot):
    bot.add_cog(Preview(bot))

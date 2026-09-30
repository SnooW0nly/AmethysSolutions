"""
Sender: envia o painel de resgate de gifts para um canal.
"""
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class GiftSender:

    @staticmethod
    def painel_enviar(inter) -> dict:
        mode    = db.get_document("custom_mode").get("mode")
        primary = (db.get_document("custom_colors") or {}).get("primary")

        if mode == "embed":
            ekw = {"color": int(primary.replace("#", ""), 16)} if primary else {}
            return {
                "embed": disnake.Embed(
                    description="-# Painel > Loja > Gifts > **Enviar Painel**\n\nSelecione o canal onde o painel será publicado.",
                    **ekw,
                ),
                "components": [
                    disnake.ui.ActionRow(disnake.ui.ChannelSelect(
                        placeholder="Selecione o canal de destino",
                        custom_id="GiftSender_Canal",
                        channel_types=[disnake.ChannelType.text],
                        min_values=1, max_values=1,
                    )),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
                ],
            }

        ckw = {"accent_colour": disnake.Colour(int(primary.replace("#", ""), 16))} if primary else {}
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Gifts > **Enviar Painel**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Selecione o canal onde o painel de resgate de gifts será publicado."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal de destino",
                    custom_id="GiftSender_Canal",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1, max_values=1,
                )),
                **ckw,
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
        ]}

    @staticmethod
    async def enviar_para_canal(channel: disnake.TextChannel) -> disnake.Message:
        from .builder import build_gift_panel_message
        built = await build_gift_panel_message(include_button=True)
        if built["mode"] == "v2":
            return await channel.send(
                components=built["components"],
                flags=built["flags"],
                allowed_mentions=disnake.AllowedMentions.none(),
            )
        kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
        if built.get("content"):
            kwargs["content"] = built["content"]
        if built.get("embed"):
            kwargs["embed"] = built["embed"]
        if built.get("components"):
            kwargs["components"] = built["components"]
        return await channel.send(**kwargs)


class GiftSenderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "GiftSender_Canal":
            return

        mode        = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        channel = None
        try:
            channel = inter.guild.get_channel(int(inter.values[0])) or self.bot.get_channel(int(inter.values[0]))
        except Exception:
            pass

        if channel is None:
            await inter.followup.send(f"{emoji.wrong} Canal inválido.", ephemeral=True)
            return

        try:
            sent = await GiftSender.enviar_para_canal(channel)
        except Exception as e:
            await inter.followup.send(f"{emoji.wrong} Erro ao enviar: {e}", ephemeral=True)
            return

        from .cog import GiftsCog
        panel_data = GiftsCog.painel(inter)
        if "embed" in panel_data:
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))

        primary = (db.get_document("custom_colors") or {}).get("primary")
        ckw = {"accent_colour": disnake.Colour(int(primary.replace("#", ""), 16))} if primary else {}
        await inter.followup.send(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"✅ Painel enviado em {channel.mention} (`{sent.id}`)"),
                    **ckw,
                ),
                disnake.ui.ActionRow(disnake.ui.Button(label="Ir para a mensagem", url=sent.jump_url)),
            ],
            ephemeral=True,
            flags=disnake.MessageFlags(is_components_v2=True),
        )


def setup(bot: commands.Bot):
    bot.add_cog(GiftSenderCog(bot))
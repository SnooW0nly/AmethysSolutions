import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message
from functions.database import database
from .builder import Builder
from ..anunciar import Anunciar

SEND_MODE_LABELS = {
    "auto":      "Automático",
    "content":   "Só Texto",
    "embed":     "Embed",
    "container": "Container (v2)",
}

_SEND_MODE_OPTIONS = [
    disnake.SelectOption(
        label="Automático",
        value="auto",
        emoji=emoji.search,
        description="Detecta o melhor formato automaticamente.",
    ),
    disnake.SelectOption(
        label="Só Texto",
        value="content",
        emoji=emoji.message,
        description="Envia apenas o texto da mensagem.",
    ),
    disnake.SelectOption(
        label="Embed",
        value="embed",
        emoji=emoji.embed,
        description="Força o envio em modo embed.",
    ),
    disnake.SelectOption(
        label="Container (v2)",
        value="container",
        emoji=emoji.commands,
        description="Força o modo container/v2.",
    ),
]


def _get_current_send_mode() -> str:
    cfg = database.get_document("messages_anunciar") or {}
    return cfg.get("message", {}).get("send_mode", "auto")


def _build_post_panel(send_mode: str) -> list:
    mode_label = SEND_MODE_LABELS.get(send_mode, "Automático")
    opts_with_default = [
        disnake.SelectOption(
            label=o.label,
            value=o.value,
            emoji=o.emoji,
            description=o.description,
            default=o.value == send_mode,
        )
        for o in _SEND_MODE_OPTIONS
    ]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"-# Selecione o canal e o modo de envio da mensagem\n"
                f"-# Modo atual: **{mode_label}**"
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Modo de envio",
                    custom_id="Anunciar_PostarMensagem_ModoEnvio",
                    options=opts_with_default,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Anunciar_EnviarMensagem_Canal",
                    placeholder="Selecione o canal de destino",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Enviar a mensagem neste canal",
                    style=disnake.ButtonStyle.green,
                    custom_id="Anunciar_EnviarMensagem_EnviarNoCanal",
                    emoji=emoji.arrow,
                )
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Anunciar_PainelInicial")
        ),
    ]


async def _send_built(channel: disnake.TextChannel, built: dict) -> disnake.Message:
    """Envia a mensagem já construída para o canal."""
    if built["mode"] == "v2":
        kwargs_v2: dict = {
            "components": built["components"],
            "flags":      built["flags"],
            "allowed_mentions": disnake.AllowedMentions.none(),
        }
        if built.get("files"):
            kwargs_v2["files"] = built["files"]
        return await channel.send(**kwargs_v2)
    else:
        kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
        if built.get("content") is not None:
            kwargs["content"] = built["content"]
        if built.get("embed") is not None:
            kwargs["embed"] = built["embed"]
        if built.get("components"):
            kwargs["components"] = built["components"]
        if built.get("files"):
            kwargs["files"] = built["files"]
        return await channel.send(**kwargs)


class Enviar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    async def send_to_channel(channel: disnake.TextChannel) -> disnake.Message:
        built = await Builder.build()
        return await _send_built(channel, built)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Abrir painel de envio ──
        if cid == "Anunciar_PostarMensagem":
            tg_cfg = database.get_document("telegram_anunciar") or {}
            if tg_cfg.get("mode") == "telegram":
                return  # TelegramAnunciar cuida disso nesse modo
            send_mode = _get_current_send_mode()
            await inter.response.edit_message(components=_build_post_panel(send_mode))

        # ── Confirmar envio no canal atual ──
        elif cid == "Anunciar_EnviarMensagem_EnviarNoCanal":
            await inter.response.defer(with_message=False)
            channel: disnake.TextChannel = inter.channel
            try:
                # Constrói e envia em paralelo com o defer já feito
                built = await Builder.build()
                msg_sent = await _send_built(channel, built)
            except Exception as e:
                await message.error(inter, f"Erro ao enviar: {e}", send=False)
                return
            await inter.edit_original_message(components=Anunciar.create_buttons())
            await message.success(
                inter,
                f"Mensagem enviada com sucesso em {channel.mention} (`{msg_sent.id}`)",
                followup=True,
                component=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Ir para a mensagem", url=msg_sent.jump_url)
                    )
                ],
            )

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Alterar modo de envio ──
        if cid == "Anunciar_PostarMensagem_ModoEnvio":
            selected = inter.values[0] if inter.values else "auto"
            db       = database.get_document("messages_anunciar")
            db.get("message", {})["send_mode"] = selected
            database.save_document("messages_anunciar", {}, db)
            await inter.response.edit_message(components=_build_post_panel(selected))

        # ── Canal selecionado via ChannelSelect → enviar imediatamente ──
        elif cid == "Anunciar_EnviarMensagem_Canal":
            await inter.response.defer(with_message=False)
            selected = inter.values[0]
            channel: disnake.TextChannel | None = None
            if isinstance(selected, str):
                try:
                    channel = inter.guild.get_channel(int(selected)) or self.bot.get_channel(int(selected))
                except Exception:
                    channel = None
            else:
                channel = selected

            if channel is None or not hasattr(channel, "send"):
                await message.error(
                    inter,
                    "Não consegui acessar o canal selecionado. Tente novamente ou verifique permissões.",
                    followup=True,
                )
                return

            try:
                built    = await Builder.build()
                msg_sent = await _send_built(channel, built)
            except Exception as e:
                await message.error(inter, f"Erro ao enviar: {e}", send=False)
                return

            await inter.edit_original_message(components=Anunciar.create_buttons())
            await message.success(
                inter,
                f"Mensagem enviada com sucesso em {channel.mention} (`{msg_sent.id}`)",
                followup=True,
                component=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Ir para a mensagem", url=msg_sent.jump_url)
                    )
                ],
            )


def setup(bot: commands.Bot):
    bot.add_cog(Enviar(bot))
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

REDEEM_MODE_LABELS = {
    "painel":  "Painel",
    "comando": "Comando",
    "canal":   "Canal",
}

# Ciclo do toggle: Painel → Comando → Canal → Painel
REDEEM_MODE_CYCLE = {
    "painel":  "comando",
    "comando": "canal",
    "canal":   "painel",
}


def _container_kwargs():
    color_data = db.get_document("custom_colors")
    primary = color_data.get("primary")
    if primary:
        return {"accent_colour": disnake.Colour(int(primary.replace("#", ""), 16))}
    return {}


def _embed_kwargs():
    color_data = db.get_document("custom_colors")
    primary = color_data.get("primary")
    if primary:
        return {"color": int(primary.replace("#", ""), 16)}
    return {}


class GiftsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── Painel ───────────────────────────────────────────────────────────────

    @staticmethod
    def painel(inter) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return GiftsCog._painel_embed()
        return GiftsCog._painel_components()

    @staticmethod
    def _stats():
        gifts = db.get_document("gifts_data") or {}
        total = len(gifts)
        redeemed = sum(1 for g in gifts.values() if g.get("redeemed"))
        return total, total - redeemed, redeemed

    @staticmethod
    def _painel_components() -> dict:
        cfg = db.get_document("gifts_config") or {}
        redeem_mode = cfg.get("redeem_mode", "painel")
        canal_id = cfg.get("canal_id")
        total, active, redeemed = GiftsCog._stats()

        # 1 botão toggle que mostra o modo atual e avança no ciclo ao clicar
        toggle_btn = disnake.ui.Button(
            label=f"Modo: {REDEEM_MODE_LABELS[redeem_mode]}",
            style=disnake.ButtonStyle.blurple,
            custom_id="Gifts_ModeToggle",
            emoji=emoji.edit,
        )

        # Botões contextuais dependendo do modo atual
        if redeem_mode == "painel":
            extra = [
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Personalizar Mensagem", style=disnake.ButtonStyle.secondary, custom_id="Gifts_PersonalizarMensagem", emoji=emoji.edit),
                    disnake.ui.Button(label="Personalizar Botão",    style=disnake.ButtonStyle.secondary, custom_id="Gifts_PersonalizarBotao",    emoji=emoji.plus),
                    disnake.ui.Button(label="Enviar Painel",         style=disnake.ButtonStyle.green,     custom_id="Gifts_EnviarPainel",          emoji=emoji.arrow),
                ),
            ]
        elif redeem_mode == "canal":
            canal_txt = f"Canal atual: <#{canal_id}>" if canal_id else "Nenhum canal selecionado"
            extra = [
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"-# {canal_txt}"),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        placeholder="Selecione o canal de resgate",
                        custom_id="Gifts_SelecionarCanal",
                        channel_types=[disnake.ChannelType.text],
                        min_values=1, max_values=1,
                    )
                ),
            ]
        else:  # comando
            extra = []

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Loja > **Gifts**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"-# Total: `{total}` | Ativos: `{active}` | Resgatados: `{redeemed}`\n"
                    f"-# Modo de resgate: **{REDEEM_MODE_LABELS[redeem_mode]}**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(toggle_btn),
                *extra,
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Criar Gift",      style=disnake.ButtonStyle.green,     custom_id="Gifts_CriarGift", emoji=emoji.plus),
                    disnake.ui.Button(label="Gerenciar Gifts", style=disnake.ButtonStyle.secondary, custom_id="Gifts_Gerenciar", emoji=emoji.edit, disabled=total == 0),
                ),
                **_container_kwargs(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Panel"),
            ),
        ]}

    @staticmethod
    def _painel_embed() -> dict:
        cfg = db.get_document("gifts_config") or {}
        redeem_mode = cfg.get("redeem_mode", "painel")
        canal_id = cfg.get("canal_id")
        total, active, redeemed = GiftsCog._stats()

        embed = disnake.Embed(
            description=(
                f"-# Painel > Loja > **Gifts**\n\n"
                f"-# Total: `{total}` | Ativos: `{active}` | Resgatados: `{redeemed}`\n"
                f"-# Modo de resgate: **{REDEEM_MODE_LABELS[redeem_mode]}**"
            ),
            **_embed_kwargs(),
        )

        rows = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=f"Modo: {REDEEM_MODE_LABELS[redeem_mode]}",
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Gifts_ModeToggle",
                    emoji=emoji.edit,
                )
            ),
        ]

        if redeem_mode == "painel":
            rows.append(disnake.ui.ActionRow(
                disnake.ui.Button(label="Personalizar Mensagem", style=disnake.ButtonStyle.secondary, custom_id="Gifts_PersonalizarMensagem", emoji=emoji.edit),
                disnake.ui.Button(label="Personalizar Botão",    style=disnake.ButtonStyle.secondary, custom_id="Gifts_PersonalizarBotao",    emoji=emoji.plus),
                disnake.ui.Button(label="Enviar Painel",         style=disnake.ButtonStyle.green,     custom_id="Gifts_EnviarPainel",          emoji=emoji.arrow),
            ))
        elif redeem_mode == "canal":
            rows.append(disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal de resgate",
                    custom_id="Gifts_SelecionarCanal",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1, max_values=1,
                )
            ))

        rows += [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Gift",      style=disnake.ButtonStyle.green,     custom_id="Gifts_CriarGift", emoji=emoji.plus),
                disnake.ui.Button(label="Gerenciar Gifts", style=disnake.ButtonStyle.secondary, custom_id="Gifts_Gerenciar", emoji=emoji.edit, disabled=total == 0),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Panel")),
        ]
        return {"embed": embed, "components": rows}

    # ─── Listeners ────────────────────────────────────────────────────────────

    async def _navigate(self, inter: disnake.MessageInteraction, panel_data: dict):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if "embed" in panel_data:
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid in ("gifts", "Painel_Gifts"):
            await self._navigate(inter, self.painel(inter))

        elif cid == "Gifts_ModeToggle":
            cfg = db.get_document("gifts_config") or {}
            current = cfg.get("redeem_mode", "painel")
            cfg["redeem_mode"] = REDEEM_MODE_CYCLE[current]
            db.save_document("gifts_config", {}, cfg)
            await self._navigate(inter, self.painel(inter))

        elif cid == "Gifts_PersonalizarMensagem":
            from .message_editor import GiftMessageEditor
            await self._navigate(inter, GiftMessageEditor.painel(inter))

        elif cid == "Gifts_PersonalizarBotao":
            from .message_editor import GiftMessageEditor
            await self._navigate(inter, GiftMessageEditor.painel_botao(inter))

        elif cid == "Gifts_EnviarPainel":
            from .sender import GiftSender
            await self._navigate(inter, GiftSender.painel_enviar(inter))

        elif cid == "Gifts_CriarGift":
            from .manager import GiftManager
            await self._navigate(inter, GiftManager.painel_criar(inter))

        elif cid == "Gifts_Gerenciar":
            from .manager import GiftManager
            await self._navigate(inter, GiftManager.painel_listar(inter))

        elif cid == "Gifts_VoltarPainel":
            await self._navigate(inter, self.painel(inter))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Gifts_SelecionarCanal":
            canal_id = str(inter.values[0])
            cfg = db.get_document("gifts_config") or {}
            cfg["canal_id"] = canal_id
            db.save_document("gifts_config", {}, cfg)
            await self._navigate(inter, self.painel(inter))


def setup(bot: commands.Bot):
    bot.add_cog(GiftsCog(bot))
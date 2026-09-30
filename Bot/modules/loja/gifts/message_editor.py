"""
Editor de mensagem do painel de Gifts.
Idêntico ao editor do MsgAuto, mas sem a parte de botões.
Para construir a mensagem, reutiliza o Builder do sistema de Anunciar.
"""
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

# Chave no banco onde a mensagem do painel é salva
# (mesmo formato que messages_anunciar["message"])
_DOC = "gifts_panel_message"


def _get_cfg() -> dict:
    return db.get_document(_DOC) or {"message": {}}


def _save_cfg(cfg: dict):
    db.save_document(_DOC, {}, cfg)


def _msg(cfg: dict) -> dict:
    return cfg.get("message") or {}


# ─── Modais (idênticos ao MsgAuto) ───────────────────────────────────────────

class DefinirMensagemModal(disnake.ui.Modal):
    def __init__(self):
        msg = _msg(_get_cfg())
        super().__init__(
            title="Definir Mensagem",
            custom_id="GiftMsg_Modal:mensagem",
            components=[disnake.ui.TextInput(
                label="Mensagem", custom_id="content",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Texto da mensagem do painel de gifts.",
                value=msg.get("content") or "", max_length=2000, required=False,
            )],
        )


class DefinirEmbedModal(disnake.ui.Modal):
    def __init__(self):
        msg = _msg(_get_cfg())
        embed = msg.get("embed") or {}
        super().__init__(
            title="Definir Embed",
            custom_id="GiftMsg_Modal:embed",
            components=[
                disnake.ui.TextInput(label="Título",       custom_id="title",       style=disnake.TextInputStyle.short,     required=False, value=embed.get("title") or ""),
                disnake.ui.TextInput(label="Descrição",    custom_id="description", style=disnake.TextInputStyle.paragraph, required=False, value=embed.get("description") or ""),
                disnake.ui.TextInput(label="Cor (Hex)",    custom_id="color",       style=disnake.TextInputStyle.short,     required=False, value=embed.get("color") or "", placeholder="#FFFFFF"),
                disnake.ui.TextInput(label="Footer",       custom_id="footer",      style=disnake.TextInputStyle.short,     required=False, value=embed.get("footer") or ""),
            ],
        )


class DefinirImagensModal(disnake.ui.Modal):
    def __init__(self):
        msg = _msg(_get_cfg())
        embed = msg.get("embed") or {}
        has_embed = any(embed.get(k) for k in ("title", "description", "footer"))
        components = [
            disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage", style=disnake.TextInputStyle.short, required=False, value=msg.get("externalImage") or ""),
        ]
        if has_embed:
            components += [
                disnake.ui.TextInput(label="URL do Banner (embed)",    custom_id="banner",    style=disnake.TextInputStyle.short, required=False, value=embed.get("banner") or ""),
                disnake.ui.TextInput(label="URL da Thumbnail (embed)", custom_id="thumbnail", style=disnake.TextInputStyle.short, required=False, value=embed.get("thumbnail") or ""),
            ]
        super().__init__(title="Definir Imagens", custom_id="GiftMsg_Modal:imagens", components=components)


class DefinirContainerModal(disnake.ui.Modal):
    def __init__(self):
        msg = _msg(_get_cfg())
        super().__init__(
            title="Definir Container",
            custom_id="GiftMsg_Modal:container",
            components=[disnake.ui.TextInput(
                label="Conteúdo do container", custom_id="container",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Use {{separator}}, {{color:#...}}, {{image url='...'}}", 
                value=msg.get("container") or "", required=True,
            )],
        )


class PersonalizarBotaoModal(disnake.ui.Modal):
    def __init__(self):
        cfg = db.get_document("gifts_config") or {}
        btn = cfg.get("redeem_button") or {}
        super().__init__(
            title="Personalizar Botão de Resgate",
            custom_id="GiftMsg_Modal:botao",
            components=[
                disnake.ui.TextInput(label="Label", custom_id="label", style=disnake.TextInputStyle.short, required=True, value=btn.get("label") or "Resgatar Gift", max_length=80),
                disnake.ui.TextInput(label="Emoji (opcional)", custom_id="emoji_input", style=disnake.TextInputStyle.short, required=False, value=btn.get("emoji") or "", placeholder="🎁 ou <:nome:id>"),
            ],
        )


# ─── Painel do editor ─────────────────────────────────────────────────────────

class GiftMessageEditor:

    @staticmethod
    def painel(inter) -> dict:
        cfg = _get_cfg()
        msg = _msg(cfg)

        has_content   = bool(msg.get("content"))
        embed_data    = msg.get("embed") or {}
        has_embed     = any(embed_data.get(k) for k in ("title", "description", "color", "footer"))
        has_image     = bool(msg.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
        has_container = bool(msg.get("container"))
        has_any       = any([has_content, has_embed, has_image, has_container])

        # Container desabilita mensagem e embed (igual ao anunciar)
        container_blocks_others = has_container

        mode = db.get_document("custom_mode").get("mode")
        from functions.database import database
        color_data = database.get_document("custom_colors")
        primary = color_data.get("primary")

        def _row(label, define_id, delete_id, icon, has_val, define_disabled=False):
            return disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.red,       custom_id=delete_id, emoji=emoji.delete, disabled=not has_val),
                disnake.ui.Button(label=f"Definir {label}", style=disnake.ButtonStyle.secondary, custom_id=define_id, emoji=icon, disabled=define_disabled),
            )

        if mode == "embed":
            embed_kw = {}
            if primary:
                embed_kw["color"] = int(primary.replace("#", ""), 16)
            return {
                "embed": disnake.Embed(
                    description="-# Painel > Loja > Gifts > **Personalizar Mensagem**\n\nConfigure a mensagem do painel de resgate de gifts.",
                    **embed_kw,
                ),
                "components": [
                    _row("Mensagem",  "GiftMsg_Abrir:mensagem",  "GiftMsg_Apagar:content",   emoji.message,  has_content,   define_disabled=container_blocks_others),
                    _row("Embed",     "GiftMsg_Abrir:embed",     "GiftMsg_Apagar:embed",     emoji.embed,    has_embed,     define_disabled=has_container),
                    _row("Imagens",   "GiftMsg_Abrir:imagens",   "GiftMsg_Apagar:imagens",   emoji.image,    has_image),
                    _row("Container", "GiftMsg_Abrir:container", "GiftMsg_Apagar:container", emoji.commands, has_container, define_disabled=(has_content or has_embed) and not has_container),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.secondary, emoji=emoji.search, custom_id="GiftMsg_Visualizar", disabled=not has_any)),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
                ],
            }

        ckw = {}
        if primary:
            ckw["accent_colour"] = disnake.Colour(int(primary.replace("#", ""), 16))

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Gifts > **Personalizar Mensagem**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure a mensagem exibida no painel de resgate de gifts."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                _row("Mensagem",  "GiftMsg_Abrir:mensagem",  "GiftMsg_Apagar:content",   emoji.message,  has_content,   define_disabled=container_blocks_others),
                _row("Embed",     "GiftMsg_Abrir:embed",     "GiftMsg_Apagar:embed",     emoji.embed,    has_embed,     define_disabled=has_container),
                _row("Imagens",   "GiftMsg_Abrir:imagens",   "GiftMsg_Apagar:imagens",   emoji.image,    has_image),
                _row("Container", "GiftMsg_Abrir:container", "GiftMsg_Apagar:container", emoji.commands, has_container, define_disabled=(has_content or has_embed) and not has_container),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.secondary, emoji=emoji.search, custom_id="GiftMsg_Visualizar", disabled=not has_any)),
                **ckw,
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
        ]}

    @staticmethod
    def painel_botao(inter) -> dict:
        cfg = db.get_document("gifts_config") or {}
        btn = cfg.get("redeem_button") or {}
        label = btn.get("label") or "Resgatar Gift"
        emj   = btn.get("emoji") or "Nenhum"

        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary = color_data.get("primary")

        desc = (
            f"-# Painel > Loja > Gifts > **Personalizar Botão**\n\n"
            f"**Configuração atual do botão de resgate:**\n"
            f"-# Label: `{label}`\n"
            f"-# Emoji: `{emj}`\n\n"
            "-# Este botão aparece no painel de resgate de gifts."
        )

        if mode == "embed":
            ekw = {}
            if primary:
                ekw["color"] = int(primary.replace("#", ""), 16)
            return {
                "embed": disnake.Embed(description=desc, **ekw),
                "components": [
                    disnake.ui.ActionRow(disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="GiftMsg_Abrir:botao")),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
                ],
            }

        ckw = {}
        if primary:
            ckw["accent_colour"] = disnake.Colour(int(primary.replace("#", ""), 16))
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Gifts > **Personalizar Botão**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(desc),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="GiftMsg_Abrir:botao")),
                **ckw,
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
        ]}


# ─── Cog ─────────────────────────────────────────────────────────────────────

class GiftMessageEditorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _back_to_editor(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        panel_data = GiftMessageEditor.painel(inter)
        if "embed" in panel_data:
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("GiftMsg_"):
            return

        if cid.startswith("GiftMsg_Abrir:"):
            field = cid.split(":")[1]
            modal_map = {
                "mensagem":  DefinirMensagemModal,
                "embed":     DefinirEmbedModal,
                "imagens":   DefinirImagensModal,
                "container": DefinirContainerModal,
                "botao":     PersonalizarBotaoModal,
            }
            if field in modal_map:
                await inter.response.send_modal(modal_map[field]())

        elif cid.startswith("GiftMsg_Apagar:"):
            field = cid.split(":")[1]
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            cfg = _get_cfg()
            msg = cfg.setdefault("message", {})
            if field == "content":
                msg["content"] = None
            elif field == "embed":
                msg["embed"] = {}
            elif field == "imagens":
                msg["externalImage"] = None
                msg.setdefault("embed", {}).update({"banner": None, "thumbnail": None})
            elif field == "container":
                msg["container"] = None
            _save_cfg(cfg)
            await self._back_to_editor(inter)

        elif cid == "GiftMsg_Visualizar":
            from .builder import build_gift_panel_message
            await inter.response.defer(ephemeral=True)
            built = await build_gift_panel_message()
            if built["mode"] == "v2":
                await inter.followup.send(
                    components=built["components"], flags=built["flags"],
                    ephemeral=True, allowed_mentions=disnake.AllowedMentions.none(),
                )
            else:
                kwargs = {"ephemeral": True, "allowed_mentions": disnake.AllowedMentions.none()}
                if built.get("content"):
                    kwargs["content"] = built["content"]
                if built.get("embed"):
                    kwargs["embed"] = built["embed"]
                if built.get("components"):
                    kwargs["components"] = built["components"]
                await inter.followup.send(**kwargs)

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("GiftMsg_Modal:"):
            return

        field = cid.split(":")[1]
        cfg = _get_cfg()
        msg = cfg.setdefault("message", {})

        if field == "mensagem":
            msg["content"] = inter.text_values.get("content") or None
            msg.pop("container", None)

        elif field == "embed":
            color_raw = inter.text_values.get("color", "").strip().lstrip("#")
            color_val = None
            if len(color_raw) in (3, 6):
                try:
                    int(color_raw, 16)
                    color_val = f"#{color_raw.upper()}"
                except ValueError:
                    pass
            msg["embed"] = {
                "title":       inter.text_values.get("title")       or None,
                "description": inter.text_values.get("description") or None,
                "color":       color_val,
                "footer":      inter.text_values.get("footer")      or None,
            }
            msg.pop("container", None)

        elif field == "imagens":
            msg["externalImage"] = inter.text_values.get("externalImage") or None
            embed = msg.setdefault("embed", {})
            if "banner" in inter.text_values:
                embed["banner"] = inter.text_values.get("banner") or None
            if "thumbnail" in inter.text_values:
                embed["thumbnail"] = inter.text_values.get("thumbnail") or None

        elif field == "container":
            msg["container"] = inter.text_values.get("container") or None
            msg.pop("content", None)
            msg.pop("embed", None)

        elif field == "botao":
            label = inter.text_values.get("label", "Resgatar Gift").strip() or "Resgatar Gift"
            emj   = inter.text_values.get("emoji_input", "").strip()
            gcfg = db.get_document("gifts_config") or {}
            gcfg["redeem_button"] = {"label": label, "emoji": emj or None}
            db.save_document("gifts_config", {}, gcfg)
            # retornar painel do botão, não do editor de mensagem
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            panel_data = GiftMessageEditor.painel_botao(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return

        _save_cfg(cfg)
        await self._back_to_editor(inter)


def setup(bot: commands.Bot):
    bot.add_cog(GiftMessageEditorCog(bot))
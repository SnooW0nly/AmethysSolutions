"""
Sistema de personalização dos logs de vendas
Suporta três modos: Imagem Pillow, Embed e Componentes.
O painel principal usa o Builder do Anunciar para configurar o layout.
"""
# atualizado
import disnake
import re
import json
import aiohttp
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils


# ── Constantes de modo ──────────────────────────────────────────────────────
_MODE_LABELS = {"image": "Imagem", "embed": "Embed", "components": "Componentes"}
_MODE_ICONS  = {"image": "🖼️", "embed": "📋", "components": "🧩"}

_AVAILABLE_FIELDS = ["cliente", "produto", "valor", "quantidade", "desconto", "cupom"]
_DEFAULT_FIELDS   = "cliente, produto, valor, desconto, cupom"

_FIELD_DESCRIPTIONS = {
    "cliente":    "Nome e @ do comprador",
    "produto":    "Nome do produto adquirido",
    "valor":      "Valor total pago",
    "quantidade": "Quantidade de itens",
    "desconto":   "Valor/% de desconto aplicado",
    "cupom":      "Código de cupom utilizado",
}


# ── Modal de imagem (Pillow) ─────────────────────────────────────────────────

class SalesLogsImageModal(disnake.ui.Modal):
    """Modal de configuração para o modo Imagem (Pillow)"""

    def __init__(self):
        data = db.get_document("loja_receipt_customization")
        super().__init__(
            title="🖼️ Configurar Imagem (Pillow)",
            custom_id="Loja_SalesLogs_ImageModal",
            components=[
                disnake.ui.TextInput(
                    label="Cor de Fundo (hex)",
                    custom_id="bg_color",
                    value=data.get("bg_color", "#0D0D0D"),
                    placeholder="#0D0D0D  →  fundo externo do recibo",
                    max_length=7,
                    required=True,
                    style=disnake.TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Cor do Card (hex)",
                    custom_id="card_color",
                    value=data.get("card_color", "#161618"),
                    placeholder="#161618  →  card interno",
                    max_length=7,
                    required=True,
                    style=disnake.TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Cor de Destaque (hex)",
                    custom_id="accent_color",
                    value=data.get("accent_color", "#57F287"),
                    placeholder="#57F287  →  total, checkmark",
                    max_length=7,
                    required=True,
                    style=disnake.TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Texto do Rodapé",
                    custom_id="footer_text",
                    value=data.get("footer_text", "amethys.solutions"),
                    placeholder="amethys.solutions",
                    max_length=50,
                    required=True,
                    style=disnake.TextInputStyle.short,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        def _valid(v: str) -> bool:
            return v.strip().startswith("#") and len(v.strip()) == 7

        bg_color     = (inter.text_values.get("bg_color") or "").strip()
        card_color   = (inter.text_values.get("card_color") or "").strip()
        accent_color = (inter.text_values.get("accent_color") or "").strip()
        footer_text  = (inter.text_values.get("footer_text") or "amethys.solutions").strip()

        for label, val in [("Cor de Fundo", bg_color), ("Cor do Card", card_color), ("Cor de Destaque", accent_color)]:
            if not _valid(val):
                await inter.response.send_message(f"{emoji.wrong} **{label}** inválida! Use formato hex: `#RRGGBB`", ephemeral=True)
                return

        data = db.get_document("loja_receipt_customization")
        data.update({"bg_color": bg_color, "card_color": card_color, "accent_color": accent_color, "footer_text": footer_text})
        db.save_document("loja_receipt_customization", data)

        await inter.response.edit_message(components=SalesLogsSystem.panel_builder(bot=inter.bot))


# ── Modal de importação do Anunciar ──────────────────────────────────────────

class ImportarDoAnunciarModal(disnake.ui.Modal):
    """Importa a mensagem configurada no Anunciar como template do evento de compra."""

    _LINK_RE = re.compile(
        r"https?://(?:builder\.amethysapplications\.com\.br|amethysapplications\.com\.br|amethysapp\.vercel\.app)(?:/builder)?/s/([a-f0-9]{24})",
        re.IGNORECASE,
    )

    _T_ACTION_ROW    = 1
    _T_BUTTON        = 2
    _T_STRING_SELECT = 3
    _T_TEXT_DISPLAY  = 10
    _T_MEDIA_GALLERY = 12
    _T_SEPARATOR     = 14
    _T_CONTAINER     = 17
    _BTN_STYLE_MAP   = {1: "blue", 2: "gray", 3: "green", 4: "red", 5: "url"}

    def __init__(self):
        super().__init__(
            title="Importar do Amethys Builder",
            custom_id="Loja_SalesLogs_ImportarModal",
            components=[
                disnake.ui.TextInput(
                    label="Link do Builder",
                    custom_id="link",
                    placeholder="https://amethysapp.vercel.app/builder/s/...",
                    required=True,
                    style=disnake.TextInputStyle.short,
                    max_length=200,
                )
            ],
        )

    @staticmethod
    def _emoji_str(emoji_data: dict | None) -> str | None:
        if not emoji_data:
            return None
        eid  = emoji_data.get("id")
        name = emoji_data.get("name") or ""
        return f"<:{name}:{eid}>" if eid else (name or None)

    @classmethod
    def _extract_action_row(cls, comp: dict, buttons: list) -> None:
        for ic in comp.get("components") or []:
            it = ic.get("type")
            if it == cls._T_BUTTON:
                style_num = ic.get("style", 2)
                url       = ic.get("url") or None
                btn_type  = "url" if (style_num == 5 and url) else "disabled"
                buttons.append({
                    "id":     utils.gerar_id(),
                    "label":  ic.get("label") or "",
                    "button": {
                        "type":      btn_type,
                        "style":     cls._BTN_STYLE_MAP.get(style_num, "gray"),
                        "emoji":     cls._emoji_str(ic.get("emoji")),
                        "url":       url if btn_type == "url" else None,
                        "disabled":  btn_type == "disabled",
                        "custom_id": ic.get("custom_id") or None,
                        "action":    {},
                    },
                })

    @classmethod
    def _extract_components(cls, components_list: list[dict]) -> dict:
        container_parts: list[dict] = []
        buttons:         list[dict] = []
        external_image:  str | None = None

        for comp in components_list:
            t = comp.get("type")
            if t == cls._T_ACTION_ROW:
                cls._extract_action_row(comp, buttons)
                continue
            if t == cls._T_MEDIA_GALLERY:
                items = comp.get("items") or []
                if items and external_image is None:
                    external_image = (items[0].get("media") or {}).get("url") or None
                continue
            if t == cls._T_CONTAINER:
                clean_inner = []
                for ic in comp.get("components") or []:
                    if ic.get("type") == cls._T_ACTION_ROW:
                        cls._extract_action_row(ic, buttons)
                    else:
                        clean_inner.append(ic)
                if clean_inner:
                    clean = dict(comp)
                    clean["components"] = clean_inner
                    container_parts.append(clean)
                continue
            if t in (cls._T_TEXT_DISPLAY, cls._T_SEPARATOR):
                container_parts.append(comp)
                continue

        return {
            "container_parts": container_parts,
            "buttons":         buttons[:5],
            "external_image":  external_image,
        }

    async def callback(self, inter: disnake.ModalInteraction):
        from functions.message import message as msg_util

        link = inter.text_values.get("link", "").strip()
        match = self._LINK_RE.search(link)
        if not match:
            await inter.response.send_message(
                components=[disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"{emoji.wrong} **Link inválido.**\n"
                        "-# O link deve ser do formato `https://amethysapp.vercel.app/builder/s/<id>`"
                    )
                )],
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True,
            )
            return

        snippet_id = match.group(1)
        api_url = (
            f"https://amethysapp.vercel.app/api/builder/{snippet_id}"
            if "vercel.app" in link
            else f"https://amethysapplications.com.br/api/builder/{snippet_id}"
        )

        await msg_util.wait(inter, send=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 404:
                        await inter.edit_original_message(components=[
                            disnake.ui.Container(disnake.ui.TextDisplay(
                                f"{emoji.wrong} **Link não encontrado ou expirado.**\n"
                                "-# Links do Builder expiram em 7 dias."
                            )),
                            disnake.ui.ActionRow(disnake.ui.Button(
                                label="Voltar", emoji=emoji.back,
                                custom_id="Loja_SalesLogs_VoltarPainel",
                            )),
                        ])
                        return
                    if not resp.ok:
                        raise ValueError(f"HTTP {resp.status}")
                    data_resp = await resp.json()
        except Exception as e:
            await inter.edit_original_message(components=[
                disnake.ui.Container(disnake.ui.TextDisplay(
                    f"{emoji.wrong} **Erro ao buscar o link.**\n-# `{e}`"
                )),
                disnake.ui.ActionRow(disnake.ui.Button(
                    label="Voltar", emoji=emoji.back,
                    custom_id="Loja_SalesLogs_VoltarPainel",
                )),
            ])
            return

        raw_json = data_resp.get("json", "")
        try:
            components_list = json.loads(raw_json)
            if not isinstance(components_list, list):
                raise ValueError("JSON deve ser uma lista de componentes")
        except Exception as e:
            await inter.edit_original_message(components=[
                disnake.ui.Container(disnake.ui.TextDisplay(
                    f"{emoji.wrong} **JSON inválido no link.**\n-# `{e}`"
                )),
                disnake.ui.ActionRow(disnake.ui.Button(
                    label="Voltar", emoji=emoji.back,
                    custom_id="Loja_SalesLogs_VoltarPainel",
                )),
            ])
            return

        extracted = self._extract_components(components_list)

        data = db.get_document("loja_receipt_customization")
        data["builder_container"]      = json.dumps(extracted["container_parts"], ensure_ascii=False) if extracted["container_parts"] else None
        data["builder_buttons"]        = extracted["buttons"]
        data["builder_external_image"] = extracted["external_image"]
        data["builder_content"]        = None
        data["builder_embed"]          = None
        data["mode"]                   = "builder"
        db.save_document("loja_receipt_customization", data)

        await inter.edit_original_message(components=SalesLogsSystem.panel_builder(bot=inter.bot))

        parts = []
        if extracted["container_parts"]:
            parts.append(f"`{len(extracted['container_parts'])}` componente(s) de conteúdo")
        if extracted["buttons"]:
            parts.append(f"`{len(extracted['buttons'])}` botão(ões)")
        if extracted["external_image"]:
            parts.append("imagem externa")
        resumo = "\n".join(f"• {p}" for p in parts) if parts else "Nenhum conteúdo identificado."
        await msg_util.success(inter, f"Importado com sucesso!\n{resumo}", followup=True)


# ── Modais do builder ────────────────────────────────────────────────────────

class BuilderMensagemModal(disnake.ui.Modal):
    def __init__(self):
        data        = db.get_document("loja_receipt_customization")
        editor_data = data.get("builder_editor", {})
        super().__init__(
            title="Definir Mensagem",
            custom_id="Loja_SalesLogs_MensagemModal",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem",
                    custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Digite a mensagem. Use {cliente}, {produto}, {valor}...",
                    value=editor_data.get("content", ""),
                    max_length=2000,
                    required=True,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        data = db.get_document("loja_receipt_customization")
        editor = data.setdefault("builder_editor", {})
        editor["content"] = inter.text_values["content"]
        editor.pop("container", None)
        data["builder_editor"] = editor
        db.save_document("loja_receipt_customization", data)
        await inter.response.edit_message(components=SalesLogsSystem.panel_builder(bot=inter.bot))


class BuilderEmbedModal(disnake.ui.Modal):
    def __init__(self):
        data        = db.get_document("loja_receipt_customization")
        editor_data = data.get("builder_editor", {})
        embed_data  = editor_data.get("embed", {})
        super().__init__(
            title="Definir Embed",
            custom_id="Loja_SalesLogs_EmbedModal",
            components=[
                disnake.ui.TextInput(label="Título",      custom_id="embed_title",       style=disnake.TextInputStyle.short,     required=False, value=embed_data.get("title", "")),
                disnake.ui.TextInput(label="Descrição",   custom_id="embed_description", style=disnake.TextInputStyle.paragraph, required=True,  value=embed_data.get("description", ""), placeholder="Use {cliente}, {produto}, {valor}..."),
                disnake.ui.TextInput(label="Cor (Hex)",   custom_id="embed_color",       style=disnake.TextInputStyle.short,     required=False, value=embed_data.get("color", ""), placeholder="#FFFFFF"),
                disnake.ui.TextInput(label="Footer",      custom_id="embed_footer",      style=disnake.TextInputStyle.short,     required=False, value=embed_data.get("footer", "")),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        def validar_hex(codigo: str) -> str | None:
            if not codigo: return None
            codigo = codigo.strip().lstrip("#")
            if len(codigo) not in (3, 6): return None
            try: int(codigo, 16)
            except ValueError: return None
            return f"#{codigo.upper()}"

        data   = db.get_document("loja_receipt_customization")
        editor = data.setdefault("builder_editor", {})
        editor["embed"] = {
            "title":       inter.text_values.get("embed_title"),
            "description": inter.text_values.get("embed_description"),
            "color":       validar_hex(inter.text_values.get("embed_color")),
            "footer":      inter.text_values.get("embed_footer"),
        }
        editor.pop("container", None)
        data["builder_editor"] = editor
        db.save_document("loja_receipt_customization", data)
        await inter.response.edit_message(components=SalesLogsSystem.panel_builder(bot=inter.bot))


class BuilderImagensModal(disnake.ui.Modal):
    def __init__(self):
        data        = db.get_document("loja_receipt_customization")
        editor_data = data.get("builder_editor", {})
        embed_data  = editor_data.get("embed", {})
        has_embed   = bool(embed_data.get("title") or embed_data.get("description"))

        components = [
            disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage", style=disnake.TextInputStyle.short, required=False, value=editor_data.get("externalImage", "")),
        ]
        if has_embed:
            components.extend([
                disnake.ui.TextInput(label="URL do Banner do Embed",     custom_id="banner",    style=disnake.TextInputStyle.short, required=False, value=embed_data.get("banner", "")),
                disnake.ui.TextInput(label="URL da Thumbnail do Embed",  custom_id="thumbnail", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("thumbnail", "")),
            ])

        super().__init__(title="Definir Imagens", custom_id="Loja_SalesLogs_ImagensModal", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        data   = db.get_document("loja_receipt_customization")
        editor = data.setdefault("builder_editor", {})
        editor["externalImage"] = inter.text_values.get("externalImage") or None
        if "banner" in inter.text_values:
            editor.setdefault("embed", {})["banner"]    = inter.text_values.get("banner") or None
        if "thumbnail" in inter.text_values:
            editor.setdefault("embed", {})["thumbnail"] = inter.text_values.get("thumbnail") or None
        data["builder_editor"] = editor
        db.save_document("loja_receipt_customization", data)
        await inter.response.edit_message(components=SalesLogsSystem.panel_builder(bot=inter.bot))


class BuilderContainerModal(disnake.ui.Modal):
    def __init__(self):
        data        = db.get_document("loja_receipt_customization")
        editor_data = data.get("builder_editor", {})
        super().__init__(
            title="Definir Container",
            custom_id="Loja_SalesLogs_ContainerModal",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container",
                    custom_id="container_content",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Use {{separator}}, {{color:#...}}, {{image url=...}}",
                    required=True,
                    value=editor_data.get("container", ""),
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        data   = db.get_document("loja_receipt_customization")
        editor = data.setdefault("builder_editor", {})
        editor["container"] = inter.text_values["container_content"]
        editor.pop("content", None)
        editor.pop("embed", None)
        data["builder_editor"] = editor
        db.save_document("loja_receipt_customization", data)
        await inter.response.edit_message(components=SalesLogsSystem.panel_builder(bot=inter.bot))


# ── Sistema principal ─────────────────────────────────────────────────────────

class SalesLogsSystem:

    @staticmethod
    def get_config() -> dict:
        return db.get_document("loja_receipt_customization")

    @staticmethod
    def _container_kwargs() -> dict:
        colors      = db.get_document("custom_colors")
        primary_hex = colors.get("primary")
        if primary_hex:
            return {"accent_colour": disnake.Colour(int(primary_hex.replace("#", ""), 16))}
        return {}

    # ── painel principal (components v2) ────────────────────────────────────

    @staticmethod
    def panel(inter: disnake.Interaction) -> dict:
        ui_mode = db.get_document("custom_mode").get("mode")
        if ui_mode == "components":
            return SalesLogsSystem._panel_components(inter)
        return SalesLogsSystem._panel_embed(inter)

    @staticmethod
    def _panel_components(inter: disnake.Interaction) -> dict:
        data        = db.get_document("loja_receipt_customization")
        editor_data = data.get("builder_editor", {})
        enabled     = data.get("enabled", True)
        ckwargs     = SalesLogsSystem._container_kwargs()

        has_message   = bool(editor_data.get("content"))
        embed_data    = editor_data.get("embed", {})
        has_embed     = any(embed_data.get(k) for k in ("title", "description", "footer"))
        has_image     = bool(editor_data.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
        has_container = bool(editor_data.get("container"))
        botoes        = editor_data.get("botoes", [])
        has_buttons   = isinstance(botoes, list) and len(botoes) > 0
        has_any       = has_message or has_embed or has_container or has_image or has_buttons
        other_disabled = has_container

        pillow_disabled   = has_message or has_embed or has_container
        status_txt = f"{emoji.on} Ativado" if enabled else f"{emoji.off} Desativado"

        return {"components": [
            disnake.ui.Container(
                disnake.ui.Section(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Loja > Personalizar > **Logs de Vendas**"
                    ),
                    accessory=disnake.ui.Thumbnail(media=str(inter.bot.user.display_avatar.url)),
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"Monte o layout do evento público de compra. Importe um design pronto ou configure campo a campo.\n"
                    f"-# Variáveis: `{{cliente}}` `{{produto}}` `{{valor}}` `{{quantidade}}` `{{desconto}}` `{{cupom}}`\n\n"
                    f"**Status:** {status_txt}"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:content",   disabled=not has_message or other_disabled),
                    disnake.ui.Button(label="Definir Mensagem",           style=disnake.ButtonStyle.grey, emoji=emoji.message,  custom_id="Loja_Builder_Mensagem",    disabled=other_disabled),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:embed",     disabled=not has_embed or other_disabled),
                    disnake.ui.Button(label="Definir Embed",              style=disnake.ButtonStyle.grey, emoji=emoji.embed,    custom_id="Loja_Builder_Embed",        disabled=other_disabled),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:images",    disabled=not has_image),
                    disnake.ui.Button(label="Definir Imagens",            style=disnake.ButtonStyle.grey, emoji=emoji.image,    custom_id="Loja_Builder_Imagens"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:container", disabled=not has_container),
                    disnake.ui.Button(label="Definir Container",          style=disnake.ButtonStyle.grey, emoji=emoji.commands, custom_id="Loja_Builder_Container",    disabled=(has_message or has_embed) and not has_container),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:pillow",    disabled=pillow_disabled),
                    disnake.ui.Button(label="Configurar Imagem (Pillow)", style=disnake.ButtonStyle.grey, emoji="🖼️",           custom_id="Loja_Builder_ConfigImagem", disabled=pillow_disabled),
                ),
                **ckwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Ativar" if not enabled else "Desativar", style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red, emoji=emoji.power,  custom_id="Loja_SalesLogs_Toggle"),
                disnake.ui.Button(label="Visualizar",          style=disnake.ButtonStyle.grey,    emoji=emoji.search, custom_id="Loja_Builder_Visualizar",      disabled=not has_any),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Importar do Builder",  style=disnake.ButtonStyle.blurple, emoji=emoji.route,  custom_id="Loja_Builder_ImportarSite"),
                disnake.ui.Button(label="Voltar",               style=disnake.ButtonStyle.grey,    emoji=emoji.back,   custom_id="Loja_Personalizar"),
            ),
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.Interaction) -> dict:
        data        = db.get_document("loja_receipt_customization")
        editor_data = data.get("builder_editor", {})
        enabled     = data.get("enabled", True)

        has_message   = bool(editor_data.get("content"))
        embed_data    = editor_data.get("embed", {})
        has_embed     = any(embed_data.get(k) for k in ("title", "description", "footer"))
        has_image     = bool(editor_data.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
        has_container = bool(editor_data.get("container"))
        botoes        = editor_data.get("botoes", [])
        has_buttons   = isinstance(botoes, list) and len(botoes) > 0
        has_any       = has_message or has_embed or has_container or has_image or has_buttons
        other_disabled = has_container

        pillow_disabled   = has_message or has_embed or has_container

        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Logs de Vendas",
            description=(
                "-# Loja > Personalizar > **Logs de Vendas**\n\n"
                "Monte o layout do evento público de compra. Importe um design pronto ou configure campo a campo.\n"
                "-# Variáveis: `{cliente}` `{produto}` `{valor}` `{quantidade}` `{desconto}` `{cupom}`"
            ),
            color=disnake.Color.from_rgb(0, 202, 164),
        )
        embed.set_thumbnail(url=str(inter.bot.user.display_avatar.url))
        embed.add_field(name="Status", value=f"{emoji.on if enabled else emoji.off} {'Ativado' if enabled else 'Desativado'}", inline=True)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:content",   disabled=not has_message or other_disabled),
                disnake.ui.Button(label="Definir Mensagem",           style=disnake.ButtonStyle.grey, emoji=emoji.message,  custom_id="Loja_Builder_Mensagem",    disabled=other_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:embed",     disabled=not has_embed or other_disabled),
                disnake.ui.Button(label="Definir Embed",              style=disnake.ButtonStyle.grey, emoji=emoji.embed,    custom_id="Loja_Builder_Embed",        disabled=other_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:images",    disabled=not has_image),
                disnake.ui.Button(label="Definir Imagens",            style=disnake.ButtonStyle.grey, emoji=emoji.image,    custom_id="Loja_Builder_Imagens"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:container", disabled=not has_container),
                disnake.ui.Button(label="Definir Container",          style=disnake.ButtonStyle.grey, emoji=emoji.commands, custom_id="Loja_Builder_Container",    disabled=(has_message or has_embed) and not has_container),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:pillow",    disabled=pillow_disabled),
                disnake.ui.Button(label="Configurar Imagem (Pillow)", style=disnake.ButtonStyle.grey, emoji="🖼️",           custom_id="Loja_Builder_ConfigImagem", disabled=pillow_disabled),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Ativar" if not enabled else "Desativar", style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red, emoji=emoji.power, custom_id="Loja_SalesLogs_Toggle"),
                disnake.ui.Button(label="Visualizar",          style=disnake.ButtonStyle.grey,    emoji=emoji.search, custom_id="Loja_Builder_Visualizar",      disabled=not has_any),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Importar do Builder",  style=disnake.ButtonStyle.blurple, emoji=emoji.route,  custom_id="Loja_Builder_ImportarSite"),
                disnake.ui.Button(label="Voltar",               style=disnake.ButtonStyle.grey,    emoji=emoji.back,   custom_id="Loja_Personalizar"),
            ),
        ]
        return {"embed": embed, "components": components}

    # ── painel builder ───────────────────────────────────────────────────────

    @staticmethod
    def panel_builder(bot=None) -> list:
        """Painel unificado — retorna lista de components para edit_message nos callbacks de modais."""
        data        = db.get_document("loja_receipt_customization")
        editor_data = data.get("builder_editor", {})
        enabled     = data.get("enabled", True)
        ckwargs     = SalesLogsSystem._container_kwargs()

        has_message   = bool(editor_data.get("content"))
        embed_data    = editor_data.get("embed", {})
        has_embed     = any(embed_data.get(k) for k in ("title", "description", "footer"))
        has_image     = bool(editor_data.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
        has_container = bool(editor_data.get("container"))
        botoes        = editor_data.get("botoes", [])
        has_buttons   = isinstance(botoes, list) and len(botoes) > 0
        has_any       = has_message or has_embed or has_container or has_image or has_buttons
        other_disabled = has_container

        pillow_disabled   = has_message or has_embed or has_container
        status_txt = f"{emoji.on} Ativado" if enabled else f"{emoji.off} Desativado"

        header_component = (
            disnake.ui.Section(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Loja > Personalizar > **Logs de Vendas**"
                ),
                accessory=disnake.ui.Thumbnail(media=str(bot.user.display_avatar.url)),
            ) if bot else disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Loja > Personalizar > **Logs de Vendas**"
            )
        )

        return [
            disnake.ui.Container(
                header_component,
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"Monte o layout do evento público de compra. Importe um design pronto ou configure campo a campo.\n"
                    f"-# Variáveis: `{{cliente}}` `{{produto}}` `{{valor}}` `{{quantidade}}` `{{desconto}}` `{{cupom}}`\n\n"
                    f"**Status:** {status_txt}"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:content",   disabled=not has_message or other_disabled),
                    disnake.ui.Button(label="Definir Mensagem",           style=disnake.ButtonStyle.grey, emoji=emoji.message,  custom_id="Loja_Builder_Mensagem",    disabled=other_disabled),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:embed",     disabled=not has_embed or other_disabled),
                    disnake.ui.Button(label="Definir Embed",              style=disnake.ButtonStyle.grey, emoji=emoji.embed,    custom_id="Loja_Builder_Embed",        disabled=other_disabled),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:images",    disabled=not has_image),
                    disnake.ui.Button(label="Definir Imagens",            style=disnake.ButtonStyle.grey, emoji=emoji.image,    custom_id="Loja_Builder_Imagens"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:container", disabled=not has_container),
                    disnake.ui.Button(label="Definir Container",          style=disnake.ButtonStyle.grey, emoji=emoji.commands, custom_id="Loja_Builder_Container",    disabled=(has_message or has_embed) and not has_container),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red,  emoji=emoji.delete, custom_id="Loja_Builder_Apagar:pillow",    disabled=pillow_disabled),
                    disnake.ui.Button(label="Configurar Imagem (Pillow)", style=disnake.ButtonStyle.grey, emoji="🖼️",           custom_id="Loja_Builder_ConfigImagem", disabled=pillow_disabled),
                ),
                **ckwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Ativar" if not enabled else "Desativar", style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red, emoji=emoji.power,  custom_id="Loja_SalesLogs_Toggle"),
                disnake.ui.Button(label="Visualizar",          style=disnake.ButtonStyle.grey,    emoji=emoji.search, custom_id="Loja_Builder_Visualizar",      disabled=not has_any),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Importar do Builder",  style=disnake.ButtonStyle.blurple, emoji=emoji.route,  custom_id="Loja_Builder_ImportarSite"),
                disnake.ui.Button(label="Voltar",               style=disnake.ButtonStyle.grey,    emoji=emoji.back,   custom_id="Loja_Personalizar"),
            ),
        ]

    # ── preview de teste ────────────────────────────────────────────────────

    @staticmethod
    def build_test_image_config() -> dict:
        """Retorna as configurações da imagem para preview."""
        data = db.get_document("loja_receipt_customization")
        return {
            "bg_color":     data.get("bg_color", "#0D0D0D"),
            "card_color":   data.get("card_color", "#161618"),
            "accent_color": data.get("accent_color", "#57F287"),
            "footer_text":  data.get("footer_text", "amethys.solutions"),
        }

    @staticmethod
    def build_test_builder(inter: disnake.MessageInteraction) -> dict:
        """Monta payload de preview do builder (ephemeral)."""
        from commands.admin.anunciar.builder import Builder as _Builder
        import asyncio

        data        = db.get_document("loja_receipt_customization")
        editor_data = data.get("builder_editor", {})

        if not editor_data:
            return {"content": "Nenhum conteúdo configurado no builder.", "ephemeral": True}

        data_to_build = editor_data.copy()
        if "botoes" in data_to_build and data_to_build["botoes"]:
            data_to_build["buttons"] = data_to_build.pop("botoes")
        else:
            data_to_build.pop("botoes", None)
            data_to_build["buttons"] = []

        return data_to_build

    # ── importar do Anunciar ─────────────────────────────────────────────────

    @staticmethod
    def import_from_anunciar() -> bool:
        """Copia a configuração do Anunciar para o builder de logs de vendas."""
        anunciar_data = db.get_document("messages_anunciar")
        msg = anunciar_data.get("message") or {}

        if not msg:
            return False

        data = db.get_document("loja_receipt_customization")
        editor = {
            "content":       msg.get("content"),
            "embed":         msg.get("embed"),
            "externalImage": msg.get("externalImage"),
            "container":     msg.get("container"),
            "botoes":        msg.get("buttons", []),
        }
        # Remove áudio se existir
        editor.pop("audio", None)

        data["builder_editor"] = editor
        data["mode"]           = "builder"
        db.save_document("loja_receipt_customization", data)
        return True


# ── Cog ───────────────────────────────────────────────────────────────────────

from disnake.ext import commands


class SalesLogsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _refresh(self, inter: disnake.MessageInteraction):
        from functions.message import message, embed_message
        mode = db.get_document("custom_mode").get("mode")
        return message if mode != "embed" else embed_message

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "Loja_Builder_Visualizar":
            await inter.response.defer(ephemeral=True)
            data        = db.get_document("loja_receipt_customization")
            editor_data = data.get("builder_editor", {})
            if not editor_data:
                await inter.followup.send(f"{emoji.wrong} Nenhum conteúdo configurado.", ephemeral=True)
                return
            from commands.admin.anunciar.builder import Builder as _Builder
            cfg = {"message": {
                "content":       editor_data.get("content"),
                "embed":         editor_data.get("embed"),
                "externalImage": editor_data.get("externalImage"),
                "container":     editor_data.get("container"),
                "buttons":       editor_data.get("botoes", []),
            }}
            built = await _Builder.build_from_cfg(cfg)
            if built["mode"] == "v2":
                await inter.followup.send(
                    components=built["components"],
                    flags=built["flags"],
                    ephemeral=True,
                    allowed_mentions=disnake.AllowedMentions.none(),
                )
            else:
                kwargs = {"ephemeral": True, "allowed_mentions": disnake.AllowedMentions.none()}
                if built.get("content"):   kwargs["content"]    = built["content"]
                if built.get("embed"):     kwargs["embed"]      = built["embed"]
                if built.get("components"): kwargs["components"] = built["components"]
                if built.get("files"):     kwargs["files"]      = built["files"]
                await inter.followup.send(**kwargs)

        elif cid == "Loja_Builder_ImportarSite":
            await inter.response.send_modal(ImportarDoAnunciarModal())

        elif cid == "Loja_Builder_Mensagem":
            await inter.response.send_modal(BuilderMensagemModal())

        elif cid == "Loja_Builder_Embed":
            await inter.response.send_modal(BuilderEmbedModal())

        elif cid == "Loja_Builder_Imagens":
            await inter.response.send_modal(BuilderImagensModal())

        elif cid == "Loja_Builder_Container":
            await inter.response.send_modal(BuilderContainerModal())

        elif cid == "Loja_Builder_ConfigImagem":
            await inter.response.send_modal(SalesLogsImageModal())

        elif cid.startswith("Loja_Builder_Apagar:"):
            campo = cid.split(":", 1)[1]
            data  = db.get_document("loja_receipt_customization")
            editor = data.setdefault("builder_editor", {})
            if campo == "content":
                editor.pop("content", None)
            elif campo == "embed":
                editor.pop("embed", None)
            elif campo == "images":
                editor.pop("externalImage", None)
                editor.get("embed", {}).pop("banner",    None)
                editor.get("embed", {}).pop("thumbnail", None)
            elif campo == "container":
                editor.pop("container", None)
            elif campo == "pillow":
                for k, v in [("bg_color", "#0D0D0D"), ("card_color", "#161618"), ("accent_color", "#57F287"), ("footer_text", "amethys.solutions")]:
                    data[k] = v
            data["builder_editor"] = editor
            db.save_document("loja_receipt_customization", data)
            await inter.response.edit_message(components=SalesLogsSystem.panel_builder(bot=inter.bot))

        elif cid == "Loja_SalesLogs_VoltarPainel":
            msg_util = self._refresh(inter)
            await msg_util.wait(inter, send=False)
            panel_data = SalesLogsSystem.panel(inter)
            await inter.edit_original_message(**panel_data)


def setup(bot: commands.Bot):
    bot.add_cog(SalesLogsCog(bot))
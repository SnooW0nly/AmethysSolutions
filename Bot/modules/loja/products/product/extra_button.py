import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.loja_products import (
    get_product, get_products, save_products,
    container_kwargs_for_product, embed_kwargs_for_product,
)
from commands.admin.anunciar.builder import Builder


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_extra_button_cfg(product_id: str) -> dict:
    """Retorna a configuração do botão extra do produto (ou dict vazio)."""
    product = get_product(product_id) or {}
    return product.get("info", {}).get("extra_button", {})


def _save_extra_button_cfg(product_id: str, cfg: dict) -> None:
    products = get_products()
    product = products.get(product_id)
    if not product:
        return
    product.setdefault("info", {})["extra_button"] = cfg
    save_products(products)


async def _sync_product_messages(bot: commands.Bot, product_id: str) -> None:
    """Sincroniza silenciosamente as mensagens já enviadas do produto."""
    try:
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(bot, product_id)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  Painel principal do botão extra
# ──────────────────────────────────────────────────────────────────────────────

def build_panel(inter: disnake.MessageInteraction, product_id: str) -> dict:
    mode = db.get_document("custom_mode").get("mode")
    if mode == "embed":
        return _panel_embed(inter, product_id)
    return _panel_components(inter, product_id)


def _panel_components(inter: disnake.MessageInteraction, product_id: str) -> dict:
    product = get_product(product_id) or {}
    cfg = _get_extra_button_cfg(product_id)
    container_kwargs = container_kwargs_for_product(product)

    enabled      = cfg.get("enabled", False)
    label        = cfg.get("label") or "Botão Extra"
    has_content  = bool(cfg.get("message", {}).get("content") or cfg.get("message", {}).get("container"))
    product_name = product.get("name", product_id)

    status_text = (
        f"-# Status: `{'Ativado' if enabled else 'Desativado'}`\n"
        f"-# Label: `{label}`\n"
        f"-# Conteúdo: `{'Configurado' if has_content else 'Não configurado'}`"
    )

    return {"components": [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Loja > {product_name} > **Botão Extra**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Configure um botão extra que aparecerá na mensagem do produto.\n"
                "Ao ser clicado, enviará uma mensagem efêmera ao usuário."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(status_text),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ativar" if not enabled else "Desativar",
                    emoji=emoji.off if not enabled else emoji.on,
                    style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                    custom_id=f"LojaBotaoExtra_Toggle:{product_id}",
                ),
                disnake.ui.Button(
                    label="Editar Label",
                    emoji=emoji.edit,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f"LojaBotaoExtra_EditLabel:{product_id}",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar Mensagem",
                    emoji=emoji.message,
                    style=disnake.ButtonStyle.blurple,
                    custom_id=f"LojaBotaoExtra_ConfigMsg:{product_id}",
                ),
            ),
            **container_kwargs,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                emoji=emoji.back,
                style=disnake.ButtonStyle.grey,
                custom_id=f"Loja_ConfigurarProduto:{product_id}",
            )
        ),
    ]}


def _panel_embed(inter: disnake.MessageInteraction, product_id: str) -> dict:
    product  = get_product(product_id) or {}
    cfg      = _get_extra_button_cfg(product_id)
    embed_kw = embed_kwargs_for_product(product)

    enabled     = cfg.get("enabled", False)
    label       = cfg.get("label") or "Botão Extra"
    has_content = bool(cfg.get("message", {}).get("content") or cfg.get("message", {}).get("container"))
    product_name = product.get("name", product_id)

    embed = disnake.Embed(
        description=(
            f"-# Painel > Loja > {product_name} > **Botão Extra**\n\n"
            f"-# Status: `{'Ativado' if enabled else 'Desativado'}`\n"
            f"-# Label: `{label}`\n"
            f"-# Conteúdo: `{'Configurado' if has_content else 'Não configurado'}`"
        ),
        **embed_kw,
    )
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Ativar" if not enabled else "Desativar",
                emoji=emoji.off if not enabled else emoji.on,
                style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                custom_id=f"LojaBotaoExtra_Toggle:{product_id}",
            ),
            disnake.ui.Button(
                label="Editar Label",
                emoji=emoji.edit,
                style=disnake.ButtonStyle.grey,
                custom_id=f"LojaBotaoExtra_EditLabel:{product_id}",
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Configurar Mensagem",
                emoji=emoji.message,
                style=disnake.ButtonStyle.blurple,
                custom_id=f"LojaBotaoExtra_ConfigMsg:{product_id}",
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                emoji=emoji.back,
                style=disnake.ButtonStyle.grey,
                custom_id=f"Loja_ConfigurarProduto:{product_id}",
            )
        ),
    ]
    return {"embed": embed, "components": components}


# ──────────────────────────────────────────────────────────────────────────────
#  Painel de edição de mensagem (inspirado no Anunciar / MsgAuto)
# ──────────────────────────────────────────────────────────────────────────────

def build_msg_editor_panel(inter: disnake.MessageInteraction, product_id: str) -> dict:
    product = get_product(product_id) or {}
    cfg     = _get_extra_button_cfg(product_id)
    msg_cfg = cfg.get("message", {})
    container_kwargs = container_kwargs_for_product(product)

    has_content   = bool(msg_cfg.get("content"))
    has_embed     = any(msg_cfg.get("embed", {}).get(k) for k in ("title", "description", "footer"))
    has_container = bool(msg_cfg.get("container"))
    has_image     = bool(msg_cfg.get("externalImage") or msg_cfg.get("embed", {}).get("banner"))

    # Container desabilita content/embed
    other_disabled = has_container

    return {"components": [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Loja > {product.get('name', product_id)} > Botão Extra > **Mensagem**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Configure o conteúdo que será enviado de forma efêmera\n"
                "ao usuário quando ele clicar no botão extra."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                    custom_id=f"LojaBotaoExtra_ApagarCampo:content:{product_id}",
                    disabled=not has_content or other_disabled,
                ),
                disnake.ui.Button(
                    label="Definir Mensagem", style=disnake.ButtonStyle.grey, emoji=emoji.message,
                    custom_id=f"LojaBotaoExtra_DefinirMensagem:{product_id}",
                    disabled=other_disabled,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                    custom_id=f"LojaBotaoExtra_ApagarCampo:embed:{product_id}",
                    disabled=not has_embed or other_disabled,
                ),
                disnake.ui.Button(
                    label="Definir Embed", style=disnake.ButtonStyle.grey, emoji=emoji.embed,
                    custom_id=f"LojaBotaoExtra_DefinirEmbed:{product_id}",
                    disabled=other_disabled,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                    custom_id=f"LojaBotaoExtra_ApagarCampo:image:{product_id}",
                    disabled=not has_image,
                ),
                disnake.ui.Button(
                    label="Definir Imagem", style=disnake.ButtonStyle.grey, emoji=emoji.image,
                    custom_id=f"LojaBotaoExtra_DefinirImagem:{product_id}",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                    custom_id=f"LojaBotaoExtra_ApagarCampo:container:{product_id}",
                    disabled=not has_container,
                ),
                disnake.ui.Button(
                    label="Definir Container", style=disnake.ButtonStyle.grey, emoji=emoji.commands,
                    custom_id=f"LojaBotaoExtra_DefinirContainer:{product_id}",
                    disabled=(has_content or has_embed) and not has_container,
                ),
            ),
            **container_kwargs,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search,
                custom_id=f"LojaBotaoExtra_Visualizar:{product_id}",
                disabled=not any([has_content, has_embed, has_container, has_image]),
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                custom_id=f"LojaBotaoExtra_Painel:{product_id}",
            )
        ),
    ]}


# ──────────────────────────────────────────────────────────────────────────────
#  Modals
# ──────────────────────────────────────────────────────────────────────────────

class EditLabelModal(disnake.ui.Modal):
    def __init__(self, product_id: str):
        self.product_id = product_id
        cfg = _get_extra_button_cfg(product_id)
        super().__init__(
            title="Editar Label do Botão Extra",
            custom_id=f"LojaBotaoExtra_LabelModal:{product_id}",
            components=[
                disnake.ui.TextInput(
                    label="Label do botão",
                    custom_id="label",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=80,
                    value=cfg.get("label") or "",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cfg = _get_extra_button_cfg(self.product_id)
        cfg["label"] = inter.text_values["label"].strip() or "Botão Extra"
        _save_extra_button_cfg(self.product_id, cfg)
        await inter.response.edit_message(**build_panel(inter, self.product_id))


class DefinirMensagemModal(disnake.ui.Modal):
    def __init__(self, product_id: str):
        self.product_id = product_id
        cfg = _get_extra_button_cfg(product_id)
        super().__init__(
            title="Definir Mensagem do Botão Extra",
            custom_id=f"LojaBotaoExtra_MsgModal:{product_id}",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem",
                    custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    max_length=2000,
                    value=cfg.get("message", {}).get("content") or "",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cfg = _get_extra_button_cfg(self.product_id)
        msg = cfg.setdefault("message", {})
        msg["content"] = inter.text_values["content"]
        msg.pop("container", None)
        _save_extra_button_cfg(self.product_id, cfg)
        await inter.response.edit_message(**build_msg_editor_panel(inter, self.product_id))


class DefinirEmbedModal(disnake.ui.Modal):
    def __init__(self, product_id: str):
        self.product_id = product_id
        cfg     = _get_extra_button_cfg(product_id)
        embed_d = cfg.get("message", {}).get("embed", {})
        super().__init__(
            title="Definir Embed do Botão Extra",
            custom_id=f"LojaBotaoExtra_EmbedModal:{product_id}",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="title", style=disnake.TextInputStyle.short, required=False, value=embed_d.get("title") or ""),
                disnake.ui.TextInput(label="Descrição", custom_id="description", style=disnake.TextInputStyle.paragraph, required=True, value=embed_d.get("description") or ""),
                disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", style=disnake.TextInputStyle.short, required=False, placeholder="#FFFFFF", value=embed_d.get("color") or ""),
                disnake.ui.TextInput(label="Footer", custom_id="footer", style=disnake.TextInputStyle.short, required=False, value=embed_d.get("footer") or ""),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        def _hex(v):
            if not v:
                return None
            v = v.strip().lstrip("#")
            if len(v) not in (3, 6):
                return None
            try:
                int(v, 16)
            except ValueError:
                return None
            return f"#{v.upper()}"

        cfg = _get_extra_button_cfg(self.product_id)
        msg = cfg.setdefault("message", {})
        msg["embed"] = {
            "title":       inter.text_values.get("title") or None,
            "description": inter.text_values.get("description"),
            "color":       _hex(inter.text_values.get("color")),
            "footer":      inter.text_values.get("footer") or None,
        }
        msg.pop("container", None)
        _save_extra_button_cfg(self.product_id, cfg)
        await inter.response.edit_message(**build_msg_editor_panel(inter, self.product_id))


class DefinirImagemModal(disnake.ui.Modal):
    def __init__(self, product_id: str):
        self.product_id = product_id
        cfg     = _get_extra_button_cfg(product_id)
        msg     = cfg.get("message", {})
        embed_d = msg.get("embed", {})
        super().__init__(
            title="Definir Imagem do Botão Extra",
            custom_id=f"LojaBotaoExtra_ImagemModal:{product_id}",
            components=[
                disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage", style=disnake.TextInputStyle.short, required=False, value=msg.get("externalImage") or ""),
                disnake.ui.TextInput(label="URL do Banner (embed)", custom_id="banner", style=disnake.TextInputStyle.short, required=False, value=embed_d.get("banner") or ""),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cfg = _get_extra_button_cfg(self.product_id)
        msg = cfg.setdefault("message", {})
        msg["externalImage"] = inter.text_values.get("externalImage") or None
        msg.setdefault("embed", {})["banner"] = inter.text_values.get("banner") or None
        _save_extra_button_cfg(self.product_id, cfg)
        await inter.response.edit_message(**build_msg_editor_panel(inter, self.product_id))


class DefinirContainerModal(disnake.ui.Modal):
    def __init__(self, product_id: str):
        self.product_id = product_id
        cfg = _get_extra_button_cfg(product_id)
        super().__init__(
            title="Definir Container do Botão Extra",
            custom_id=f"LojaBotaoExtra_ContainerModal:{product_id}",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container",
                    custom_id="container",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    placeholder="Use {{separator}}, {{color:#...}}, {{image url=...}}",
                    value=cfg.get("message", {}).get("container") or "",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cfg = _get_extra_button_cfg(self.product_id)
        msg = cfg.setdefault("message", {})
        msg["container"] = inter.text_values["container"]
        msg.pop("content", None)
        msg.pop("embed",    None)
        _save_extra_button_cfg(self.product_id, cfg)
        await inter.response.edit_message(**build_msg_editor_panel(inter, self.product_id))


# ──────────────────────────────────────────────────────────────────────────────
#  Cog principal
# ──────────────────────────────────────────────────────────────────────────────

class ExtraButtonCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Utilitário de envio da preview ────────────────────────────────────────

    @staticmethod
    async def _send_preview(inter: disnake.MessageInteraction, product_id: str) -> None:
        cfg     = _get_extra_button_cfg(product_id)
        msg_cfg = cfg.get("message", {})

        # Adapta o cfg para o formato esperado pelo Builder
        built = Builder.build_from_cfg({"message": msg_cfg})

        if built["mode"] == "v2":
            await inter.followup.send(
                components=built["components"],
                flags=built["flags"],
                ephemeral=True,
                allowed_mentions=disnake.AllowedMentions.none(),
            )
        else:
            kwargs: dict = {
                "ephemeral": True,
                "allowed_mentions": disnake.AllowedMentions.none(),
            }
            if built.get("content"):
                kwargs["content"] = built["content"]
            if built.get("embed"):
                kwargs["embed"] = built["embed"]
            if built.get("components"):
                kwargs["components"] = built["components"]
            if built.get("files"):
                kwargs["files"] = built["files"]
            await inter.followup.send(**kwargs)

    # ── Listener de clique em botão de produto (runtime) ─────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        # ── Runtime: usuário clica no botão extra de um produto publicado ──
        if cid.startswith("product_extra_button:"):
            product_id = cid.split(":", 1)[1]
            cfg     = _get_extra_button_cfg(product_id)

            if not cfg.get("enabled"):
                await inter.response.send_message(
                    f"{emoji.warn} Este botão não está mais ativo.", ephemeral=True
                )
                return

            msg_cfg = cfg.get("message", {})
            if not any([msg_cfg.get("content"), msg_cfg.get("container"),
                        msg_cfg.get("embed", {}).get("description")]):
                await inter.response.send_message(
                    f"{emoji.warn} O conteúdo deste botão não foi configurado.", ephemeral=True
                )
                return

            built = Builder.build_from_cfg({"message": msg_cfg})

            await inter.response.defer(ephemeral=True)
            if built["mode"] == "v2":
                await inter.followup.send(
                    components=built["components"],
                    flags=built["flags"],
                    ephemeral=True,
                    allowed_mentions=disnake.AllowedMentions.none(),
                )
            else:
                kwargs: dict = {
                    "ephemeral": True,
                    "allowed_mentions": disnake.AllowedMentions.none(),
                }
                if built.get("content"):
                    kwargs["content"] = built["content"]
                if built.get("embed"):
                    kwargs["embed"] = built["embed"]
                if built.get("components"):
                    kwargs["components"] = built["components"]
                if built.get("files"):
                    kwargs["files"] = built["files"]
                await inter.followup.send(**kwargs)
            return

        # ── Painel admin ───────────────────────────────────────────────────────
        if not cid.startswith("LojaBotaoExtra_"):
            return

        # Navegar para o painel do botão extra
        if cid.startswith("LojaBotaoExtra_Painel:"):
            product_id = cid.split(":", 1)[1]
            mode = db.get_document("custom_mode").get("mode")
            await inter.response.defer()
            panel_data = build_panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return

        # Toggle ativar/desativar
        if cid.startswith("LojaBotaoExtra_Toggle:"):
            product_id = cid.split(":", 1)[1]
            await inter.response.defer()
            cfg = _get_extra_button_cfg(product_id)
            cfg["enabled"] = not cfg.get("enabled", False)
            _save_extra_button_cfg(product_id, cfg)
            # Sincronizar mensagens existentes para adicionar/remover o botão
            await _sync_product_messages(self.bot, product_id)
            mode = db.get_document("custom_mode").get("mode")
            panel_data = build_panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return

        # Editar label
        if cid.startswith("LojaBotaoExtra_EditLabel:"):
            product_id = cid.split(":", 1)[1]
            await inter.response.send_modal(EditLabelModal(product_id))
            return

        # Abrir editor de mensagem
        if cid.startswith("LojaBotaoExtra_ConfigMsg:"):
            product_id = cid.split(":", 1)[1]
            await inter.response.defer()
            mode = db.get_document("custom_mode").get("mode")
            panel_data = build_msg_editor_panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return

        # Modais de configuração de conteúdo
        if cid.startswith("LojaBotaoExtra_DefinirMensagem:"):
            await inter.response.send_modal(DefinirMensagemModal(cid.split(":", 1)[1]))
            return

        if cid.startswith("LojaBotaoExtra_DefinirEmbed:"):
            await inter.response.send_modal(DefinirEmbedModal(cid.split(":", 1)[1]))
            return

        if cid.startswith("LojaBotaoExtra_DefinirImagem:"):
            await inter.response.send_modal(DefinirImagemModal(cid.split(":", 1)[1]))
            return

        if cid.startswith("LojaBotaoExtra_DefinirContainer:"):
            await inter.response.send_modal(DefinirContainerModal(cid.split(":", 1)[1]))
            return

        # Apagar campo específico
        if cid.startswith("LojaBotaoExtra_ApagarCampo:"):
            await inter.response.defer()
            _, field, product_id = cid.split(":", 2)
            cfg = _get_extra_button_cfg(product_id)
            msg = cfg.setdefault("message", {})
            if field == "content":
                msg.pop("content", None)
            elif field == "embed":
                msg.pop("embed", None)
            elif field == "image":
                msg.pop("externalImage", None)
                msg.get("embed", {}).pop("banner", None) if "embed" in msg else None
            elif field == "container":
                msg.pop("container", None)
            _save_extra_button_cfg(product_id, cfg)
            mode = db.get_document("custom_mode").get("mode")
            panel_data = build_msg_editor_panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return

        # Visualizar preview
        if cid.startswith("LojaBotaoExtra_Visualizar:"):
            product_id = cid.split(":", 1)[1]
            await inter.response.defer(ephemeral=True)
            await self._send_preview(inter, product_id)
            return


def setup(bot: commands.Bot):
    bot.add_cog(ExtraButtonCog(bot))
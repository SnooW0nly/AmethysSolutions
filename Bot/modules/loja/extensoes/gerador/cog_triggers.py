"""
cog_triggers.py — Editor de mensagem de entrega dos serviços do Gerador
Usa o mesmo sistema de builder do Anunciar (Builder.build_from_cfg)
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from commands.admin.anunciar.builder import Builder

from .helpers import get_service, update_service


def _accent() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


def _embed_color() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"color": int(hex_.replace("#", ""), 16)}
    return {}


def _mode() -> str:
    return db.get_document("custom_mode").get("mode")


# ──────────────────────────────────────────────────────────
#  Painéis do editor de mensagem
# ──────────────────────────────────────────────────────────

def _msg_status(msg_cfg: dict) -> tuple[bool, bool, bool, bool]:
    has_content = bool(msg_cfg.get("content"))
    embed = msg_cfg.get("embed", {})
    has_embed = bool(embed.get("title") or embed.get("description"))
    has_container = bool(msg_cfg.get("container"))
    has_image = bool(msg_cfg.get("externalImage") or embed.get("banner"))
    return has_content, has_embed, has_container, has_image


def build_msg_editor(mode: str, service_id: str, msg_key: str = "mensagem") -> dict:
    """msg_key = 'mensagem' (entrega) ou 'mensagem_sem_estoque' (sem estoque)"""
    svc = get_service(service_id)
    if not svc:
        from .cog_servicos import build_services_panel
        return build_services_panel(mode)

    msg_cfg = svc.get(msg_key, {})
    has_content, has_embed, has_container, has_image = _msg_status(msg_cfg)
    other_disabled = has_container

    title_label = "Mensagem de Entrega" if msg_key == "mensagem" else "Mensagem Sem Estoque"

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                              custom_id=f"GenMsg_Apagar:content:{service_id}:{msg_key}",
                              disabled=not has_content or other_disabled),
            disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.grey, emoji=emoji.message,
                              custom_id=f"GenMsg_Content:{service_id}:{msg_key}", disabled=other_disabled),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                              custom_id=f"GenMsg_Apagar:embed:{service_id}:{msg_key}",
                              disabled=not has_embed or other_disabled),
            disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.grey, emoji=emoji.embed,
                              custom_id=f"GenMsg_Embed:{service_id}:{msg_key}", disabled=other_disabled),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                              custom_id=f"GenMsg_Apagar:image:{service_id}:{msg_key}",
                              disabled=not has_image),
            disnake.ui.Button(label="Definir Imagem", style=disnake.ButtonStyle.grey, emoji=emoji.image,
                              custom_id=f"GenMsg_Image:{service_id}:{msg_key}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                              custom_id=f"GenMsg_Apagar:container:{service_id}:{msg_key}",
                              disabled=not has_container),
            disnake.ui.Button(label="Definir Container", style=disnake.ButtonStyle.grey, emoji=emoji.commands,
                              custom_id=f"GenMsg_Container:{service_id}:{msg_key}",
                              disabled=(has_content or has_embed) and not has_container),
        ),
    ]

    has_any = has_content or has_embed or has_container or has_image
    action_row = disnake.ui.ActionRow(
        disnake.ui.Button(label="Visualizar", emoji=emoji.search, style=disnake.ButtonStyle.grey,
                          custom_id=f"GenMsg_Preview:{service_id}:{msg_key}", disabled=not has_any),
    )

    vars_info = (
        f"-# Variáveis disponíveis: `{{user}}` `{{servico}}` `{{item}}` `{{quem_gerou}}`\n"
        f"-# Use `{{item}}` para inserir o conteúdo do estoque na mensagem."
    )

    if mode == "embed":
        embed = disnake.Embed(
            title=f"Editor: {title_label}",
            description=f"-# Painel > Gerador > {svc['nome']} > **{title_label}**\n\n{vars_info}",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [action_row, disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                              custom_id=f"Gerador_Servico_Detalhe:{service_id}")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerador > {svc['nome']} > **{title_label}**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(vars_info),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                action_row,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Gerador_Servico_Detalhe:{service_id}")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


# ──────────────────────────────────────────────────────────
#  Modais
# ──────────────────────────────────────────────────────────

class ContentModal(disnake.ui.Modal):
    def __init__(self, service_id: str, msg_key: str):
        self.service_id = service_id
        self.msg_key = msg_key
        svc = get_service(service_id) or {}
        current = svc.get(msg_key, {}).get("content") or ""
        super().__init__(
            title="Definir Mensagem de Texto",
            custom_id=f"GenMsg_ContentModal:{service_id}:{msg_key}",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo (use {user}, {item}, {servico})",
                    custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    value=current, required=True, max_length=2000,
                    placeholder="✅ {user} aqui está o {servico}!\n\n`{item}`",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        svc = get_service(self.service_id) or {}
        msg_cfg = svc.get(self.msg_key, {})
        msg_cfg["content"] = inter.text_values["content"]
        msg_cfg.pop("container", None)
        update_service(self.service_id, {self.msg_key: msg_cfg})
        mode = _mode()
        panel = build_msg_editor(mode, self.service_id, self.msg_key)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class EmbedModal(disnake.ui.Modal):
    def __init__(self, service_id: str, msg_key: str):
        self.service_id = service_id
        self.msg_key = msg_key
        svc = get_service(service_id) or {}
        embed_data = svc.get(msg_key, {}).get("embed", {})
        super().__init__(
            title="Definir Embed",
            custom_id=f"GenMsg_EmbedModal:{service_id}:{msg_key}",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="title",
                                     value=embed_data.get("title") or "", required=False, max_length=256),
                disnake.ui.TextInput(label="Descrição (use {user}, {item}, {servico})", custom_id="description",
                                     style=disnake.TextInputStyle.paragraph,
                                     value=embed_data.get("description") or "", required=True, max_length=4000),
                disnake.ui.TextInput(label="Cor hex", custom_id="color",
                                     value=embed_data.get("color") or "", required=False, max_length=7),
                disnake.ui.TextInput(label="Footer", custom_id="footer",
                                     value=embed_data.get("footer") or "", required=False, max_length=2048),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        svc = get_service(self.service_id) or {}
        msg_cfg = svc.get(self.msg_key, {})
        msg_cfg.setdefault("embed", {})
        msg_cfg["embed"]["title"] = inter.text_values.get("title") or None
        msg_cfg["embed"]["description"] = inter.text_values.get("description") or None
        msg_cfg["embed"]["color"] = inter.text_values.get("color") or None
        msg_cfg["embed"]["footer"] = inter.text_values.get("footer") or None
        msg_cfg.pop("container", None)
        update_service(self.service_id, {self.msg_key: msg_cfg})
        mode = _mode()
        panel = build_msg_editor(mode, self.service_id, self.msg_key)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class ImageModal(disnake.ui.Modal):
    def __init__(self, service_id: str, msg_key: str):
        self.service_id = service_id
        self.msg_key = msg_key
        svc = get_service(service_id) or {}
        msg_cfg = svc.get(msg_key, {})
        embed_data = msg_cfg.get("embed", {})
        super().__init__(
            title="Definir Imagens",
            custom_id=f"GenMsg_ImageModal:{service_id}:{msg_key}",
            components=[
                disnake.ui.TextInput(label="URL imagem externa", custom_id="externalImage",
                                     value=msg_cfg.get("externalImage") or "", required=False, max_length=500),
                disnake.ui.TextInput(label="URL banner do embed", custom_id="banner",
                                     value=embed_data.get("banner") or "", required=False, max_length=500),
                disnake.ui.TextInput(label="URL thumbnail do embed", custom_id="thumbnail",
                                     value=embed_data.get("thumbnail") or "", required=False, max_length=500),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        svc = get_service(self.service_id) or {}
        msg_cfg = svc.get(self.msg_key, {})
        msg_cfg["externalImage"] = inter.text_values.get("externalImage") or None
        msg_cfg.setdefault("embed", {})
        msg_cfg["embed"]["banner"] = inter.text_values.get("banner") or None
        msg_cfg["embed"]["thumbnail"] = inter.text_values.get("thumbnail") or None
        update_service(self.service_id, {self.msg_key: msg_cfg})
        mode = _mode()
        panel = build_msg_editor(mode, self.service_id, self.msg_key)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class ContainerModal(disnake.ui.Modal):
    def __init__(self, service_id: str, msg_key: str):
        self.service_id = service_id
        self.msg_key = msg_key
        svc = get_service(service_id) or {}
        current = svc.get(msg_key, {}).get("container") or ""
        super().__init__(
            title="Definir Container",
            custom_id=f"GenMsg_ContainerModal:{service_id}:{msg_key}",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo (use {user}, {item}, {servico})",
                    custom_id="container",
                    style=disnake.TextInputStyle.paragraph,
                    value=current, required=True, max_length=4000,
                    placeholder="{{color:#5865F2}}\n✅ {user} aqui está o {servico}!\n\n`{item}`",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        svc = get_service(self.service_id) or {}
        msg_cfg = svc.get(self.msg_key, {})
        msg_cfg["container"] = inter.text_values["container"]
        msg_cfg.pop("content", None)
        msg_cfg.pop("embed", None)
        update_service(self.service_id, {self.msg_key: msg_cfg})
        mode = _mode()
        panel = build_msg_editor(mode, self.service_id, self.msg_key)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


# ──────────────────────────────────────────────────────────
#  Painel seletor: mensagem de entrega vs sem estoque
# ──────────────────────────────────────────────────────────

def build_msg_selector(mode: str, service_id: str) -> dict:
    svc = get_service(service_id)
    if not svc:
        from .cog_servicos import build_services_panel
        return build_services_panel(mode)

    entrega_cfg = svc.get("mensagem", {})
    sem_estoque_cfg = svc.get("mensagem_sem_estoque", {})
    h1, h2, h3, h4 = _msg_status(entrega_cfg)
    h5, h6, h7, h8 = _msg_status(sem_estoque_cfg)

    entrega_ok = h1 or h2 or h3 or h4
    sem_estoque_ok = h5 or h6 or h7 or h8

    body = (
        f"{emoji.correct if entrega_ok else emoji.wrong} **Mensagem de Entrega:** {'Configurada' if entrega_ok else 'Não configurada'}\n"
        f"{emoji.correct if sem_estoque_ok else emoji.wrong} **Mensagem Sem Estoque:** {'Configurada' if sem_estoque_ok else 'Não configurada'}\n\n"
        f"-# A mensagem de entrega é enviada com o item do estoque.\n"
        f"-# A mensagem sem estoque é enviada quando não há itens disponíveis (e stock fake está OFF)."
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Editar: Entrega", emoji=emoji.correct, style=disnake.ButtonStyle.green,
                              custom_id=f"GenMsg_Open:{service_id}:mensagem"),
            disnake.ui.Button(label="Editar: Sem Estoque", emoji=emoji.wrong, style=disnake.ButtonStyle.red,
                              custom_id=f"GenMsg_Open:{service_id}:mensagem_sem_estoque"),
        ),
    ]

    if mode == "embed":
        embed = disnake.Embed(
            title=f"Mensagens: {svc['nome']}",
            description=f"-# Painel > Gerador > {svc['nome']} > **Mensagens**\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                              custom_id=f"Gerador_Servico_Detalhe:{service_id}")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerador > {svc['nome']} > **Mensagens**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Gerador_Servico_Detalhe:{service_id}")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


# ──────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────

class GeradorTriggersCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send(self, inter, panel: dict):
        mode = _mode()
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
            await inter.edit_original_message(**panel, flags=flags)

    async def _wait_send(self, inter, panel: dict):
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        await self._send(inter, panel)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        if cid.startswith("Gerador_Servico_Mensagem:"):
            sid = cid.split(":", 1)[1]
            await self._wait_send(inter, build_msg_selector(_mode(), sid))

        elif cid.startswith("GenMsg_Open:"):
            _, sid, msg_key = cid.split(":", 2)
            await self._wait_send(inter, build_msg_editor(_mode(), sid, msg_key))

        elif cid.startswith("GenMsg_Content:"):
            _, sid, msg_key = cid.split(":", 2)
            await inter.response.send_modal(ContentModal(sid, msg_key))

        elif cid.startswith("GenMsg_Embed:"):
            _, sid, msg_key = cid.split(":", 2)
            await inter.response.send_modal(EmbedModal(sid, msg_key))

        elif cid.startswith("GenMsg_Image:"):
            _, sid, msg_key = cid.split(":", 2)
            await inter.response.send_modal(ImageModal(sid, msg_key))

        elif cid.startswith("GenMsg_Container:"):
            _, sid, msg_key = cid.split(":", 2)
            await inter.response.send_modal(ContainerModal(sid, msg_key))

        elif cid.startswith("GenMsg_Apagar:"):
            parts = cid.split(":", 3)
            field = parts[1]
            sid = parts[2]
            msg_key = parts[3]
            svc = get_service(sid) or {}
            msg_cfg = svc.get(msg_key, {})
            if field == "content":
                msg_cfg.pop("content", None)
            elif field == "embed":
                msg_cfg.pop("embed", None)
            elif field == "container":
                msg_cfg.pop("container", None)
            elif field == "image":
                msg_cfg.pop("externalImage", None)
                msg_cfg.get("embed", {}).pop("banner", None)
                msg_cfg.get("embed", {}).pop("thumbnail", None)
            update_service(sid, {msg_key: msg_cfg})
            await self._wait_send(inter, build_msg_editor(_mode(), sid, msg_key))

        elif cid.startswith("GenMsg_Preview:"):
            _, sid, msg_key = cid.split(":", 2)
            svc = get_service(sid) or {}
            msg_cfg = svc.get(msg_key, {})
            # Substituir variáveis por exemplos
            preview_item = "exemplo:senha123"
            preview_cfg = _replace_vars_in_cfg(msg_cfg, inter.user, svc["nome"], preview_item, inter.user)
            built = Builder.build_from_cfg({"message": preview_cfg})
            await inter.response.defer(ephemeral=True)
            try:
                if built["mode"] == "v2":
                    await inter.followup.send(
                        components=built["components"], flags=built["flags"],
                        ephemeral=True, allowed_mentions=disnake.AllowedMentions.none(),
                    )
                else:
                    kw = {"ephemeral": True, "allowed_mentions": disnake.AllowedMentions.none()}
                    if built.get("content"):
                        kw["content"] = built["content"]
                    if built.get("embed"):
                        kw["embed"] = built["embed"]
                    if built.get("components"):
                        kw["components"] = built["components"]
                    await inter.followup.send(**kw)
            except Exception as e:
                await inter.followup.send(f"Erro na preview: {e}", ephemeral=True)


def _replace_vars_in_cfg(msg_cfg: dict, user, service_name: str, item: str, quem_gerou) -> dict:
    """Substitui variáveis {user}, {item}, {servico}, {quem_gerou} em todos os campos de texto."""
    import copy, json
    data = copy.deepcopy(msg_cfg)
    replacements = {
        "{user}": user.mention if user else "@usuário",
        "{item}": item or "(item do estoque)",
        "{servico}": service_name,
        "{quem_gerou}": quem_gerou.mention if quem_gerou else "@moderador",
    }
    raw = json.dumps(data)
    for k, v in replacements.items():
        raw = raw.replace(k, v)
    return json.loads(raw)

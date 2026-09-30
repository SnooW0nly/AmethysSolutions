import disnake
from disnake.ext import commands
from typing import Optional, Dict, Any

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message
from commands.admin.anunciar.builder import Builder
from commands.admin.anunciar.components.helper import Helper as AnunciarHelper


DB_KEY = "roblox_mensagem"


def _get_msg_cfg() -> Dict[str, Any]:
    data = db.get_document(DB_KEY) or {}
    if "message" not in data:
        data["message"] = {
            "content": None,
            "container": None,
            "embed": {
                "title": None,
                "description": None,
                "color": None,
                "footer": None,
                "banner": None,
                "thumbnail": None,
            },
            "externalImage": None,
            "buttons": [],
        }
    return data


def _save_msg_cfg(data: dict):
    db.save_document(DB_KEY, data)


def _is_v2(cfg: dict) -> bool:
    """Auto-detecta modo v2 com base no container ou imagem externa sem conteúdo embed."""
    msg = cfg.get("message", {})
    return bool(msg.get("container") or (msg.get("externalImage") and not msg.get("embed", {}).get("description") and not msg.get("embed", {}).get("title")))


def _build_editor_panel(mode: str):
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")
    cfg = _get_msg_cfg()
    msg = cfg.get("message", {})

    has_content = bool(msg.get("content"))
    has_container = bool(msg.get("container"))
    has_embed = bool(msg.get("embed", {}).get("title") or msg.get("embed", {}).get("description"))
    has_image = bool(msg.get("externalImage"))

    status_content = "✅" if has_content else "❌"
    status_container = "✅" if has_container else "❌"
    status_embed = "✅" if has_embed else "❌"
    status_image = "✅" if has_image else "❌"

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=(
                f"-# Painel > Roblox > **Configurar Mensagem**\n\n"
                f"Configure a mensagem que será postada no painel de compra de Robux.\n\n"
                f"-# Content: `{status_content}` | Container: `{status_container}` | Embed: `{status_embed}` | Imagem: `{status_image}`"
            )
        )
        if embed_color:
            embed.color = embed_color

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="RobloxMsg_Content"),
                disnake.ui.Button(label="Definir Container", style=disnake.ButtonStyle.blurple, emoji=emoji.commands, custom_id="RobloxMsg_Container"),
                disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="RobloxMsg_Embed"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Definir Imagens", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="RobloxMsg_Imagens"),
                disnake.ui.Button(label="Limpar Tudo", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="RobloxMsg_LimparTudo"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Botão Robux", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Roblox_EditarBotaoRobux"),
                disnake.ui.Button(label="Editar Botão Gamepass", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Roblox_EditarBotaoGamepass"),
                disnake.ui.Button(label="Editar Botão Calcular", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Roblox_EditarBotaoCalcular"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.commands, custom_id="RobloxMsg_Visualizar"),
                disnake.ui.Button(label="Postar Mensagem", style=disnake.ButtonStyle.green, emoji=emoji.arrow, custom_id="RobloxMsg_Postar"),
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Roblox_PainelPrincipal"),
            ),
        ]
        return (embed, components), None

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    components = [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Roblox > **Configurar Mensagem**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"Configure a mensagem que será postada no painel de compra de Robux.\n"
                f"-# Content: `{status_content}` | Container: `{status_container}` | Embed: `{status_embed}` | Imagem: `{status_image}`"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="RobloxMsg_Content"),
                disnake.ui.Button(label="Definir Container", style=disnake.ButtonStyle.blurple, emoji=emoji.commands, custom_id="RobloxMsg_Container"),
                disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="RobloxMsg_Embed"),
                disnake.ui.Button(label="Definir Imagens", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="RobloxMsg_Imagens"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Botão Robux", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Roblox_EditarBotaoRobux"),
                disnake.ui.Button(label="Editar Botão Gamepass", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Roblox_EditarBotaoGamepass"),
                disnake.ui.Button(label="Editar Botão Calcular", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Roblox_EditarBotaoCalcular"),
            ),
            **container_kwargs,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Roblox_PainelPrincipal"),
            disnake.ui.Button(label="Limpar Tudo", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="RobloxMsg_LimparTudo"),
            disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.commands, custom_id="RobloxMsg_Visualizar"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Postar Mensagem", style=disnake.ButtonStyle.green, emoji=emoji.arrow, custom_id="RobloxMsg_Postar"),
        ),
    ]
    return components, disnake.MessageFlags(is_components_v2=True)


def _build_postar_panel(mode: str):
    """Painel de seleção de canal para postar a mensagem — sem modais."""
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=(
                f"-# Painel > Roblox > Configurar Mensagem > **Postar**\n\n"
                f"Selecione o canal onde deseja postar a mensagem do painel Roblox."
            )
        )
        if embed_color:
            embed.color = embed_color
        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="RobloxMsg_CanalSelecionado",
                    placeholder="Selecione o canal de texto",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RobloxMsg_VoltarEditor"),
            ),
        ]
        return (embed, components), None

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    components = [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Roblox > Configurar Mensagem > **Postar**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay("Selecione o canal onde deseja postar a mensagem do painel Roblox."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="RobloxMsg_CanalSelecionado",
                    placeholder="Selecione o canal de texto",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            ),
            **container_kwargs,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RobloxMsg_VoltarEditor"),
        ),
    ]
    return components, disnake.MessageFlags(is_components_v2=True)


def _build_roblox_action_buttons(config: dict) -> list:
    btn_robux = config.get("btn_robux", {})
    btn_gamepass = config.get("btn_gamepass", {})
    btn_calcular = config.get("btn_calcular", {})

    def style_from_str(s):
        return {
            "blurple": disnake.ButtonStyle.blurple,
            "green": disnake.ButtonStyle.green,
            "red": disnake.ButtonStyle.red,
            "grey": disnake.ButtonStyle.grey,
            "gray": disnake.ButtonStyle.grey,
        }.get(str(s).lower(), disnake.ButtonStyle.blurple)

    def parse_emoji(e):
        if not e:
            return None
        if isinstance(e, str) and e.startswith("<"):
            try:
                return disnake.PartialEmoji.from_str(e)
            except Exception:
                return None
        return e

    roblox_config = db.get_document("roblox_config") or {}
    robux_enabled = roblox_config.get("robux_sale_enabled", True)
    gamepass_enabled = roblox_config.get("gamepass_sale_enabled", True)

    buttons = []

    if robux_enabled and gamepass_enabled:
        # Ambos ativos → botão unificado que abre ephemeral com as 2 opções
        buttons.append(
            disnake.ui.Button(
                label="Comprar",
                style=style_from_str(btn_robux.get("style", "blurple")),
                emoji=emoji.cart,
                custom_id="Roblox_SelecionarTipo",
            )
        )
    else:
        # Só um ativo → mostra direto
        if robux_enabled:
            buttons.append(
                disnake.ui.Button(
                    label=btn_robux.get("label", "Comprar Robux"),
                    style=style_from_str(btn_robux.get("style", "blurple")),
                    emoji=parse_emoji(btn_robux.get("emoji")),
                    custom_id="Roblox_ComprarRobux",
                )
            )
        if gamepass_enabled:
            buttons.append(
                disnake.ui.Button(
                    label=btn_gamepass.get("label", "Comprar Gamepass"),
                    style=style_from_str(btn_gamepass.get("style", "blurple")),
                    emoji=parse_emoji(btn_gamepass.get("emoji")),
                    custom_id="Roblox_ComprarGamepass",
                )
            )

    buttons.append(
        disnake.ui.Button(
            label=btn_calcular.get("label", "Calcular Preço"),
            style=style_from_str(btn_calcular.get("style", "grey")),
            emoji=parse_emoji(btn_calcular.get("emoji")),
            custom_id="Roblox_CalcularPreco",
        )
    )
    return [disnake.ui.ActionRow(*buttons)] if buttons else []


async def _postar_em_canal(inter, channel: disnake.TextChannel):
    """Efetua o envio da mensagem Roblox no canal indicado."""
    cfg = _get_msg_cfg()
    roblox_config = db.get_document("roblox_config") or {}
    action_rows = _build_roblox_action_buttons(roblox_config)
    built = await Builder.build_from_cfg(cfg)

    if built["mode"] == "v2":
        # Container — action_rows ficam fora do container (sem content/embed juntos)
        all_components = built["components"] + action_rows
        posted_msg = await channel.send(
            components=all_components,
            flags=built["flags"],
            allowed_mentions=disnake.AllowedMentions.none(),
        )
    else:
        posted_msg = await channel.send(
            content=built.get("content"),
            embed=built.get("embed"),
            components=(built.get("components") or []) + action_rows,
            files=built.get("files") or None,
            allowed_mentions=disnake.AllowedMentions.none(),
        )

    roblox_config["posted_message_id"] = posted_msg.id
    roblox_config["posted_channel_id"] = channel.id
    db.save_document("roblox_config", roblox_config)
    return posted_msg


class ContentModal(disnake.ui.Modal):
    def __init__(self):
        cfg = _get_msg_cfg()
        super().__init__(
            title="Definir Mensagem (Content)",
            custom_id="RobloxMsg_ContentModal",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem",
                    custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=2000,
                    value=cfg.get("message", {}).get("content", "") or "",
                    placeholder="Conteúdo da mensagem (texto simples)",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        cfg = _get_msg_cfg()
        val = inter.resolved_values.get("content", "").strip()
        cfg["message"]["content"] = val if val else None
        _save_msg_cfg(cfg)
        components, flags = _build_editor_panel(mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)


class ContainerModal(disnake.ui.Modal):
    def __init__(self):
        cfg = _get_msg_cfg()
        super().__init__(
            title="Definir Container",
            custom_id="RobloxMsg_ContainerModal",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container",
                    custom_id="container_content",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=2000,
                    value=cfg.get("message", {}).get("container", "") or "",
                    placeholder="Use {{separator}}, {{color:#RRGGBB}}, {{image url='...'}}",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        cfg = _get_msg_cfg()
        val = inter.resolved_values.get("container_content", "").strip()
        cfg["message"]["container"] = val if val else None
        _save_msg_cfg(cfg)
        components, flags = _build_editor_panel(mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)


class EmbedModal(disnake.ui.Modal):
    def __init__(self):
        cfg = _get_msg_cfg()
        embed_data = cfg.get("message", {}).get("embed", {}) or {}
        super().__init__(
            title="Definir Embed",
            custom_id="RobloxMsg_EmbedModal",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="embed_title", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("title", "") or ""),
                disnake.ui.TextInput(label="Descrição", custom_id="embed_description", style=disnake.TextInputStyle.paragraph, required=False, value=embed_data.get("description", "") or "", placeholder="Descrição do embed"),
                disnake.ui.TextInput(label="Cor (Hex)", custom_id="embed_color", style=disnake.TextInputStyle.short, required=False, placeholder="#FFFFFF", value=embed_data.get("color", "") or ""),
                disnake.ui.TextInput(label="Footer", custom_id="embed_footer", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("footer", "") or ""),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        cfg = _get_msg_cfg()
        v = inter.resolved_values
        cfg["message"]["embed"]["title"] = v.get("embed_title", "").strip() or None
        cfg["message"]["embed"]["description"] = v.get("embed_description", "").strip() or None
        cfg["message"]["embed"]["color"] = v.get("embed_color", "").strip() or None
        cfg["message"]["embed"]["footer"] = v.get("embed_footer", "").strip() or None
        _save_msg_cfg(cfg)
        components, flags = _build_editor_panel(mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)


class ImagensModal(disnake.ui.Modal):
    def __init__(self):
        cfg = _get_msg_cfg()
        embed_data = cfg.get("message", {}).get("embed", {}) or {}
        super().__init__(
            title="Definir Imagens",
            custom_id="RobloxMsg_ImagensModal",
            components=[
                disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage", style=disnake.TextInputStyle.short, required=False, value=cfg.get("message", {}).get("externalImage", "") or ""),
                disnake.ui.TextInput(label="URL do Banner do Embed", custom_id="banner", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("banner", "") or ""),
                disnake.ui.TextInput(label="URL da Thumbnail do Embed", custom_id="thumbnail", style=disnake.TextInputStyle.short, required=False, value=embed_data.get("thumbnail", "") or ""),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        cfg = _get_msg_cfg()
        v = inter.resolved_values
        cfg["message"]["externalImage"] = v.get("externalImage", "").strip() or None
        cfg["message"]["embed"]["banner"] = v.get("banner", "").strip() or None
        cfg["message"]["embed"]["thumbnail"] = v.get("thumbnail", "").strip() or None
        _save_msg_cfg(cfg)
        components, flags = _build_editor_panel(mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)


class RobloxMensagemEditor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @classmethod
    async def open_editor(cls, inter: disnake.MessageInteraction, mode: str):
        components, flags = _build_editor_panel(mode)
        if inter.response.is_done():
            # Chamado após defer() — usar edit_original_message
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)
        else:
            # Chamado de modal callback — usar response.edit_message
            if mode == "embed":
                embed, comps = components
                await inter.response.edit_message(content=None, embed=embed, components=comps)
            else:
                await inter.response.edit_message(components=components, flags=flags)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""

        if custom_id == "RobloxMsg_Content":
            await inter.response.send_modal(ContentModal())

        elif custom_id == "RobloxMsg_Container":
            await inter.response.send_modal(ContainerModal())

        elif custom_id == "RobloxMsg_Embed":
            await inter.response.send_modal(EmbedModal())

        elif custom_id == "RobloxMsg_Imagens":
            await inter.response.send_modal(ImagensModal())

        elif custom_id == "RobloxMsg_Postar":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            components, flags = _build_postar_panel(mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "RobloxMsg_VoltarEditor":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            components, flags = _build_editor_panel(mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "RobloxMsg_LimparTudo":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = _get_msg_cfg()
            cfg["message"]["content"] = None
            cfg["message"]["container"] = None
            cfg["message"]["externalImage"] = None
            cfg["message"]["buttons"] = []
            for k in cfg["message"]["embed"]:
                cfg["message"]["embed"][k] = None
            _save_msg_cfg(cfg)
            components, flags = _build_editor_panel(mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "RobloxMsg_Visualizar":
            cfg = _get_msg_cfg()
            roblox_config = db.get_document("roblox_config") or {}
            action_rows = _build_roblox_action_buttons(roblox_config)
            built = await Builder.build_from_cfg(cfg)
            try:
                if built["mode"] == "v2":
                    all_components = built["components"] + action_rows
                    await inter.response.send_message(
                        components=all_components,
                        flags=built["flags"],
                        ephemeral=True,
                        allowed_mentions=disnake.AllowedMentions.none(),
                    )
                else:
                    kwargs = {"ephemeral": True, "allowed_mentions": disnake.AllowedMentions.none()}
                    if built.get("content"):
                        kwargs["content"] = built["content"]
                    if built.get("embed"):
                        kwargs["embed"] = built["embed"]
                    final_components = (built.get("components") or []) + action_rows
                    if final_components:
                        kwargs["components"] = final_components
                    if built.get("files"):
                        kwargs["files"] = built["files"]
                    await inter.response.send_message(**kwargs)
            except Exception as e:
                await inter.response.send_message(f"Erro ao visualizar: {e}", ephemeral=True)

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "RobloxMsg_CanalSelecionado":
            return

        await inter.response.defer()
        mode = db.get_document("custom_mode").get("mode")

        # Obter canal selecionado
        selected = inter.values[0] if inter.values else None
        channel = None
        if selected:
            try:
                channel_id = int(selected)
                channel = inter.guild.get_channel(channel_id) or self.bot.get_channel(channel_id)
            except Exception:
                pass

        if not channel or not hasattr(channel, "send"):
            await message.error(inter, "Canal inválido ou sem permissão de acesso.", followup=True)
            return

        try:
            posted_msg = await _postar_em_canal(inter, channel)
        except Exception as e:
            await message.error(inter, f"Erro ao postar mensagem: {e}", followup=True)
            return

        # Voltar ao editor com confirmação
        components, flags = _build_editor_panel(mode)
        if mode == "embed":
            embed_obj, comps = components
            await inter.edit_original_message(content=None, embed=embed_obj, components=comps)
        else:
            await inter.edit_original_message(components=components, flags=flags)

        await message.success(
            inter,
            f"Mensagem postada com sucesso em {channel.mention} (`{posted_msg.id}`)",
            followup=True,
            component=[
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Ir para a mensagem", url=posted_msg.jump_url)
                )
            ],
        )


def setup(bot: commands.Bot):
    bot.add_cog(RobloxMensagemEditor(bot))
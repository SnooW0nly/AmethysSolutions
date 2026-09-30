import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from functions.perms import perms
from commands.admin.anunciar.builder import Builder
import re
import aiohttp
import uuid


def get_webhook_system_data() -> dict:
    """Obtém os dados gerais do sistema de webhook."""
    return db.get_document("webhook_system") or {}


def save_webhook_system_data(data: dict):
    """Salva os dados gerais do sistema de webhook."""
    db.save_document("webhook_system", data)


def get_webhook_editor_data() -> dict:
    """Obtém os dados da mensagem no editor da webhook."""
    data = get_webhook_system_data()
    return data.get("mensagem", {})


def set_webhook_editor_data(editor_data: dict):
    """Define os dados completos da mensagem no editor."""
    data = get_webhook_system_data()
    data["mensagem"] = editor_data
    save_webhook_system_data(data)


def set_webhook_editor_field(field: str, value):
    """Define um campo no editor de mensagem."""
    editor_data = get_webhook_editor_data()
    editor_data[field] = value
    set_webhook_editor_data(editor_data)
    return True


def clear_webhook_editor_field(field: str):
    """Limpa um campo do editor de mensagem."""
    editor_data = get_webhook_editor_data()
    if field in editor_data:
        del editor_data[field]
        set_webhook_editor_data(editor_data)
        return True
    return False


async def download_image(url: str) -> bytes:
    """Faz o download de uma imagem a partir de uma URL para bytes."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception:
        pass
    return None


class Webhook_DefinirMensagemModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = get_webhook_editor_data()
        super().__init__(
            title="Definir Mensagem",
            custom_id="Webhook_DefinirMensagemModal",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem",
                    custom_id="message",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Digite a mensagem que deseja enviar",
                    value=editor_data.get("content", ""),
                    max_length=2000,
                    required=True
                )
            ],
        )


class Webhook_DefinirEmbedModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = get_webhook_editor_data()
        embed_data = editor_data.get("embed", {})
        super().__init__(
            title="Definir Embed",
            custom_id="Webhook_DefinirEmbedModal",
            components=[
                disnake.ui.TextInput(
                    label="Título",
                    custom_id="embed_title",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=embed_data.get("title", "")
                ),
                disnake.ui.TextInput(
                    label="Descrição",
                    custom_id="embed_description",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Descrição do embed aqui",
                    required=True,
                    value=embed_data.get("description", "")
                ),
                disnake.ui.TextInput(
                    label="Cor (Hex)",
                    custom_id="embed_color",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    placeholder="#FFFFFF",
                    value=embed_data.get("color", "")
                ),
                disnake.ui.TextInput(
                    label="Footer",
                    custom_id="embed_footer",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=embed_data.get("footer", "")
                ),
            ]
        )


class Webhook_DefinirImagensModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = get_webhook_editor_data()
        embed_data = editor_data.get("embed", {})
        has_embed = bool(embed_data.get("title") or embed_data.get("description"))

        components = [
            disnake.ui.TextInput(
                label="URL da imagem externa",
                custom_id="externalImage",
                style=disnake.TextInputStyle.short,
                required=False,
                value=editor_data.get("externalImage", "")
            ),
        ]

        if has_embed:
            components.extend([
                disnake.ui.TextInput(
                    label="URL do Banner do Embed",
                    custom_id="banner",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=embed_data.get("banner", "")
                ),
                disnake.ui.TextInput(
                    label="URL da Thumbnail do Embed",
                    custom_id="thumbnail",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    value=embed_data.get("thumbnail", "")
                ),
            ])
        
        super().__init__(
            title="Definir Imagens",
            custom_id="Webhook_DefinirImagensModal",
            components=components
        )


class Webhook_DefinirBotoesModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar Botão",
            custom_id="Webhook_DefinirBotoesModal",
            components=[
                disnake.ui.TextInput(
                    label="Label",
                    custom_id="button_label",
                    required=True,
                    max_length=80
                ),
                disnake.ui.TextInput(
                    label="URL (Obrigatório para botões de link)",
                    custom_id="button_url",
                    placeholder="https://exemplo.com",
                    required=False
                ),
                disnake.ui.TextInput(
                    label="Emoji (Opcional)",
                    custom_id="button_emoji",
                    required=False
                ),
            ]
        )


class Webhook_CriarModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Nova Webhook",
            custom_id="Webhook_CriarModal",
            components=[
                disnake.ui.TextInput(
                    label="Nome da Webhook",
                    custom_id="webhook_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=80
                )
            ]
        )


class Webhook_EditarNomeModal(disnake.ui.Modal):
    def __init__(self, current_name: str):
        super().__init__(
            title="Editar Nome da Webhook",
            custom_id="Webhook_EditarNomeModal",
            components=[
                disnake.ui.TextInput(
                    label="Novo Nome",
                    custom_id="webhook_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    value=current_name,
                    max_length=80
                )
            ]
        )


class Webhook_EditarAvatarModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Editar Avatar da Webhook",
            custom_id="Webhook_EditarAvatarModal",
            components=[
                disnake.ui.TextInput(
                    label="URL da Imagem",
                    custom_id="webhook_avatar_url",
                    style=disnake.TextInputStyle.short,
                    placeholder="https://exemplo.com/imagem.png",
                    required=True
                )
            ]
        )


class WebhookCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def get_accent_color() -> dict:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            return {"accent_colour": disnake.Colour(primary_color)}
        return {}

    @staticmethod
    def get_embed_color() -> dict:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        if primary_color_hex:
            return {"color": int(primary_color_hex.replace("#", ""), 16)}
        return {}

    def PainelPrincipal(self, webhooks: list[disnake.Webhook]) -> list[disnake.ui.Container]:
        container_kwargs = self.get_accent_color()
        
        containers = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Webhooks > **Menu Principal**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Selecione uma webhook existente para gerenciar ou crie uma nova."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                **container_kwargs,
            )
        ]

        if webhooks:
            options = []
            for wh in webhooks[:25]:
                options.append(
                    disnake.SelectOption(
                        label=wh.name or "Sem Nome",
                        description=f"Canal: #{wh.channel.name}" if wh.channel else "Sem canal",
                        value=str(wh.id),
                        emoji=emoji.route
                    )
                )
            
            containers[0].add_child(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione uma webhook",
                        custom_id="Webhook_Selecionar",
                        options=options
                    )
                )
            )
        else:
            containers[0].add_child(
                disnake.ui.TextDisplay("Nenhuma webhook encontrada no servidor.")
            )

        containers.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Criar Webhook",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.plus,
                    custom_id="Webhook_IniciarCriacao"
                )
            )
        )
        return containers

    def PainelGerenciar(self, webhook: disnake.Webhook) -> list[disnake.ui.Container]:
        container_kwargs = self.get_accent_color()
        
        channel_name = f"#{webhook.channel.name}" if webhook.channel else "Desconhecido"
        
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Webhooks > **Gerenciar**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**Nome:** `{webhook.name}`\n**Canal:** `{channel_name}`\n**ID:** `{webhook.id}`"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Alterar Nome",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.edit,
                        custom_id="Webhook_EditarNome"
                    ),
                    disnake.ui.Button(
                        label="Alterar Avatar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.image,
                        custom_id="Webhook_EditarAvatar"
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        placeholder="Alterar canal da webhook",
                        custom_id="Webhook_AlterarCanal",
                        channel_types=[disnake.ChannelType.text, disnake.ChannelType.news]
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Webhook_VoltarPrincipal"
                ),
                disnake.ui.Button(
                    label="Configurar Mensagem",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.message,
                    custom_id="Webhook_AbrirEditor"
                ),
                disnake.ui.Button(
                    label="Apagar Webhook",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id="Webhook_Apagar"
                )
            )
        ]

    def PainelEditor(self) -> list[disnake.ui.Container]:
        container_kwargs = self.get_accent_color()
        editor_data = get_webhook_editor_data()
        
        has_message = bool(editor_data.get("content"))
        embed_data = editor_data.get("embed", {})
        has_embed = any(embed_data.get(k) for k in ("title", "description", "footer"))
        has_image = bool(editor_data.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
        botoes = editor_data.get("botoes", [])
        has_buttons = isinstance(botoes, list) and len(botoes) > 0
        limite_botoes = isinstance(botoes, list) and len(botoes) >= 5

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Webhooks > **Editor de Mensagem**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Configure a mensagem que será enviada através da webhook selecionada."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="Webhook_ApagarCampo:content",
                        disabled=not has_message
                    ),
                    disnake.ui.Button(
                        label="Definir Mensagem",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.message,
                        custom_id="Webhook_DefinirMensagem"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="Webhook_ApagarCampo:embed",
                        disabled=not has_embed
                    ),
                    disnake.ui.Button(
                        label="Definir Embed",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.embed,
                        custom_id="Webhook_DefinirEmbed"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="Webhook_ApagarImagensMulti",
                        disabled=not has_image
                    ),
                    disnake.ui.Button(
                        label="Definir Imagens",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.image,
                        custom_id="Webhook_DefinirImagens"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="Webhook_ApagarCampo:botoes",
                        disabled=not has_buttons
                    ),
                    disnake.ui.Button(
                        label="Gerenciar Botões" if has_buttons else "Adicionar Botão",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.edit if has_buttons else emoji.plus,
                        custom_id="Webhook_GerenciarBotoes",
                        disabled=limite_botoes
                    ),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Webhook_VoltarGerenciar"
                ),
                disnake.ui.Button(
                    label="Enviar",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.correct,
                    custom_id="Webhook_EnviarMensagem",
                    disabled=not (has_message or has_embed or has_image or has_buttons)
                )
            )
        ]

    def PainelGerenciarBotoes(self) -> list[disnake.ui.Container]:
        container_kwargs = self.get_accent_color()
        editor_data = get_webhook_editor_data()
        botoes = editor_data.get("botoes", [])

        if not botoes:
            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Webhooks > **Gerenciar Botões**"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay("Nenhum botão foi adicionado ainda."),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Adicionar Botão",
                            style=disnake.ButtonStyle.green,
                            emoji=emoji.plus,
                            custom_id="Webhook_AdicionarBotao"
                        )
                    ),
                    **container_kwargs,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Webhook_VoltarEditor"
                    ),
                )
            ]

        options = []
        for btn in botoes:
            label = btn.get("label", "Sem label")[:100]
            btn_id = btn.get("id", "")
            btn_type = btn.get("button", {}).get("type", "disabled")
            tipo_desc = "Link" if btn_type == "url" else "Desativado"
            options.append(
                disnake.SelectOption(
                    label=label,
                    value=btn_id,
                    description=f"Tipo: {tipo_desc}",
                    emoji=emoji.route if btn_type == "url" else emoji.wrong
                )
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Webhooks > **Gerenciar Botões**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Total de botões:** `{len(botoes)}`/`5`\n-# Selecione um botão para remover ou adicione um novo."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione um botão para remover",
                        custom_id="Webhook_RemoverBotao",
                        options=options
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Botão",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.plus,
                        custom_id="Webhook_AdicionarBotao",
                        disabled=len(botoes) >= 5
                    ),
                    disnake.ui.Button(
                        label="Remover Todos",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="Webhook_RemoverTodosBotoes"
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Webhook_VoltarEditor"
                ),
            )
        ]

    def validar_emoji(self, emoji_input: str) -> bool:
        if not emoji_input or emoji_input.strip() == "":
            return True
        emoji_input = emoji_input.strip()
        DISCORD_EMOJI_RE = re.compile(r"<a?:[a-zA-Z0-9_]{2,32}:\d{17,22}>")
        UNICODE_EMOJI_RE = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U0001F900-\U0001F9FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE,
        )
        if hasattr(emoji, emoji_input):
            value = getattr(emoji, emoji_input)
            if isinstance(value, str) and DISCORD_EMOJI_RE.fullmatch(value):
                try:
                    pe = disnake.PartialEmoji.from_str(value)
                    return bool(pe and pe.id)
                except Exception:
                    return False
            return True
        if DISCORD_EMOJI_RE.fullmatch(emoji_input):
            try:
                pe = disnake.PartialEmoji.from_str(emoji_input)
                return bool(pe and pe.id)
            except Exception:
                return False
        if UNICODE_EMOJI_RE.fullmatch(emoji_input):
            return True
        return False

    def processar_emoji(self, emoji_input: str):
        if not emoji_input or emoji_input.strip() == "":
            return None
        emoji_input = emoji_input.strip()
        DISCORD_EMOJI_RE = re.compile(r"<a?:[a-zA-Z0-9_]{2,32}:\d{17,22}>")
        UNICODE_EMOJI_RE = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U0001F900-\U0001F9FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE,
        )
        
        if hasattr(emoji, emoji_input):
            value = getattr(emoji, emoji_input)
            if isinstance(value, str) and DISCORD_EMOJI_RE.fullmatch(value):
                try:
                    return disnake.PartialEmoji.from_str(value)
                except Exception:
                    return None
            return value if isinstance(value, str) else None
        if DISCORD_EMOJI_RE.fullmatch(emoji_input):
            try:
                return disnake.PartialEmoji.from_str(emoji_input)
            except Exception:
                return None
        if UNICODE_EMOJI_RE.fullmatch(emoji_input):
            return emoji_input
        return None

    async def update_panel(self, inter, components_func, *args):
        mode = db.get_document("custom_mode").get("mode")
        components = components_func(*args)
        
        if mode == "components":
            await inter.edit_original_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
        else:
            embed = disnake.Embed(
                title="Sistema de Webhooks",
                description="Utilize os componentes abaixo para gerenciar.",
                **self.get_embed_color()
            )
            await inter.edit_original_message(embed=embed, components=components)

    @commands.slash_command(
        name="webhook",
        description="Gerencie e envie mensagens por webhooks",
        guild_ids=[utils.obter_server_principal()]
    )
    async def webhook_cmd(self, inter: disnake.ApplicationCommandInteraction):
        if not await perms.check(inter.author.id):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando!",
                ephemeral=True
            )
            return
        
        await inter.response.defer(ephemeral=True)
        webhooks = await inter.guild.webhooks()
        
        mode = db.get_document("custom_mode").get("mode")
        components = self.PainelPrincipal(webhooks)
        
        if mode == "components":
            await inter.followup.send(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True
            )
        else:
            embed = disnake.Embed(
                title="Sistema de Webhooks",
                description="Utilize os componentes abaixo para gerenciar.",
                **self.get_embed_color()
            )
            await inter.followup.send(
                embed=embed,
                components=components,
                ephemeral=True
            )

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("Webhook_"):
            return
        
        cid = inter.component.custom_id
        
        if cid == "Webhook_VoltarPrincipal":
            await inter.response.defer()
            webhooks = await inter.guild.webhooks()
            await self.update_panel(inter, self.PainelPrincipal, webhooks)

        elif cid == "Webhook_IniciarCriacao":
            await inter.response.send_modal(Webhook_CriarModal())

        elif cid == "Webhook_EditarNome":
            data = get_webhook_system_data()
            wh_id = data.get("selected_webhook_id")
            if not wh_id:
                return await inter.response.send_message(f"{emoji.wrong} Nenhuma webhook selecionada.", ephemeral=True)
            try:
                wh = await inter.guild.fetch_webhook(wh_id)
                await inter.response.send_modal(Webhook_EditarNomeModal(wh.name))
            except disnake.NotFound:
                await inter.response.send_message(f"{emoji.wrong} Webhook não encontrada.", ephemeral=True)

        elif cid == "Webhook_EditarAvatar":
            await inter.response.send_modal(Webhook_EditarAvatarModal())

        elif cid == "Webhook_Apagar":
            await inter.response.defer()
            data = get_webhook_system_data()
            wh_id = data.get("selected_webhook_id")
            if wh_id:
                try:
                    wh = await inter.guild.fetch_webhook(wh_id)
                    await wh.delete(reason=f"Deletada por {inter.author}")
                    data["selected_webhook_id"] = None
                    save_webhook_system_data(data)
                except Exception:
                    pass
            webhooks = await inter.guild.webhooks()
            await self.update_panel(inter, self.PainelPrincipal, webhooks)

        elif cid == "Webhook_AbrirEditor":
            await inter.response.defer()
            await self.update_panel(inter, self.PainelEditor)

        elif cid == "Webhook_VoltarGerenciar":
            await inter.response.defer()
            data = get_webhook_system_data()
            wh_id = data.get("selected_webhook_id")
            if not wh_id:
                webhooks = await inter.guild.webhooks()
                return await self.update_panel(inter, self.PainelPrincipal, webhooks)
            try:
                wh = await inter.guild.fetch_webhook(wh_id)
                await self.update_panel(inter, self.PainelGerenciar, wh)
            except disnake.NotFound:
                webhooks = await inter.guild.webhooks()
                await self.update_panel(inter, self.PainelPrincipal, webhooks)

        elif cid == "Webhook_DefinirMensagem":
            await inter.response.send_modal(Webhook_DefinirMensagemModal())
        
        elif cid == "Webhook_DefinirEmbed":
            await inter.response.send_modal(Webhook_DefinirEmbedModal())
        
        elif cid == "Webhook_DefinirImagens":
            await inter.response.send_modal(Webhook_DefinirImagensModal())

        elif cid == "Webhook_GerenciarBotoes":
            await inter.response.defer()
            await self.update_panel(inter, self.PainelGerenciarBotoes)

        elif cid == "Webhook_AdicionarBotao":
            await inter.response.send_modal(Webhook_DefinirBotoesModal())

        elif cid == "Webhook_RemoverTodosBotoes":
            await inter.response.defer()
            editor_data = get_webhook_editor_data()
            editor_data["botoes"] = []
            set_webhook_editor_data(editor_data)
            await self.update_panel(inter, self.PainelGerenciarBotoes)

        elif cid == "Webhook_VoltarEditor":
            await inter.response.defer()
            await self.update_panel(inter, self.PainelEditor)

        elif cid.startswith("Webhook_ApagarCampo:"):
            await inter.response.defer()
            campo = cid.split(":")[1]
            if campo == "content":
                clear_webhook_editor_field("content")
            elif campo == "embed":
                editor_data = get_webhook_editor_data()
                editor_data.pop("embed", None)
                set_webhook_editor_data(editor_data)
            elif campo == "botoes":
                editor_data = get_webhook_editor_data()
                editor_data.pop("botoes", None)
                set_webhook_editor_data(editor_data)
            await self.update_panel(inter, self.PainelEditor)

        elif cid == "Webhook_ApagarImagensMulti":
            await inter.response.defer()
            editor_data = get_webhook_editor_data()
            editor_data.pop("externalImage", None)
            embed_data = editor_data.get("embed", {})
            embed_data.pop("banner", None)
            embed_data.pop("thumbnail", None)
            editor_data["embed"] = embed_data
            set_webhook_editor_data(editor_data)
            await self.update_panel(inter, self.PainelEditor)

        elif cid == "Webhook_EnviarMensagem":
            await inter.response.defer()
            data = get_webhook_system_data()
            wh_id = data.get("selected_webhook_id")
            if not wh_id:
                return await inter.followup.send(f"{emoji.wrong} Nenhuma webhook selecionada.", ephemeral=True)
            
            try:
                wh = await inter.guild.fetch_webhook(wh_id)
            except disnake.NotFound:
                return await inter.followup.send(f"{emoji.wrong} Webhook não encontrada.", ephemeral=True)

            editor_data = get_webhook_editor_data()
            if not any(editor_data.get(k) for k in ["content", "embed", "externalImage", "botoes"]):
                return await inter.followup.send(f"{emoji.wrong} Configure pelo menos um campo antes de enviar!", ephemeral=True)

            data_to_build = editor_data.copy()
            data_to_build.pop("container", None)
            
            if "botoes" in data_to_build and data_to_build["botoes"]:
                data_to_build["buttons"] = data_to_build.pop("botoes")
            else:
                data_to_build["buttons"] = []
            
            built = await Builder.build_from_cfg({"message": data_to_build})
            
            # Remover kwargs não suportados por webhooks ao enviar mensagens normais
            built.pop("ephemeral", None)
            
            try:
                await wh.send(**built)
                await inter.followup.send(f"{emoji.correct} Mensagem enviada com sucesso pela webhook `{wh.name}`!", ephemeral=True)
            except Exception as e:
                await inter.followup.send(f"{emoji.wrong} Erro ao enviar mensagem pela webhook: {str(e)}", ephemeral=True)

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("Webhook_"):
            return
            
        cid = inter.component.custom_id

        if cid == "Webhook_Selecionar":
            await inter.response.defer()
            wh_id = int(inter.values[0])
            try:
                wh = await inter.guild.fetch_webhook(wh_id)
                data = get_webhook_system_data()
                data["selected_webhook_id"] = wh_id
                save_webhook_system_data(data)
                await self.update_panel(inter, self.PainelGerenciar, wh)
            except disnake.NotFound:
                await inter.followup.send(f"{emoji.wrong} Webhook não encontrada.", ephemeral=True)

        elif cid == "Webhook_AlterarCanal":
            await inter.response.defer()
            channel_id = int(inter.values[0])
            channel = inter.guild.get_channel(channel_id)
            
            data = get_webhook_system_data()
            wh_id = data.get("selected_webhook_id")
            if wh_id and channel:
                try:
                    wh = await inter.guild.fetch_webhook(wh_id)
                    await wh.edit(channel=channel, reason=f"Canal alterado por {inter.author}")
                    await self.update_panel(inter, self.PainelGerenciar, wh)
                except Exception as e:
                    await inter.followup.send(f"{emoji.wrong} Erro ao alterar canal: {e}", ephemeral=True)

        elif cid == "Webhook_RemoverBotao":
            await inter.response.defer()
            btn_id = inter.values[0]
            editor_data = get_webhook_editor_data()
            botoes = editor_data.get("botoes", [])
            editor_data["botoes"] = [btn for btn in botoes if btn.get("id") != btn_id]
            set_webhook_editor_data(editor_data)
            await self.update_panel(inter, self.PainelGerenciarBotoes)

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        if not inter.custom_id.startswith("Webhook_"):
            return
        
        cid = inter.custom_id

        if cid == "Webhook_CriarModal":
            name = inter.text_values.get("webhook_name", "").strip()
            
            class ChannelSelectView(disnake.ui.View):
                def __init__(self, cog_instance):
                    super().__init__(timeout=120)
                    self.cog_instance = cog_instance

                @disnake.ui.channel_select(
                    custom_id="Webhook_SelectCriacaoCanal",
                    placeholder="Selecione o canal para a Webhook",
                    channel_types=[disnake.ChannelType.text, disnake.ChannelType.news]
                )
                async def select_channel(self, select: disnake.ui.ChannelSelect, interaction: disnake.MessageInteraction):
                    await interaction.response.defer()
                    channel = interaction.guild.get_channel(int(select.values[0]))
                    try:
                        wh = await channel.create_webhook(name=name, reason=f"Criada por {interaction.author}")
                        data = get_webhook_system_data()
                        data["selected_webhook_id"] = wh.id
                        save_webhook_system_data(data)
                        await self.cog_instance.update_panel(interaction, self.cog_instance.PainelGerenciar, wh)
                    except Exception as e:
                        await interaction.followup.send(f"{emoji.wrong} Erro ao criar webhook: {e}", ephemeral=True)

            await inter.response.send_message(
                f"{emoji.information} Selecione o canal onde a webhook `{name}` será criada:",
                view=ChannelSelectView(self),
                ephemeral=True
            )

        elif cid == "Webhook_EditarNomeModal":
            await inter.response.defer()
            new_name = inter.text_values.get("webhook_name", "").strip()
            data = get_webhook_system_data()
            wh_id = data.get("selected_webhook_id")
            if wh_id:
                try:
                    wh = await inter.guild.fetch_webhook(wh_id)
                    await wh.edit(name=new_name, reason=f"Editada por {inter.author}")
                    await self.update_panel(inter, self.PainelGerenciar, wh)
                except Exception as e:
                    await inter.followup.send(f"{emoji.wrong} Erro ao editar nome: {e}", ephemeral=True)

        elif cid == "Webhook_EditarAvatarModal":
            await inter.response.defer()
            url = inter.text_values.get("webhook_avatar_url", "").strip()
            data = get_webhook_system_data()
            wh_id = data.get("selected_webhook_id")
            if wh_id:
                try:
                    image_bytes = await download_image(url)
                    if not image_bytes:
                        return await inter.followup.send(f"{emoji.wrong} Não foi possível baixar a imagem dessa URL.", ephemeral=True)
                    
                    wh = await inter.guild.fetch_webhook(wh_id)
                    await wh.edit(avatar=image_bytes, reason=f"Avatar editado por {inter.author}")
                    await self.update_panel(inter, self.PainelGerenciar, wh)
                except Exception as e:
                    await inter.followup.send(f"{emoji.wrong} Erro ao editar avatar: {e}", ephemeral=True)

        elif cid == "Webhook_DefinirMensagemModal":
            await inter.response.defer()
            content = inter.text_values.get("message", "").strip()
            if content:
                set_webhook_editor_field("content", content)
            else:
                clear_webhook_editor_field("content")
            await self.update_panel(inter, self.PainelEditor)

        elif cid == "Webhook_DefinirEmbedModal":
            await inter.response.defer()
            editor_data = get_webhook_editor_data()
            embed_data = editor_data.get("embed", {})
            
            embed_data["title"] = inter.text_values.get("embed_title", "").strip()
            embed_data["description"] = inter.text_values.get("embed_description", "").strip()
            embed_data["color"] = inter.text_values.get("embed_color", "").strip()
            embed_data["footer"] = inter.text_values.get("embed_footer", "").strip()
            
            if not any([embed_data.get("title"), embed_data.get("description"), embed_data.get("footer")]):
                editor_data.pop("embed", None)
            else:
                editor_data["embed"] = embed_data
            
            set_webhook_editor_data(editor_data)
            await self.update_panel(inter, self.PainelEditor)

        elif cid == "Webhook_DefinirImagensModal":
            await inter.response.defer()
            editor_data = get_webhook_editor_data()
            
            external_image = inter.text_values.get("externalImage", "").strip()
            if external_image:
                editor_data["externalImage"] = external_image
            else:
                editor_data.pop("externalImage", None)
            
            embed_data = editor_data.get("embed", {})
            banner = inter.text_values.get("banner", "").strip()
            thumbnail = inter.text_values.get("thumbnail", "").strip()
            
            if banner:
                embed_data["banner"] = banner
            else:
                embed_data.pop("banner", None)
            
            if thumbnail:
                embed_data["thumbnail"] = thumbnail
            else:
                embed_data.pop("thumbnail", None)
            
            if embed_data:
                editor_data["embed"] = embed_data
            
            set_webhook_editor_data(editor_data)
            await self.update_panel(inter, self.PainelEditor)

        elif cid == "Webhook_DefinirBotoesModal":
            label = inter.text_values.get("button_label", "").strip()
            url = inter.text_values.get("button_url", "").strip()
            emoji_str = inter.text_values.get("button_emoji", "").strip()
            
            if not label:
                return await inter.response.send_message(f"{emoji.wrong} O label do botão é obrigatório!", ephemeral=True)
            
            editor_data = get_webhook_editor_data()
            botoes = editor_data.get("botoes", [])
            
            if len(botoes) >= 5:
                return await inter.response.send_message(f"{emoji.wrong} Você atingiu o limite de 5 botões!", ephemeral=True)
            
            emoji_obj = None
            if emoji_str:
                if not self.validar_emoji(emoji_str):
                    return await inter.response.send_message(f"{emoji.wrong} Emoji inválido!", ephemeral=True)
                emoji_obj = self.processar_emoji(emoji_str)
            
            button_type = "disabled"
            if url:
                if not url.startswith(("http://", "https://")):
                    return await inter.response.send_message(f"{emoji.wrong} URL inválida! Deve começar com http:// ou https://", ephemeral=True)
                button_type = "url"
            
            btn_id = str(uuid.uuid4())[:8]
            
            btn_data = {
                "id": btn_id,
                "label": label,
                "button": {
                    "type": button_type,
                    "url": url if button_type == "url" else None
                }
            }
            
            if emoji_obj:
                if isinstance(emoji_obj, disnake.PartialEmoji):
                    btn_data["emoji"] = str(emoji_obj)
                else:
                    btn_data["emoji"] = emoji_obj
            
            botoes.append(btn_data)
            editor_data["botoes"] = botoes
            set_webhook_editor_data(editor_data)
            
            await inter.response.defer()
            await self.update_panel(inter, self.PainelGerenciarBotoes)


def setup(bot: commands.Bot):
    bot.add_cog(WebhookCog(bot))
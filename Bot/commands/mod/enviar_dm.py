import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils
from functions.perms import perms
from commands.admin.anunciar.builder import Builder
from modules.automations.disparador_dm.cog import DisparadorDMCog
import re


# Helper functions para gerenciar o editor de mensagem do enviar_dm
def get_enviar_dm_editor_data() -> dict:
    """Obtém os dados do editor do enviar_dm."""
    editor_data = db.get_document("enviar_dm_editor") or {}
    return editor_data.get("mensagem", {})


def set_enviar_dm_editor_data(editor_data: dict):
    """Define os dados completos do editor do enviar_dm."""
    db.save_document("enviar_dm_editor", {"mensagem": editor_data})


def set_enviar_dm_editor_field(field: str, value):
    """Define um campo no editor de mensagem do enviar_dm."""
    editor_data = get_enviar_dm_editor_data()
    editor_data[field] = value
    set_enviar_dm_editor_data(editor_data)
    return True


def clear_enviar_dm_editor_field(field: str):
    """Limpa um campo do editor do enviar_dm."""
    editor_data = get_enviar_dm_editor_data()
    if field in editor_data:
        del editor_data[field]
        set_enviar_dm_editor_data(editor_data)
        return True
    return False


# Modais para editar mensagem
class EnviarDM_DefinirMensagemModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = get_enviar_dm_editor_data()
        super().__init__(
            title="Definir Mensagem",
            custom_id="EnviarDM_DefinirMensagemModal",
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


class EnviarDM_DefinirEmbedModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = get_enviar_dm_editor_data()
        embed_data = editor_data.get("embed", {})
        super().__init__(
            title="Definir Embed",
            custom_id="EnviarDM_DefinirEmbedModal",
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


class EnviarDM_DefinirImagensModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = get_enviar_dm_editor_data()
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
            custom_id="EnviarDM_DefinirImagensModal",
            components=components
        )


class EnviarDM_DefinirBotoesModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar Botão",
            custom_id="EnviarDM_DefinirBotoesModal",
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


class EnviarDM_UserSelect(disnake.ui.UserSelect):
    """UserSelect para selecionar o usuário que receberá a DM"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__(
            placeholder="Selecione o usuário que receberá a mensagem",
            custom_id="EnviarDM_SelectUser",
            min_values=1,
            max_values=1
        )
    
    async def callback(self, inter: disnake.MessageInteraction):
        user = self.values[0]
        
        await inter.response.defer()
        
        editor_data = get_enviar_dm_editor_data()
        if not any(editor_data.get(k) for k in ["content", "embed", "externalImage", "botoes"]):
            await inter.followup.send(
                f"{emoji.wrong} A mensagem está vazia! Configure pelo menos um campo antes de enviar.",
                ephemeral=True
            )
            return
        
        data_to_build = editor_data.copy()
        data_to_build.pop("container", None)
        
        if "botoes" in data_to_build and data_to_build["botoes"]:
            data_to_build["buttons"] = data_to_build.pop("botoes")
        else:
            data_to_build["buttons"] = []
        
        built = await Builder.build_from_cfg({"message": data_to_build})
        
        try:
            await DisparadorDMCog._send_built_message(user, built, ephemeral=False)
            await inter.followup.send(
                f"{emoji.correct} Mensagem enviada com sucesso para {user.mention}!",
                ephemeral=True
            )
        except disnake.Forbidden:
            await inter.followup.send(
                f"{emoji.wrong} Não foi possível enviar a mensagem para {user.mention}. O usuário pode ter as DMs desativadas.",
                ephemeral=True
            )
        except Exception as e:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao enviar mensagem: {str(e)}",
                ephemeral=True
            )


class EnviarDM_UserSelectView(disnake.ui.View):
    """View com UserSelect para selecionar o usuário que receberá a DM"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.add_item(EnviarDM_UserSelect(bot))


class EnviarDMCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def PainelEditor(bot: commands.Bot) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        editor_data = get_enviar_dm_editor_data()
        
        has_message = bool(editor_data.get("content"))
        embed_data = editor_data.get("embed", {})
        has_embed = any(embed_data.get(k) for k in ("title", "description", "footer"))
        has_image = bool(editor_data.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
        botoes = editor_data.get("botoes", [])
        has_buttons = isinstance(botoes, list) and len(botoes) > 0
        limite_botoes = isinstance(botoes, list) and len(botoes) >= 5

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Enviar DM > **Editor de Mensagem**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Configure a mensagem que será enviada ao usuário selecionado."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="EnviarDM_ApagarCampo:content",
                        disabled=not has_message
                    ),
                    disnake.ui.Button(
                        label="Definir Mensagem",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.message,
                        custom_id="EnviarDM_DefinirMensagem"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="EnviarDM_ApagarCampo:embed",
                        disabled=not has_embed
                    ),
                    disnake.ui.Button(
                        label="Definir Embed",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.embed,
                        custom_id="EnviarDM_DefinirEmbed"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="EnviarDM_ApagarImagensMulti",
                        disabled=not has_image
                    ),
                    disnake.ui.Button(
                        label="Definir Imagens",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.image,
                        custom_id="EnviarDM_DefinirImagens"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="EnviarDM_ApagarCampo:botoes",
                        disabled=not has_buttons
                    ),
                    disnake.ui.Button(
                        label="Gerenciar Botões" if has_buttons else "Adicionar Botão",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.edit if has_buttons else emoji.plus,
                        custom_id="EnviarDM_GerenciarBotoes",
                        disabled=limite_botoes
                    ),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Visualizar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.search,
                    custom_id="EnviarDM_Visualizar",
                    disabled=not (has_message or has_embed or has_image or has_buttons)
                ),
                disnake.ui.Button(
                    label="Enviar",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.correct,
                    custom_id="EnviarDM_Enviar",
                    disabled=not (has_message or has_embed or has_image or has_buttons)
                )
            )
        ]

    @staticmethod
    def PainelGerenciarBotoes() -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        editor_data = get_enviar_dm_editor_data()
        botoes = editor_data.get("botoes", [])

        if not botoes:
            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Enviar DM > **Gerenciar Botões**"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay("Nenhum botão foi adicionado ainda."),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Adicionar Botão",
                            style=disnake.ButtonStyle.green,
                            emoji=emoji.plus,
                            custom_id="EnviarDM_AdicionarBotao"
                        )
                    ),
                    **container_kwargs,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="EnviarDM_VoltarEditor"
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
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Enviar DM > **Gerenciar Botões**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Total de botões:** `{len(botoes)}`/`5`\n-# Selecione um botão para remover ou adicione um novo."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione um botão para remover",
                        custom_id="EnviarDM_RemoverBotao",
                        options=options
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Botão",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.plus,
                        custom_id="EnviarDM_AdicionarBotao",
                        disabled=len(botoes) >= 5
                    ),
                    disnake.ui.Button(
                        label="Remover Todos",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="EnviarDM_RemoverTodosBotoes"
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="EnviarDM_VoltarEditor"
                ),
            )
        ]

    @staticmethod
    def validar_emoji(emoji_input: str, bot: commands.Bot) -> bool:
        """Valida se um emoji é válido."""
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

    @staticmethod
    def processar_emoji(emoji_input: str):
        """Processa um emoji para uso em componentes."""
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

    @commands.slash_command(
        name="enviar_dm",
        description="Enviar uma mensagem DM para um usuário usando o builder",
        guild_ids=[utils.obter_server_principal()]
    )
    async def enviar_dm(self, inter: disnake.ApplicationCommandInteraction):
        # Verificar permissões
        if not await perms.check(inter.author.id):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando!",
                ephemeral=True
            )
            return
        
        mode = db.get_document("custom_mode").get("mode")
        
        components = self.PainelEditor(self.bot)
        if mode == "components":
            await inter.response.send_message(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True
            )
        else:
            # Para modo embed, criar um embed simples com os botões
            colors = db.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            embed_kwargs = {}
            if primary_color_hex:
                embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
            
            embed = disnake.Embed(
                title="Enviar DM",
                description="Configure a mensagem que será enviada ao usuário selecionado.",
                **embed_kwargs
            )
            await inter.response.send_message(
                embed=embed,
                components=components,
                ephemeral=True
            )

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("EnviarDM_"):
            return
        
        cid = inter.component.custom_id
        
        # Editor de mensagem
        if cid == "EnviarDM_DefinirMensagem":
            await inter.response.send_modal(EnviarDM_DefinirMensagemModal())
        
        elif cid == "EnviarDM_DefinirEmbed":
            await inter.response.send_modal(EnviarDM_DefinirEmbedModal())
        
        elif cid == "EnviarDM_DefinirImagens":
            await inter.response.send_modal(EnviarDM_DefinirImagensModal())
        
        elif cid == "EnviarDM_GerenciarBotoes":
            await inter.response.defer()
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelGerenciarBotoes()
            if mode == "components":
                await inter.edit_original_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Gerenciar Botões",
                    description="Gerencie os botões da mensagem.",
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, components=components)
        
        elif cid == "EnviarDM_AdicionarBotao":
            await inter.response.send_modal(EnviarDM_DefinirBotoesModal())
        
        elif cid == "EnviarDM_RemoverTodosBotoes":
            await inter.response.defer()
            editor_data = get_enviar_dm_editor_data()
            editor_data["botoes"] = []
            set_enviar_dm_editor_data(editor_data)
            
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelGerenciarBotoes()
            if mode == "components":
                await inter.edit_original_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Gerenciar Botões",
                    description="Gerencie os botões da mensagem.",
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, components=components)
        
        elif cid == "EnviarDM_VoltarEditor":
            await inter.response.defer()
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelEditor(self.bot)
            if mode == "components":
                await inter.edit_original_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Enviar DM",
                    description="Configure a mensagem que será enviada ao usuário selecionado.",
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, components=components)
        
        elif cid.startswith("EnviarDM_ApagarCampo:"):
            await inter.response.defer()
            campo = cid.split(":")[1]
            if campo == "content":
                clear_enviar_dm_editor_field("content")
            elif campo == "embed":
                editor_data = get_enviar_dm_editor_data()
                editor_data.pop("embed", None)
                set_enviar_dm_editor_data(editor_data)
            elif campo == "botoes":
                editor_data = get_enviar_dm_editor_data()
                editor_data.pop("botoes", None)
                set_enviar_dm_editor_data(editor_data)
            
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelEditor(self.bot)
            if mode == "components":
                await inter.edit_original_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Enviar DM",
                    description="Configure a mensagem que será enviada ao usuário selecionado.",
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, components=components)
        
        elif cid == "EnviarDM_ApagarImagensMulti":
            await inter.response.defer()
            editor_data = get_enviar_dm_editor_data()
            editor_data.pop("externalImage", None)
            embed_data = editor_data.get("embed", {})
            embed_data.pop("banner", None)
            embed_data.pop("thumbnail", None)
            editor_data["embed"] = embed_data
            set_enviar_dm_editor_data(editor_data)
            
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelEditor(self.bot)
            if mode == "components":
                await inter.edit_original_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Enviar DM",
                    description="Configure a mensagem que será enviada ao usuário selecionado.",
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, components=components)
        
        elif cid == "EnviarDM_Visualizar":
            await inter.response.defer()
            editor_data = get_enviar_dm_editor_data()
            if not any(editor_data.get(k) for k in ["content", "embed", "externalImage", "botoes"]):
                await inter.followup.send("Não há nada para visualizar.", ephemeral=True)
                return
            
            data_to_build = editor_data.copy()
            data_to_build.pop("container", None)
            
            if "botoes" in data_to_build and data_to_build["botoes"]:
                data_to_build["buttons"] = data_to_build.pop("botoes")
            else:
                data_to_build["buttons"] = []
            
            built = await Builder.build_from_cfg({"message": data_to_build})
            await DisparadorDMCog._send_built_message(inter, built, ephemeral=True)
        
        elif cid == "EnviarDM_Enviar":
            editor_data = get_enviar_dm_editor_data()
            if not any(editor_data.get(k) for k in ["content", "embed", "externalImage", "botoes"]):
                await inter.response.send_message(
                    f"{emoji.wrong} Configure pelo menos um campo antes de enviar!",
                    ephemeral=True
                )
                return
            
            # Enviar view com UserSelect
            view = EnviarDM_UserSelectView(self.bot)
            await inter.response.send_message(
                f"{emoji.information} Selecione o usuário que receberá a mensagem:",
                view=view,
                ephemeral=True
            )

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "EnviarDM_RemoverBotao":
            await inter.response.defer()
            btn_id = inter.values[0]
            editor_data = get_enviar_dm_editor_data()
            botoes = editor_data.get("botoes", [])
            editor_data["botoes"] = [btn for btn in botoes if btn.get("id") != btn_id]
            set_enviar_dm_editor_data(editor_data)
            
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelGerenciarBotoes()
            if mode == "components":
                await inter.edit_original_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Gerenciar Botões",
                    description="Gerencie os botões da mensagem.",
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, components=components)


    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        if not inter.custom_id.startswith("EnviarDM_"):
            return
        
        cid = inter.custom_id
        
        if cid == "EnviarDM_DefinirMensagemModal":
            content = inter.text_values.get("message", "").strip()
            if content:
                set_enviar_dm_editor_field("content", content)
            else:
                clear_enviar_dm_editor_field("content")
            
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelEditor(self.bot)
            if mode == "components":
                await inter.response.edit_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Enviar DM",
                    description="Configure a mensagem que será enviada ao usuário selecionado.",
                    **embed_kwargs
                )
                await inter.response.edit_message(embed=embed, components=components)
        
        elif cid == "EnviarDM_DefinirEmbedModal":
            editor_data = get_enviar_dm_editor_data()
            embed_data = editor_data.get("embed", {})
            
            embed_data["title"] = inter.text_values.get("embed_title", "").strip()
            embed_data["description"] = inter.text_values.get("embed_description", "").strip()
            embed_data["color"] = inter.text_values.get("embed_color", "").strip()
            embed_data["footer"] = inter.text_values.get("embed_footer", "").strip()
            
            if not any([embed_data.get("title"), embed_data.get("description"), embed_data.get("footer")]):
                editor_data.pop("embed", None)
            else:
                editor_data["embed"] = embed_data
            
            set_enviar_dm_editor_data(editor_data)
            
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelEditor(self.bot)
            if mode == "components":
                await inter.response.edit_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Enviar DM",
                    description="Configure a mensagem que será enviada ao usuário selecionado.",
                    **embed_kwargs
                )
                await inter.response.edit_message(embed=embed, components=components)
        
        elif cid == "EnviarDM_DefinirImagensModal":
            editor_data = get_enviar_dm_editor_data()
            
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
            
            set_enviar_dm_editor_data(editor_data)
            
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelEditor(self.bot)
            if mode == "components":
                await inter.response.edit_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Enviar DM",
                    description="Configure a mensagem que será enviada ao usuário selecionado.",
                    **embed_kwargs
                )
                await inter.response.edit_message(embed=embed, components=components)
        
        elif cid == "EnviarDM_DefinirBotoesModal":
            label = inter.text_values.get("button_label", "").strip()
            url = inter.text_values.get("button_url", "").strip()
            emoji_str = inter.text_values.get("button_emoji", "").strip()
            
            if not label:
                await inter.response.send_message(
                    f"{emoji.wrong} O label do botão é obrigatório!",
                    ephemeral=True
                )
                return
            
            editor_data = get_enviar_dm_editor_data()
            botoes = editor_data.get("botoes", [])
            
            if len(botoes) >= 5:
                await inter.response.send_message(
                    f"{emoji.wrong} Você atingiu o limite de 5 botões!",
                    ephemeral=True
                )
                return
            
            # Validar emoji
            emoji_obj = None
            if emoji_str:
                if not self.validar_emoji(emoji_str, self.bot):
                    await inter.response.send_message(
                        f"{emoji.wrong} Emoji inválido!",
                        ephemeral=True
                    )
                    return
                emoji_obj = self.processar_emoji(emoji_str)
            
            # Validar URL se fornecida
            button_type = "disabled"
            if url:
                if not url.startswith(("http://", "https://")):
                    await inter.response.send_message(
                        f"{emoji.wrong} URL inválida! Deve começar com http:// ou https://",
                        ephemeral=True
                    )
                    return
                button_type = "url"
            
            import uuid
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
            set_enviar_dm_editor_data(editor_data)
            
            mode = db.get_document("custom_mode").get("mode")
            components = self.PainelGerenciarBotoes()
            if mode == "components":
                await inter.response.edit_message(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            else:
                colors = db.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title="Gerenciar Botões",
                    description="Gerencie os botões da mensagem.",
                    **embed_kwargs
                )
                await inter.response.edit_message(embed=embed, components=components)


def setup(bot: commands.Bot):
    bot.add_cog(EnviarDMCog(bot))

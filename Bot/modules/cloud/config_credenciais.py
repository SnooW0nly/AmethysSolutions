import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message
from .update_api import register_bot


async def process_submission(inter: disnake.ModalInteraction, bot, bot_token: str, client_secret: str):
    await inter.response.defer(ephemeral=True)

    cloud_config = db.get_document("cloud_data") or {}
    cargos_config = db.get_document("cargos")
    log_channel_id = cloud_config.get("log_channel_id")
    verified_role_id = cargos_config.get("cargo_verificado")
    auto_role_id = cargos_config.get("cargo_auto_role")

    if not log_channel_id or not verified_role_id:
        await inter.edit_original_message(content=f"{emoji.wrong} Por favor, defina o canal de logs e o cargo de verificado primeiro.")
        return

    success, message_text, bot_info = await register_bot(str(bot.user.id), bot_token, client_secret, verified_role_id, log_channel_id, auto_role_id)

    if success:
        cloud_config.update(bot_info)
        db.save_document("cloud_data", cloud_config)
        
        # Atualizar oauth_client_id no websocket manager
        from .update_api import get_websocket_manager
        ws_manager = get_websocket_manager()
        if bot_info.get("client_id"):
            ws_manager.oauth_client_id = bot_info.get("client_id")
            # Se o websocket estiver conectado, enviar definições atualizadas
            if ws_manager.is_connected():
                definitions = cloud_config.get("definitions", {})
                if definitions:
                    try:
                        await ws_manager.update_definitions(definitions)
                    except Exception as e:
                        print(f"[Config Credenciais] Erro ao sincronizar definições após atualizar credenciais: {e}")
        
        await inter.edit_original_message(content=f"{emoji.correct} {message_text}")
    else:
        await inter.edit_original_message(content=f"{emoji.wrong} {message_text}")


class CredentialModal(disnake.ui.Modal):
    def __init__(self, bot, bot_token: str = "", client_secret: str = ""):
        self.bot = bot
        components = [
            disnake.ui.TextInput(
                label="Token do Bot",
                custom_id="bot_token",
                style=disnake.TextInputStyle.short,
                placeholder="Insira o token da sua aplicação",
                required=True,
                value=bot_token
            ),
            disnake.ui.TextInput(
                label="Client Secret",
                custom_id="client_secret",
                style=disnake.TextInputStyle.short,
                placeholder="Insira o client secret da sua aplicação",
                required=True,
                value=client_secret
            ),
        ]
        super().__init__(title="Definir Credenciais", components=components, custom_id="credential_modal")

    async def callback(self, inter: disnake.ModalInteraction):
        bot_token = inter.text_values["bot_token"]
        client_secret = inter.text_values["client_secret"]
        await process_submission(inter, self.bot, bot_token, client_secret)


def CredentialsView_components() -> list[disnake.ui.Container]:
    from .cloud_config import get_auth_callback_url
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#7289da")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    auth_callback_url = get_auth_callback_url()
    explanation = (
        "Para utilizar os serviços da **AmyCloud**, é necessário um **bot exclusivo** que realiza a conexão com nossa **API**, permitindo que os **membros do seu servidor autorizem-o** de forma segura e integrada.\n\n"
        f"{emoji.student} **Passo a Passo:**\n"
        f"{emoji.arrow} 1. Acesse o [Portal de Desenvolvedores do Discord](https://discord.com/developers/applications).\n"
        "> **Dica:** Crie uma nova conta no Discord para este bot, não use sua conta principal.\n"
        f"{emoji.arrow} 2. Crie uma **nova aplicação** e navegue até a aba **'Bot'**.\n"
        f"{emoji.arrow} 3. Clique em **'Add Bot'** e copie o **Token**.\n"
        f"{emoji.arrow} 4. Vá para a aba **'OAuth2'** e copie o **Client Secret**.\n"
        f"{emoji.arrow} 5. Em **'OAuth2' -> 'Redirects'**, adicione a URL abaixo:\n"
        f"`{auth_callback_url}`"
    )

    cloud_config = db.get_document("cloud_data") or {}
    cargos_config = db.get_document("cargos")
    log_channel_id = cloud_config.get("log_channel_id")
    verified_role_id = cargos_config.get("cargo_verificado")
    is_ready = bool(log_channel_id and verified_role_id)

    if not is_ready:
        explanation += "\n\n**Aviso:** Você precisa definir um canal de logs e um cargo de verificado antes de configurar as credenciais. Use o botão 'Definir Logs' no painel anterior."

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Configurar Credenciais**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(explanation),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Credenciais", style=disnake.ButtonStyle.green, custom_id="Cloud_SetCredentialsModal", emoji=emoji.double_check, disabled=not is_ready),
            disnake.ui.Button(label="Copiar URL", style=disnake.ButtonStyle.grey, custom_id="Cloud_CopyAuthURL", emoji=emoji.web, disabled=not is_ready)
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_MainPanel"),
    )
    
    return [container, buttons]

def CredentialsView_embed(inter: disnake.Interaction):
    from .cloud_config import get_auth_callback_url
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#7289da")
    
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    auth_callback_url = get_auth_callback_url()
    explanation = (
        "Para utilizar os serviços da **AmyCloud**, é necessário um **bot exclusivo** que realiza a conexão com nossa **API**, permitindo que os **membros do seu servidor autorizem-o** de forma segura e integrada.\n\n"
        f"{emoji.student} **Passo a Passo:**\n"
        "1. Acesse o [Portal de Desenvolvedores do Discord](https://discord.com/developers/applications).\n"
        "> **Dica:** Crie uma nova conta no Discord para este bot, não use sua conta principal.\n"
        "2. Crie uma **nova aplicação** e navegue até a aba **'Bot'**.\n"
        "3. Clique em **'Add Bot'** e copie o **Token**.\n"
        "4. Vá para a aba **'OAuth2'** e copie o **Client Secret**.\n"
        "5. Em **'OAuth2' -> 'Redirects'**, adicione a URL abaixo:\n"
        f"`{auth_callback_url}`"
    )

    cloud_config = db.get_document("cloud_data") or {}
    cargos_config = db.get_document("cargos")
    log_channel_id = cloud_config.get("log_channel_id")
    verified_role_id = cargos_config.get("cargo_verificado")
    is_ready = bool(log_channel_id and verified_role_id)

    if not is_ready:
        explanation += "\n\n**Aviso:** Você precisa definir um canal de logs e um cargo de verificado antes de configurar as credenciais. Use o botão 'Definir Logs' no painel anterior."

    embed = disnake.Embed(
        title=f"Configurar Credenciais",
        description=explanation,
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Credenciais", style=disnake.ButtonStyle.green, custom_id="Cloud_SetCredentialsModal", emoji=emoji.double_check, disabled=not is_ready),
            disnake.ui.Button(label="Copiar URL", style=disnake.ButtonStyle.grey, custom_id="Cloud_CopyAuthURL", emoji=emoji.web, disabled=not is_ready)
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_MainPanel")
        )
    ]

    return embed, components

async def show_panel(inter: disnake.MessageInteraction):
    mode = db.get_document("custom_mode").get("mode")
    if mode == "embed":
        await embed_message.wait(inter)
        embed, components = CredentialsView_embed(inter)
        await inter.edit_original_message(content=None, embed=embed, components=components)
    else:
        await message.wait(inter)
        components = CredentialsView_components()
        await inter.edit_original_message(components=components)

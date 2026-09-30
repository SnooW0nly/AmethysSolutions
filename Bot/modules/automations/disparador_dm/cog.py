import disnake
from disnake.ext import commands, tasks
import asyncio
from typing import Optional
import aiohttp          # adicionado para requisições assíncronas

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from . import helpers
from commands.admin.anunciar.builder import Builder
import re
import datetime

# region Modals
class GerenciarTokensModal(disnake.ui.Modal):
    def __init__(self, tokens_atuais: list):
        tokens_text = "\n".join(tokens_atuais) if tokens_atuais else ""
        super().__init__(
            title="Gerenciar Tokens de Bots",
            custom_id="DisparadorDM_GerenciarTokensModal",
            components=[
                disnake.ui.TextInput(
                    label="Tokens (1 por linha)",
                    placeholder="Cole os tokens dos bots aqui, um por linha",
                    custom_id="tokens",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    value=tokens_text,
                    max_length=4000
                )
            ],
        )

class DefinirMensagemModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = helpers.get_editor_data()
        super().__init__(
            title="Definir Mensagem",
            custom_id="DisparadorDM_DefinirMensagemModal",
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

class DefinirEmbedModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = helpers.get_editor_data()
        embed_data = editor_data.get("embed", {})
        super().__init__(
            title="Definir Embed",
            custom_id="DisparadorDM_DefinirEmbedModal",
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

class DefinirImagensModal(disnake.ui.Modal):
    def __init__(self):
        editor_data = helpers.get_editor_data()
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
            custom_id="DisparadorDM_DefinirImagensModal",
            components=components
        )

class ConfigurarDisparoModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Configurar Disparo",
            custom_id="DisparadorDM_ConfigurarDisparoModal",
            components=[
                disnake.ui.TextInput(
                    label="ID do Servidor (opcional)",
                    custom_id="server_id",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    placeholder="Vazio = servidor principal"
                ),
                disnake.ui.TextInput(
                    label="ID do Cargo (opcional)",
                    custom_id="role_id",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    placeholder="Vazio = enviar para todos"
                ),
                disnake.ui.TextInput(
                    label="Cargos Excluídos (separados por vírgula)",
                    custom_id="exclude_roles",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    placeholder="Ex: 123456789, 987654321"
                ),
                disnake.ui.TextInput(
                    label="Usuários Excluídos (separados por vírgula)",
                    custom_id="exclude_users",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    placeholder="Ex: 123456789, 987654321"
                ),
            ],
        )

class DefinirBotoesModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar Botão",
            custom_id="DisparadorDM_DefinirBotoesModal",
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

# endregion


class DisparadorDMCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.disparo_em_andamento = False
        self.task_disparo = None

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bio_updater.is_running():
            self.bio_updater.start()

    def cog_unload(self):
        self.bio_updater.cancel()

    @tasks.loop(hours=1)
    async def bio_updater(self):
        """Atualiza a bio dos bots configurados."""
        try:
            config = helpers.carregar_config()
            tokens = config.get("tokens", [])
            
            for token in tokens:
                bot_info = helpers.obter_bot_info(token)
                if bot_info:
                    try:
                        import requests
                        
                        description = (
                            f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            f"https://amethys.solutions/"
                        )
                        
                        app_id = bot_info.get("id")
                        url = f"https://discord.com/api/v10/applications/{app_id}"
                        headers = {
                            "authorization": f"Bot {token}",
                            "content-type": "application/json",
                        }
                        payload = {"description": description}
                        requests.patch(url, headers=headers, json=payload, timeout=10)
                    except Exception as e:
                        print(f"Erro ao atualizar bio: {e}")
        except Exception as e:
            print(f"Erro no bio_updater: {e}")

    @bio_updater.before_loop
    async def before_bio_updater(self):
        await self.bot.wait_until_ready()

    @staticmethod
    def Painel() -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        config = helpers.carregar_config()
        tokens = config.get("tokens", [])
        total_tokens = len(tokens)
        tokens_validos = sum(1 for token in tokens if helpers.validar_token(token))
        
        mensagem_data = config.get("mensagem", {})
        mensagem_configurada = bool(
            mensagem_data.get("content") or 
            mensagem_data.get("embed")
        )
        
        temp_db = helpers.carregar_temp_db()
        total_alvo = len(temp_db.get("usuarios_alvo", []))
        total_enviados = len(temp_db.get("usuarios_enviados", []))
        pendentes = total_alvo - total_enviados
        tokens_falhos = len(temp_db.get("tokens_falhos", []))

        total_falhos = len(temp_db.get("usuarios_falhos", []))
        pendentes = total_alvo - total_enviados - total_falhos

        resumo = (
            f"{emoji.robot} **Bots configurados:** `{total_tokens}` (Válidos: `{tokens_validos}`)\n"
            f"{emoji.message} **Mensagem:** `{'Configurada' if mensagem_configurada else 'Não configurada'}`\n"
            f"{emoji.members} **Usuários alvo:** `{total_alvo}`\n"
            f"{emoji.correct} **Enviados:** `{total_enviados}`\n"
            f"{emoji.wrong} **Erros:** `{total_falhos}`\n"
            f"{emoji.time} **Pendentes:** `{pendentes}`"
        )
        
        if tokens_falhos > 0:
            resumo += f"\n{emoji.warn} **Tokens falhos:** `{tokens_falhos}`"
        
        # Aviso sobre intents
        if tokens_validos > 0:
            resumo += f"\n\n{emoji.warn} **Aviso:** Certifique-se de que todos os bots têm as intents privilegiadas ativadas no Developer Portal (PRESENCE, SERVER_MEMBERS, MESSAGE_CONTENT)."

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > **Disparador DM's**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure o sistema de disparo de mensagens diretas em massa."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Gerenciar Tokens",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.robot,
                        custom_id="DisparadorDM_GerenciarTokens"
                    ),
                    disnake.ui.Button(
                        label="Mensagem",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.message,
                        custom_id="DisparadorDM_EditarMensagem"
                    ),
                    disnake.ui.Button(
                        label="Atualizar",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.reload,
                        custom_id="DisparadorDM_AtualizarPainel"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Iniciar Disparo",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.correct,
                        custom_id="DisparadorDM_IniciarDisparo",
                        disabled=not mensagem_configurada or tokens_validos == 0
                    ),
                    disnake.ui.Button(
                        label="Limpar DB",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="DisparadorDM_LimparDB",
                        disabled=total_alvo == 0 and tokens_falhos == 0
                    ),
                    disnake.ui.Button(
                        label=f"Ver Tokens Falhos ({tokens_falhos})" if tokens_falhos > 0 else "Tokens Falhos",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.warn,
                        custom_id="DisparadorDM_VerTokensFalhos",
                        disabled=tokens_falhos == 0
                    ),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="DisparadorDM_VoltarAutomacoes"
                ),
            )
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        config = helpers.carregar_config()
        tokens = config.get("tokens", [])
        total_tokens = len(tokens)
        tokens_validos = sum(1 for token in tokens if helpers.validar_token(token))
        
        mensagem_data = config.get("mensagem", {})
        mensagem_configurada = bool(
            mensagem_data.get("content") or 
            mensagem_data.get("embed")
        )
        
        temp_db = helpers.carregar_temp_db()
        total_alvo = len(temp_db.get("usuarios_alvo", []))
        total_enviados = len(temp_db.get("usuarios_enviados", []))
        pendentes = total_alvo - total_enviados

        total_falhos = len(temp_db.get("usuarios_falhos", []))
        pendentes = total_alvo - total_enviados - total_falhos

        description_text = (
            f"**Bots configurados:** `{total_tokens}` (Válidos: `{tokens_validos}`)\n"
            f"**Mensagem:** `{'Configurada' if mensagem_configurada else 'Não configurada'}`\n"
            f"**Usuários alvo:** `{total_alvo}`\n"
            f"**Enviados:** `{total_enviados}`\n"
            f"**Erros:** `{total_falhos}`\n"
            f"**Pendentes:** `{pendentes}`"
        )
        
        # Aviso sobre intents
        if tokens_validos > 0:
            description_text += f"\n\n**Aviso:** Certifique-se de que todos os bots têm as intents privilegiadas ativadas no Developer Portal (PRESENCE, SERVER_MEMBERS, MESSAGE_CONTENT)."
        
        embed = disnake.Embed(
            title=f"Disparador DM's",
            description=description_text
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Gerenciar Tokens",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.robot,
                    custom_id="DisparadorDM_GerenciarTokens"
                ),
                disnake.ui.Button(
                    label="Mensagem",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.message,
                    custom_id="DisparadorDM_EditarMensagem"
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Iniciar Disparo",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.correct,
                    custom_id="DisparadorDM_IniciarDisparo",
                    disabled=not mensagem_configurada or tokens_validos == 0
                ),
                disnake.ui.Button(
                    label="Limpar DB",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id="DisparadorDM_LimparDB",
                    disabled=total_alvo == 0
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="DisparadorDM_VoltarAutomacoes"
                ),
            )
        ]
        return embed, components

    @staticmethod
    def PainelTokensFalhos() -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        tokens_falhos = helpers.obter_tokens_falhos()

        if not tokens_falhos:
            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Disparador DM's > **Tokens Falhos**"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay("Nenhum token falhou durante o disparo."),
                    **container_kwargs,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="DisparadorDM_VoltarPainel"
                    ),
                )
            ]

        # Criar texto com lista de tokens falhos
        lista_tokens = f"**Total de tokens falhos:** `{len(tokens_falhos)}`\n\n"
        
        for idx, tf in enumerate(tokens_falhos, 1):
            token_mask = tf.get("token_mascarado", "Token desconhecido")
            motivo = tf.get("motivo", "Sem motivo especificado")
            timestamp = tf.get("timestamp", 0)
            
            # Converter timestamp para data
            import datetime
            data = datetime.datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M") if timestamp else "N/A"
            
            lista_tokens += f"**{idx}.** `{token_mask}`\n"
            lista_tokens += f"  ├ **Motivo:** {motivo}\n"
            lista_tokens += f"  └ **Data:** {data}\n\n"

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Disparador DM's > **Tokens Falhos**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(lista_tokens[:2000]),  # Limitar a 2000 caracteres
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{emoji.warn} Estes tokens foram removidos automaticamente da configuração.\n"
                    f"Eles estão salvos aqui apenas para referência."
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Limpar Tokens Falhos",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="DisparadorDM_LimparTokensFalhos"
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="DisparadorDM_VoltarPainel"
                ),
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

        editor_data = helpers.get_editor_data()
        botoes = editor_data.get("botoes", [])

        if not botoes:
            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Disparador DM's > **Gerenciar Botões**"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay("Nenhum botão foi adicionado ainda."),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Adicionar Botão",
                            style=disnake.ButtonStyle.green,
                            emoji=emoji.plus,
                            custom_id="DisparadorDM_AdicionarBotao"
                        )
                    ),
                    **container_kwargs,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="DisparadorDM_VoltarEditor"
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
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Disparador DM's > **Gerenciar Botões**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Total de botões:** `{len(botoes)}`/`5`\n-# Selecione um botão para remover ou adicione um novo."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione um botão para remover",
                        custom_id="DisparadorDM_RemoverBotao",
                        options=options
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Botão",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.plus,
                        custom_id="DisparadorDM_AdicionarBotao",
                        disabled=len(botoes) >= 5
                    ),
                    disnake.ui.Button(
                        label="Remover Todos",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="DisparadorDM_RemoverTodosBotoes"
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="DisparadorDM_VoltarEditor"
                ),
            )
        ]

    @staticmethod
    def PainelEditor(bot: commands.Bot) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        editor_data = helpers.get_editor_data()
        
        has_message = bool(editor_data.get("content"))
        embed_data = editor_data.get("embed", {})
        has_embed = any(embed_data.get(k) for k in ("title", "description", "footer"))
        has_image = bool(editor_data.get("externalImage") or embed_data.get("banner") or embed_data.get("thumbnail"))
        botoes = editor_data.get("botoes", [])
        has_buttons = isinstance(botoes, list) and len(botoes) > 0
        limite_botoes = isinstance(botoes, list) and len(botoes) >= 5

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Disparador DM's > **Editor de Mensagem**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Configure a mensagem que será enviada aos usuários."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="DisparadorDM_ApagarCampo:content",
                        disabled=not has_message
                    ),
                    disnake.ui.Button(
                        label="Definir Mensagem",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.message,
                        custom_id="DisparadorDM_DefinirMensagem"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="DisparadorDM_ApagarCampo:embed",
                        disabled=not has_embed
                    ),
                    disnake.ui.Button(
                        label="Definir Embed",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.embed,
                        custom_id="DisparadorDM_DefinirEmbed"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="DisparadorDM_ApagarImagensMulti",
                        disabled=not has_image
                    ),
                    disnake.ui.Button(
                        label="Definir Imagens",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.image,
                        custom_id="DisparadorDM_DefinirImagens"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="DisparadorDM_ApagarCampo:botoes",
                        disabled=not has_buttons
                    ),
                    disnake.ui.Button(
                        label="Gerenciar Botões" if has_buttons else "Adicionar Botão",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.edit if has_buttons else emoji.plus,
                        custom_id="DisparadorDM_GerenciarBotoes",
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
                    custom_id="DisparadorDM_VoltarPainel"
                ),
                disnake.ui.Button(
                    label="Visualizar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.search,
                    custom_id="DisparadorDM_Visualizar",
                    disabled=not (has_message or has_embed or has_image or has_buttons)
                )
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
        
        # Handle shortnames from functions.emoji
        if hasattr(emoji, emoji_input):
            emoji_input = getattr(emoji, emoji_input)
        
        if DISCORD_EMOJI_RE.fullmatch(emoji_input):
            try:
                return disnake.PartialEmoji.from_str(emoji_input)
            except Exception:
                return None
        if UNICODE_EMOJI_RE.fullmatch(emoji_input):
            return emoji_input
        return None

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Valida se uma URL é válida."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.netloc or " " in parsed.netloc:
                return False
            if "." not in parsed.netloc:
                return False
            return True
        except Exception:
            return False

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("DisparadorDM_"):
            return

        # Função auxiliar para fazer defer com tratamento de erro
        async def safe_defer():
            try:
                if not inter.response.is_done():
                    await inter.response.defer()
            except disnake.errors.NotFound:
                # Interação expirada ou já respondida, ignorar silenciosamente
                pass
            except Exception as e:
                print(f"Erro ao fazer defer da interação: {e}")

        if cid == "DisparadorDM_VoltarAutomacoes":
            from modules.automations.cog import AutomationModulesCog
            await safe_defer()
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = AutomationModulesCog.PainelEmbed()
                await inter.edit_original_message(embed=embed, components=components)
            else:
                components = AutomationModulesCog.PainelComponents()
                await inter.edit_original_message(components=components)
            return

        if cid == "DisparadorDM_AtualizarPainel":
            await safe_defer()
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(embed=embed, components=components)
            else:
                components = self.Painel()
                await inter.edit_original_message(components=components)

        elif cid == "DisparadorDM_GerenciarTokens":
            config = helpers.carregar_config()
            tokens = config.get("tokens", [])
            await inter.response.send_modal(GerenciarTokensModal(tokens))

        elif cid == "DisparadorDM_EditarMensagem":
            await safe_defer()
            await inter.edit_original_message(components=self.PainelEditor(self.bot))

        elif cid == "DisparadorDM_VoltarPainel":
            await safe_defer()
            await inter.edit_original_message(components=self.Painel())

        elif cid == "DisparadorDM_DefinirMensagem":
            await inter.response.send_modal(DefinirMensagemModal())

        elif cid == "DisparadorDM_DefinirEmbed":
            await inter.response.send_modal(DefinirEmbedModal())

        elif cid == "DisparadorDM_DefinirImagens":
            await inter.response.send_modal(DefinirImagensModal())

        elif cid == "DisparadorDM_GerenciarBotoes":
            await safe_defer()
            await inter.edit_original_message(components=self.PainelGerenciarBotoes())

        elif cid == "DisparadorDM_VoltarEditor":
            await safe_defer()
            await inter.edit_original_message(components=self.PainelEditor(self.bot))

        elif cid == "DisparadorDM_AdicionarBotao":
            await inter.response.send_modal(DefinirBotoesModal())

        elif cid == "DisparadorDM_RemoverTodosBotoes":
            await safe_defer()
            helpers.clear_editor_field("botoes")
            await inter.edit_original_message(components=self.PainelGerenciarBotoes())
            await inter.followup.send(f"{emoji.correct} Todos os botões foram removidos!", ephemeral=True)

        elif cid.startswith("DisparadorDM_ApagarCampo:"):
            await safe_defer()
            field = cid.split(":", 1)[1]
            helpers.clear_editor_field(field)
            await inter.edit_original_message(components=self.PainelEditor(self.bot))

        elif cid == "DisparadorDM_ApagarImagensMulti":
            await safe_defer()
            editor_data = helpers.get_editor_data()
            editor_data["externalImage"] = None
            if "embed" in editor_data:
                editor_data["embed"]["banner"] = None
                editor_data["embed"]["thumbnail"] = None
            helpers.set_editor_data(editor_data)
            await inter.edit_original_message(components=self.PainelEditor(self.bot))

        elif cid == "DisparadorDM_Visualizar":
            await safe_defer()
            editor_data = helpers.get_editor_data()
            if not any(editor_data.get(k) for k in ["content", "embed", "externalImage", "botoes"]):
                await inter.followup.send("Não há nada para visualizar.", ephemeral=True)
                return
            
            data_to_build = editor_data.copy()
            # Remover container se existir (não é suportado)
            data_to_build.pop("container", None)
            
            if "botoes" in data_to_build and data_to_build["botoes"]:
                data_to_build["buttons"] = data_to_build.pop("botoes")
            else:
                data_to_build["buttons"] = []
            
            built = await self.bot.loop.run_in_executor(None, Builder.build_from_cfg, {"message": data_to_build})
            await self._send_built_message(inter, built, ephemeral=True)

        elif cid == "DisparadorDM_IniciarDisparo":
            # Verifica se já existe configuração
            temp_db = helpers.carregar_temp_db()
            if self.disparo_em_andamento:
                await inter.response.send_message(f"{emoji.warn} Já existe um disparo em andamento!", ephemeral=True)
                return
            
            if temp_db.get("usuarios_alvo"):
                # Já tem configuração, iniciar disparo
                await safe_defer()
                await inter.followup.send(f"{emoji.time} Iniciando disparo... Você receberá logs na DM!", ephemeral=True)
                self.task_disparo = asyncio.create_task(self._executar_disparo(inter))
            else:
                # Não tem configuração, abrir modal
                await inter.response.send_modal(ConfigurarDisparoModal())

        elif cid == "DisparadorDM_LimparDB":
            await safe_defer()
            helpers.limpar_temp_db()
            await inter.edit_original_message(components=self.Painel())
            await inter.followup.send(f"{emoji.correct} Base de dados limpa com sucesso!", ephemeral=True)

        elif cid == "DisparadorDM_VerTokensFalhos":
            await safe_defer()
            await inter.edit_original_message(components=self.PainelTokensFalhos())

        elif cid == "DisparadorDM_LimparTokensFalhos":
            await safe_defer()
            helpers.limpar_tokens_falhos()
            await inter.edit_original_message(components=self.PainelTokensFalhos())
            await inter.followup.send(f"{emoji.correct} Lista de tokens falhos limpa!", ephemeral=True)

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("DisparadorDM_"):
            return

        # Função auxiliar para fazer defer com tratamento de erro
        async def safe_defer():
            try:
                if not inter.response.is_done():
                    await inter.response.defer()
            except disnake.errors.NotFound:
                # Interação expirada ou já respondida, ignorar silenciosamente
                pass
            except Exception as e:
                print(f"Erro ao fazer defer da interação: {e}")

        if cid == "DisparadorDM_RemoverBotao":
            await safe_defer()
            button_id = inter.values[0]
            
            editor_data = helpers.get_editor_data()
            botoes = editor_data.get("botoes", [])
            botoes = [b for b in botoes if b.get("id") != button_id]
            helpers.set_editor_field("botoes", botoes)
            
            await inter.edit_original_message(components=self.PainelGerenciarBotoes())
            await inter.followup.send(f"{emoji.correct} Botão removido!", ephemeral=True)

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("DisparadorDM_"):
            return

        if cid == "DisparadorDM_GerenciarTokensModal":
            tokens_text = inter.text_values.get("tokens", "").strip()
            tokens = [t.strip() for t in tokens_text.split("\n") if t.strip()]
            
            config = helpers.carregar_config()
            config["tokens"] = tokens
            helpers.salvar_config(config)
            
            # Validar tokens
            total, validos = helpers.validar_tokens(tokens)
            
            await inter.response.edit_message(components=self.Painel())
            await inter.followup.send(
                f"{emoji.correct} Tokens salvos! Total: `{total}`, Válidos: `{validos}`",
                ephemeral=True
            )

        elif cid == "DisparadorDM_DefinirMensagemModal":
            helpers.set_editor_field("content", inter.text_values["message"])
            await inter.response.edit_message(components=self.PainelEditor(self.bot))

        elif cid == "DisparadorDM_DefinirEmbedModal":
            def validar_hex(codigo: str) -> Optional[str]:
                if not codigo:
                    return None
                codigo = codigo.strip().lstrip("#")
                if len(codigo) not in (3, 6):
                    return None
                try:
                    int(codigo, 16)
                except ValueError:
                    return None
                return f"#{codigo.upper()}"
            
            embed_data = {
                "title": inter.text_values.get("embed_title"),
                "description": inter.text_values.get("embed_description"),
                "color": validar_hex(inter.text_values.get("embed_color")),
                "footer": inter.text_values.get("embed_footer"),
            }
            helpers.set_editor_field("embed", embed_data)
            await inter.response.edit_message(components=self.PainelEditor(self.bot))

        elif cid == "DisparadorDM_DefinirImagensModal":
            editor_data = helpers.get_editor_data()
            editor_data["externalImage"] = inter.text_values.get("externalImage") or None
            if "banner" in inter.text_values:
                if "embed" not in editor_data:
                    editor_data["embed"] = {}
                editor_data["embed"]["banner"] = inter.text_values.get("banner") or None
            if "thumbnail" in inter.text_values:
                if "embed" not in editor_data:
                    editor_data["embed"] = {}
                editor_data["embed"]["thumbnail"] = inter.text_values.get("thumbnail") or None
            helpers.set_editor_data(editor_data)
            await inter.response.edit_message(components=self.PainelEditor(self.bot))

        elif cid == "DisparadorDM_DefinirBotoesModal":
            label = inter.text_values.get("button_label", "").strip()
            url = inter.text_values.get("button_url", "").strip()
            emoji_input = inter.text_values.get("button_emoji", "").strip()
            
            # Validar emoji
            if emoji_input and not self.validar_emoji(emoji_input, self.bot):
                await inter.response.send_message(f"{emoji.warn} Emoji inválido.", ephemeral=True)
                return
            
            # Validar URL se fornecida
            if url and not self._is_valid_url(url):
                await inter.response.send_message(f"{emoji.wrong} URL inválida. Use http(s)://", ephemeral=True)
                return
            
            # Criar botão
            import uuid
            editor_data = helpers.get_editor_data()
            botoes = editor_data.get("botoes", [])
            
            if len(botoes) >= 5:
                await inter.response.send_message("Limite de 5 botões atingido.", ephemeral=True)
                return
            
            button_id = str(uuid.uuid4())
            button_data = {
                "id": button_id,
                "label": label,
                "button": {
                    "type": "url" if url else "disabled",
                    "emoji": emoji_input or None,
                    "url": url or None,
                    "style": "gray" if not url else "url",
                    "disabled": not url,
                }
            }
            
            botoes.append(button_data)
            helpers.set_editor_field("botoes", botoes)
            await inter.response.edit_message(components=self.PainelGerenciarBotoes())
            await inter.followup.send(f"{emoji.correct} Botão adicionado!", ephemeral=True)

        elif cid == "DisparadorDM_ConfigurarDisparoModal":
            server_id = inter.text_values.get("server_id", "").strip()
            role_id = inter.text_values.get("role_id", "").strip()
            exclude_roles = [r.strip() for r in inter.text_values.get("exclude_roles", "").split(",") if r.strip()]
            exclude_users = [u.strip() for u in inter.text_values.get("exclude_users", "").split(",") if u.strip()]
            
            # Mapear usuários alvo
            usuarios_alvo = await helpers.mapear_usuarios_alvo(
                self.bot,
                server_id if server_id else None,
                role_id if role_id else None,
                exclude_roles,
                exclude_users
            )
            
            if not usuarios_alvo:
                await inter.response.send_message(
                    f"{emoji.wrong} Nenhum usuário encontrado com os critérios especificados.",
                    ephemeral=True
                )
                return
            
            # Salvar no temp DB
            helpers.salvar_usuarios_alvo(usuarios_alvo)
            
            # Atualizar painel e enviar mensagem de sucesso
            await inter.response.edit_message(components=self.Painel())
            await inter.followup.send(
                f"{emoji.correct} Disparo configurado! `{len(usuarios_alvo)}` usuários serão notificados.\n"
                f"Clique em **Iniciar Disparo** novamente para começar o envio.",
                ephemeral=True
            )

    # ========== MÉTODOS OTIMIZADOS DE ENVIO ==========
    # Substituem completamente os anteriores _executar_disparo e _send_dm_via_token
    # Além disso, adicionamos funções de serialização de componentes

    @staticmethod
    def _serialize_button(button: disnake.ui.Button) -> dict | None:
        if not isinstance(button, disnake.ui.Button):
            return None
        d: dict = {"type": 2}
        if button.label:    d["label"]     = button.label
        if button.style:    d["style"]     = button.style.value if hasattr(button.style, "value") else int(button.style)
        if button.custom_id: d["custom_id"] = button.custom_id
        if button.url:      d["url"]       = button.url
        if button.disabled: d["disabled"]  = True
        if button.emoji:
            em = button.emoji
            if isinstance(em, str):
                d["emoji"] = {"name": em}
            elif hasattr(em, "id") and em.id:
                d["emoji"] = {"id": str(em.id), "name": em.name, "animated": getattr(em, "animated", False)}
            elif hasattr(em, "name"):
                d["emoji"] = {"name": em.name}
        return d

    @staticmethod
    def _serialize_action_row(row: disnake.ui.ActionRow) -> dict | None:
        children = getattr(row, "children", None) or []
        comps = []
        for child in children:
            if isinstance(child, disnake.ui.Button):
                b = DisparadorDMCog._serialize_button(child)
                if b:
                    comps.append(b)
            elif hasattr(child, "to_dict"):
                try:
                    comps.append(child.to_dict())
                except Exception:
                    pass
        return {"type": 1, "components": comps} if comps else None

    @staticmethod
    def _serialize_components(components: list) -> list:
        result = []
        for comp in components:
            if isinstance(comp, disnake.ui.ActionRow):
                d = DisparadorDMCog._serialize_action_row(comp)
            elif hasattr(comp, "to_dict"):
                try:
                    d = comp.to_dict()
                except Exception:
                    d = None
            else:
                d = None
            if d:
                result.append(d)
        return result

    async def _send_dm_via_token(
        self,
        session: aiohttp.ClientSession,
        token: str,
        user_id: int,
        built_message: dict,
    ) -> tuple[bool, int]:
        """
        Envia uma DM usando aiohttp. Retorna (sucesso, status_code).
        Usa a sessão compartilhada — sem abrir/fechar conexão a cada chamada.
        """
        headers = {"Authorization": f"Bot {token}"}

        # 1. Criar/obter canal DM
        try:
            async with session.post(
                "https://discord.com/api/v10/users/@me/channels",
                headers={**headers, "Content-Type": "application/json"},
                json={"recipient_id": str(user_id)},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status not in (200, 201):
                    return False, r.status
                dm = await r.json()
                channel_id = dm.get("id")
                if not channel_id:
                    return False, 0
        except asyncio.TimeoutError:
            return False, 0
        except Exception as e:
            print(f"[DM] Erro ao criar canal para {user_id}: {e}")
            return False, 0

        # 2. Montar payload (reutiliza a lógica de serialização existente)
        payload_data: dict = {}

        if built_message.get("mode") == "v2":
            components = built_message.get("components") or []
            serialized = self._serialize_components(components)
            if serialized:
                payload_data["components"] = serialized
            flags = built_message.get("flags")
            if flags and hasattr(flags, "value"):
                payload_data["flags"] = flags.value
        else:
            if built_message.get("content"):
                payload_data["content"] = built_message["content"]
            embed = built_message.get("embed")
            if embed:
                if isinstance(embed, disnake.Embed):
                    payload_data["embeds"] = [embed.to_dict()]
                elif isinstance(embed, dict):
                    payload_data["embeds"] = [embed]
            components = built_message.get("components") or []
            serialized = self._serialize_components(components)
            if serialized:
                payload_data["components"] = serialized

        if not payload_data:
            return False, 0

        # 3. Enviar mensagem
        msg_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        try:
            async with session.post(
                msg_url,
                headers={**headers, "Content-Type": "application/json"},
                json=payload_data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                return r.status in (200, 201), r.status
        except asyncio.TimeoutError:
            return False, 0
        except Exception as e:
            print(f"[DM] Erro ao enviar para canal {channel_id}: {e}")
            return False, 0

    async def _executar_disparo(self, inter: disnake.MessageInteraction):
        """
        Executa o disparo de DMs com:
        - aiohttp (sem bloquear o event loop)
        - writes em lote (FLUSH_INTERVAL)
        - log em lote (LOG_INTERVAL)
        - retry com backoff em 429
        - remoção segura de tokens mid-loop
        """
        self.disparo_em_andamento = True

        # Constantes internas
        FLUSH_INTERVAL = 25
        LOG_INTERVAL   = 10
        DELAY_MULTI    = 0.8
        DELAY_SINGLE   = 1.5
        MAX_FORBIDDEN  = 3
        MAX_RATELIMIT  = 5

        async with aiohttp.ClientSession() as session:
            try:
                config = helpers.carregar_config()
                tokens_validos: list[str] = []

                # Validar todos os tokens antes de começar (assíncrono, em paralelo)
                async def _check(token: str):
                    try:
                        async with session.get(
                            "https://discord.com/api/v10/users/@me",
                            headers={"Authorization": f"Bot {token}"},
                            timeout=aiohttp.ClientTimeout(total=5),
                        ) as r:
                            return token if r.status == 200 else None
                    except Exception:
                        return None

                resultados = await asyncio.gather(*[_check(t) for t in config.get("tokens", []) if t.strip()])
                for token, ok in zip(config.get("tokens", []), resultados):
                    if ok:
                        tokens_validos.append(token)
                    else:
                        helpers.adicionar_token_falho(token, "Token inválido ou expirado")
                        helpers.remover_token_do_config(token)

                if not tokens_validos:
                    await inter.followup.send(f"{emoji.wrong} Nenhum token válido disponível.", ephemeral=True)
                    return

                # Construir mensagem
                editor_data = helpers.get_editor_data()
                data_to_build = {k: v for k, v in editor_data.items() if k != "container"}
                data_to_build["buttons"] = data_to_build.pop("botoes", []) or []
                built = await Builder.build_from_cfg({"message": data_to_build})

                pendentes = helpers.get_usuarios_pendentes()
                if not pendentes:
                    await inter.followup.send(f"{emoji.correct} Todos os usuários já receberam a mensagem!", ephemeral=True)
                    return

                total = len(pendentes)
                enviados = 0
                erros = 0

                # Status ephemeral inicial
                try:
                    status_msg = await inter.followup.send(
                        f"{emoji.time} Disparo iniciado! `0/{total}` enviados...\n"
                        f"Tokens ativos: `{len(tokens_validos)}`",
                        ephemeral=True,
                    )
                except Exception:
                    status_msg = None

                # Preparar DM de log
                dm_channel = None
                log_msg = None
                try:
                    dm_channel = await inter.user.create_dm()
                    log_msg = await dm_channel.send(
                        f"**{emoji.correct} Disparo iniciado**\n"
                        f"> Total: `{total}` usuários\n"
                        f"> Tokens: `{len(tokens_validos)}`"
                    )
                except Exception as e:
                    print(f"[DM-log] Não foi possível abrir DM com o operador: {e}")

                # Contadores de erro por token
                forbidden_count: dict[str, int] = {t: 0 for t in tokens_validos}
                ratelimit_count: dict[str, int] = {t: 0 for t in tokens_validos}

                # Índice para rotacionar tokens
                token_idx = 0

                # Buffer de progresso (escritas em lote)
                enviados_buf: list[int] = []
                falhos_buf:   list[int] = []

                # Buffer de log (linhas acumuladas)
                log_buf: list[str] = []

                async def _flush_bufs(force: bool = False):
                    """Persiste progresso e atualiza log se necessário."""
                    nonlocal log_msg
                    if enviados_buf:
                        helpers.adicionar_usuario_enviado_bulk(enviados_buf)
                        enviados_buf.clear()
                    if falhos_buf:
                        helpers.adicionar_usuario_falho_bulk(falhos_buf)
                        falhos_buf.clear()
                    if force or (enviados + erros) % FLUSH_INTERVAL == 0:
                        helpers.flush_progresso()

                    if log_buf and log_msg and (force or (enviados + erros) % LOG_INTERVAL == 0):
                        bloco = "\n".join(log_buf)
                        log_buf.clear()
                        try:
                            current = log_msg.content
                            novo = f"{current}\n{bloco}"
                            if len(novo) > 1950:
                                await log_msg.edit(content=current + "\n`[continua...]`")
                                log_msg = await dm_channel.send(bloco)
                            else:
                                await log_msg.edit(content=novo)
                        except Exception as e:
                            print(f"[DM-log] Erro ao atualizar log: {e}")

                # ── Loop de envio ────────────────────────────────────────────────
                for user_id in pendentes:
                    if not tokens_validos:
                        await inter.followup.send(
                            f"{emoji.wrong} Todos os tokens falharam! Enviados: `{enviados}/{total}`",
                            ephemeral=True,
                        )
                        break

                    token = tokens_validos[token_idx % len(tokens_validos)]
                    retry_delay = 0.0

                    try:
                        user_name = f"ID:{user_id}"
                        try:
                            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                            if user:
                                user_name = user.name
                        except Exception:
                            pass

                        ok, status = await self._send_dm_via_token(session, token, user_id, built)

                        if ok:
                            enviados += 1
                            enviados_buf.append(user_id)
                            forbidden_count[token] = 0
                            ratelimit_count[token] = 0
                            log_buf.append(
                                f"{datetime.datetime.now().strftime('%H:%M:%S')} "
                                f"✓ **{user_name}** (`{user_id}`)"
                            )
                            token_idx += 1

                        elif status == 403:
                            # Usuário bloqueou DMs
                            forbidden_count[token] = forbidden_count.get(token, 0) + 1
                            erros += 1
                            falhos_buf.append(user_id)
                            log_buf.append(
                                f"{datetime.datetime.now().strftime('%H:%M:%S')} "
                                f"✗ **{user_name}** (`{user_id}`) — DMs fechadas"
                            )

                            if forbidden_count[token] >= MAX_FORBIDDEN:
                                helpers.adicionar_token_falho(token, f"{MAX_FORBIDDEN} erros 403 seguidos")
                                helpers.remover_token_do_config(token)
                                tokens_validos.remove(token)
                                del forbidden_count[token]
                                del ratelimit_count[token]
                                if tokens_validos:
                                    token_idx = token_idx % len(tokens_validos)
                            else:
                                token_idx += 1

                        elif status == 429:
                            # Rate limit — backoff e trocar token
                            ratelimit_count[token] = ratelimit_count.get(token, 0) + 1
                            retry_delay = 5.0

                            if ratelimit_count[token] >= MAX_RATELIMIT:
                                helpers.adicionar_token_falho(token, "Rate limit excessivo (429)")
                                helpers.remover_token_do_config(token)
                                tokens_validos.remove(token)
                                del forbidden_count[token]
                                del ratelimit_count[token]
                                if tokens_validos:
                                    token_idx = token_idx % len(tokens_validos)
                                retry_delay = 0.0
                            else:
                                token_idx += 1

                            erros += 1
                            falhos_buf.append(user_id)

                        else:
                            erros += 1
                            falhos_buf.append(user_id)
                            token_idx += 1

                    except Exception as e:
                        print(f"[disparo] Erro inesperado para {user_id}: {e}")
                        erros += 1
                        falhos_buf.append(user_id)
                        token_idx += 1

                    # Flush em lote
                    await _flush_bufs()

                    # Atualizar status a cada 10 envios
                    if (enviados + erros) % 10 == 0 and status_msg:
                        try:
                            await status_msg.edit(
                                content=(
                                    f"{emoji.time} Disparo em andamento... `{enviados}/{total}` enviados\n"
                                    f"Tokens ativos: `{len(tokens_validos)}`"
                                )
                            )
                        except Exception:
                            pass

                    delay = retry_delay or (DELAY_MULTI if len(tokens_validos) > 1 else DELAY_SINGLE)
                    await asyncio.sleep(delay)

                # Flush final de tudo
                await _flush_bufs(force=True)

                # Relatório final
                resumo = (
                    f"**{emoji.correct} Disparo concluído!**\n"
                    f"> Enviados: `{enviados}`\n"
                    f"> Erros: `{erros}`\n"
                    f"> Tokens restantes: `{len(tokens_validos)}`"
                )
                tokens_falhos_lista = helpers.obter_tokens_falhos()
                if tokens_falhos_lista:
                    resumo += f"\n\n{emoji.warn} **Tokens que falharam:** `{len(tokens_falhos_lista)}`"
                    for tf in tokens_falhos_lista[-3:]:
                        resumo += f"\n• `{tf.get('token_mascarado')}` — {tf.get('motivo')}"
                    if len(tokens_falhos_lista) > 3:
                        resumo += f"\n_...e mais {len(tokens_falhos_lista) - 3}_"

                try:
                    if status_msg:
                        await status_msg.edit(content=resumo)
                    else:
                        await inter.followup.send(resumo, ephemeral=True)
                except Exception:
                    pass

                if dm_channel:
                    try:
                        await dm_channel.send(resumo)
                    except Exception:
                        pass

            except Exception as e:
                import traceback
                traceback.print_exc()
                try:
                    await inter.followup.send(f"{emoji.wrong} Erro durante o disparo: {e}", ephemeral=True)
                except Exception:
                    pass
            finally:
                self.disparo_em_andamento = False

    # ========== FIM DOS MÉTODOS OTIMIZADOS ==========

    @staticmethod
    async def _send_built_message(target, built_message: dict, ephemeral: bool = False):
        """Envia uma mensagem construída pelo builder."""
        kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
        if ephemeral:
            kwargs["ephemeral"] = True

        components = built_message.get("components")
        has_components = bool(components and (isinstance(components, list) and len(components) > 0))
        is_empty = not any([
            built_message.get("content"),
            built_message.get("embed"),
            has_components,
            built_message.get("files")
        ])
        if is_empty:
            if isinstance(target, disnake.Interaction):
                await target.followup.send("A mensagem está vazia.", ephemeral=True)
            return None

        if built_message.get("mode") == "v2":
            kwargs["components"] = components
            kwargs["flags"] = built_message.get("flags")
        else:
            if built_message.get("content"):
                kwargs["content"] = built_message["content"]
            if built_message.get("embed"):
                embed_data = built_message["embed"]
                if isinstance(embed_data, disnake.Embed):
                    kwargs["embed"] = embed_data
                else:
                    kwargs["embed"] = disnake.Embed.from_dict(embed_data)
            if built_message.get("components"):
                kwargs["components"] = built_message["components"]
            if built_message.get("files"):
                kwargs["files"] = built_message["files"]
        
        if isinstance(target, disnake.Interaction):
            return await target.followup.send(**kwargs)
        elif isinstance(target, (disnake.TextChannel, disnake.DMChannel, disnake.User, disnake.Member)):
            return await target.send(**kwargs)
        return None


def setup(bot: commands.Bot):
    bot.add_cog(DisparadorDMCog(bot))
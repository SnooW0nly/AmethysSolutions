from disnake.ext import commands
import disnake

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.plan import should_enable_settings_button


class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def settings_components(self, inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        options = [
            disnake.SelectOption(label="Cargos", value="cargos", emoji=emoji.role, description="Gerencie cargos do servidor"),
            disnake.SelectOption(label="Canais", value="canais", emoji=emoji.textc, description="Gerencie canais do servidor"),
            disnake.SelectOption(label="Formas de Pagamento", value="pagamentos", emoji=emoji.wallet, description="Configure provedores e status"),
            disnake.SelectOption(label="Anti-Fake", value="antifake", emoji=emoji.members, description="Configure proteção contra contas falsas"),
            disnake.SelectOption(label="Gerenciar Permissões", value="permissoes", emoji=emoji.members, description="Adicione ou remova permissões de usuários"),
          #  disnake.SelectOption(label="Extensões", value="extensoes", emoji=emoji.commands, description="Gerencie as extensões do bot"),
            disnake.SelectOption(label="Configurar Telegram", value="telegram", emoji=emoji.telegram, description="Configure e valide o bot do Telegram"),
            disnake.SelectOption(label="Notificações", value="notificacoes", emoji=emoji.warn, description="Configure as notificações de vendas"),
            disnake.SelectOption(label="Bloquear Usuários", value="blacklist", emoji=emoji.lock, description="Bloqueie usuários de Comprar em Seu Bot"),
            disnake.SelectOption(label="Tokens", value="tokens", emoji=emoji.members, description="Gerencie tokens de conta do Discord"),
        ]

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > **Configurações**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure e personalize os canais, cargos e formas de pagamento.\n"
                    "Selecione uma seção abaixo para configurar."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Configuracoes_Select",
                        placeholder="Selecione uma seção para configurar",
                        options=options,
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="PainelInicial"
                )
            )
        ]

    def settings_embed(self, inter: disnake.MessageInteraction):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        embed = disnake.Embed(
            title="Configurações",
            description=(
                "Configure e personalize os canais, cargos e formas de pagamento.\n"
                "Selecione uma seção abaixo para configurar."
            ),
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color

        options = [
            disnake.SelectOption(label="Cargos", value="cargos", emoji=emoji.role, description="Gerencie cargos do servidor"),
            disnake.SelectOption(label="Canais", value="canais", emoji=emoji.textc, description="Gerencie canais do servidor"),
            disnake.SelectOption(label="Formas de Pagamento", value="pagamentos", emoji=emoji.wallet, description="Configure provedores e status"),
            disnake.SelectOption(label="Anti-Fake", value="antifake", emoji=emoji.members, description="Configure proteção contra contas falsas"),
            disnake.SelectOption(label="Gerenciar Permissões", value="permissoes", emoji=emoji.members, description="Adicione ou remova permissões de usuários"),
            disnake.SelectOption(label="Extensões", value="extensoes", emoji=emoji.commands, description="Gerencie as extensões do bot"),
            disnake.SelectOption(label="Configurar Telegram", value="telegram", emoji=emoji.telegram, description="Configure e valide o bot do Telegram"),
            disnake.SelectOption(label="Notificações", value="notificacoes", emoji=emoji.warn, description="Configure as notificações de vendas"),
            disnake.SelectOption(label="Bloquear Usuários", value="blacklist", emoji=emoji.lock, description="Bloqueie usuários de Comprar em Seu Bot"),
            disnake.SelectOption(label="Tokens", value="tokens", emoji=emoji.members, description="Gerencie tokens de conta do Discord"),
        ]

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Configuracoes_Select",
                    placeholder="Selecione uma seção para configurar",
                    options=options,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="PainelInicial"
                )
            )
        ]
        return embed, components

    # O ouvinte para "Painel_Configuracoes" foi movido/centralizado no painel principal (painel.py)
    # para evitar o erro "Interaction already acknowledged".

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "Configuracoes_Select":
            return

        choice = inter.values[0]

        if choice == "extensoes":
            from .extensions.cog import ExtensionsPanel
            await ExtensionsPanel.display_panel(inter)
            return

        mode = db.get_document("custom_mode").get("mode")

        if choice == "notificacoes":
            from .notificacoes.cog import ConfigureNotifications
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                panel = ConfigureNotifications.panel(inter)
                await inter.edit_original_message(content=None, **panel)
            else:
                await message.wait(inter, send=False)
                panel = ConfigureNotifications.panel(inter)
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

        elif choice == "blacklist":
            from .bloquear.cog import ConfigurarBlacklist
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                panel = ConfigurarBlacklist.panel(inter)
                await inter.edit_original_message(content=None, **panel)
            else:
                await message.wait(inter, send=False)
                panel = ConfigurarBlacklist.panel(inter)
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

        elif choice == "antifake":
            from .antifake.cog import AntiFakeConfig
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                panel = AntiFakeConfig.panel(inter)
                await inter.edit_original_message(content=None, **panel)
            else:
                await message.wait(inter, send=False)
                panel = AntiFakeConfig.panel(inter)
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

        elif choice == "cargos":
            from .cargos.cog import ConfigurarCargos
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = ConfigurarCargos.cargos_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=ConfigurarCargos.cargos_components(inter))

        elif choice == "canais":
            from .canais.cog import ConfigurarCanais
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = ConfigurarCanais.canais_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=ConfigurarCanais.canais_components(inter))

        elif choice == "pagamentos":
            from .payments.cog import ConfigurarPagamentos
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = ConfigurarPagamentos.pagamentos_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=ConfigurarPagamentos.pagamentos_components(inter))

        elif choice == "permissoes":
            from .permissoes.cog import GerenciarPermissoes
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = GerenciarPermissoes.panel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                panel = GerenciarPermissoes.panel(inter)
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

        elif choice == "tokens":
            from .tokens.cog import TokensPanel
            await message.wait(inter, send=False)
            panel = TokensPanel.panel(inter)
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

        elif choice == "telegram":
            from .telegram.cog import TelegramConfig
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                panel = TelegramConfig.panel(inter)
                await inter.edit_original_message(content=None, **panel)
            else:
                await message.wait(inter, send=False)
                panel = TelegramConfig.panel(inter)
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
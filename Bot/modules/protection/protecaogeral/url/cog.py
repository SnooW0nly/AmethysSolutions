import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message
from . import helpers, interactions, url_manager

class ProtecaoUrlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.url_manager = url_manager.URLManager(bot)

    def _get_advanced_descriptions(self, avancado: dict) -> tuple:
        url_nome = avancado.get("url_nome") or "Nenhum"
        canal_logs_id = avancado.get("canal_logs")
        canal = self.bot.get_channel(canal_logs_id) if canal_logs_id else None
        token_user_id = avancado.get("token_user_id")
        token_data = None
        if token_user_id:
            tokens = db.get_document("tokens", {}).get("list", [])
            token_data = next((t for t in tokens if t["user_id"] == token_user_id), None)
        return (f"Atual: {url_nome}", f"Atual: {canal.name if canal else 'Nenhum'}",
                f"Atual: {token_data['username'] if token_data else 'Nenhuma'}")

    async def display_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, comps = self._painel_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            comps = self._painel_components(inter)
            await inter.edit_original_message(content=None, embed=None, components=comps)

    async def display_url_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, comps = self._url_panel_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            comps = self._url_panel_components(inter)
            await inter.edit_original_message(content=None, embed=None, components=comps)

    async def display_log_channel_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, comps = self._log_panel_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            comps = self._log_panel_components(inter)
            await inter.edit_original_message(content=None, embed=None, components=comps)

    async def display_token_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, comps = self._token_panel_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            comps = self._token_panel_components(inter)
            await inter.edit_original_message(content=None, embed=None, components=comps)

    def _painel_embed(self, inter):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        av = config.get("protecao_url_avancado", {})
        colors = db.get_document("custom_colors")
        color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None
        embed = disnake.Embed(title="Proteção de URL", color=color)
        status = emoji.on if dados.get("ativado") else emoji.off
        desc_url, desc_logs, desc_token = self._get_advanced_descriptions(av)
        embed.description = f"{status} **Status:** `{'Ativado' if dados.get('ativado') else 'Desativado'}`"
        comps = [
            disnake.ui.ActionRow(disnake.ui.Select(
                placeholder="Configurar Proteção",
                options=[disnake.SelectOption(label="Desativar" if dados.get('ativado') else "Ativar",
                                               value="toggle", emoji=emoji.power)],
                custom_id="ProtUrlConfigSelect")),
            disnake.ui.ActionRow(disnake.ui.Select(
                placeholder="Configurações Avançadas",
                options=[
                    disnake.SelectOption(label="Configurar URL", value="url", emoji=emoji.link, description=desc_url),
                    disnake.SelectOption(label="Configurar Conta", value="token", emoji=emoji.members, description=desc_token),
                    disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=desc_logs),
                ],
                custom_id="ProtUrlConfigSelectAvancado")),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                                                   emoji=emoji.back, custom_id="Protecao_Geral"))
        ]
        return embed, comps

    def _painel_components(self, inter):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        av = config.get("protecao_url_avancado", {})
        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        accent = {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))} if hex_color else {}
        status = emoji.on if dados.get("ativado") else emoji.off
        desc_url, desc_logs, desc_token = self._get_advanced_descriptions(av)
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > **Proteção URL**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"{status} **Status:** `{'Ativado' if dados.get('ativado') else 'Desativado'}`\n"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(disnake.ui.Select(
                    placeholder="Configurar Proteção",
                    options=[disnake.SelectOption(label="Desativar" if dados.get('ativado') else "Ativar",
                                                   value="toggle", emoji=emoji.power)],
                    custom_id="ProtUrlConfigSelect")),
                disnake.ui.ActionRow(disnake.ui.Select(
                    placeholder="Configurações Avançadas",
                    options=[
                        disnake.SelectOption(label="Configurar URL", value="url", emoji=emoji.link, description=desc_url),
                        disnake.SelectOption(label="Configurar Conta", value="token", emoji=emoji.members, description=desc_token),
                        disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=desc_logs),
                    ],
                    custom_id="ProtUrlConfigSelectAvancado")),
                **accent
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                                                   emoji=emoji.back, custom_id="Protecao_Geral"))
        ]

    def _url_panel_embed(self, inter):
        config = helpers.carregar_config()
        av = config.get("protecao_url_avancado", {})
        colors = db.get_document("custom_colors")
        color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None
        embed = disnake.Embed(title="Configurar URL", description="Defina a vanity URL do servidor.", color=color)
        embed.add_field(name="Nome atual", value=f"`{av.get('url_nome') or 'Nenhum'}`")
        comps = [
            disnake.ui.ActionRow(disnake.ui.Button(label="Configurar URL", style=disnake.ButtonStyle.blurple,
                                                   emoji=emoji.link, custom_id="ProtUrl_Configure"),
                                 disnake.ui.Button(label="Verificar Status", style=disnake.ButtonStyle.grey,
                                                   emoji=emoji.search, custom_id="ProtUrl_CheckStatus")),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtUrl_Back"))
        ]
        return embed, comps

    def _url_panel_components(self, inter):
        config = helpers.carregar_config()
        av = config.get("protecao_url_avancado", {})
        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        accent = {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))} if hex_color else {}
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Proteção URL > **URL**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**URL atual:** `{av.get('url_nome') or 'Nenhum'}`"),
                disnake.ui.ActionRow(disnake.ui.Button(label="Configurar URL", style=disnake.ButtonStyle.blurple,
                                                       emoji=emoji.link, custom_id="ProtUrl_Configure"),
                                     disnake.ui.Button(label="Verificar Status", style=disnake.ButtonStyle.grey,
                                                       emoji=emoji.search, custom_id="ProtUrl_CheckStatus")),
                **accent
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtUrl_Back"))
        ]

    def _log_panel_embed(self, inter):
        config = helpers.carregar_config()
        av = config.get("protecao_url_avancado", {})
        colors = db.get_document("custom_colors")
        color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None
        embed = disnake.Embed(title="Canal de Logs", color=color)
        canal_id = av.get("canal_logs")
        embed.add_field(name="Canal atual", value=f"<#{canal_id}>" if canal_id else "Nenhum")
        comps = [
            disnake.ui.ActionRow(disnake.ui.ChannelSelect(custom_id="ProtUrlLogChannelSelect", channel_types=[disnake.ChannelType.text])),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtUrl_Back"),
                                 disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                                   custom_id="ProtUrlLogChannelClear", disabled=not canal_id),
                                 disnake.ui.Button(label="Criar para mim", style=disnake.ButtonStyle.blurple,
                                                   emoji=emoji.wand, custom_id="ProtUrlLogChannelCreate"))
        ]
        return embed, comps

    def _log_panel_components(self, inter):
        config = helpers.carregar_config()
        av = config.get("protecao_url_avancado", {})
        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        accent = {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))} if hex_color else {}
        canal_id = av.get("canal_logs")
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Proteção URL > **Logs**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Canal atual: {f'<#{canal_id}>' if canal_id else 'Nenhum'}"),
                disnake.ui.ActionRow(disnake.ui.ChannelSelect(custom_id="ProtUrlLogChannelSelect", channel_types=[disnake.ChannelType.text])),
                **accent
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtUrl_Back"),
                                 disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                                   custom_id="ProtUrlLogChannelClear", disabled=not canal_id),
                                 disnake.ui.Button(label="Criar para mim", style=disnake.ButtonStyle.blurple,
                                                   emoji=emoji.wand, custom_id="ProtUrlLogChannelCreate"))
        ]

    def _token_panel_embed(self, inter):
        config = helpers.carregar_config()
        av = config.get("protecao_url_avancado", {})
        colors = db.get_document("custom_colors")
        color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None
        embed = disnake.Embed(title="Conta para Gerenciar URL", color=color)
        token_user_id = av.get("token_user_id")
        tokens = db.get_document("tokens", {}).get("list", [])
        token_data = next((t for t in tokens if t["user_id"] == token_user_id), None)
        embed.add_field(name="Conta selecionada", value=f"**{token_data['username']}** (`{token_user_id}`)" if token_data else "Nenhuma")
        options = [disnake.SelectOption(label=t["username"], value=t["user_id"], description=f"ID: {t['user_id']}",
                                        default=t["user_id"] == token_user_id) for t in tokens]
        if not options:
            options.append(disnake.SelectOption(label="Nenhuma conta disponível", value="__empty__"))
        comps = [
            disnake.ui.ActionRow(disnake.ui.Select(options=options, custom_id="ProtUrlTokenSelect", placeholder="Selecione uma conta")),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtUrl_Back"))
        ]
        return embed, comps

    def _token_panel_components(self, inter):
        config = helpers.carregar_config()
        av = config.get("protecao_url_avancado", {})
        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        accent = {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))} if hex_color else {}
        token_user_id = av.get("token_user_id")
        tokens = db.get_document("tokens", {}).get("list", [])
        token_data = next((t for t in tokens if t["user_id"] == token_user_id), None)
        options = [disnake.SelectOption(label=t["username"], value=t["user_id"], description=f"ID: {t['user_id']}",
                                        default=t["user_id"] == token_user_id) for t in tokens]
        if not options:
            options.append(disnake.SelectOption(label="Nenhuma conta disponível", value="__empty__"))
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Proteção URL > **Conta**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Conta atual: {token_data['username'] if token_data else 'Nenhuma'}"),
                disnake.ui.ActionRow(disnake.ui.Select(options=options, custom_id="ProtUrlTokenSelect", placeholder="Selecione uma conta")),
                **accent
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtUrl_Back"))
        ]

    @commands.Cog.listener("on_dropdown")
    async def _on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if "ProtUrl" not in cid:
            return
        if cid == "ProtUrlTokenSelect":
            await interactions.handle_token_select(self, inter)
            return
        if cid == "ProtUrlLogChannelSelect":
            await interactions.handle_log_channel_select(self, inter)
            return
        if inter.values:
            value = inter.values[0]
            mapping = {"toggle": interactions.handle_toggle, "url": interactions.handle_set_url,
                       "token": interactions.handle_set_token, "canal_logs": interactions.handle_set_log_channel}
            if handler := mapping.get(value):
                await handler(self, inter)

    @commands.Cog.listener("on_button_click")
    async def _on_button(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if "ProtUrl" not in cid:
            return
        mapping = {
            "ProtUrl_Back": self.display_panel,
            "ProtUrl_Configure": interactions.handle_configure_url,
            "ProtUrl_CheckStatus": interactions.handle_check_status,
            "ProtUrlLogChannelClear": interactions.handle_log_channel_clear,
            "ProtUrlLogChannelCreate": interactions.handle_log_channel_create,
        }
        if handler := mapping.get(cid):
            if cid == "ProtUrl_Back":
                await handler(inter)
            else:
                await handler(self, inter)


def setup(bot: commands.Bot):
    bot.add_cog(ProtecaoUrlCog(bot))
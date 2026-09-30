import disnake
from disnake.ext import commands

from datetime import datetime
from functions.emoji import emoji
from functions.database import database as db
from functions.perms import perms
from functions.message import message, embed_message
from functions.utils import utils
from functions.plan import should_enable_panel_button


def _get_user_features(user_id: str) -> list[str] | None:
    """Retorna as features liberadas para o usuário ou None (= acesso total)."""
    doc = db.get_document("user_permissions") or {}
    return doc.get("permissions", {}).get(str(user_id))


def _mode() -> str:
    return (db.get_document("custom_mode") or {}).get("mode", "components")


def _primary_color() -> str | None:
    colors = db.get_document("custom_colors")
    return colors.get("primary") if colors else None


async def _defer_interaction(inter: disnake.MessageInteraction):
    """
    Faz defer da interaction de forma segura.
    Evita o erro 40060 (already acknowledged) verificando se já foi respondida.
    """
    if inter.response.is_done():
        return
    try:
        await inter.response.defer(with_message=False)
    except disnake.errors.HTTPException:
        pass


class PainelCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS INTERNOS
    # ══════════════════════════════════════════════════════════════════════════

    def _get_salutation(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "bom dia! ☀️"
        elif 12 <= hour < 18:
            return "boa tarde! 🌞"
        else:
            return "boa noite! 🌙"

    def _build_button_states(self, user_id: str | None = None) -> dict:
        global_states = {
            "loja":           should_enable_panel_button("loja"),
            "ticket":         should_enable_panel_button("ticket"),
            "cloud":          should_enable_panel_button("cloud"),
            "personalizacao": should_enable_panel_button("personalizacao"),
            "automacoes":     should_enable_panel_button("automacoes"),
            "protection":     should_enable_panel_button("protection"),
            "sorteios":       should_enable_panel_button("sorteios"),
            "configuracoes":  should_enable_panel_button("configuracoes"),
            "economia":       should_enable_panel_button("economia"),
        }

        if user_id is None:
            return global_states

        owner_id = perms.get_owner_id()
        if str(user_id) == str(owner_id):
            return global_states

        user_features = _get_user_features(user_id)
        if user_features is None:
            return global_states

        return {
            key: global_states[key] and (key in user_features)
            for key in global_states
        }

    # ══════════════════════════════════════════════════════════════════════════
    # BUILDERS DE COMPONENTES
    # ══════════════════════════════════════════════════════════════════════════

    def PainelComponents(
        self,
        inter: disnake.MessageInteraction,
        primary_color_hex: str = None,
        button_states: dict = None,
    ) -> list:
        """
        Retorna os components no modo Container (Components V2).
        Container é exclusivo — não pode ser misturado com embed/content.
        """
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        if button_states is None:
            button_states = self._build_button_states(str(inter.user.id))

        # SelectMenu com Economia e Comunidade + Ferramentas, Parcerias e Apostado Free Fire
        select_options = [
            disnake.SelectOption(
                label="Economia",
                value="economia",
                emoji=emoji.coin,
                description="Gerencie o sistema de economia",
            ),
            disnake.SelectOption(
                label="Comunidade",
                value="comunidade",
                emoji=emoji.group,
                description="Recursos de comunidade do servidor",
            ),
            disnake.SelectOption(
                label="Formulários",
                value="formularios",
                emoji=emoji.pin,
                description="Gerencie o sistema de formulários",
            ),
            disnake.SelectOption(
                label="Ferramentas",
                value="tools",
                emoji=emoji.config,
                description="Ferramentas e utilitários do sistema",
            ),
         #   disnake.SelectOption(
           #     label="Parcerias",
             #   value="parcerias",
             #   emoji=emoji.partner,
             #   description="Gerencie o sistema de parcerias automática",
           # ),
            disnake.SelectOption(
                label="Apostado Free Fire",
                value="apostadoff",
                emoji=emoji.gun,
                description="Gerencie o sistema de apostas Free Fire",
            ),
        ]

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"Olá senhor(a) **{inter.user.name}**, {self._get_salutation()} \n"
                    f"-# Aqui você pode **configurar** e **personalizar** as funcionalidades do seu **Amethys Pro**."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Painel_Select_Menu",
                        placeholder="Selecione uma categoria para gerenciar",
                        options=select_options,
                    )
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Configurar Loja",      style=disnake.ButtonStyle.grey, emoji=emoji.cart,     custom_id="Painel_Loja",           disabled=not button_states["loja"]),
                    disnake.ui.Button(label="Gerenciar Ticket",     style=disnake.ButtonStyle.grey, emoji=emoji.ticket,   custom_id="Painel_Ticket",         disabled=not button_states["ticket"]),
                    disnake.ui.Button(label="AMYCloud",             style=disnake.ButtonStyle.grey, emoji=emoji.cloud,    custom_id="Painel_Cloud",          disabled=not button_states["cloud"]),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Ver Rendimento",       style=disnake.ButtonStyle.grey, emoji=emoji.chart,    custom_id="Painel_Rendimentos",    disabled=not button_states["ticket"]),
                    disnake.ui.Button(label="Personalização",       style=disnake.ButtonStyle.grey, emoji=emoji.wand,     custom_id="Painel_Personalizacao", disabled=not button_states["personalizacao"]),
                    disnake.ui.Button(label="Automações",           style=disnake.ButtonStyle.grey, emoji=emoji.reload,   custom_id="Painel_Automacoes",     disabled=not button_states["automacoes"]),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Proteção do Servidor", style=disnake.ButtonStyle.grey, emoji=emoji.shield,   custom_id="Painel_Protection",     disabled=not button_states["protection"]),
                    disnake.ui.Button(label="Sorteios",             style=disnake.ButtonStyle.grey, emoji=emoji.giveaway, custom_id="Painel_Sorteios",        disabled=not button_states["sorteios"]),
                    disnake.ui.Button(label="Configurações",        style=disnake.ButtonStyle.grey, emoji=emoji.config,   custom_id="Painel_Configuracoes",   disabled=not button_states["configuracoes"]),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Acesse a Dashboard", style=disnake.ButtonStyle.grey, url="https://www.amethys.solutions"),
            ),
        ]

    def PainelEmbed(
        self,
        inter: disnake.MessageInteraction,
        primary_color_hex: str = None,
        button_states: dict = None,
    ) -> tuple[disnake.Embed, list]:
        """
        Retorna (embed, components) no modo Embed clássico.
        Embed não pode ser usado junto de Container — são modos separados.
        """
        embed = disnake.Embed(
            title="Painel",
            description=(
                f"Olá senhor(a) **{inter.user.name}**, {self._get_salutation()} \n"
                f"-# Aqui você pode **configurar** e **personalizar** as funcionalidades do seu **Amethys Pro**."
            ),
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        if button_states is None:
            button_states = self._build_button_states(str(inter.user.id))

        # SelectMenu com Economia e Comunidade + Ferramentas, Parcerias e Apostado Free Fire
        select_options = [
            disnake.SelectOption(
                label="Economia",
                value="economia",
                emoji=emoji.coin,
                description="Gerencie o sistema de economia",
            ),
            disnake.SelectOption(
                label="Comunidade",
                value="comunidade",
                emoji=emoji.group,
                description="Recursos de comunidade do servidor",
            ),
            disnake.SelectOption(
                label="Formulários",
                value="formularios",
                emoji=emoji.pin,
                description="Gerencie o sistema de formulários",
            ),
            disnake.SelectOption(
                label="Ferramentas",
                value="tools",
                emoji=emoji.config,
                description="Ferramentas e utilitários do sistema",
            ),
            disnake.SelectOption(
                label="Apostado Free Fire",
                value="apostadoff",
                emoji=emoji.gun,
                description="Gerencie o sistema de apostas Free Fire",
            ),
        ]

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Painel_Select_Menu",
                    placeholder="Selecione uma categoria para gerenciar",
                    options=select_options,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Configurar Loja",      style=disnake.ButtonStyle.grey, emoji=emoji.cart,     custom_id="Painel_Loja",           disabled=not button_states["loja"]),
                disnake.ui.Button(label="Gerenciar Ticket",     style=disnake.ButtonStyle.grey, emoji=emoji.ticket,   custom_id="Painel_Ticket",         disabled=not button_states["ticket"]),
                disnake.ui.Button(label="AMYCloud",             style=disnake.ButtonStyle.grey, emoji=emoji.cloud,    custom_id="Painel_Cloud",          disabled=not button_states["cloud"]),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Ver Rendimento",       style=disnake.ButtonStyle.grey, emoji=emoji.chart,    custom_id="Painel_Rendimentos",    disabled=not button_states["ticket"]),
                disnake.ui.Button(label="Personalização",       style=disnake.ButtonStyle.grey, emoji=emoji.wand,     custom_id="Painel_Personalizacao", disabled=not button_states["personalizacao"]),
                disnake.ui.Button(label="Automações",           style=disnake.ButtonStyle.grey, emoji=emoji.reload,   custom_id="Painel_Automacoes",     disabled=not button_states["automacoes"]),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Proteção do Servidor", style=disnake.ButtonStyle.grey, emoji=emoji.shield,   custom_id="Painel_Protection",     disabled=not button_states["protection"]),
                disnake.ui.Button(label="Sorteios",             style=disnake.ButtonStyle.grey, emoji=emoji.giveaway, custom_id="Painel_Sorteios",        disabled=not button_states["sorteios"]),
                disnake.ui.Button(label="Configurações",        style=disnake.ButtonStyle.grey, emoji=emoji.config,   custom_id="Painel_Configuracoes",   disabled=not button_states["configuracoes"]),
            ),
        ]
        return embed, components

    # ══════════════════════════════════════════════════════════════════════════
    # COMANDO /painel
    # ══════════════════════════════════════════════════════════════════════════

    @commands.slash_command(
        name="painel",
        description="Abre o painel de controle do bot.",
        guild_ids=[utils.obter_server_principal()],
    )
    async def painel(self, inter: disnake.ApplicationCommandInteraction):
        mode              = _mode()
        primary_color_hex = _primary_color()

        # Slash commands sempre precisam de defer antes de edit_original_response
        if mode == "embed":
            await embed_message.wait(inter, send=True)
        else:
            await message.wait(inter, send=True)

        if not await perms.check(inter.user.id):
            if mode == "embed":
                await embed_message.error(inter, "Você não tem permissão para usar este comando", send=False)
            else:
                await message.error(inter, "Você não tem permissão para usar este comando", send=False)
            return

        button_states = self._build_button_states(str(inter.user.id))

        if mode == "embed":
            embed, components = self.PainelEmbed(inter, primary_color_hex, button_states)
            await inter.edit_original_response(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_response(
                components=self.PainelComponents(inter, primary_color_hex, button_states),
            )

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENER — DROPDOWN
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_dropdown")
    async def Painel_Dropdown_Listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "Painel_Select_Menu":
            return

        if not inter.response.is_done():
            await inter.response.defer(with_message=False)

        choice = inter.values[0]
        mode   = _mode()

        if choice == "economia":
            economy_cog = self.bot.get_cog("EconomyCog")
            if not economy_cog:
                await inter.edit_original_message(content="⚠️ Módulo de economia não encontrado.")
                return

            if mode == "embed":
                embed, components = economy_cog.economy_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(
                    components=economy_cog.economy_components(inter)
                )

        elif choice == "comunidade":
            comunidade_cog = self.bot.get_cog("ComunidadeCog")
            if not comunidade_cog:
                await inter.edit_original_message(content="⚠️ Módulo de comunidade não encontrado.")
                return

            if mode == "embed":
                embed, components = comunidade_cog.community_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(
                    components=comunidade_cog.community_components(inter)
                )

        elif choice == "formularios":
            formulario_cog = self.bot.get_cog("FormularioCog")
            if not formulario_cog:
                await inter.edit_original_message(content="⚠️ Módulo de formulários não encontrado.")
                return

            if mode == "embed":
                if hasattr(formulario_cog, "PainelEmbed"):
                    embed, components = formulario_cog.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                if hasattr(formulario_cog, "Painel"):
                    await inter.edit_original_message(components=formulario_cog.Painel())

        # ── NOVAS OPÇÕES (apenas componentes v2) ──
        elif choice == "tools":
            from modules.utilitarios.tools import paineis as tools_paineis
            config = db.get_document("tools_config") or {}
            await inter.edit_original_message(
                components=tools_paineis.get_tools_main(config),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif choice == "parcerias":
            from modules.utilitarios.parcerias.cog import get_parcerias_main
            config = db.get_document("parcerias_config") or {}
            await inter.edit_original_message(
                components=get_parcerias_main(config),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif choice == "apostadoff":
            from modules.utilitarios.apostadoff.paineis import get_painel_principal
            config = db.get_document("apostadoff_config") or {}
            await inter.edit_original_message(
                components=get_painel_principal(config),
                flags=disnake.MessageFlags(is_components_v2=True)
            )

        elif choice == "middleman":
            from modules.utilitarios.middleman.cog import get_middleman_main
            await inter.edit_original_message(
                components=get_middleman_main(inter),
                flags=disnake.MessageFlags(is_components_v2=True)
            )
    # ══════════════════════════════════════════════════════════════════════════
    # LISTENER — BUTTONS
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def Painel_Button_Listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Painel"):
            return

        # Reconhecer a interação imediatamente para evitar que outros listeners disparem erro
        await _defer_interaction(inter)

        mode              = _mode()
        primary_color_hex = _primary_color()

        # ── Voltar ao painel inicial ──────────────────────────────────────────
        if cid == "PainelInicial":
            button_states = self._build_button_states(str(inter.user.id))

            if mode == "embed":
                embed, components = self.PainelEmbed(inter, primary_color_hex, button_states)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(
                    components=self.PainelComponents(inter, primary_color_hex, button_states),
                )

        # ── Configurações ─────────────────────────────────────────────────────
        elif cid == "Painel_Configuracoes":
            settings_cog = self.bot.get_cog("Settings")
            if not settings_cog:
                await inter.followup.send("⚠️ Módulo de configurações não encontrado.", ephemeral=True)
                return

            if mode == "embed":
                embed, components = settings_cog.settings_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(
                    components=settings_cog.settings_components(inter)
                )

        # ── Economia (botão direto, caso exista) ──────────────────────────────
        elif cid == "Painel_Economia":
            economy_cog = self.bot.get_cog("EconomyCog")
            if not economy_cog:
                await inter.followup.send("⚠️ Módulo de economia não encontrado.", ephemeral=True)
                return

            if mode == "embed":
                embed, components = economy_cog.economy_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(
                    components=economy_cog.economy_components(inter)
                )

        # ── Proteção ─────────────────────────────────────────────────────────
        elif cid == "Painel_Protection":
            config   = db.obter("config.json")
            owner_id = config.get("bot", {}).get("owner")
            if str(inter.user.id) != str(owner_id):
                await inter.followup.send(
                    f"{emoji.wrong} Apenas o dono do bot pode acessar esta funcionalidade.",
                    ephemeral=True,
                )
                return
            protection_cog = self.bot.get_cog("ProtectionCog")
            if protection_cog:
                await protection_cog.display_protection_panel(inter)

        # ── Automações ───────────────────────────────────────────────────────
        elif cid == "Painel_Automacoes":
            automations_cog = self.bot.get_cog("AutomationModulesCog")
            if automations_cog:
                await automations_cog.display_automations_panel(inter)

        # ── Ticket ───────────────────────────────────────────────────────────
        elif cid == "Painel_Ticket":
            ticket_cog = self.bot.get_cog("TicketConfigCog")
            if ticket_cog:
                await ticket_cog.display_ticket_panel(inter)

        # ── Sorteios ─────────────────────────────────────────────────────────
        elif cid == "Painel_Sorteios":
            giveaways_cog = self.bot.get_cog("Giveaways")
            if giveaways_cog:
                await giveaways_cog.display_giveaways_panel(inter)

        # ── Cloud ────────────────────────────────────────────────────────────
        elif cid == "Painel_Cloud":
            cloud_cog = self.bot.get_cog("Cloud")
            if cloud_cog:
                await cloud_cog.display_cloud_panel(inter)

        # ── Rendimentos ──────────────────────────────────────────────────────
        elif cid == "Painel_Rendimentos":
            rendimentos_cog = self.bot.get_cog("RendimentosSystem")
            if not rendimentos_cog:
                await inter.followup.send("⚠️ Módulo de rendimentos não encontrado.", ephemeral=True)
                return

            if mode == "embed":
                embed, components = rendimentos_cog.panel(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(**rendimentos_cog.panel(inter))


def setup(bot: commands.Bot):
    bot.add_cog(PainelCommand(bot))
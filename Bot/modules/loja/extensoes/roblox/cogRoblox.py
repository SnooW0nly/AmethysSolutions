import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message
from .paineis import get_roblox_main_panel, get_botoes_panel, get_calculadora_panel, get_auto_delivery_panel, get_extensoes_panel


class CookieModal(disnake.ui.Modal):
    """Modal para o admin configurar o cookie .ROBLOSECURITY da conta que faz entregas."""
    def __init__(self):
        super().__init__(
            title="Configurar Cookie Roblox",
            custom_id="Roblox_CookieModal",
            components=[
                disnake.ui.TextInput(
                    label="Cookie .ROBLOSECURITY",
                    custom_id="cookie",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    max_length=2000,
                    placeholder="Cole aqui o valor do cookie .ROBLOSECURITY da sua conta Roblox",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        cookie = str(inter.resolved_values.get("cookie", "")).strip()

        if not cookie:
            await inter.response.send_message(f"{emoji.wrong} Cookie inválido.", ephemeral=True)
            return

        # Salvar cookie e testar login via API
        from .roblox_auto_delivery import RobloxAutoClient
        client = RobloxAutoClient(cookie)
        ok, msg = await client.login()

        if not ok:
            await inter.response.send_message(
                f"{emoji.wrong} Não foi possível autenticar com este cookie: `{msg}`\n"
                f"-# Verifique se o cookie está correto e tente novamente.",
                ephemeral=True,
            )
            return

        cfg = db.get_document("roblox_auto_config") or {}
        cfg["cookie"] = cookie
        cfg["enabled"] = cfg.get("enabled", True)
        db.save_document("roblox_auto_config", cfg)

        config = db.get_document("roblox_config") or {}
        components, flags = get_auto_delivery_panel(config, mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)


class LimitesModal(disnake.ui.Modal):
    def __init__(self):
        config = db.get_document("roblox_config") or {}
        super().__init__(
            title="Configurar Limites de Robux",
            custom_id="Roblox_LimitesModal",
            components=[
                disnake.ui.TextInput(
                    label="Valor mínimo de Robux",
                    custom_id="min_robux",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=10,
                    value=str(config.get("min_robux", 100)),
                    placeholder="Ex: 100",
                ),
                disnake.ui.TextInput(
                    label="Valor máximo de Robux",
                    custom_id="max_robux",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=10,
                    value=str(config.get("max_robux", 100000)),
                    placeholder="Ex: 100000",
                ),
                disnake.ui.TextInput(
                    label="Preço por 1000 Robux (R$)",
                    custom_id="preco_por_mil",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=10,
                    value=str(config.get("preco_por_mil", 32.70)),
                    placeholder="Ex: 32.70",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")

        valores = inter.resolved_values
        try:
            min_robux = int(str(valores.get("min_robux", "100")).strip())
        except Exception:
            min_robux = 100
        try:
            max_robux = int(str(valores.get("max_robux", "100000")).strip())
        except Exception:
            max_robux = 100000
        try:
            preco_por_mil = float(str(valores.get("preco_por_mil", "32.70")).replace(",", ".").strip())
        except Exception:
            preco_por_mil = 32.70

        if min_robux < 1:
            min_robux = 1
        if max_robux < min_robux:
            max_robux = min_robux

        config = db.get_document("roblox_config") or {}
        config["min_robux"] = min_robux
        config["max_robux"] = max_robux
        config["preco_por_mil"] = preco_por_mil
        db.save_document("roblox_config", config)

        components, flags = get_roblox_main_panel(config, mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)


class VendasModal(disnake.ui.Modal):
    """Modal com Label+StringSelect para ativar/desativar vendas de Robux e Gamepass."""
    def __init__(self):
        config = db.get_document("roblox_config") or {}
        robux_default = "ativar" if config.get("robux_sale_enabled", True) else "desativar"
        gamepass_default = "ativar" if config.get("gamepass_sale_enabled", True) else "desativar"

        super().__init__(
            title="Configurar Vendas Ativas",
            custom_id="Roblox_VendasModal",
            components=[
                disnake.ui.Label(
                    text="Venda de Robux",
                    component=disnake.ui.StringSelect(
                        custom_id="robux_sale",
                        placeholder=f"Atual: {robux_default}",
                        options=[
                            disnake.SelectOption(label="Ativar", value="true",emoji=emoji.on, description="Permitir compras de Robux"),
                            disnake.SelectOption(label="Desativar", value="false",emoji=emoji.off, description="Bloquear compras de Robux"),
                        ],
                        min_values=1,
                        max_values=1,
                    ),
                    description="Controla se a venda de Robux está disponível.",
                ),
                disnake.ui.Label(
                    text="Venda de Gamepass",
                    component=disnake.ui.StringSelect(
                        custom_id="gamepass_sale",
                        placeholder=f"Atual: {gamepass_default}",
                        options=[
                            disnake.SelectOption(label="Ativar", value="true",emoji=emoji.on, description="Permitir compras de Gamepass"),
                            disnake.SelectOption(label="Desativar", value="false",emoji=emoji.off, description="Bloquear compras de Gamepass"),
                        ],
                        min_values=1,
                        max_values=1,
                    ),
                    description="Controla se a venda de Gamepass está disponível.",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")

        valores = inter.resolved_values

        # StringSelect retorna lista de valores selecionados
        robux_raw = valores.get("robux_sale", ["true"])
        gamepass_raw = valores.get("gamepass_sale", ["true"])

        if isinstance(robux_raw, list):
            robux_raw = robux_raw[0] if robux_raw else "true"
        if isinstance(gamepass_raw, list):
            gamepass_raw = gamepass_raw[0] if gamepass_raw else "true"

        robux_enabled = str(robux_raw).lower() == "true"
        gamepass_enabled = str(gamepass_raw).lower() == "true"

        config = db.get_document("roblox_config") or {}
        config["robux_sale_enabled"] = robux_enabled
        config["gamepass_sale_enabled"] = gamepass_enabled
        db.save_document("roblox_config", config)

        components, flags = get_roblox_main_panel(config, mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)


def _build_canais_panel(mode: str):
    """
    Painel INLINE com ChannelSelects para configurar canais/categorias.
    Modais só aceitam TextInput (tipo 4) — ChannelSelect não funciona em modal.
    Cada select é salvo individualmente no on_dropdown conforme o usuário seleciona.
    """
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")
    config = db.get_document("roblox_config") or {}
    canais = config.get("canais", {})

    def _ch_mention(cid) -> str:
        if not cid:
            return "`Não configurado`"
        return f"<#{cid}>"

    cat_robux = canais.get("categoria_robux")
    cat_gamepass = canais.get("categoria_gamepass")
    log_vendas = canais.get("canal_vendas_log")
    canal_entregas = canais.get("canal_entregas")

    status_text = (
        f"**Categoria Robux:** {_ch_mention(cat_robux)}\n"
        f"**Categoria Gamepass:** {_ch_mention(cat_gamepass)}\n"
        f"**Log de Vendas:** {_ch_mention(log_vendas)}\n"
        f"**Canal de Entregas:** {_ch_mention(canal_entregas)}"
    )

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=(
                f"-# Painel > Roblox > **Configurar Canais**\n\n"
                f"Selecione abaixo cada canal ou categoria. "
                f"Cada seleção é salva automaticamente.\n\n"
                + status_text
            )
        )
        if embed_color:
            embed.color = embed_color

        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_CategoriaRobux",
                    placeholder="Categoria de tickets — Robux",
                    channel_types=[disnake.ChannelType.category],
                    min_values=1, max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_CategoriaGamepass",
                    placeholder="Categoria de tickets — Gamepass",
                    channel_types=[disnake.ChannelType.category],
                    min_values=1, max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_LogVendas",
                    placeholder="Canal de log de vendas aprovadas",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1, max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_Entregas",
                    placeholder="Canal de avisos de entrega (notificação ao comprador)",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1, max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Roblox_PainelPrincipal",
                )
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
                f"-# Painel > Roblox > **Configurar Canais**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"Selecione cada canal ou categoria abaixo. "
                f"Cada seleção é **salva automaticamente**.\n\n"
                + status_text
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_CategoriaRobux",
                    placeholder="Categoria de tickets — Robux",
                    channel_types=[disnake.ChannelType.category],
                    min_values=1, max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_CategoriaGamepass",
                    placeholder="Categoria de tickets — Gamepass",
                    channel_types=[disnake.ChannelType.category],
                    min_values=1, max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_LogVendas",
                    placeholder="Canal de log de vendas aprovadas",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1, max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_Entregas",
                    placeholder="Canal de avisos de entrega (notificação ao comprador)",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1, max_values=1,
                )
            ),
            **container_kwargs,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="Roblox_PainelPrincipal",
            )
        ),
    ]
    return components, disnake.MessageFlags(is_components_v2=True)


class EditarBotaoModal(disnake.ui.Modal):
    def __init__(self, botao_tipo: str):
        self.botao_tipo = botao_tipo
        config = db.get_document("roblox_config") or {}
        key_map = {
            "robux": "btn_robux",
            "gamepass": "btn_gamepass",
            "calcular": "btn_calcular",
        }
        defaults = {
            "robux": {"label": "Comprar Robux", "emoji": "💎", "style": "blurple"},
            "gamepass": {"label": "Comprar Gamepass", "emoji": "🎮", "style": "blurple"},
            "calcular": {"label": "Calcular Preço", "emoji": "🧮", "style": "grey"},
        }
        btn_data = config.get(key_map.get(botao_tipo, "btn_robux"), defaults.get(botao_tipo, {}))

        title_map = {
            "robux": "Editar Botão - Comprar Robux",
            "gamepass": "Editar Botão - Comprar Gamepass",
            "calcular": "Editar Botão - Calcular Preço",
        }
        super().__init__(
            title=title_map.get(botao_tipo, "Editar Botão"),
            custom_id=f"Roblox_EditarBotaoModal:{botao_tipo}",
            components=[
                disnake.ui.TextInput(
                    label="Label do botão",
                    custom_id="btn_label",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=40,
                    value=btn_data.get("label", defaults[botao_tipo]["label"]),
                ),
                disnake.ui.TextInput(
                    label="Emoji (Unicode ou ID customizado)",
                    custom_id="btn_emoji",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=100,
                    value=btn_data.get("emoji", defaults[botao_tipo]["emoji"]),
                    placeholder="Ex: 💎 ou <:nome:id>",
                ),
                disnake.ui.TextInput(
                    label="Estilo (blurple, green, red, grey)",
                    custom_id="btn_style",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=10,
                    value=btn_data.get("style", defaults[botao_tipo]["style"]),
                    placeholder="blurple, green, red, grey",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")

        valores = inter.resolved_values
        key_map = {
            "robux": "btn_robux",
            "gamepass": "btn_gamepass",
            "calcular": "btn_calcular",
        }
        config = db.get_document("roblox_config") or {}
        key = key_map.get(self.botao_tipo, "btn_robux")
        config.setdefault(key, {})
        config[key]["label"] = str(valores.get("btn_label", "")).strip() or config[key].get("label", "Botão")
        config[key]["emoji"] = str(valores.get("btn_emoji", "")).strip() or None
        config[key]["style"] = str(valores.get("btn_style", "blurple")).strip().lower()
        db.save_document("roblox_config", config)

        components, flags = get_botoes_panel(config, mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)




class ConfigurarGrupoModal(disnake.ui.Modal):
    """Modal para configurar o ID e link do grupo Roblox para entrega via Group Funds."""
    def __init__(self):
        config = db.get_document("roblox_config") or {}
        super().__init__(
            title="Configurar Grupo Roblox",
            custom_id="Roblox_ConfigurarGrupoModal",
            components=[
                disnake.ui.TextInput(
                    label="ID do Grupo Roblox",
                    custom_id="group_id",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=20,
                    value=str(config.get("group_id", "") or ""),
                    placeholder="Ex: 12345678",
                ),
                disnake.ui.TextInput(
                    label="Link do Grupo (enviado ao comprador)",
                    custom_id="group_link",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=200,
                    value=str(config.get("group_link", "") or ""),
                    placeholder="Ex: https://www.roblox.com/groups/12345678",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        valores = inter.resolved_values

        group_id_raw = str(valores.get("group_id", "")).strip()
        group_link = str(valores.get("group_link", "")).strip()

        try:
            group_id = int(group_id_raw) if group_id_raw else None
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} ID do grupo inválido. Use apenas números.", ephemeral=True
            )
            return

        config = db.get_document("roblox_config") or {}
        config["group_id"] = group_id
        config["group_link"] = group_link
        db.save_document("roblox_config", config)

        components, flags = _build_grupo_panel(config, mode)
        if mode == "embed":
            embed, comps = components
            await inter.response.edit_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.edit_message(components=components, flags=flags)


def _build_grupo_panel(config: dict, mode: str):
    """
    Painel de configuração do método de entrega e dados do grupo Roblox.
    Permite alternar entre entrega via Gamepass e entrega via Group Funds.
    """
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    delivery_method = config.get("delivery_method", "gamepass")
    group_id = config.get("group_id", None)
    group_link = config.get("group_link", "")

    method_label = "🎮 Gamepass" if delivery_method == "gamepass" else f"{emoji.group} Group Funds"
    toggle_label = "Mudar para Group Funds" if delivery_method == "gamepass" else "Mudar para Gamepass"
    toggle_style = disnake.ButtonStyle.blurple if delivery_method == "gamepass" else disnake.ButtonStyle.green

    group_id_txt = f"`{group_id}`" if group_id else "`Não configurado`"
    group_link_txt = group_link if group_link else "`Não configurado`"

    desc = (
        f"Configure o método de entrega dos Robux.\n\n"
        f"**Método atual:** {method_label}\n"
        f"**ID do Grupo:** {group_id_txt}\n"
        f"**Link do Grupo:** {group_link_txt}\n\n"
        f"-# **Gamepass:** o comprador cria uma gamepass com o valor bruto e a loja compra.\n"
        f"-# **Group Funds:** o comprador entra no grupo e recebe Robux via Group Funds.\n"
        f"-# No modo grupo, o ticket exibe o link do grupo e instrui o comprador a entrar."
    )

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=f"-# Painel > Roblox > **Configurar Grupo**\n\n" + desc
        )
        if embed_color:
            embed.color = embed_color

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=toggle_label,
                    style=toggle_style,
                    emoji=emoji.reload,
                    custom_id="Roblox_ToggleDeliveryMethod",
                ),
                disnake.ui.Button(
                    label="Editar ID / Link do Grupo",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="Roblox_EditarGrupoDados",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Roblox_PainelPrincipal",
                ),
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
                f"-# Painel > Roblox > **Configurar Grupo**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(desc),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=toggle_label,
                    style=toggle_style,
                    emoji=emoji.reload,
                    custom_id="Roblox_ToggleDeliveryMethod",
                ),
                disnake.ui.Button(
                    label="Editar ID / Link do Grupo",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="Roblox_EditarGrupoDados",
                ),
            ),
            **container_kwargs,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="Roblox_PainelPrincipal",
            ),
        ),
    ]
    return components, disnake.MessageFlags(is_components_v2=True)


class CogRoblox(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""

        if custom_id == "Roblox_ToggleSistema":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            config = db.get_document("roblox_config") or {}
            config["enabled"] = not bool(config.get("enabled", False))
            db.save_document("roblox_config", config)

            components, flags = get_roblox_main_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "Roblox_ConfigurarVendas":
            await inter.response.send_modal(VendasModal())

        elif custom_id == "Roblox_ConfigurarLimites":
            await inter.response.send_modal(LimitesModal())

        elif custom_id == "Roblox_ConfigurarCanais":
            mode = db.get_document("custom_mode").get("mode")
            components, flags = _build_canais_panel(mode)
            if mode == "embed":
                embed, comps = components
                await inter.response.edit_message(content=None, embed=embed, components=comps)
            else:
                await inter.response.edit_message(components=components, flags=flags)

        elif custom_id == "Roblox_ConfigurarMensagem":
            from .cogMensagemRoblox import RobloxMensagemEditor
            mode = db.get_document("custom_mode").get("mode")
            await RobloxMensagemEditor.open_editor(inter, mode)

        elif custom_id == "Roblox_ConfigurarBotoes":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            config = db.get_document("roblox_config") or {}
            components, flags = get_botoes_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "Roblox_EditarBotaoRobux":
            await inter.response.send_modal(EditarBotaoModal("robux"))

        elif custom_id == "Roblox_EditarBotaoGamepass":
            await inter.response.send_modal(EditarBotaoModal("gamepass"))

        elif custom_id == "Roblox_EditarBotaoCalcular":
            await inter.response.send_modal(EditarBotaoModal("calcular"))

        elif custom_id == "Roblox_PainelPrincipal":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            config = db.get_document("roblox_config") or {}
            components, flags = get_roblox_main_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "Roblox_ConfigurarCalculadora":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            config = db.get_document("roblox_config") or {}
            components, flags = get_calculadora_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "Roblox_ToggleCalculadora":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            config = db.get_document("roblox_config") or {}
            config["calculadora_enabled"] = not bool(config.get("calculadora_enabled", True))
            db.save_document("roblox_config", config)
            components, flags = get_calculadora_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "Roblox_ConfigurarGrupo":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            config = db.get_document("roblox_config") or {}
            components, flags = _build_grupo_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "Roblox_EditarGrupoDados":
            await inter.response.send_modal(ConfigurarGrupoModal())

        elif custom_id == "Roblox_ToggleDeliveryMethod":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            config = db.get_document("roblox_config") or {}
            current = config.get("delivery_method", "gamepass")
            config["delivery_method"] = "group" if current == "gamepass" else "gamepass"
            db.save_document("roblox_config", config)
            components, flags = _build_grupo_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "Roblox_Extensoes":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            components, flags = get_extensoes_panel(mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "Roblox_ConfigurarCookie":
            await inter.response.send_modal(CookieModal())

        elif custom_id == "Roblox_ToggleAutoEntrega":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            cfg = db.get_document("roblox_auto_config") or {}
            cfg["enabled"] = not bool(cfg.get("enabled", True))
            db.save_document("roblox_auto_config", cfg)
            config = db.get_document("roblox_config") or {}
            components, flags = get_auto_delivery_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif custom_id == "RobloxAuto_Comprar":
            from modules.settings.extensions.subscription_manager import create_payment, PURCHASABLE_EXTENSIONS
            await inter.response.defer(ephemeral=True)
            payer_name = inter.user.display_name or inter.user.name
            payer_doc_map = db.get_document("user_documents") or {}
            payer_document = payer_doc_map.get(str(inter.user.id), "00000000000")
            result = await create_payment("roblox_auto", str(inter.user.id), payer_name, payer_document)
            if result.get("success"):
                preco = PURCHASABLE_EXTENSIONS.get("roblox_auto", {}).get("price", 40.00)
                await inter.followup.send(
                    f"# ⚡ Pagamento gerado!\n\n"
                    f"- **Extensão:** Entrega Automática de Robux\n"
                    f"- **Valor:** `R$ {result['value']:.2f}`\n\n"
                    f"> Código PIX:\n```\n{result.get('copy_paste', 'N/A')}\n```\n"
                    f"-# ID do pagamento: `{result['payment_id']}`\n"
                    f"-# A extensão será ativada automaticamente após a confirmação do pagamento.",
                    ephemeral=True,
                )
            else:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao gerar pagamento: `{result.get('error', 'desconhecido')}`",
                    ephemeral=True,
                )

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        _CANAL_MAP = {
            "Roblox_Canal_CategoriaRobux": "categoria_robux",
            "Roblox_Canal_CategoriaGamepass": "categoria_gamepass",
            "Roblox_Canal_LogVendas": "canal_vendas_log",
            "Roblox_Canal_Calculadora": "canal_calculadora",
            "Roblox_Canal_Entregas": "canal_entregas",
        }

        if cid == "Roblox_ExtensaoSelecionada":
            extensao = inter.values[0] if inter.values else None
            if extensao == "roblox_auto":
                await inter.response.defer()
                mode = db.get_document("custom_mode").get("mode")
                config = db.get_document("roblox_config") or {}
                components, flags = get_auto_delivery_panel(config, mode)
                if mode == "embed":
                    embed, comps = components
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await inter.edit_original_message(components=components, flags=flags)
            return

        if cid not in _CANAL_MAP:
            return

        await inter.response.defer()

        def _extract_id(val) -> int | None:
            if not val:
                return None
            if isinstance(val, list):
                val = val[0] if val else None
            if isinstance(val, disnake.abc.GuildChannel):
                return val.id
            try:
                return int(val)
            except Exception:
                return None

        channel_id = _extract_id(inter.values[0] if inter.values else None)

        config = db.get_document("roblox_config") or {}
        config.setdefault("canais", {})
        config["canais"][_CANAL_MAP[cid]] = channel_id
        db.save_document("roblox_config", config)

        mode = db.get_document("custom_mode").get("mode")

        # Calculadora volta pro painel da calculadora; demais voltam pro de canais
        if cid == "Roblox_Canal_Calculadora":
            components, flags = get_calculadora_panel(config, mode)
        else:
            components, flags = _build_canais_panel(mode)

        if mode == "embed":
            embed, comps = components
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(components=components, flags=flags)


def setup(bot: commands.Bot):
    bot.add_cog(CogRoblox(bot))
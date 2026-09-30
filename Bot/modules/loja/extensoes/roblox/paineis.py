import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils


ROBUX_TAXA_ROBLOX = 0.30


def calcular_robux_bruto(robux_solicitados: int) -> int:
    return int(robux_solicitados / (1 - ROBUX_TAXA_ROBLOX))


def calcular_preco_robux(robux_amount: int, preco_por_mil: float) -> float:
    return round((robux_amount / 1000) * preco_por_mil, 2)


def get_roblox_main_panel(config: dict, mode: str):
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    system_enabled = config.get("enabled", False)
    robux_sale_enabled = config.get("robux_sale_enabled", True)
    gamepass_sale_enabled = config.get("gamepass_sale_enabled", True)
    preco_por_mil = config.get("preco_por_mil", 32.70)
    min_robux = config.get("min_robux", 100)
    max_robux = config.get("max_robux", 100000)
    delivery_method = config.get("delivery_method", "gamepass")
    group_id = config.get("group_id", None)

    delivery_status = "🎮 Gamepass" if delivery_method == "gamepass" else f"{emoji.group} Grupo ({group_id or 'não configurado'})"

    toggle_label = "Desativar Sistema" if system_enabled else "Ativar Sistema"
    toggle_emoji = emoji.on if system_enabled else emoji.off
    toggle_style = disnake.ButtonStyle.red if system_enabled else disnake.ButtonStyle.green
    status_text = f"{emoji.correct} Ativo" if system_enabled else f"{emoji.wrong} Inativo"
    robux_status = f"{emoji.correct} Ativo" if robux_sale_enabled else f"{emoji.wrong} Inativo"
    gamepass_status = f"{emoji.correct} Ativo" if gamepass_sale_enabled else f"{emoji.wrong} Inativo"

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=(
                f"-# Painel > Configurações > Extensões > **Roblox**\n\n"
                f"**Sistema de Venda de Robux**\n"
                f"-# Status geral: {status_text}\n"
                f"-# Venda de Robux: {robux_status}\n"
                f"-# Venda de Gamepass: {gamepass_status}\n"
                f"-# Preço por 1000 Robux: `R$ {preco_por_mil:.2f}`\n"
                f"-# Mínimo: `{min_robux} Robux` | Máximo: `{max_robux} Robux`\n"
                f"-# Método de entrega: `{delivery_status}`"
            )
        )
        if embed_color:
            embed.color = embed_color

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                   # label=toggle_label,
                    style=toggle_style,
                    emoji=emoji.power,
                    custom_id="Roblox_ToggleSistema",
                ),
                disnake.ui.Button(
                    label="Vendas Ativas",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.settings2,
                    custom_id="Roblox_ConfigurarVendas",
                ),
                disnake.ui.Button(
                    label="Configurar Limites",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="Roblox_ConfigurarLimites",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar Mensagem",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.commands,
                    custom_id="Roblox_ConfigurarMensagem",
                ),
                disnake.ui.Button(
                    label="Configurar Canais",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.settings2,
                    custom_id="Roblox_ConfigurarCanais",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Calculadora",
                    style=disnake.ButtonStyle.green,
                    emoji="🧮",
                    custom_id="Roblox_ConfigurarCalculadora",
                ),
                disnake.ui.Button(
                    label="Configurar Grupo",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.group,
                    custom_id="Roblox_ConfigurarGrupo",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="LojaExtensoes_Panel",
                ),
                disnake.ui.Button(
                    label="Extensões",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.commands,
                    custom_id="Roblox_Extensoes",
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
                f"-# Painel > Configurações > Extensões > **Roblox**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**Sistema de Venda de Robux**\n"
                f"-# Status geral: {status_text}\n"
                f"-# Venda de Robux: {robux_status}\n"
                f"-# Venda de Gamepass: {gamepass_status}\n"
                f"-# Preço por 1000 Robux: `R$ {preco_por_mil:.2f}`\n"
                f"-# Mínimo: `{min_robux} Robux` | Máximo: `{max_robux} Robux`\n"
                f"-# Método de entrega: `{delivery_status}`"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    #label=toggle_label,
                    style=toggle_style,
                    emoji=emoji.power,
                    custom_id="Roblox_ToggleSistema",
                ),
                disnake.ui.Button(
                    label="Vendas Ativas",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.settings2,
                    custom_id="Roblox_ConfigurarVendas",
                ),
                disnake.ui.Button(
                    label="Configurar Limites",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="Roblox_ConfigurarLimites",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar Mensagem",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.commands,
                    custom_id="Roblox_ConfigurarMensagem",
                ),
                disnake.ui.Button(
                    label="Configurar Canais",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.settings2,
                    custom_id="Roblox_ConfigurarCanais",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Calculadora",
                    style=disnake.ButtonStyle.green,
                    emoji="🧮",
                    custom_id="Roblox_ConfigurarCalculadora",
                ),
                disnake.ui.Button(
                    label="Configurar Grupo",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.group,
                    custom_id="Roblox_ConfigurarGrupo",
                ),
            ),
            **container_kwargs,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="LojaExtensoes_Panel",
            ),
            disnake.ui.Button(
                label="Extensões",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.commands,
                custom_id="Roblox_Extensoes",
            ),
        ),
    ]

    return components, disnake.MessageFlags(is_components_v2=True)


def get_extensoes_panel(mode: str):
    """
    Painel intermediário com select menu das extensões disponíveis para o módulo Roblox.
    """
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    desc = "Selecione uma extensão para configurar ou adquirir."

    select = disnake.ui.StringSelect(
        custom_id="Roblox_ExtensaoSelecionada",
        placeholder="Selecione uma extensão...",
        options=[
            disnake.SelectOption(
                label="⚡ Entrega Automática",
                value="roblox_auto",
                description="Configure ou adquira a entrega automática de Robux",
            ),
        ],
        min_values=1,
        max_values=1,
    )

    back_row = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id="Roblox_PainelPrincipal",
        )
    )

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=(
                f"-# Painel > Configurações > Extensões > **Roblox** > Extensões\n\n"
                + desc
            )
        )
        if embed_color:
            embed.color = embed_color

        components = [
            disnake.ui.ActionRow(select),
            back_row,
        ]
        return (embed, components), None

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    components = [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Configurações > Extensões > Roblox > **Extensões**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(desc),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(select),
            **container_kwargs,
        ),
        back_row,
    ]
    return components, disnake.MessageFlags(is_components_v2=True)


def get_botoes_panel(config: dict, mode: str):
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    btn_robux = config.get("btn_robux", {})
    btn_gamepass = config.get("btn_gamepass", {})
    btn_calcular = config.get("btn_calcular", {})

    robux_label = btn_robux.get("label", "Comprar Robux")
    robux_emoji_raw = btn_robux.get("emoji", "💎")
    robux_style_str = btn_robux.get("style", "blurple")

    gamepass_label = btn_gamepass.get("label", "Comprar Gamepass")
    gamepass_emoji_raw = btn_gamepass.get("emoji", "🎮")
    gamepass_style_str = btn_gamepass.get("style", "blurple")

    calcular_label = btn_calcular.get("label", "Calcular Preço")
    calcular_emoji_raw = btn_calcular.get("emoji", "🧮")
    calcular_style_str = btn_calcular.get("style", "grey")

    def style_from_str(s):
        return {
            "blurple": disnake.ButtonStyle.blurple,
            "green": disnake.ButtonStyle.green,
            "red": disnake.ButtonStyle.red,
            "grey": disnake.ButtonStyle.grey,
            "gray": disnake.ButtonStyle.grey,
        }.get(str(s).lower(), disnake.ButtonStyle.blurple)

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=(
                f"-# Painel > Roblox > **Configurar Botões**\n\n"
                f"Configure os botões que aparecerão na mensagem do painel Roblox.\n\n"
                f"**Botão de Comprar Robux**\n-# Label: `{robux_label}` | Emoji: `{robux_emoji_raw}` | Estilo: `{robux_style_str}`\n\n"
                f"**Botão de Comprar Gamepass**\n-# Label: `{gamepass_label}` | Emoji: `{gamepass_emoji_raw}` | Estilo: `{gamepass_style_str}`\n\n"
                f"**Botão de Calcular Preço**\n-# Label: `{calcular_label}` | Emoji: `{calcular_emoji_raw}` | Estilo: `{calcular_style_str}`"
            )
        )
        if embed_color:
            embed.color = embed_color

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Botão Robux", style=style_from_str(robux_style_str), emoji=robux_emoji_raw if len(str(robux_emoji_raw)) <= 2 else None, custom_id="Roblox_EditarBotaoRobux"),
                disnake.ui.Button(label="Editar Botão Gamepass", style=style_from_str(gamepass_style_str), emoji=gamepass_emoji_raw if len(str(gamepass_emoji_raw)) <= 2 else None, custom_id="Roblox_EditarBotaoGamepass"),
                disnake.ui.Button(label="Editar Botão Calcular", style=style_from_str(calcular_style_str), emoji=calcular_emoji_raw if len(str(calcular_emoji_raw)) <= 2 else None, custom_id="Roblox_EditarBotaoCalcular"),
            ),
            disnake.ui.ActionRow(
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
                f"-# Painel > Roblox > **Configurar Botões**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"Configure os botões que aparecerão na mensagem do painel Roblox.\n\n"
                f"**{emoji.commands} Botão de Comprar Robux**\n"
                f"-# Label: `{robux_label}` | Emoji: `{robux_emoji_raw}` | Estilo: `{robux_style_str}`\n\n"
                f"**{emoji.commands} Botão de Comprar Gamepass**\n"
                f"-# Label: `{gamepass_label}` | Emoji: `{gamepass_emoji_raw}` | Estilo: `{gamepass_style_str}`\n\n"
                f"**{emoji.commands} Botão de Calcular Preço**\n"
                f"-# Label: `{calcular_label}` | Emoji: `{calcular_emoji_raw}` | Estilo: `{calcular_style_str}`"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Botão Robux", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Roblox_EditarBotaoRobux"),
                disnake.ui.Button(label="Editar Botão Gamepass", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Roblox_EditarBotaoGamepass"),
                disnake.ui.Button(label="Editar Botão Calcular", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Roblox_EditarBotaoCalcular"),
            ),
            **container_kwargs,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Roblox_PainelPrincipal"),
        ),
    ]
    return components, disnake.MessageFlags(is_components_v2=True)

def get_calculadora_panel(config: dict, mode: str):
    """
    Painel de configuração da Calculadora de Robux.
    Permite selecionar o canal onde o bot responderá cálculos automáticos.
    """
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    canais = config.get("canais", {})
    canal_calc_id = canais.get("canal_calculadora")
    canal_calc_mention = f"<#{canal_calc_id}>" if canal_calc_id else "`Não configurado`"

    calc_enabled = config.get("calculadora_enabled", True)
    status_text = f"{emoji.correct} Ativo" if calc_enabled else f"{emoji.wrong} Inativo"
    toggle_label = f"Desativar Calculadora" if calc_enabled else f"{emoji.on} Ativar Calculadora"
    toggle_style = disnake.ButtonStyle.red if calc_enabled else disnake.ButtonStyle.green

    preco_por_mil = config.get("preco_por_mil", 32.70)

    desc = (
        f"Configure o canal onde o bot responderá automaticamente\n"
        f"quando alguém digitar algo como `500 robux` ou `50 reais`.\n\n"
        f"**Canal configurado:** {canal_calc_mention}\n"
        f"**Status:** `{status_text}`\n"
        f"**Preço por 1000 Robux:** `R$ {preco_por_mil:.2f}`\n\n"
        f"-# O bot responde com uma imagem estilo conquista do Minecraft\n"
        f"-# mostrando a conversão calculada."
    )

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=f"-# Painel > Roblox > **Calculadora**\n\n" + desc
        )
        if embed_color:
            embed.color = embed_color

        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_Calculadora",
                    placeholder="Selecione o canal da calculadora",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=toggle_label,
                    style=toggle_style,
                    emoji=emoji.power,
                    custom_id="Roblox_ToggleCalculadora",
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
                f"-# Painel > Roblox > **Calculadora**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(desc),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Roblox_Canal_Calculadora",
                    placeholder="Selecione o canal da calculadora",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=toggle_label,
                    style=toggle_style,
                    emoji=emoji.reload,
                    custom_id="Roblox_ToggleCalculadora",
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


def get_auto_delivery_panel(config: dict, mode: str):
    """
    Painel de configuração da Entrega Automática de Robux.
    Exibe status da extensão (ativa/inativa), cookie configurado e botões de ação.
    Se a extensão não estiver ativa, exibe painel de compra.
    """
    from modules.loja.extensoes.subscription_manager import is_extension_active, PURCHASABLE_EXTENSIONS
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    extensao_ativa = is_extension_active("roblox_auto")
    preco = PURCHASABLE_EXTENSIONS.get("roblox_auto", {}).get("price", 40.00)

    roblox_auto_cfg = db.get_document("roblox_auto_config") or {}
    cookie_salvo = roblox_auto_cfg.get("cookie", "")
    cookie_status = f"{emoji.correct} Configurado" if cookie_salvo else f"{emoji.wrong} Não configurado"
    cookie_preview = f"`...{cookie_salvo[-12:]}`" if cookie_salvo else "`—`"

    auto_enabled = roblox_auto_cfg.get("enabled", True)
    toggle_auto_label = f"{emoji.off} Desativar Auto" if auto_enabled else f"{emoji.on} Ativar Auto"
    toggle_auto_style = disnake.ButtonStyle.red if auto_enabled else disnake.ButtonStyle.green

    if extensao_ativa:
        desc = (
            f"## ⚡ Entrega Automática\n\n"
            f"A entrega automática está **{'ativa' if auto_enabled else 'desativada'}**.\n"
            f"Quando ativa, pedidos aprovados são entregues automaticamente via API do Roblox,\n"
            f"sem precisar de ação manual do admin.\n\n"
            f"**Cookie do Roblox:** {cookie_status}\n"
            f"**Prévia:** {cookie_preview}\n\n"
            f"-# Gamepass: a loja compra automaticamente a gamepass criada pelo comprador.\n"
            f"-# Group Funds: os Robux são distribuídos automaticamente via Group Funds."
        )
        rows_inside = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar Cookie",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="Roblox_ConfigurarCookie",
                ),
                disnake.ui.Button(
                    label=toggle_auto_label,
                    style=toggle_auto_style,
                    emoji=emoji.reload,
                    custom_id="Roblox_ToggleAutoEntrega",
                ),
            ),
        ]
    else:
        desc = (
            f"## ⚡ Entrega Automática\n\n"
            f"Esta extensão **não está ativa** no momento.\n\n"
            f"**O que ela faz:**\n"
            f"├ Entrega Robux automaticamente via Gamepass após pagamento aprovado\n"
            f"├ Distribui via Group Funds sem ação manual do admin\n"
            f"└ Painel completo de configuração de cookie e toggle on/off\n\n"
            f"**Valor:** R$ {preco:.2f} — Permanente"
        )
        rows_inside = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=f"Assinar por R$ {preco:.2f}",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.cart,
                    custom_id="RobloxAuto_Comprar",
                ),
            ),
        ]

    back_row = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id="Roblox_PainelPrincipal",
        ),
    )

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(
            description=f"-# Painel > Roblox > **Entrega Automática**\n\n" + desc
        )
        if embed_color:
            embed.color = embed_color
        return (embed, rows_inside + [back_row]), None

    container_kw = {}
    if primary_color_hex:
        container_kw["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    components = [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Roblox > **Entrega Automática**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(desc),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            *rows_inside,
            **container_kw,
        ),
        back_row,
    ]
    return components, disnake.MessageFlags(is_components_v2=True)
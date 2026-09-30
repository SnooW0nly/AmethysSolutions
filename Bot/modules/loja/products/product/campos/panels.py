import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from functions.text_utils import safe_textdisplay, safe_select_option_label, safe_select_option_description
from functions.loja_products import container_kwargs_for_product, embed_kwargs_for_product, get_stock_quantity
from modules.loja.cart.stock_manager import StockManager


# ── Helpers para produto de membros ──────────────────────────────────────────

def _is_members_product(product: dict) -> bool:
    """Retorna True se o produto é do tipo 'Venda de Membros' (AmyCloud)."""
    return bool(product.get("is_members_product"))


def _build_members_product_rows(product: dict, product_id: str) -> list:
    """
    Painel de campos para produto de membros:
    sem dropdown de campos, apenas botão 'Comprar Membros'.
    Verifica se cloud está configurado e se há membros disponíveis.
    """
    cloud_config = db.get_document("cloud_data") or {}
    cloud_active = bool(cloud_config.get("client_id"))
    available = int(cloud_config.get("cached_auth_count", 0))

    status_text = (
        f"{emoji.on if cloud_active else emoji.off} AmyCloud: "
        f"{'Ativo' if cloud_active else 'Não configurado'}"
    )
    if cloud_active:
        status_text += f"\n🧑‍🤝‍🧑 Membros disponíveis: `{available}`"

    btn_disabled = not cloud_active or available < 1
    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Comprar Membros",
                style=disnake.ButtonStyle.green,
                emoji=emoji.members if hasattr(emoji, "members") else None,
                custom_id=f"buy_members_product:{product_id}",
                disabled=btn_disabled,
            )
        )
    ]
    return rows, status_text

def _get_boost_real_stock(campo: dict) -> int:
    """
    Calcula estoque real de um campo boost baseado nos tokens de conta do Joiner.
    Conta keys ativas com usos restantes, filtradas por boost_period do campo.
    Cada token de conta vinculado representa 2 boosts (1 slot mensal ou 1 trimestral).
    """
    try:
        from modules.joiner.helpers import _load_account_tokens
        period = campo.get("boost_period")  # "mensal" ou "trimestral"
        boost_qty = int(campo.get("boost_qty") or campo.get("boost_count") or 2)

        data = _load_account_tokens()
        tokens = data.get("tokens", {})

        # Contar tokens vinculados (com OAuth) — prontos para boost
        linked_count = sum(
            1 for t in tokens.values()
            if t.get("status") == "linked" and t.get("linked_oauth_user_id")
        )

        # Cada conta fornece 2 boosts. Estoque = quantas vezes podemos entregar boost_qty boosts.
        boosts_available = linked_count * 2
        accounts_needed = max(1, boost_qty // 2)
        return max(0, boosts_available // accounts_needed)
    except Exception:
        return 0


def _get_stock_display(product_id: str, field_id: str) -> str:
    """Retorna a quantidade de estoque formatada (Infinito ou número).
    Para campos boost vinculados, usa estoque real calculado via tokens do Joiner."""
    products = db.get_document("loja_products") or {}
    product = products.get(product_id, {})
    campo = product.get("campos", {}).get(field_id, {})

    # Verificar se é estoque infinito
    if campo.get("infinite_stock", {}).get("enabled"):
        return "Infinito"

    # Campo boost vinculado → estoque calculado automaticamente via Joiner
    if campo.get("boost_field"):
        return str(_get_boost_real_stock(campo))

    # Produto normal → sistema centralizado de estoque
    stock_qtd = StockManager.get_available_stock(product_id, field_id)
    return str(stock_qtd)


def _dropdown_categorias(product: dict, product_id: str) -> disnake.ui.Select:
    categorias = product.get("categorias", {}) or {}
    options = []
    disabled = False
    for categoria in categorias.values():
        name = categoria.get("name") or categoria.get("id")
        label = safe_select_option_label(name)
        description = safe_select_option_description(f"Campos: {len(categoria.get('campos', {}))}")
        options.append(disnake.SelectOption(label=label, value=categoria.get("id"), description=description))
    if not options:
        disabled = True
        options.append(disnake.SelectOption(label="Nenhuma categoria encontrada", value="disabled"))
    return disnake.ui.StringSelect(
        placeholder=f"[{len(categorias)}] Selecione uma categoria",
        options=options,
        custom_id=f"Loja_Categorias_Select:{product_id}",
        disabled=disabled,
    )


def _dropdown_campos(product: dict, product_id: str) -> disnake.ui.Select:
    campos = product.get("campos", {}) or {}
    options = []
    disabled = False
    for campo in campos.values():
        # Campos boost desativados são removidos do dropdown (não existem para o comprador)
        if campo.get("boost_disabled"):
            continue
        name = campo.get("name") or campo.get("id")
        label = safe_select_option_label(name)
        price = utils.format_price_brl(campo.get('price'))
        stock_qtd = _get_stock_display(product_id=product_id, field_id=campo.get("id"))
        description = safe_select_option_description(f"Preço: {price} | Estoque: {stock_qtd}")
        options.append(disnake.SelectOption(label=label, value=campo.get("id"), description=description))
    if not options:
        disabled = True
        options.append(disnake.SelectOption(label="Nenhum campo encontrado", value="disabled"))
    return disnake.ui.StringSelect(
        placeholder=f"[{len(options) if not disabled else 0}] Selecione um campo",
        options=options,
        custom_id=f"Loja_Campos_Select:{product_id}",
        disabled=disabled,
    )


def _is_boost_product(product: dict) -> bool:
    """Retorna True se o nome do produto indicar que é um produto de Boost/Impulso."""
    name = (product.get("name") or "").lower()
    boost_keywords = ["boost", "impulso", "impulsionar", "nitro", "server boost"]
    return any(kw in name for kw in boost_keywords)


def _boost_linked_fields(product: dict) -> list:
    """Retorna lista de campos boost vinculados no produto."""
    return [c for c in (product.get("campos") or {}).values() if c.get("boost_field")]


def _boost_period_status(product: dict) -> tuple[bool, bool]:
    """Retorna (mensal_ativo, trimestral_ativo) — True = pelo menos 1 campo do período ativo."""
    campos = (product.get("campos") or {}).values()
    boost = [c for c in campos if c.get("boost_field")]
    mensal_ativo = any(c.get("boost_period") == "mensal" and not c.get("boost_disabled") for c in boost)
    trimestral_ativo = any(c.get("boost_period") == "trimestral" and not c.get("boost_disabled") for c in boost)
    return mensal_ativo, trimestral_ativo


def _build_boost_action_rows(product: dict, product_id: str) -> list:
    """
    Constrói as ActionRows de boost para o painel de campos.
    — Sempre: botão Criar Campo
    — Se produto boost + NÃO vinculado: botão Vincular Boost
    — Se produto boost + JÁ vinculado: botão Desvincular + toggles Mensal/Trimestral
    """
    is_boost = _is_boost_product(product)
    linked = _boost_linked_fields(product) if is_boost else []
    rows = []

    if not is_boost:
        # Produto normal — só botão Criar Campo
        rows.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Campo", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_CriarCampo:{product_id}"),
        ))
        return rows

    if not linked:
        # Boost mas ainda não vinculado
        rows.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Campo", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_CriarCampo:{product_id}"),
            disnake.ui.Button(label="Vincular Boost", style=disnake.ButtonStyle.blurple, emoji=emoji.boost, custom_id=f"Loja_VincularBoost:{product_id}"),
        ))
        return rows

    # Já vinculado — mostrar Desvincular + toggles de período
    mensal_ativo, trimestral_ativo = _boost_period_status(product)
    rows.append(disnake.ui.ActionRow(
        disnake.ui.Button(label="Criar Campo", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_CriarCampo:{product_id}"),
        disnake.ui.Button(label="Desvincular Boost", style=disnake.ButtonStyle.red, emoji=emoji.boost, custom_id=f"Loja_DesvincularBoost:{product_id}"),
    ))
    rows.append(disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Mensal" if mensal_ativo else "Mensal",
            style=disnake.ButtonStyle.green if mensal_ativo else disnake.ButtonStyle.grey,
            emoji=emoji.power,
            custom_id=f"Loja_ToggleBoostPeriodo:{product_id}:mensal",
        ),
        disnake.ui.Button(
            label="Trimestral" if trimestral_ativo else "Trimestral",
            style=disnake.ButtonStyle.green if trimestral_ativo else disnake.ButtonStyle.grey,
            emoji=emoji.power,
            custom_id=f"Loja_ToggleBoostPeriodo:{product_id}:trimestral",
        ),
    ))
    return rows


def build_components(product: dict, product_id: str) -> dict:
    container_kwargs = container_kwargs_for_product(product)
    product_name = safe_textdisplay(product.get('name', product_id), 50)
    header_text = safe_textdisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > {product_name} > **Campos**")

    # ── Produto de membros: painel simplificado ───────────────────────────────
    if _is_members_product(product):
        members_rows, status_text = _build_members_product_rows(product, product_id)
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(header_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"Este produto vende membros verificados via AmyCloud.\n"
                    f"Não possui campos configuráveis.\n\n{status_text}"
                ),
                disnake.ui.Separator(),
                *members_rows,
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarProduto:{product_id}")),
        ]}

    dropdown_campos = _dropdown_campos(product, product_id)
    boost_rows = _build_boost_action_rows(product, product_id)

    return {"components": [
        disnake.ui.Container(
            disnake.ui.TextDisplay(header_text),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Selecione um campo para gerenciar.\nPara criar, use o botão abaixo."),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(dropdown_campos),
            *boost_rows,
            **container_kwargs
        ),
        disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarProduto:{product_id}")),
    ]}


def build_embed(product: dict, product_id: str) -> dict:
    embed_kwargs = embed_kwargs_for_product(product)

    # ── Produto de membros: embed simplificado ────────────────────────────────
    if _is_members_product(product):
        members_rows, status_text = _build_members_product_rows(product, product_id)
        embed = disnake.Embed(
            description=(
                f"-# Painel > Loja > {product.get('name', product_id)} > **Campos**\n\n"
                f"Este produto vende membros verificados via AmyCloud.\n"
                f"Não possui campos configuráveis.\n\n{status_text}"
            ),
            **embed_kwargs
        )
        components = [
            *[disnake.ui.ActionRow(r) if not isinstance(r, disnake.ui.ActionRow) else r for r in members_rows],
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarProduto:{product_id}")),
        ]
        return {"embed": embed, "components": components}

    dropdown_campos = _dropdown_campos(product, product_id)
    boost_rows = _build_boost_action_rows(product, product_id)

    embed = disnake.Embed(
        description=f"-# Painel > Loja > {product.get('name', product_id)} > **Campos**\n\nSelecione um campo para gerenciar.",
        **embed_kwargs
    )

    components = [
        disnake.ui.ActionRow(dropdown_campos),
        *boost_rows,
        disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarProduto:{product_id}")),
    ]
    return {"embed": embed, "components": components}


def build_category_fields_components(product: dict, product_id: str, category_id: str) -> dict:
    campos = product.get("campos", {}) or {}
    options = []
    disabled = False
    for campo in campos.values():
        if campo.get("category_id") != category_id:
            continue
        name = campo.get("name") or campo.get("id")
        label = safe_select_option_label(name)
        price = utils.format_price_brl(campo.get('price'))
        stock_qtd = _get_stock_display(product_id=product_id, field_id=campo.get("id"))
        description = safe_select_option_description(f"Preço: {price} | Estoque: {stock_qtd}")
        options.append(disnake.SelectOption(label=label, value=campo.get("id"), description=description))
    if not options:
        disabled = True
        options.append(disnake.SelectOption(label="Nenhum campo nesta categoria", value="disabled"))

    dropdown_campos_categoria = disnake.ui.StringSelect(
        placeholder=f"Selecione um campo desta categoria",
        options=options,
        custom_id=f"Loja_CamposCategoria_Select:{product_id}:{category_id}",
        disabled=disabled,
    )

    container_kwargs = container_kwargs_for_product(product)
    product_name = safe_textdisplay(product.get('name', product_id), 50)
    header_text = safe_textdisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > {product_name} > **Campos da Categoria**")
    
    return {"components": [
        disnake.ui.Container(
            disnake.ui.TextDisplay(header_text),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Selecione um campo para gerenciar ou crie um novo."),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(dropdown_campos_categoria),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Campo", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_CriarCampoCategoria:{product_id}:{category_id}"),
            ),
            **container_kwargs
        ),
        disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarCategoria:{product_id}:{category_id}")),
    ]}


def build_category_fields_embed(product: dict, product_id: str, category_id: str) -> dict:
    embed_kwargs = embed_kwargs_for_product(product)
    embed = disnake.Embed(
        description=f"-# Painel > Loja > {product.get('name', product_id)} > **Campos da Categoria**",
        **embed_kwargs
    )
    # Dropdown built in components to avoid duplication here
    components = build_category_fields_components(product, product_id, category_id)["components"]
    return {"embed": embed, "components": components}
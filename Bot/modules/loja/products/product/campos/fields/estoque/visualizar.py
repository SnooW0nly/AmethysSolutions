import disnake

from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from functions.text_utils import safe_textdisplay
from functions.loja_products import container_kwargs_for_product, embed_kwargs_for_product, get_stock_quantity, get_product, get_products
from modules.loja.cart.stock_manager import StockManager


KEY_PRODUCTS = "loja_products"


def _ensure_stock_list(field: dict) -> list[str]:
    stock = field.get("stock")
    if isinstance(stock, list):
        return stock
    # Convert dict or None to list
    if isinstance(stock, dict):
        try:
            # If dict of {code: count}
            expanded: list[str] = []
            for key, val in stock.items():
                try:
                    count = int(val)
                except Exception:
                    count = 1
                expanded.extend([str(key)] * max(count, 1))
            return expanded
        except Exception:
            return list(stock.keys())
    return []


def panel_components(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
    product = get_product(product_id)
    field = (product.get("campos") or {}).get(field_id) or {}
    
    # Verificar se é estoque infinito
    is_infinite = field.get("infinite_stock", {}).get("enabled", False)
    
    if is_infinite:
        stock_qtd = "Infinito"
        stock_info_text = f"-# Estoque: **Infinito**\n-# Última atualização: {utils.format_timestamp((field.get('stock_info') or {}).get('last'))}"
    else:
        # Obter estoque do database centralizado
        stock_qtd = StockManager.get_available_stock(product_id, field_id)
        stock_info_text = f"-# Itens em estoque: `{stock_qtd}`\n-# Última atualização: {utils.format_timestamp((field.get('stock_info') or {}).get('last'))}"
    
    product_name = safe_textdisplay(product.get("name") or product_id, 50)
    
    header_text = safe_textdisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > {product_name} > Campo > **Estoque**")

    components = [
        disnake.ui.Container(
            disnake.ui.TextDisplay(header_text),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Gerencie os itens de estoque entregues após a compra deste campo."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(stock_info_text),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_Estoque_Add:{product_id}:{field_id}"),
                disnake.ui.Button(label="Infinito", style=disnake.ButtonStyle.blurple, emoji=emoji.infinity, custom_id=f"Loja_Estoque_AddInfinite:{product_id}:{field_id}"),
                disnake.ui.Button(label="Upload .txt", style=disnake.ButtonStyle.blurple, emoji=emoji.folder, custom_id=f"Loja_Estoque_Upload:{product_id}:{field_id}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Ver estoque", emoji=emoji.search, custom_id=f"Loja_Estoque_View:{product_id}:{field_id}"),
                disnake.ui.Button(label="Pegar item", emoji=emoji.arrow, custom_id=f"Loja_Estoque_Pegar:{product_id}:{field_id}"),
                disnake.ui.Button(label="Gerenciar", style=disnake.ButtonStyle.blurple,emoji=emoji.settings2, custom_id=f"Loja_Estoque_Gerenciar:{product_id}:{field_id}"),
                disnake.ui.Button(label="Limpar", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"Loja_Estoque_Clear:{product_id}:{field_id}"),
            ),
            **container_kwargs_for_product(product)
        ),
        disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_EstoqueCampo_Voltar:{product_id}:{field_id}")),
    ]
    return {"components": components}


def panel_embed(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
    product = get_product(product_id)
    field = (product.get("campos") or {}).get(field_id) or {}
    product_name = safe_textdisplay(product.get("name") or product_id, 50)
    
    # Verificar se é estoque infinito
    is_infinite = field.get("infinite_stock", {}).get("enabled", False)
    
    if is_infinite:
        stock_qtd = "Infinito"
        description_text = safe_textdisplay(
            f"-# Painel > Loja > {product_name} > **Campo > Estoque**\n\n"
            f"-# Estoque: **Infinito**\n-# Última atualização: {utils.format_timestamp((field.get('stock_info') or {}).get('last'))}\n"
        )
    else:
        # Obter estoque do database centralizado
        stock_qtd = StockManager.get_available_stock(product_id, field_id)
        last_ts = (field.get("stock_info") or {}).get("last")
        
        description_text = safe_textdisplay(
            f"-# Painel > Loja > {product_name} > **Campo > Estoque**\n\n"
            f"-# Itens em estoque: `{stock_qtd}`\n-# Última atualização: {utils.format_timestamp(last_ts)}\n"
        )

    embed = disnake.Embed(
        description=description_text,
        **embed_kwargs_for_product(product)
    )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_Estoque_Add:{product_id}:{field_id}"),
            disnake.ui.Button(label="Infinito", style=disnake.ButtonStyle.blurple, emoji=emoji.infinity, custom_id=f"Loja_Estoque_AddInfinite:{product_id}:{field_id}"),
            disnake.ui.Button(label="Upload .txt", style=disnake.ButtonStyle.blurple, emoji=emoji.folder, custom_id=f"Loja_Estoque_Upload:{product_id}:{field_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Ver estoque", emoji=emoji.search, custom_id=f"Loja_Estoque_View:{product_id}:{field_id}"),
            disnake.ui.Button(label="Pegar item", emoji=emoji.arrow, custom_id=f"Loja_Estoque_Pegar:{product_id}:{field_id}"),
            disnake.ui.Button(label="Gerenciar", style=disnake.ButtonStyle.blurple,emoji=emoji.settings2, custom_id=f"Loja_Estoque_Gerenciar:{product_id}:{field_id}"),
            disnake.ui.Button(label="Limpar", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"Loja_Estoque_Clear:{product_id}:{field_id}"),
        ),
        disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_EstoqueCampo_Voltar:{product_id}:{field_id}")),
    ]
    return {"embed": embed, "components": components}


def panel(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
    mode = db.get_document("custom_mode").get("mode")
    if mode == "embed":
        return panel_embed(inter, product_id, field_id)
    return panel_components(inter, product_id, field_id)


def export_stock_file(product_id: str, field_id: str) -> str | None:
    """Exporta o estoque para um arquivo temporário .txt e retorna o caminho."""
    # Obter estoque do database centralizado
    stock_data = StockManager._load_stock()
    stock = stock_data.get(product_id, {}).get(field_id, [])
    
    if not stock or not isinstance(stock, list):
        return None

    # Obter informações do produto e campo
    products = get_products() or {}
    product = products.get(product_id) or {}
    product_name = product.get("name", product_id)
    campo = (product.get("campos") or {}).get(field_id) or {}
    campo_name = campo.get("name", field_id)
    
    # Criar conteúdo do arquivo
    from datetime import datetime
    content = "=" * 50 + "\n"
    content += "ESTOQUE DO CAMPO\n"
    content += "=" * 50 + "\n\n"
    content += f"Produto: {product_name}\n"
    content += f"Campo: {campo_name}\n"
    content += f"Quantidade: {len(stock)} itens\n"
    content += f"Exportado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    content += "=" * 50 + "\n"
    content += "ITENS\n"
    content += "=" * 50 + "\n\n"
    
    for i, item in enumerate(stock, 1):
        content += f"{i}. {item}\n"
    
    content += "\n" + "=" * 50 + "\n"
    content += f"TOTAL: {len(stock)} item(s)\n"
    content += "=" * 50 + "\n"

    import os
    os.makedirs("database/loja/temp", exist_ok=True)
    filename = f"Estoque_{product_name}_{campo_name}.txt"
    # Remover caracteres inválidos do nome do arquivo
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '_', '-', '.')).strip()
    fullpath = os.path.join("database/loja/temp", filename)
    with open(fullpath, "w", encoding="utf-8") as fp:
        fp.write(content)
    return fullpath

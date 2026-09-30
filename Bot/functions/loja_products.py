import disnake

from functions.database import database as db
from functions.utils import utils


# Storage helpers


def get_products() -> dict:
    return db.get_document("loja_products")


def save_products(products: dict) -> None:
    db.save_document("loja_products", products)


def get_product(product_id: str) -> dict:
    products = get_products()
    return (products or {}).get(product_id) or {}


def upsert_product(product_id: str, product: dict) -> None:
    products = get_products()
    products[product_id] = product
    save_products(products)


# UI helpers (colors, embeds, containers)
def container_kwargs_for_product(product: dict) -> dict:
    color_data = db.get_document("custom_colors")
    primary_color_hex = color_data.get("primary")
    kwargs = {}
    info = product.get("info", {}) if isinstance(product, dict) else {}
    hex_color = info.get("hex_color")
    if hex_color:
        kwargs["accent_colour"] = disnake.Colour(int(hex_color.replace("#", ""), 16))
    elif primary_color_hex:
        kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
    return kwargs


def embed_kwargs_for_product(product: dict) -> dict:
    color_data = db.get_document("custom_colors")
    primary_color_hex = color_data.get("primary")
    kwargs = {}
    info = product.get("info", {}) if isinstance(product, dict) else {}
    hex_color = info.get("hex_color")
    if hex_color:
        kwargs["color"] = int(hex_color.replace("#", ""), 16)
    elif primary_color_hex:
        kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
    return kwargs


# Parsing/formatting helpers
def parse_price_brl_to_float(value: str) -> float:
    try:
        if value is None:
            return 0.0
        s = str(value).replace("R$", "").replace(" ", "").replace(",", ".")
        return round(float(s), 2)
    except Exception:
        return 0.0


def format_price_brl(price: float) -> str:
    return utils.format_price_brl(float(price or 0.0))


# IDs / time helpers
def generate_id(length: int = 10) -> str:
    return utils.gerar_id(length)


def now_ts() -> int:
    return int(disnake.utils.utcnow().timestamp())


# Stock helpers
def get_stock_quantity(field: dict = None, product_id: str = None, field_id: str = None) -> int:
    """
    Obtém a quantidade de estoque.
    Pode receber field (antigo) ou product_id + field_id (novo com estoque centralizado)
    """
    # Se receber product_id e field_id, usar estoque centralizado
    if product_id and field_id:
        from modules.loja.cart.stock_manager import StockManager
        return StockManager.get_available_stock(product_id, field_id)
    
    # Fallback para compatibilidade com código antigo
    if field:
        stock = field.get("stock") if isinstance(field, dict) else None
        if stock is None:
            return 0
        # Support list or dict-based storage
        if isinstance(stock, list):
            return len(stock)
        if isinstance(stock, dict):
            try:
                # If values are counts
                return int(sum(int(v) for v in stock.values()))
            except Exception:
                return len(stock.keys())
    return 0


# Emoji validation
def validate_emoji_string(bot, emoji_str: str | None) -> str | None:
    """
    Valida emoji para uso em componentes do Discord.
    Usa a função validate_emoji_for_components do utils.
    """
    if not emoji_str:
        return None
    
    validation = utils.validate_emoji_for_components(emoji_str)
    if not validation["valid"]:
        return None
    
    # Converter para string apropriada
    emoji_result = validation["emoji"]
    if isinstance(emoji_result, disnake.PartialEmoji):
        # Para emojis customizados, verificar se o bot tem acesso
        if emoji_result.id:
            for e in getattr(bot, "emojis", []):
                if getattr(e, "id", None) == emoji_result.id:
                    return str(emoji_result)
            return None
        return str(emoji_result)
    else:
        # Emoji unicode
        return emoji_result


# Roles helpers
async def apply_field_roles_after_purchase(guild: disnake.Guild, member: disnake.Member, field: dict) -> None:
    if not guild or not member or not isinstance(field, dict):
        return
    cargos = (field or {}).get("cargos") or {}
    to_add_ids = [int(x) for x in (cargos.get("adicionar") or []) if str(x).isdigit()]
    to_rem_ids = [int(x) for x in (cargos.get("remover") or []) if str(x).isdigit()]

    # Resolve Role objects and filter manageable roles
    me: disnake.Member = guild.me  # type: ignore
    add_roles: list[disnake.Role] = []
    rem_roles: list[disnake.Role] = []
    for rid in to_add_ids:
        role = guild.get_role(rid)
        if role and me and me.guild_permissions.manage_roles and role < me.top_role:
            add_roles.append(role)
    for rid in to_rem_ids:
        role = guild.get_role(rid)
        if role and me and me.guild_permissions.manage_roles and role < me.top_role:
            rem_roles.append(role)

    try:
        if add_roles:
            await member.add_roles(*add_roles, reason="Compra na loja - adicionar cargos do campo")
    except Exception:
        pass
    try:
        if rem_roles:
            await member.remove_roles(*rem_roles, reason="Compra na loja - remover cargos do campo")
    except Exception:
        pass



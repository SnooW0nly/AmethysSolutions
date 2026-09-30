import re
import asyncio
import disnake

from functions.database import database as db
from functions.emoji import emoji
from functions.text_utils import safe_textdisplay
from functions.loja_products import get_product, container_kwargs_for_product, embed_kwargs_for_product
from functions.message import message, embed_message
from modules.loja.cart.stock_manager import StockManager

KEY_PRODUCTS = "loja_products"
ITEMS_PER_PAGE = 20
STATE_KEY = "loja_estoque_gerenciar_state"


# ── Estado do usuário (busca persistente por sessão) ─────────────────────────

def _state_get(user_id: int, product_id: str, field_id: str) -> dict:
    state = db.get_document(STATE_KEY) or {}
    return (state.get(str(user_id)) or {}).get(f"{product_id}:{field_id}") or {}


def _state_set(user_id: int, product_id: str, field_id: str, data: dict):
    state = db.get_document(STATE_KEY) or {}
    uid = str(user_id)
    key = f"{product_id}:{field_id}"
    if uid not in state:
        state[uid] = {}
    state[uid][key] = data
    db.save_document(STATE_KEY, state)


def _state_clear(user_id: int, product_id: str, field_id: str):
    _state_set(user_id, product_id, field_id, {})


# ── Helpers de estoque ───────────────────────────────────────────────────────

def _load(product_id: str, field_id: str) -> list[str]:
    return StockManager._load_stock().get(product_id, {}).get(field_id, [])


def _save(product_id: str, field_id: str, items: list[str]):
    stock = StockManager._load_stock()
    if product_id not in stock:
        stock[product_id] = {}
    stock[product_id][field_id] = items
    StockManager._save_stock(stock)


def _update_timestamps(product_id: str, field_id: str):
    products = db.get_document(KEY_PRODUCTS) or {}
    product = products.get(product_id) or {}
    campos = product.get("campos") or {}
    field = campos.get(field_id) or {}
    now = int(disnake.utils.utcnow().timestamp())
    stock_info = field.get("stock_info") or {}
    stock_info["last"] = now
    field["stock_info"] = stock_info
    field["updated_at"] = now
    campos[field_id] = field
    product["campos"] = campos
    info = product.get("info") or {}
    info["updated_at"] = now
    product["info"] = info
    products[product_id] = product
    db.save_document(KEY_PRODUCTS, products)


# ── Parser de posições ───────────────────────────────────────────────────────

def _parse_positions(text: str, total: int) -> list[int] | None:
    """
    Interpreta a entrada como posições (1-based) e retorna índices 0-based.
    Aceita:  "5"  |  "1,3,7"  |  "1-10"  |  "1-5,10,15-20"
    Retorna None se o texto não for uma expressão de posições válida.
    """
    text = text.strip()
    if not re.fullmatch(r"[\d,\-\s]+", text):
        return None

    indices: set[int] = set()
    for part in re.split(r"\s*,\s*", text):
        part = part.strip()
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > b:
                a, b = b, a
            for i in range(a, b + 1):
                if 1 <= i <= total:
                    indices.add(i - 1)
        elif re.fullmatch(r"\d+", part):
            i = int(part)
            if 1 <= i <= total:
                indices.add(i - 1)
        else:
            return None  # Texto não reconhecido como posições

    return sorted(indices) if indices else None


# ── Paginação ────────────────────────────────────────────────────────────────

def _paginate(all_items: list[str], page: int, search: str = ""):
    """Retorna (itens_da_página_com_índice_global, total_pages, total_filtrado, página_corrigida)."""
    if search:
        filtered = [(i, item) for i, item in enumerate(all_items) if search.lower() in item.lower()]
    else:
        filtered = list(enumerate(all_items))

    total = len(filtered)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * ITEMS_PER_PAGE
    return filtered[start:start + ITEMS_PER_PAGE], total_pages, total, page


# ── Construção da lista de itens (texto) ─────────────────────────────────────

def _items_text(page_items: list, search: str) -> str:
    if not page_items:
        if search:
            return f"{emoji.wrong} Nenhum resultado para **\"{safe_textdisplay(search, 40)}\"**."
        return f"{emoji.wrong} Nenhum item no estoque."
    lines = []
    for orig_idx, item in page_items:
        truncated = item[:78] + ("…" if len(item) > 78 else "")
        lines.append(f"`#{orig_idx + 1}` {truncated}")
    return "\n".join(lines)


# ── Construção dos ActionRows compartilhados ─────────────────────────────────

def _action_rows(
    product_id: str, field_id: str,
    page: int, total_pages: int,
    search: str, no_items: bool,
) -> list[disnake.ui.ActionRow]:
    prev_off = page == 0
    next_off = page >= total_pages - 1

    row_page = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="◀ Anterior", style=disnake.ButtonStyle.grey,
            custom_id=f"Loja_Estoque_Gerenciar_Page:{product_id}:{field_id}:{page - 1}",
            disabled=prev_off,
        ),
        disnake.ui.Button(
            label=f"Pág {page + 1}/{total_pages}", style=disnake.ButtonStyle.grey,
            custom_id=f"Loja_Estoque_Gerenciar_PageInfo:{product_id}:{field_id}",
            disabled=True,
        ),
        disnake.ui.Button(
            label="Próxima ▶", style=disnake.ButtonStyle.grey,
            custom_id=f"Loja_Estoque_Gerenciar_Page:{product_id}:{field_id}:{page + 1}",
            disabled=next_off,
        ),
    )

    row_actions = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Remover item(s)", style=disnake.ButtonStyle.red, emoji=emoji.delete,
            custom_id=f"Loja_Estoque_Gerenciar_Remove:{product_id}:{field_id}:{page}",
            disabled=no_items,
        ),
        disnake.ui.Button(
            label="Remover duplicatas", style=disnake.ButtonStyle.blurple,
            custom_id=f"Loja_Estoque_Gerenciar_Dedup:{product_id}:{field_id}",
            emoji=emoji.delete,
            disabled=no_items,
        ),
    )

    if search:
        row_search = disnake.ui.ActionRow(
            disnake.ui.Button(
                label=f'"{safe_textdisplay(search, 22)}"',
                style=disnake.ButtonStyle.grey,
                emoji=emoji.search,
                custom_id=f"Loja_Estoque_Gerenciar_Search:{product_id}:{field_id}:{page}",
            ),
            disnake.ui.Button(
                label="Limpar busca", style=disnake.ButtonStyle.red,
                emoji=emoji.delete,
                custom_id=f"Loja_Estoque_Gerenciar_ClearSearch:{product_id}:{field_id}",
            ),
        )
    else:
        row_search = disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Buscar", style=disnake.ButtonStyle.blurple, emoji=emoji.search,
                custom_id=f"Loja_Estoque_Gerenciar_Search:{product_id}:{field_id}:{page}",
            ),
        )

    return [row_page, row_actions, row_search]


# ── Painel principal ─────────────────────────────────────────────────────────

def panel(inter, product_id: str, field_id: str, page: int = 0) -> dict:
    mode = db.get_document("custom_mode").get("mode")
    search = _state_get(inter.user.id, product_id, field_id).get("search", "")
    if mode == "embed":
        return _panel_embed(inter, product_id, field_id, page, search)
    return _panel_components(inter, product_id, field_id, page, search)


def _panel_components(inter, product_id: str, field_id: str, page: int, search: str) -> dict:
    product = get_product(product_id)
    field = (product.get("campos") or {}).get(field_id) or {}
    product_name = safe_textdisplay(product.get("name") or product_id, 35)
    campo_name = safe_textdisplay(field.get("name") or field_id, 35)

    # Estoque infinito — sem itens para gerenciar
    if field.get("infinite_stock", {}).get("enabled", False):
        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.search} Gerenciar Estoque\n"
                    f"-# {product_name} > {campo_name}"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{emoji.information} Este campo usa **estoque infinito**. "
                    f"Não há itens individuais para gerenciar."
                ),
                **container_kwargs_for_product(product),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back,
                    custom_id=f"Loja_Estoque_Gerenciar_Voltar:{product_id}:{field_id}",
                )
            ),
        ]
        return {"components": components}

    all_items = _load(product_id, field_id)
    page_items, total_pages, total, page = _paginate(all_items, page, search)
    no_items = len(all_items) == 0

    search_badge = f" | 🔍 \"{safe_textdisplay(search, 25)}\"" if search else ""
    header = (
        f"# {emoji.search} Gerenciar Estoque\n"
        f"-# {product_name} > {campo_name}{search_badge}\n"
        f"-# `{total}` resultado(s) de `{len(all_items)}` item(s) | "
        f"Pág. `{page + 1}/{total_pages}`"
    )

    rows = _action_rows(product_id, field_id, page, total_pages, search, no_items)
    components = [
        disnake.ui.Container(
            disnake.ui.TextDisplay(safe_textdisplay(header, 3000)),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(safe_textdisplay(_items_text(page_items, search), 2000)),
            disnake.ui.Separator(),
            *rows,
            **container_kwargs_for_product(product),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back,
                custom_id=f"Loja_Estoque_Gerenciar_Voltar:{product_id}:{field_id}",
            )
        ),
    ]
    return {"components": components}


def _panel_embed(inter, product_id: str, field_id: str, page: int, search: str) -> dict:
    product = get_product(product_id)
    field = (product.get("campos") or {}).get(field_id) or {}
    product_name = safe_textdisplay(product.get("name") or product_id, 35)
    campo_name = safe_textdisplay(field.get("name") or field_id, 35)

    # Estoque infinito
    if field.get("infinite_stock", {}).get("enabled", False):
        embed = disnake.Embed(
            description=(
                f"-# {product_name} > {campo_name} > **Gerenciar Estoque**\n\n"
                f"{emoji.information} Este campo usa **estoque infinito**. "
                f"Não há itens individuais para gerenciar."
            ),
            **embed_kwargs_for_product(product),
        )
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back,
                    custom_id=f"Loja_Estoque_Gerenciar_Voltar:{product_id}:{field_id}",
                )
            )
        ]
        return {"embed": embed, "components": components}

    all_items = _load(product_id, field_id)
    page_items, total_pages, total, page = _paginate(all_items, page, search)
    no_items = len(all_items) == 0

    search_badge = f" | {emoji.search} \"{safe_textdisplay(search, 25)}\"" if search else ""
    description = (
        f"-# {product_name} > {campo_name} > **Gerenciar Estoque**{search_badge}\n"
        f"-# `{total}` resultado(s) de `{len(all_items)}` item(s) | "
        f"Pág. `{page + 1}/{total_pages}`\n\n"
        + safe_textdisplay(_items_text(page_items, search), 1500)
    )

    embed = disnake.Embed(
        description=safe_textdisplay(description, 4000),
        **embed_kwargs_for_product(product),
    )

    rows = _action_rows(product_id, field_id, page, total_pages, search, no_items)
    components = [
        *rows,
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back,
                custom_id=f"Loja_Estoque_Gerenciar_Voltar:{product_id}:{field_id}",
            )
        ),
    ]
    return {"embed": embed, "components": components}


# ── Operações ────────────────────────────────────────────────────────────────

def remove_duplicates(product_id: str, field_id: str) -> int:
    """Remove duplicatas mantendo a primeira ocorrência. Retorna a quantidade removida."""
    items = _load(product_id, field_id)
    seen: set[str] = set()
    new_items: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            new_items.append(item)
    removed = len(items) - len(new_items)
    if removed > 0:
        _save(product_id, field_id, new_items)
        _update_timestamps(product_id, field_id)
    return removed


# ── Modais ───────────────────────────────────────────────────────────────────

class RemoverItemModal(disnake.ui.Modal):
    """
    Modal para remover itens por posição ou por texto exato.

    Posições aceitas:
        • Um número:       5
        • Vários:          1,3,7
        • Intervalo:       1-10
        • Combinado:       1-5,10,15-20

    Texto exato:
        • Cole o conteúdo do item para remover todas as ocorrências.
    """

    def __init__(self, product_id: str, field_id: str, page: int):
        self.product_id = product_id
        self.field_id = field_id
        self.page = page

        total = len(_load(product_id, field_id))
        components = [
            disnake.ui.TextInput(
                label="Número(s), intervalo ou texto exato",
                custom_id="remove_input",
                style=disnake.TextInputStyle.paragraph,
                placeholder=f"Posição: 5 | 1,3,7 | 1-10 | 1-5,10,20 — Texto: conteúdo exato do item",
                required=True,
                max_length=500,
            ),
        ]
        super().__init__(
            title="Remover Item(s) do Estoque",
            components=components,
            custom_id=f"Loja_Estoque_Gerenciar_RemoveModal:{product_id}:{field_id}:{page}",
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        raw = (inter.resolved_values.get("remove_input") or "").strip()
        all_items = _load(self.product_id, self.field_id)

        if not all_items:
            await inter.edit_original_message(components=[
                disnake.ui.Container(disnake.ui.TextDisplay(f"{emoji.wrong} O estoque já está vazio."))
            ])
            return

        positions = _parse_positions(raw, len(all_items))

        if positions is not None:
            # ── Remoção por posição ──────────────────────────────────────────
            removed_count = len(positions)
            pos_set = set(positions)
            new_items = [item for i, item in enumerate(all_items) if i not in pos_set]
            _save(self.product_id, self.field_id, new_items)
            _update_timestamps(self.product_id, self.field_id)
            result = (
                f"{emoji.correct} **{removed_count}** item(s) removido(s) com sucesso.\n"
                f"-# Restam `{len(new_items)}` item(s) no estoque."
            )
        else:
            # ── Remoção por texto ────────────────────────────────────────────
            # 1ª tentativa: correspondência exata
            new_items = [item for item in all_items if item != raw]
            removed_count = len(all_items) - len(new_items)

            # 2ª tentativa: sem distinção de maiúsculas/minúsculas
            if removed_count == 0:
                new_items = [item for item in all_items if item.lower() != raw.lower()]
                removed_count = len(all_items) - len(new_items)

            if removed_count == 0:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"{emoji.wrong} Nenhum item encontrado com o texto "
                            f"**\"{safe_textdisplay(raw, 50)}\"**.\n"
                            f"-# Para remover por posição use apenas números. "
                            f"Para texto, cole o conteúdo exato do item."
                        )
                    )
                ])
                return

            _save(self.product_id, self.field_id, new_items)
            _update_timestamps(self.product_id, self.field_id)
            result = (
                f"{emoji.correct} **{removed_count}** ocorrência(s) de "
                f"**\"{safe_textdisplay(raw, 50)}\"** removida(s).\n"
                f"-# Restam `{len(new_items)}` item(s) no estoque."
            )

        # Sincronizar silenciosamente
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(inter.client, self.product_id)

        # Mostrar resultado por 1,5 s e voltar ao painel
        await inter.edit_original_message(components=[
            disnake.ui.Container(disnake.ui.TextDisplay(result))
        ])
        await asyncio.sleep(1.5)

        panel_data = panel(inter, self.product_id, self.field_id, self.page)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class BuscarEstoqueModal(disnake.ui.Modal):
    """Modal para filtrar os itens exibidos no painel por texto."""

    def __init__(self, product_id: str, field_id: str, page: int):
        self.product_id = product_id
        self.field_id = field_id
        self.page = page

        components = [
            disnake.ui.TextInput(
                label="Filtrar itens por texto",
                custom_id="search_input",
                style=disnake.TextInputStyle.short,
                placeholder="Digite parte do texto para filtrar os itens...",
                required=True,
                max_length=100,
            ),
        ]
        super().__init__(
            title="Buscar no Estoque",
            components=components,
            custom_id=f"Loja_Estoque_Gerenciar_SearchModal:{product_id}:{field_id}:{page}",
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        search = (inter.resolved_values.get("search_input") or "").strip()
        _state_set(inter.user.id, self.product_id, self.field_id, {"search": search})

        panel_data = panel(inter, self.product_id, self.field_id, page=0)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)

"""
modules/loja/marketplace/cog.py
────────────────────────────────
Painel do Marketplace de Revenda.

Exibe todos os produtos com resale=True de TODOS os bots da database,
paginados em blocos de 20 itens num SelectMenu. Ao selecionar um produto,
mostra embed/componente com detalhes e categorias disponíveis.

CONCORRÊNCIA
────────────
Este cog nunca chama fetch_resale_products(force_refresh=True) diretamente —
isso é responsabilidade exclusiva de MarketplaceCacheTask (tsk_marketplace_cache).
As chamadas aqui usam sempre o cache em memória (force_refresh=False, padrão),
que é uma operação O(1) e segura no event loop.
"""

from __future__ import annotations

import asyncio
import datetime

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from functions.marketplace import (
    ResaleProduct,
    fetch_resale_products,
    paginate_products,
    get_user_resales,
    is_in_cooldown,
    is_already_reselling,
    start_resale,
    get_reseller_doc,
    save_reseller_doc,
)
from modules.loja.marketplace.reseller import notify_owner_start, stop_and_notify

_PAGE_SIZE = 20  # máx de opções por SelectMenu


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers de UI
# ──────────────────────────────────────────────────────────────────────────────

def _build_page_options(page_products: list[ResaleProduct]) -> list[disnake.SelectOption]:
    return [
        disnake.SelectOption(
            label=p.select_label,
            value=p.select_value,
            description=p.select_description,
        )
        for p in page_products
    ]


def _build_nav_buttons(page: int, total_pages: int) -> list[disnake.ui.Button]:
    buttons: list[disnake.ui.Button] = []

    if total_pages > 1:
        buttons.append(
            disnake.ui.Button(
                label="◀",
                style=disnake.ButtonStyle.blurple,
                custom_id=f"Marketplace_Page_{page - 1}",
                disabled=page == 0,
            )
        )
        buttons.append(
            disnake.ui.Button(
                label=f"{page + 1}/{total_pages}",
                style=disnake.ButtonStyle.grey,
                custom_id="Marketplace_PageInfo",
                disabled=True,
            )
        )
        buttons.append(
            disnake.ui.Button(
                label="▶",
                style=disnake.ButtonStyle.blurple,
                custom_id=f"Marketplace_Page_{page + 1}",
                disabled=page >= total_pages - 1,
            )
        )

    buttons.append(
        disnake.ui.Button(
            label="Minhas Revendas",
            style=disnake.ButtonStyle.blurple,
            emoji=emoji.basket,
            custom_id="Marketplace_MyResales",
        )
    )
    buttons.append(
        disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id="Loja_Panel",
        )
    )
    return buttons


# ──────────────────────────────────────────────────────────────────────────────
#  Builders de painel (components v2 e embed)
# ──────────────────────────────────────────────────────────────────────────────

def _panel_components(
    page_products: list[ResaleProduct],
    page: int,
    total_pages: int,
    total: int,
    color_hex: str | None,
) -> dict:
    container_kwargs = {}
    if color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(
            int(color_hex.replace("#", ""), 16)
        )

    if not page_products:
        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.basket} Marketplace\n-# Painel > Loja > **Marketplace**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        "Nenhum produto com revenda ativa foi encontrado no momento."
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Voltar",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.back,
                            custom_id="Loja_Panel",
                        )
                    ),
                    **container_kwargs,
                )
            ]
        }

    nav_buttons = _build_nav_buttons(page, total_pages)

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.basket} Marketplace\n-# Painel > Loja > **Marketplace**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"Produtos disponíveis para revenda de todos os bots.\n"
                    f"-# {total} produto(s) encontrado(s) · Página {page + 1} de {total_pages}"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Marketplace_SelectProduct",
                        placeholder="Selecione um produto para ver detalhes",
                        options=_build_page_options(page_products),
                    )
                ),
                disnake.ui.ActionRow(*nav_buttons),
                **container_kwargs,
            )
        ]
    }


def _panel_embed(
    page_products: list[ResaleProduct],
    page: int,
    total_pages: int,
    total: int,
    color_hex: str | None,
) -> dict:
    embed_kwargs: dict = {}
    if color_hex:
        embed_kwargs["color"] = int(color_hex.replace("#", ""), 16)

    if not page_products:
        embed = disnake.Embed(
            description=(
                "-# Painel > Loja > **Marketplace**\n\n"
                "Nenhum produto com revenda ativa foi encontrado no momento."
            ),
            **embed_kwargs,
        )
        return {
            "embed": embed,
            "components": [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Loja_Panel",
                    )
                )
            ],
        }

    embed = disnake.Embed(
        description=(
            f"-# Painel > Loja > **Marketplace**\n\n"
            f"Produtos disponíveis para revenda de todos os bots.\n"
            f"-# {total} produto(s) encontrado(s) · Página {page + 1} de {total_pages}"
        ),
        **embed_kwargs,
    )

    nav_buttons = _build_nav_buttons(page, total_pages)

    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id="Marketplace_SelectProduct",
                placeholder="Selecione um produto para ver detalhes",
                options=_build_page_options(page_products),
            )
        ),
        disnake.ui.ActionRow(*nav_buttons),
    ]

    return {"embed": embed, "components": components}


# ──────────────────────────────────────────────────────────────────────────────
#  Builder de detalhe do produto → painel intermediário (escolher canal)
# ──────────────────────────────────────────────────────────────────────────────

def _channel_select_components(product: ResaleProduct, color_hex: str | None) -> dict:
    container_kwargs = {}
    color = product.hex_color or color_hex
    if color:
        container_kwargs["accent_colour"] = disnake.Colour(int(color.replace("#", ""), 16))

    cats_lines = []
    for cat in product.categorias:
        resale_price = cat.get("resale_price", cat["price"])
        cats_lines.append(f"• **{cat['name']}** — R$ {resale_price:.2f}")
    cats_text = "\n".join(cats_lines) if cats_lines else "Nenhuma categoria."

    content = (
        f"# {product.name}\n"
        f"-# Painel > Loja > Marketplace > **Confirmar Revenda**\n\n"
        f"{product.description or 'Sem descrição.'}\n\n"
        f"**Entrega:** {product.delivery_label} · **Comissão:** {product.commission_label}\n\n"
        f"**Categorias disponíveis:**\n{cats_text}\n\n"
        f"-# Selecione o canal onde o painel de vendas será enviado."
    )

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(content),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id=f"Marketplace_ConfirmChannel:{product.select_value}",
                        placeholder="Selecione o canal para enviar o painel",
                        channel_types=[disnake.ChannelType.text],
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar ao Marketplace",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Marketplace_Page_0",
                    )
                ),
                **container_kwargs,
            )
        ]
    }


def _channel_select_embed(product: ResaleProduct, color_hex: str | None) -> dict:
    color = product.hex_color or color_hex
    embed_kwargs: dict = {}
    if color:
        embed_kwargs["color"] = int(color.replace("#", ""), 16)

    cats_lines = []
    for cat in product.categorias:
        resale_price = cat.get("resale_price", cat["price"])
        cats_lines.append(f"• **{cat['name']}** — R$ {resale_price:.2f}")
    cats_text = "\n".join(cats_lines) if cats_lines else "Nenhuma categoria."

    embed = disnake.Embed(
        title=product.name,
        description=(
            f"-# Painel > Loja > Marketplace > **Confirmar Revenda**\n\n"
            f"{product.description or 'Sem descrição.'}\n\n"
            f"**Entrega:** {product.delivery_label} · **Comissão:** {product.commission_label}\n\n"
            f"**Categorias disponíveis:**\n{cats_text}\n\n"
            f"-# Selecione o canal onde o painel de vendas será enviado."
        ),
        **embed_kwargs,
    )
    if product.banner:
        embed.set_image(url=product.banner)

    components = [
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                custom_id=f"Marketplace_ConfirmChannel:{product.select_value}",
                placeholder="Selecione o canal para enviar o painel",
                channel_types=[disnake.ChannelType.text],
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar ao Marketplace",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="Marketplace_Page_0",
            )
        ),
    ]
    return {"embed": embed, "components": components}


# ──────────────────────────────────────────────────────────────────────────────
#  Builder painel "Meus produtos revendidos"
# ──────────────────────────────────────────────────────────────────────────────

def _my_resales_components(user_id: str, color_hex: str | None) -> dict:
    container_kwargs = {}
    if color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(color_hex.replace("#", ""), 16))

    resales = get_user_resales(user_id)
    # Apenas entradas com revenda ativa (têm "started_at")
    active = {k: v for k, v in resales.items() if "started_at" in v}

    if not active:
        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# Meus Produtos Revendidos\n"
                        f"-# Painel > Loja > Marketplace > **Minhas Revendas**\n\n"
                        f"Você não está revendendo nenhum produto no momento."
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Voltar ao Marketplace",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.back,
                            custom_id="Marketplace_Page_0",
                        )
                    ),
                    **container_kwargs,
                )
            ]
        }

    options = [
        disnake.SelectOption(
            label=v["product_name"][:97] + "..." if len(v["product_name"]) > 100 else v["product_name"],
            value=k,
            description=f"Canal: {v.get('channel_id', '?')} · Servidor: {v.get('guild_name', '?')[:50]}",
        )
        for k, v in active.items()
    ][:25]  # SelectMenu máx 25

    lines = []
    for k, v in active.items():
        started = datetime.datetime.fromtimestamp(v["started_at"]).strftime("%d/%m %H:%M")
        lines.append(f"• **{v['product_name']}** — <#{v['channel_id']}> · desde {started}")
    listing = "\n".join(lines)

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# Meus Produtos Revendidos\n"
                    f"-# Painel > Loja > Marketplace > **Minhas Revendas**\n\n"
                    f"{listing}\n\n"
                    f"-# Selecione um produto abaixo para gerenciá-lo."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Marketplace_ManageResale",
                        placeholder="Selecione uma revenda para gerenciar",
                        options=options,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar ao Marketplace",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Marketplace_Page_0",
                    )
                ),
                **container_kwargs,
            )
        ]
    }


def _my_resales_embed(user_id: str, color_hex: str | None) -> dict:
    embed_kwargs: dict = {}
    if color_hex:
        embed_kwargs["color"] = int(color_hex.replace("#", ""), 16)

    resales = get_user_resales(user_id)
    active = {k: v for k, v in resales.items() if "started_at" in v}

    if not active:
        embed = disnake.Embed(
            description=(
                "-# Painel > Loja > Marketplace > **Minhas Revendas**\n\n"
                "Você não está revendendo nenhum produto no momento."
            ),
            **embed_kwargs,
        )
        return {
            "embed": embed,
            "components": [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar ao Marketplace",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Marketplace_Page_0",
                    )
                )
            ],
        }

    lines = []
    for k, v in active.items():
        started = datetime.datetime.fromtimestamp(v["started_at"]).strftime("%d/%m %H:%M")
        lines.append(f"• **{v['product_name']}** — <#{v['channel_id']}> · desde {started}")

    options = [
        disnake.SelectOption(
            label=v["product_name"][:100],
            value=k,
            description=f"Servidor: {v.get('guild_name', '?')[:50]}",
        )
        for k, v in active.items()
    ][:25]

    embed = disnake.Embed(
        description=(
            f"-# Painel > Loja > Marketplace > **Minhas Revendas**\n\n"
            + "\n".join(lines)
            + "\n\n-# Selecione um produto abaixo para gerenciá-lo."
        ),
        **embed_kwargs,
    )
    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id="Marketplace_ManageResale",
                placeholder="Selecione uma revenda para gerenciar",
                options=options,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar ao Marketplace",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="Marketplace_Page_0",
            )
        ),
    ]
    return {"embed": embed, "components": components}


# ──────────────────────────────────────────────────────────────────────────────
#  Painel de vendas de revenda — enviado no canal escolhido pelo revendedor
# ──────────────────────────────────────────────────────────────────────────────

async def _send_resale_panel(
    channel: disnake.TextChannel,
    product: ResaleProduct,
    reseller_user_id: str,
    mode: str,
) -> disnake.Message | None:
    """
    Envia o painel de vendas do produto revendido no canal.
    O botão de compra usa custom_id 'buy_resale:{select_value}' para
    identificar que é uma compra de produto revendido.
    """
    select_value = product.select_value  # "{bot_id}::{product_id}"

    campos_lines = []
    for cat in product.categorias:
        campos_lines.append(f"• **{cat['name']}** — R$ {cat['resale_price']:.2f}")
    campos_text = "\n".join(campos_lines) if campos_lines else "Sem opções disponíveis."

    if mode == "embed":
        embed_kwargs: dict = {}
        if product.hex_color:
            try:
                embed_kwargs["color"] = disnake.Colour(int(product.hex_color.replace("#", ""), 16))
            except Exception:
                pass

        embed = disnake.Embed(
            title=product.name,
            description=(
                f"{product.description or ''}\n\n"
                f"**Opções disponíveis:**\n{campos_text}"
            ).strip(),
            **embed_kwargs,
        )
        if product.banner:
            embed.set_image(url=product.banner)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Comprar",
                    emoji=emoji.cart,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f"buy_resale:{select_value}",
                )
            )
        ]
        return await channel.send(embed=embed, components=components)

    # mode == "components"
    container_kwargs: dict = {}
    if product.hex_color:
        try:
            container_kwargs["accent_colour"] = disnake.Colour(int(product.hex_color.replace("#", ""), 16))
        except Exception:
            pass

    prices = [cat["resale_price"] for cat in product.categorias]
    min_price = min(prices) if prices else 0.0
    max_price = max(prices) if prices else 0.0
    price_text = (
        f"R$ {min_price:.2f}"
        if min_price == max_price
        else f"R$ {min_price:.2f} - R$ {max_price:.2f}"
    )

    title_text = f"**{product.name}**"
    if product.description:
        title_text += f"\n{product.description}"

    inner_items = []
    if product.banner:
        inner_items.append(
            disnake.ui.MediaGallery(
                disnake.MediaGalleryItem(media=product.banner)
            )
        )
    inner_items.append(disnake.ui.TextDisplay(title_text))
    inner_items.append(disnake.ui.Separator())
    inner_items.append(
        disnake.ui.Section(
            disnake.ui.TextDisplay(
                f"**{price_text}**\n"
                f"-# {len(product.categorias)} {'opção' if len(product.categorias) == 1 else 'opções'} disponíve{'l' if len(product.categorias) == 1 else 'is'}"
            ),
            accessory=disnake.ui.Button(
                label="Comprar",
                emoji=emoji.cart,
                style=disnake.ButtonStyle.grey,
                custom_id=f"buy_resale:{select_value}",
            ),
        )
    )

    container = disnake.ui.Container(*inner_items, **container_kwargs)
    return await channel.send(
        components=[container],
        flags=disnake.MessageFlags(is_components_v2=True),
    )


def _manage_resale_panel(select_value: str, entry: dict, mode: str, color_hex: str | None) -> dict:
    """Monta o sub-painel de gerenciamento de uma revenda específica."""
    product_name = entry.get("product_name", "Produto")
    channel_id = entry.get("channel_id", "?")
    guild_name = entry.get("guild_name", "?")
    has_panel = bool(entry.get("panel_message_id"))

    action_buttons = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Reenviar Painel",
            style=disnake.ButtonStyle.blurple,
            emoji=emoji.reload,
            custom_id=f"Marketplace_ResaleAction:resend:{select_value}",
        ),
        disnake.ui.Button(
            label="Atualizar Painel",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.edit if hasattr(emoji, "edit") else None,
            custom_id=f"Marketplace_ResaleAction:update:{select_value}",
            disabled=not has_panel,
        ),
        disnake.ui.Button(
            label="Apagar Painel",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.trash if hasattr(emoji, "trash") else None,
            custom_id=f"Marketplace_ResaleAction:delete:{select_value}",
            disabled=not has_panel,
        ),
        disnake.ui.Button(
            label="Parar Revenda",
            style=disnake.ButtonStyle.red,
            emoji=emoji.wrong,
            custom_id=f"Marketplace_ResaleAction:stop:{select_value}",
        ),
    )
    back_button = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id="Marketplace_MyResales",
        )
    )

    started = datetime.datetime.fromtimestamp(entry.get("started_at", 0)).strftime("%d/%m/%Y às %H:%M")

    if mode == "components":
        container_kwargs = {}
        if color_hex:
            try:
                container_kwargs["accent_colour"] = disnake.Colour(int(color_hex.replace("#", ""), 16))
            except Exception:
                pass
        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# Gerenciar Revenda\n"
                        f"-# Painel > Loja > Marketplace > Minhas Revendas > **{product_name}**\n\n"
                        f"**Produto:** {product_name}\n"
                        f"**Canal:** <#{channel_id}>\n"
                        f"**Servidor:** {guild_name}\n"
                        f"**Iniciado em:** {started}\n"
                        f"**Painel ativo:** {'Sim' if has_panel else 'Não'}"
                    ),
                    disnake.ui.Separator(),
                    action_buttons,
                    back_button,
                    **container_kwargs,
                )
            ]
        }

    # embed mode
    embed_kwargs: dict = {}
    if color_hex:
        try:
            embed_kwargs["color"] = int(color_hex.replace("#", ""), 16)
        except Exception:
            pass
    embed = disnake.Embed(
        description=(
            f"-# Painel > Loja > Marketplace > Minhas Revendas > **{product_name}**\n\n"
            f"**Produto:** {product_name}\n"
            f"**Canal:** <#{channel_id}>\n"
            f"**Servidor:** {guild_name}\n"
            f"**Iniciado em:** {started}\n"
            f"**Painel ativo:** {'Sim' if has_panel else 'Não'}"
        ),
        **embed_kwargs,
    )
    return {
        "embed": embed,
        "components": [action_buttons, back_button],
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Cog principal
# ──────────────────────────────────────────────────────────────────────────────

class MarketplaceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_mode_and_color(self) -> tuple[str, str | None]:
        mode = db.get_document("custom_mode").get("mode", "components")
        color_hex = db.get_document("custom_colors").get("primary")
        return mode, color_hex

    def get_panel_data(self, page: int = 0) -> dict:
        """Monta o painel do marketplace na página indicada."""
        mode, color_hex = self._get_mode_and_color()
        products = fetch_resale_products()
        page_products, total_pages, page = paginate_products(products, page, _PAGE_SIZE)
        total = len(products)

        if mode == "embed":
            return _panel_embed(page_products, page, total_pages, total, color_hex)
        return _panel_components(page_products, page, total_pages, total, color_hex)

    def get_channel_select_data(self, select_value: str) -> dict | None:
        """
        Busca o produto e monta o painel intermediário de seleção de canal.
        """
        mode, color_hex = self._get_mode_and_color()
        products = fetch_resale_products()
        product = next((p for p in products if p.select_value == select_value), None)
        if product is None:
            return None
        if mode == "embed":
            return _channel_select_embed(product, color_hex)
        return _channel_select_components(product, color_hex)

    def get_my_resales_data(self, user_id: str) -> dict:
        mode, color_hex = self._get_mode_and_color()
        if mode == "embed":
            return _my_resales_embed(str(user_id), color_hex)
        return _my_resales_components(str(user_id), color_hex)

    # ── Listeners ────────────────────────────────────────────────────────────

    async def _edit(self, inter: disnake.MessageInteraction, data: dict, mode: str):
        """Helper para editar a mensagem respeitando o modo."""
        if "embed" in data:
            await inter.edit_original_message(content=None, **data)
        else:
            await inter.edit_original_message(
                **data,
                flags=disnake.MessageFlags(is_components_v2=True),
            )

    # Prefixos reconhecidos por este cog.
    # Qualquer custom_id fora deste conjunto é ignorado imediatamente,
    # sem deferir nem tocar na interação — evita conflito com outros cogs.
    _BUTTON_PREFIXES: tuple[str, ...] = (
        "Marketplace_Page_",
        "Marketplace_MyResales",
        "Marketplace_ResaleAction:",
    )
    _DROPDOWN_PREFIXES: tuple[str, ...] = (
        "Marketplace_SelectProduct",
        "Marketplace_ConfirmChannel:",
        "Marketplace_ManageResale",
        "Marketplace_StopResale",
    )

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        # Guard: ignora interações que não pertencem a este cog
        if not custom_id or not any(custom_id.startswith(p) for p in self._BUTTON_PREFIXES):
            return

        # Navegação de página: Marketplace_Page_{n}
        if custom_id and custom_id.startswith("Marketplace_Page_"):
            try:
                page = int(custom_id.rsplit("_", 1)[-1])
            except ValueError:
                return

            mode, _ = self._get_mode_and_color()
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            await self._edit(inter, self.get_panel_data(page), mode)

        # Painel "Minhas Revendas"
        elif custom_id == "Marketplace_MyResales":
            mode, _ = self._get_mode_and_color()
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            await self._edit(inter, self.get_my_resales_data(inter.author.id), mode)

        # ── Ações de gerenciamento de revenda ─────────────────────────────────
        elif custom_id and custom_id.startswith("Marketplace_ResaleAction:"):
            parts = custom_id.split(":", 2)
            if len(parts) < 3:
                return
            action = parts[1]       # resend | update | delete | stop
            select_value = parts[2] # "{bot_id}::{product_id}"

            mode, color_hex = self._get_mode_and_color()
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)

            resales = get_user_resales(str(inter.author.id))
            entry = resales.get(select_value)
            if not entry or "started_at" not in entry:
                await inter.followup.send("Revenda não encontrada.", ephemeral=True)
                return

            panel_message_id = entry.get("panel_message_id")
            panel_channel_id = entry.get("panel_channel_id") or entry.get("channel_id")

            async def _get_panel_channel():
                try:
                    return inter.guild.get_channel(int(panel_channel_id))
                except Exception:
                    return None

            async def _get_panel_message(channel):
                if not channel or not panel_message_id:
                    return None
                try:
                    return await channel.fetch_message(int(panel_message_id))
                except Exception:
                    return None

            def _update_entry(new_panel_message_id=None, clear_panel=False):
                doc = get_reseller_doc()
                uid = str(inter.author.id)
                if uid in doc and select_value in doc[uid]:
                    if clear_panel:
                        doc[uid][select_value].pop("panel_message_id", None)
                        doc[uid][select_value].pop("panel_channel_id", None)
                    elif new_panel_message_id:
                        doc[uid][select_value]["panel_message_id"] = str(new_panel_message_id)
                        doc[uid][select_value]["panel_channel_id"] = str(panel_channel_id)
                    save_reseller_doc(doc)

            if action == "stop":
                stopped = await stop_and_notify(
                    bot=self.bot,
                    user_id=str(inter.author.id),
                    select_value=select_value,
                    reseller=inter.author,
                )
                if stopped is None:
                    await inter.followup.send("Revenda não encontrada.", ephemeral=True)
                    return
                await self._edit(inter, self.get_my_resales_data(inter.author.id), mode)
                await inter.followup.send(
                    f"{emoji.correct} Você parou de revender **{stopped['product_name']}**.\n"
                    f"-# Cooldown de 30 minutos aplicado.",
                    ephemeral=True,
                )

            elif action == "delete":
                channel = await _get_panel_channel()
                msg = await _get_panel_message(channel)
                if msg:
                    try:
                        await msg.delete()
                        _update_entry(clear_panel=True)
                        await inter.followup.send(f"{emoji.correct} Painel apagado com sucesso.", ephemeral=True)
                    except Exception as e:
                        await inter.followup.send(f"{emoji.wrong} Não foi possível apagar o painel: `{e}`", ephemeral=True)
                else:
                    _update_entry(clear_panel=True)
                    await inter.followup.send(f"{emoji.wrong} Painel não encontrado no canal (já pode ter sido apagado).", ephemeral=True)
                # Atualizar sub-painel
                resales2 = get_user_resales(str(inter.author.id))
                entry2 = resales2.get(select_value, entry)
                await self._edit(inter, _manage_resale_panel(select_value, entry2, mode, color_hex), mode)

            elif action == "resend":
                products = fetch_resale_products(force_refresh=False)
                product = next((p for p in products if p.select_value == select_value), None)
                if not product:
                    await inter.followup.send(f"{emoji.wrong} Produto não encontrado no marketplace.", ephemeral=True)
                    return
                channel = await _get_panel_channel()
                if not channel:
                    await inter.followup.send(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
                    return
                try:
                    new_msg = await _send_resale_panel(channel, product, str(inter.author.id), mode)
                    if new_msg:
                        _update_entry(new_panel_message_id=new_msg.id)
                    resales2 = get_user_resales(str(inter.author.id))
                    entry2 = resales2.get(select_value, entry)
                    await self._edit(inter, _manage_resale_panel(select_value, entry2, mode, color_hex), mode)
                    await inter.followup.send(f"{emoji.correct} Painel reenviado em <#{channel.id}>!", ephemeral=True)
                except Exception as e:
                    await inter.followup.send(f"{emoji.wrong} Erro ao reenviar painel: `{e}`", ephemeral=True)

            elif action == "update":
                products = fetch_resale_products(force_refresh=False)
                product = next((p for p in products if p.select_value == select_value), None)
                if not product:
                    await inter.followup.send(f"{emoji.wrong} Produto não encontrado no marketplace.", ephemeral=True)
                    return
                channel = await _get_panel_channel()
                msg = await _get_panel_message(channel)
                if not msg:
                    await inter.followup.send(
                        f"{emoji.wrong} Painel original não encontrado. Use **Reenviar** para criar um novo.",
                        ephemeral=True,
                    )
                    return
                try:
                    # Montar novo conteúdo do painel sem enviar nova mensagem
                    select_val = product.select_value
                    campos_lines = [f"• **{c['name']}** — R$ {c['resale_price']:.2f}" for c in product.categorias]
                    campos_text = "\n".join(campos_lines) or "Sem opções disponíveis."
                    if mode == "embed":
                        embed_kw: dict = {}
                        if product.hex_color:
                            try:
                                embed_kw["color"] = disnake.Colour(int(product.hex_color.replace("#", ""), 16))
                            except Exception:
                                pass
                        new_embed = disnake.Embed(
                            title=product.name,
                            description=(f"{product.description or ''}\n\n**Opções disponíveis:**\n{campos_text}").strip(),
                            **embed_kw,
                        )
                        if product.banner:
                            new_embed.set_image(url=product.banner)
                        new_components = [disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label="Comprar", emoji=emoji.cart,
                                style=disnake.ButtonStyle.grey,
                                custom_id=f"buy_resale:{select_val}",
                            )
                        )]
                        await msg.edit(embed=new_embed, components=new_components)
                    else:
                        prices = [c["resale_price"] for c in product.categorias]
                        min_p = min(prices) if prices else 0.0
                        max_p = max(prices) if prices else 0.0
                        price_text = f"R$ {min_p:.2f}" if min_p == max_p else f"R$ {min_p:.2f} - R$ {max_p:.2f}"
                        title_text = f"**{product.name}**"
                        if product.description:
                            title_text += f"\n{product.description}"
                        inner = []
                        if product.banner:
                            inner.append(disnake.ui.MediaGallery(disnake.MediaGalleryItem(media=product.banner)))
                        inner.append(disnake.ui.TextDisplay(title_text))
                        inner.append(disnake.ui.Separator())
                        n = len(product.categorias)
                        inner.append(disnake.ui.Section(
                            disnake.ui.TextDisplay(
                                f"**{price_text}**\n"
                                f"-# {n} {'opção' if n == 1 else 'opções'} disponíve{'l' if n == 1 else 'is'}"
                            ),
                            accessory=disnake.ui.Button(
                                label="Comprar", emoji=emoji.cart,
                                style=disnake.ButtonStyle.grey,
                                custom_id=f"buy_resale:{select_val}",
                            ),
                        ))
                        container_kw: dict = {}
                        if product.hex_color:
                            try:
                                container_kw["accent_colour"] = disnake.Colour(int(product.hex_color.replace("#", ""), 16))
                            except Exception:
                                pass
                        await msg.edit(
                            components=[disnake.ui.Container(*inner, **container_kw)],
                            flags=disnake.MessageFlags(is_components_v2=True),
                        )
                    await inter.followup.send(f"{emoji.correct} Painel atualizado com sucesso!", ephemeral=True)
                except Exception as e:
                    await inter.followup.send(f"{emoji.wrong} Erro ao atualizar painel: `{e}`", ephemeral=True)

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # Guard: ignora interações que não pertencem a este cog
        if not cid or not any(cid.startswith(p) for p in self._DROPDOWN_PREFIXES):
            return

        # ── Seleção de produto → painel de canal ─────────────────────────────
        if cid == "Marketplace_SelectProduct":
            select_value = inter.values[0]
            mode, _ = self._get_mode_and_color()
            msg_handler = embed_message if mode == "embed" else message
            if not inter.response.is_done():
                await msg_handler.wait(inter, send=False)

            # Verificações antes de mostrar painel de canal
            if is_already_reselling(inter.author.id, select_value):
                await inter.followup.send(
                    f"{emoji.alert} Você já está revendendo esse produto. "
                    f"Acesse **Minhas Revendas** para gerenciá-lo.",
                    ephemeral=True,
                )
                return

            in_cd, secs = is_in_cooldown(inter.author.id, select_value)
            if in_cd:
                mins = secs // 60
                segs = secs % 60
                await inter.followup.send(
                    f"{emoji.alert} Você parou de revender esse produto recentemente.\n"
                    f"-# Aguarde **{mins}min {segs}s** para revendê-lo novamente.",
                    ephemeral=True,
                )
                return

            data = self.get_channel_select_data(select_value)
            if data is None:
                await inter.followup.send(
                    "Produto não encontrado. Tente novamente.", ephemeral=True
                )
                return

            await self._edit(inter, data, mode)

        # ── Seleção de canal → confirmar e iniciar revenda ───────────────────
        elif cid and cid.startswith("Marketplace_ConfirmChannel:"):
            select_value = cid.split(":", 1)[1]
            channel_id = inter.values[0]
            mode, _ = self._get_mode_and_color()
            msg_handler = embed_message if mode == "embed" else message
            if not inter.response.is_done():
                await msg_handler.wait(inter, send=False)

            products = fetch_resale_products()
            product = next((p for p in products if p.select_value == select_value), None)
            if product is None:
                await inter.followup.send("Produto não encontrado.", ephemeral=True)
                return

            # Checagem dupla de cooldown/ativo
            if is_already_reselling(inter.author.id, select_value):
                await inter.followup.send(
                    f"{emoji.alert} Você já está revendendo esse produto.", ephemeral=True
                )
                return
            in_cd, secs = is_in_cooldown(inter.author.id, select_value)
            if in_cd:
                mins = secs // 60
                await inter.followup.send(
                    f"{emoji.alert} Ainda em cooldown. Aguarde **{mins}min** para revendê-lo.",
                    ephemeral=True,
                )
                return

            guild_name = inter.guild.name if inter.guild else "Servidor desconhecido"
            ok = start_resale(
                user_id=str(inter.author.id),
                guild_id=str(inter.guild_id),
                guild_name=guild_name,
                channel_id=str(channel_id),
                product=product,
            )
            if not ok:
                await inter.followup.send(
                    f"{emoji.alert} Não foi possível iniciar a revenda (cooldown ativo).",
                    ephemeral=True,
                )
                return

            # Envia o painel de vendas do produto revendido no canal selecionado
            panel_message_id = None
            try:
                channel = inter.guild.get_channel(int(channel_id))
                if channel:
                    panel_msg = await _send_resale_panel(channel, product, str(inter.author.id), mode)
                    if panel_msg:
                        panel_message_id = str(panel_msg.id)
            except Exception as e:
                print(f"[Marketplace] Erro ao enviar painel de revenda no canal: {e}")

            # Salvar message_id no registro da revenda
            if panel_message_id:
                _doc = get_reseller_doc()
                _key = product.select_value
                if str(inter.author.id) in _doc and _key in _doc[str(inter.author.id)]:
                    _doc[str(inter.author.id)][_key]["panel_message_id"] = panel_message_id
                    _doc[str(inter.author.id)][_key]["panel_channel_id"] = str(channel_id)
                    save_reseller_doc(_doc)

            # Notifica o dono do produto via DM ou log
            await notify_owner_start(
                bot=self.bot,
                product=product,
                reseller=inter.author,
                guild=inter.guild,
                channel_id=channel_id,
            )

            # Volta ao marketplace com confirmação
            await self._edit(inter, self.get_panel_data(0), mode)
            await inter.followup.send(
                f"{emoji.correct} Revenda de **{product.name}** iniciada em <#{channel_id}>!\n"
                f"-# Acesse **Minhas Revendas** para gerenciar ou parar a revenda.",
                ephemeral=True,
            )

        # ── Gerenciar revenda específica ──────────────────────────────────────
        elif cid == "Marketplace_ManageResale":
            select_value = inter.values[0]
            mode, color_hex = self._get_mode_and_color()
            msg_handler = embed_message if mode == "embed" else message
            if not inter.response.is_done():
                await msg_handler.wait(inter, send=False)

            resales = get_user_resales(str(inter.author.id))
            entry = resales.get(select_value)
            if not entry or "started_at" not in entry:
                await inter.followup.send("Revenda não encontrada.", ephemeral=True)
                return

            await self._edit(inter, _manage_resale_panel(select_value, entry, mode, color_hex), mode)

        # ── Parar revenda ─────────────────────────────────────────────────────
        elif cid == "Marketplace_StopResale":
            select_value = inter.values[0]
            mode, _ = self._get_mode_and_color()
            msg_handler = embed_message if mode == "embed" else message
            if not inter.response.is_done():
                await msg_handler.wait(inter, send=False)

            entry = await stop_and_notify(
                bot=self.bot,
                user_id=str(inter.author.id),
                select_value=select_value,
                reseller=inter.author,
            )

            if entry is None:
                await inter.followup.send(
                    "Revenda não encontrada.", ephemeral=True
                )
                return

            await self._edit(inter, self.get_my_resales_data(inter.author.id), mode)
            await inter.followup.send(
                f"{emoji.correct} Você parou de revender **{entry['product_name']}**.\n"
                f"-# Cooldown de 30 minutos aplicado para revendê-lo novamente.",
                ephemeral=True,
            )


def setup(bot: commands.Bot):
    bot.add_cog(MarketplaceCog(bot))
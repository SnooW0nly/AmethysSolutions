"""
Sistema de carrinho para venda de membros verificados via AmyCloud.
Produto especial: sem campos, quantidade variável, entrega via painel DM.
"""
import asyncio
import disnake
from disnake.ext import commands
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from .cart_utils import get_available_payment_methods, ensure_emoji


# ── Helpers de configuração ───────────────────────────────────────────────────

def get_members_product() -> Optional[tuple[str, dict]]:
    """Retorna (product_id, product) do único produto de membros, ou None."""
    products = db.get_document("loja_products") or {}
    for pid, p in products.items():
        if p.get("is_members_product"):
            return pid, p
    return None


def is_members_product(product_id: str) -> bool:
    products = db.get_document("loja_products") or {}
    return bool(products.get(product_id, {}).get("is_members_product"))


def get_members_pricing(product_id: str) -> list[dict]:
    """Retorna lista de faixas de preço: [{min_qty, max_qty, price_per_member}]."""
    products = db.get_document("loja_products") or {}
    return products.get(product_id, {}).get("members_pricing", [])


def calc_members_price(product_id: str, quantity: int) -> float:
    """Calcula o preço total para a quantidade de membros solicitada."""
    pricing = get_members_pricing(product_id)
    if not pricing:
        return 0.0
    # Ordenar por min_qty decrescente para pegar a faixa correta
    pricing_sorted = sorted(pricing, key=lambda x: x.get("min_qty", 0), reverse=True)
    for tier in pricing_sorted:
        if quantity >= tier.get("min_qty", 0):
            return round(quantity * tier.get("price_per_member", 0.0), 2)
    # Fallback: usar o tier de menor quantidade
    last = pricing_sorted[-1]
    return round(quantity * last.get("price_per_member", 0.0), 2)


def get_cloud_available_members(product_id: str) -> int:
    """Retorna quantos membros verificados estão disponíveis no cloud."""
    try:
        cloud_config = db.get_document("cloud_data") or {}
        # Usar contagem cacheada salva pelo bot (atualizada pelo WSManager)
        return int(cloud_config.get("cached_auth_count", 0))
    except Exception:
        return 0


def _build_members_cart_panel(
    product: dict,
    product_id: str,
    quantity: int,
    payment_method: Optional[str],
) -> dict:
    """Constrói o painel do carrinho de membros (components v2)."""
    colors = db.get_document("custom_colors") or {}
    primary_hex = colors.get("primary", "#5c5ef0")
    try:
        accent = disnake.Colour(int(primary_hex.replace("#", ""), 16))
    except Exception:
        accent = disnake.Colour(0x5c5ef0)

    available = get_cloud_available_members(product_id)
    price_total = calc_members_price(product_id, quantity)
    price_str = utils.format_price_brl(price_total)
    product_name = product.get("name", "Membros")

    # Faixas de preço formatadas
    pricing = get_members_pricing(product_id)
    pricing_lines = []
    if pricing:
        for tier in sorted(pricing, key=lambda x: x.get("min_qty", 0)):
            max_q = tier.get("max_qty")
            min_q = tier.get("min_qty", 0)
            ppm = tier.get("price_per_member", 0.0)
            if max_q:
                pricing_lines.append(f"`{min_q}–{max_q}` membros → R$ {ppm:.2f}/un")
            else:
                pricing_lines.append(f"`{min_q}+` membros → R$ {ppm:.2f}/un")
    pricing_text = "\n".join(pricing_lines) if pricing_lines else "Preço não configurado"

    available_methods = get_available_payment_methods()
    method_label = "Não selecionado"
    if payment_method and payment_method in available_methods:
        method_label = available_methods[payment_method]["label"]

    body = (
        f"**Produto:** {product_name}\n"
        f"**Membros disponíveis:** `{available}`\n\n"
        f"**Quantidade selecionada:** `{quantity}`\n"
        f"**Total:** {price_str}\n\n"
        f"**Tabela de preços:**\n{pricing_text}\n\n"
        f"**Pagamento:** {method_label}"
    )

    minus_disabled = quantity <= 1
    plus_disabled = quantity >= available or quantity >= 10000

    row_qty = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="−",
            style=disnake.ButtonStyle.grey,
            custom_id=f"members_cart_qty_minus:{product_id}:{quantity}:{payment_method or 'none'}",
            disabled=minus_disabled,
        ),
        disnake.ui.Button(
            label=f"{quantity} membros",
            style=disnake.ButtonStyle.blurple,
            custom_id=f"members_cart_qty_edit:{product_id}:{quantity}:{payment_method or 'none'}",
            disabled=False,
        ),
        disnake.ui.Button(
            label="+",
            style=disnake.ButtonStyle.grey,
            custom_id=f"members_cart_qty_plus:{product_id}:{quantity}:{payment_method or 'none'}",
            disabled=plus_disabled,
        ),
    )

    # Botão de pagamento (cicla ou mostra único)
    if len(available_methods) > 1:
        pay_btn = disnake.ui.Button(
            label=f"Pag.: {method_label}",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.card if hasattr(emoji, "card") else None,
            custom_id=f"members_cart_pay_method:{product_id}:{quantity}:{payment_method or 'none'}",
        )
    else:
        pay_btn = disnake.ui.Button(
            label=f"Pag.: {method_label}",
            style=disnake.ButtonStyle.grey,
            custom_id=f"members_cart_pay_method:{product_id}:{quantity}:{payment_method or 'none'}",
            disabled=True,
        )

    can_buy = payment_method and available >= quantity and price_total > 0
    row_actions = disnake.ui.ActionRow(
        pay_btn,
        disnake.ui.Button(
            label="Comprar Membros",
            style=disnake.ButtonStyle.green,
            emoji=emoji.correct if hasattr(emoji, "correct") else None,
            custom_id=f"members_cart_buy:{product_id}:{quantity}:{payment_method or 'none'}",
            disabled=not can_buy,
        ),
    )

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# 🧑‍🤝‍🧑 Comprar Membros"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(),
                row_qty,
                row_actions,
                accent_colour=accent,
            )
        ]
    }


def _build_members_cart_embed(
    product: dict,
    product_id: str,
    quantity: int,
    payment_method: Optional[str],
) -> dict:
    """Versão embed do painel de carrinho de membros."""
    colors = db.get_document("custom_colors") or {}
    primary_hex = colors.get("primary", "#5c5ef0")
    try:
        color = int(primary_hex.replace("#", ""), 16)
    except Exception:
        color = 0x5c5ef0

    available = get_cloud_available_members(product_id)
    price_total = calc_members_price(product_id, quantity)
    price_str = utils.format_price_brl(price_total)
    product_name = product.get("name", "Membros")

    available_methods = get_available_payment_methods()
    method_label = "Não selecionado"
    if payment_method and payment_method in available_methods:
        method_label = available_methods[payment_method]["label"]

    pricing = get_members_pricing(product_id)
    pricing_lines = []
    for tier in sorted(pricing, key=lambda x: x.get("min_qty", 0)):
        max_q = tier.get("max_qty")
        min_q = tier.get("min_qty", 0)
        ppm = tier.get("price_per_member", 0.0)
        if max_q:
            pricing_lines.append(f"`{min_q}–{max_q}`: R$ {ppm:.2f}/un")
        else:
            pricing_lines.append(f"`{min_q}+`: R$ {ppm:.2f}/un")

    embed = disnake.Embed(
        title=f"🧑‍🤝‍🧑 Comprar Membros — {product_name}",
        color=color,
        description=(
            f"**Membros disponíveis:** `{available}`\n"
            f"**Quantidade:** `{quantity}`\n"
            f"**Total:** {price_str}\n"
            f"**Pagamento:** {method_label}"
        ),
    )
    if pricing_lines:
        embed.add_field(name="Tabela de preços", value="\n".join(pricing_lines), inline=False)

    minus_disabled = quantity <= 1
    plus_disabled = quantity >= available or quantity >= 10000
    can_buy = bool(payment_method) and available >= quantity and price_total > 0

    if len(available_methods) > 1:
        pay_btn = disnake.ui.Button(
            label=f"Pag.: {method_label}",
            style=disnake.ButtonStyle.grey,
            custom_id=f"members_cart_pay_method:{product_id}:{quantity}:{payment_method or 'none'}",
        )
    else:
        pay_btn = disnake.ui.Button(
            label=f"Pag.: {method_label}",
            style=disnake.ButtonStyle.grey,
            custom_id=f"members_cart_pay_method:{product_id}:{quantity}:{payment_method or 'none'}",
            disabled=True,
        )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="−", style=disnake.ButtonStyle.grey,
                custom_id=f"members_cart_qty_minus:{product_id}:{quantity}:{payment_method or 'none'}",
                disabled=minus_disabled,
            ),
            disnake.ui.Button(
                label=f"{quantity} membros", style=disnake.ButtonStyle.blurple,
                custom_id=f"members_cart_qty_edit:{product_id}:{quantity}:{payment_method or 'none'}",
            ),
            disnake.ui.Button(
                label="+", style=disnake.ButtonStyle.grey,
                custom_id=f"members_cart_qty_plus:{product_id}:{quantity}:{payment_method or 'none'}",
                disabled=plus_disabled,
            ),
        ),
        disnake.ui.ActionRow(
            pay_btn,
            disnake.ui.Button(
                label="Comprar Membros", style=disnake.ButtonStyle.green,
                custom_id=f"members_cart_buy:{product_id}:{quantity}:{payment_method or 'none'}",
                disabled=not can_buy,
            ),
        ),
    ]
    return {"embed": embed, "components": components}


def build_members_panel(product: dict, product_id: str, quantity: int = 1,
                        payment_method: Optional[str] = None) -> dict:
    """Retorna o painel correto (components ou embed) conforme custom_mode."""
    mode = (db.get_document("custom_mode") or {}).get("mode", "components")
    if mode == "embed":
        return _build_members_cart_embed(product, product_id, quantity, payment_method)
    return _build_members_cart_panel(product, product_id, quantity, payment_method)


# ── Modal: editar quantidade manualmente ─────────────────────────────────────

class MembersQtyModal(disnake.ui.Modal):
    def __init__(self, product_id: str, current_qty: int, payment_method: str):
        self.product_id = product_id
        self.payment_method = payment_method if payment_method != "none" else None
        components = [
            disnake.ui.TextInput(
                label="Quantidade de membros",
                custom_id="qty",
                style=disnake.TextInputStyle.short,
                placeholder="Ex: 100",
                value=str(current_qty),
                required=True,
                min_length=1,
                max_length=6,
            )
        ]
        super().__init__(title="Editar Quantidade de Membros", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)

        raw = inter.text_values.get("qty", "").strip()
        try:
            qty = int(raw)
            if qty < 1:
                raise ValueError
        except ValueError:
            await inter.followup.send(f"{emoji.wrong} Quantidade inválida.", ephemeral=True)
            return

        available = get_cloud_available_members(self.product_id)
        if qty > available:
            await inter.followup.send(
                f"{emoji.wrong} Quantidade solicitada (`{qty}`) maior que os membros disponíveis (`{available}`).",
                ephemeral=True,
            )
            return

        products = db.get_document("loja_products") or {}
        product = products.get(self.product_id, {})
        panel = build_members_panel(product, self.product_id, qty, self.payment_method)

        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(
                content=None, **panel,
                flags=disnake.MessageFlags(is_components_v2=True)
            )


# ── Modal: ciclar método de pagamento ────────────────────────────────────────

def _next_payment_method(current: Optional[str]) -> Optional[str]:
    methods = list(get_available_payment_methods().keys())
    if not methods:
        return None
    if current not in methods:
        return methods[0]
    idx = methods.index(current)
    return methods[(idx + 1) % len(methods)]


# ── Cog principal ─────────────────────────────────────────────────────────────

class MembersCartHandlers(commands.Cog):
    """Handles para botões do carrinho de membros."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_members_cart_button(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""

        # ── Abrir carrinho de membros (botão no painel do produto) ────────────
        if custom_id.startswith("buy_members_product:"):
            product_id = custom_id.split(":", 1)[1]
            products = db.get_document("loja_products") or {}
            product = products.get(product_id, {})

            if not product.get("is_members_product"):
                await inter.response.send_message(
                    f"{emoji.wrong} Produto de membros não encontrado.", ephemeral=True
                )
                return

            # Verificar cloud ativo e membros disponíveis
            cloud_config = db.get_document("cloud_data") or {}
            if not cloud_config.get("client_id"):
                await inter.response.send_message(
                    f"{emoji.wrong} O **AmyCloud** precisa estar configurado para vender membros.",
                    ephemeral=True,
                )
                return

            available = get_cloud_available_members(product_id)
            if available < 1:
                await inter.response.send_message(
                    f"{emoji.wrong} Não há membros verificados disponíveis no momento.",
                    ephemeral=True,
                )
                return

            # Pré-selecionar método de pagamento se só tiver um
            methods = get_available_payment_methods()
            default_method = list(methods.keys())[0] if len(methods) == 1 else None

            panel = build_members_panel(product, product_id, quantity=1,
                                        payment_method=default_method)
            mode = (db.get_document("custom_mode") or {}).get("mode", "components")
            if not inter.response.is_done():
                if mode == "embed":
                    await inter.response.send_message(
                        content=None, ephemeral=True, **panel
                    )
                else:
                    await inter.response.send_message(
                        content=None, ephemeral=True,
                        flags=disnake.MessageFlags(is_components_v2=True), **panel
                    )
            return

        # ── Quantidade − ──────────────────────────────────────────────────────
        if custom_id.startswith("members_cart_qty_minus:"):
            parts = custom_id.split(":")
            product_id, qty_str, pay = parts[1], parts[2], parts[3]
            qty = max(1, int(qty_str) - 1)
            payment_method = None if pay == "none" else pay
            await self._update_panel(inter, product_id, qty, payment_method)
            return

        # ── Quantidade + ──────────────────────────────────────────────────────
        if custom_id.startswith("members_cart_qty_plus:"):
            parts = custom_id.split(":")
            product_id, qty_str, pay = parts[1], parts[2], parts[3]
            qty = int(qty_str) + 1
            available = get_cloud_available_members(product_id)
            qty = min(qty, available, 10000)
            payment_method = None if pay == "none" else pay
            await self._update_panel(inter, product_id, qty, payment_method)
            return

        # ── Editar quantidade (abre modal) ────────────────────────────────────
        if custom_id.startswith("members_cart_qty_edit:"):
            parts = custom_id.split(":")
            product_id, qty_str, pay = parts[1], parts[2], parts[3]
            modal = MembersQtyModal(product_id, int(qty_str), pay)
            await inter.response.send_modal(modal)
            return

        # ── Ciclar método de pagamento ────────────────────────────────────────
        if custom_id.startswith("members_cart_pay_method:"):
            parts = custom_id.split(":")
            product_id, qty_str, pay = parts[1], parts[2], parts[3]
            current = None if pay == "none" else pay
            next_method = _next_payment_method(current)
            await self._update_panel(inter, product_id, int(qty_str), next_method)
            return

        # ── Confirmar compra ──────────────────────────────────────────────────
        if custom_id.startswith("members_cart_buy:"):
            parts = custom_id.split(":")
            product_id, qty_str, pay = parts[1], parts[2], parts[3]
            payment_method = None if pay == "none" else pay

            if not inter.response.is_done():
                await inter.response.defer(ephemeral=True)

            await self._process_members_purchase(inter, product_id, int(qty_str), payment_method)
            return

        # ── DM: botão de adicionar bot cloud ao servidor ──────────────────────
        if custom_id.startswith("members_delivery_add_bot:"):
            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            if not bot_id:
                await inter.response.send_message(
                    f"{emoji.wrong} Bot cloud não configurado.", ephemeral=True
                )
                return
            invite_url = (
                f"https://discord.com/api/oauth2/authorize?client_id={bot_id}"
                f"&permissions=8&scope=bot%20applications.commands"
            )
            view = disnake.ui.View()
            view.add_item(disnake.ui.Button(
                label="Adicionar Bot Cloud ao Servidor",
                style=disnake.ButtonStyle.link,
                url=invite_url,
            ))
            await inter.response.send_message(
                f"{emoji.information} Clique abaixo para adicionar o bot cloud ao seu servidor:",
                view=view,
                ephemeral=True,
            )
            return

        # ── DM: botão de puxar membros (abre modal com ID do servidor) ────────
        if custom_id.startswith("members_delivery_pull:"):
            parts = custom_id.split(":")
            # members_delivery_pull:{product_id}:{quantity}:{cart_id}
            product_id = parts[1]
            quantity = int(parts[2])
            cart_id = parts[3]
            modal = MembersPullModal(product_id, quantity, cart_id, self.bot)
            await inter.response.send_modal(modal)
            return

    async def _update_panel(
        self,
        inter: disnake.MessageInteraction,
        product_id: str,
        quantity: int,
        payment_method: Optional[str],
    ):
        if not inter.response.is_done():
            await inter.response.defer()
        products = db.get_document("loja_products") or {}
        product = products.get(product_id, {})
        panel = build_members_panel(product, product_id, quantity, payment_method)
        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(
                content=None, **panel,
                flags=disnake.MessageFlags(is_components_v2=True),
            )

    async def _process_members_purchase(
        self,
        inter: disnake.MessageInteraction,
        product_id: str,
        quantity: int,
        payment_method: Optional[str],
    ):
        """Cria o checkout de membros usando o sistema de carrinho existente."""
        if not payment_method:
            await inter.followup.send(f"{emoji.wrong} Selecione um método de pagamento.", ephemeral=True)
            return

        available = get_cloud_available_members(product_id)
        if available < quantity:
            await inter.followup.send(
                f"{emoji.wrong} Membros insuficientes (disponível: `{available}`).",
                ephemeral=True,
            )
            return

        price_total = calc_members_price(product_id, quantity)
        if price_total <= 0:
            await inter.followup.send(
                f"{emoji.wrong} Preço não configurado para esta quantidade.", ephemeral=True
            )
            return

        # Verificar manutenção e horário
        try:
            from modules.loja.preferences.utils import check_maintenance, check_store_hours
            is_maint, maint_msg = check_maintenance(inter.user.id, inter.guild)
            if is_maint:
                await inter.followup.send(maint_msg or "🔧 Sistema em manutenção.", ephemeral=True)
                return
            is_open, hours_msg = check_store_hours()
            if not is_open:
                await inter.followup.send(hours_msg or "⏰ Loja fora do horário.", ephemeral=True)
                return
        except Exception:
            pass

        # Usar campo virtual "__members__" para identificar no checkout
        from .checkout import create_checkout
        await create_checkout(
            inter=inter,
            product_id=product_id,
            campo_id="__members__",
            quantity=quantity,
            payment_method=payment_method,
            coupon_code=None,
            loading_msg=None,
        )


# ── Modal: puxar membros para um servidor ────────────────────────────────────

class MembersPullModal(disnake.ui.Modal):
    """Modal que o comprador usa para puxar membros para o servidor dele."""

    def __init__(self, product_id: str, quantity: int, cart_id: str, bot):
        self.product_id = product_id
        self.quantity = quantity
        self.cart_id = cart_id
        self.bot = bot

        components = [
            disnake.ui.TextInput(
                label="ID do Servidor de Destino",
                custom_id="guild_id",
                style=disnake.TextInputStyle.short,
                placeholder="Cole o ID numérico do servidor",
                required=True,
                min_length=17,
                max_length=22,
            )
        ]
        super().__init__(title=f"Puxar {quantity} Membros", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)

        guild_id_str = inter.text_values.get("guild_id", "").strip()
        if not guild_id_str.isdigit():
            await inter.followup.send(f"{emoji.wrong} ID de servidor inválido.", ephemeral=True)
            return

        # Chamar API de recuperação de membros
        try:
            from modules.cloud.update_api import start_recover_members
            resp = await start_recover_members(guild_id_str)
            if not resp.get("success"):
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao iniciar entrega: {resp.get('message', 'Erro desconhecido')}",
                    ephemeral=True,
                )
                return

            # Marcar carrinho como entregue
            loja_data = db.get_document("loja_data") or {}
            cart = loja_data.get("carts", {}).get(self.cart_id, {})
            if cart:
                cart["members_pulled"] = True
                cart["members_guild_id"] = guild_id_str
                loja_data["carts"][self.cart_id] = cart
                db.save_document("loja_data", loja_data)

            estimated = resp.get("data", {}).get("estimated_time", "alguns minutos")
            await inter.followup.send(
                f"{emoji.correct} **Entrega iniciada!**\n\n"
                f"Os `{self.quantity}` membros estão sendo adicionados ao servidor `{guild_id_str}`.\n"
                f"Tempo estimado: **{estimated}**\n\n"
                f"Você receberá uma notificação quando a entrega for concluída.",
                ephemeral=True,
            )
        except Exception as e:
            await inter.followup.send(
                f"{emoji.wrong} Erro inesperado: {e}", ephemeral=True
            )


def setup(bot: commands.Bot):
    bot.add_cog(MembersCartHandlers(bot))

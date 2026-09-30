"""
Gerenciador de Gifts: criar, listar, detalhar e deletar.

Ao criar um gift:
  - Estoque NORMAL   → remove 1 item do estoque (o item fica reservado no gift)
  - Estoque INFINITO → pergunta ao admin se o gift deve ser ilimitado (o código
                       pode ser resgatado 1x) ou inútil (sem entrega real).
"""
import string
import random
import time

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from modules.loja.cart.stock_manager import StockManager


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _gerar_codigo() -> str:
    chars = string.ascii_uppercase + string.digits
    raw = "".join(random.choices(chars, k=16))
    return "-".join(raw[i:i+4] for i in range(0, 16, 4))


def _codigo_unico() -> str:
    gifts = db.get_document("gifts_data") or {}
    while True:
        code = _gerar_codigo()
        if code not in gifts:
            return code


def _product_name(product_id: str) -> str:
    p = (db.get_document("loja_products") or {}).get(product_id) or {}
    return p.get("name") or product_id


def _field_name(product_id: str, field_id: str) -> str:
    p = (db.get_document("loja_products") or {}).get(product_id) or {}
    return ((p.get("campos") or {}).get(field_id) or {}).get("name") or field_id


def _ckw():
    primary = (db.get_document("custom_colors") or {}).get("primary")
    return {"accent_colour": disnake.Colour(int(primary.replace("#", ""), 16))} if primary else {}


def _ekw():
    primary = (db.get_document("custom_colors") or {}).get("primary")
    return {"color": int(primary.replace("#", ""), 16)} if primary else {}


# ─── Modais ───────────────────────────────────────────────────────────────────

class CriarGiftModal(disnake.ui.Modal):
    """Modal pedindo quantidade + observação."""
    def __init__(self, product_id: str, field_id: str, is_infinite: bool):
        self.product_id  = product_id
        self.field_id    = field_id
        self.is_infinite = is_infinite
        super().__init__(
            title="Criar Gifts",
            custom_id=f"GiftMgr_CriarModal:{product_id}:{field_id}",
            components=[
                disnake.ui.TextInput(
                    label="Quantidade de gifts",
                    custom_id="quantidade",
                    style=disnake.TextInputStyle.short,
                    placeholder="Máx. 500 por vez" + (" (estoque infinito)" if is_infinite else ""),
                    required=True, max_length=3, value="1",
                ),
                disnake.ui.TextInput(
                    label="Observação (opcional)",
                    custom_id="observacao",
                    style=disnake.TextInputStyle.short,
                    placeholder="Ex: Promoção de Natal",
                    required=False, max_length=100,
                ),
            ],
        )


# ─── GiftManager (painéis estáticos) ─────────────────────────────────────────

class GiftManager:

    # ── Criar ─────────────────────────────────────────────────────────────────

    @staticmethod
    def painel_criar(inter) -> dict:
        """Seleciona o produto."""
        products = db.get_document("loja_products") or {}
        options = [
            disnake.SelectOption(label=(p.get("name") or pid)[:100], value=pid, emoji=emoji.cardbox)
            for pid, p in products.items() if p.get("campos")
        ]
        disabled = not options
        if disabled:
            options = [disnake.SelectOption(label="Nenhum produto disponível", value="none")]

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return {
                "embed": disnake.Embed(description="-# Criar Gift > **Selecione o produto**", **_ekw()),
                "components": [
                    disnake.ui.ActionRow(disnake.ui.StringSelect(placeholder="Selecione o produto", custom_id="GiftMgr_SelecionarProduto", options=options, disabled=disabled)),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
                ],
            }
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Criar Gift > **Selecione o produto**"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(disnake.ui.StringSelect(placeholder="Selecione o produto", custom_id="GiftMgr_SelecionarProduto", options=options, disabled=disabled)),
                **_ckw(),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
        ]}

    @staticmethod
    def painel_selecionar_campo(inter, product_id: str) -> dict:
        """Seleciona o campo do produto."""
        products   = db.get_document("loja_products") or {}
        campos     = (products.get(product_id) or {}).get("campos") or {}
        pname      = _product_name(product_id)

        options = []
        for fid, f in campos.items():
            stock = StockManager.get_available_stock(product_id, fid)
            is_inf = (f.get("infinite_stock") or {}).get("enabled", False)
            stock_str = "∞ Infinito" if is_inf else str(stock)
            options.append(disnake.SelectOption(
                label=(f.get("name") or fid)[:100], value=fid, emoji=emoji.commands,
                description=f"Estoque: {stock_str}",
            ))

        disabled = not options
        if disabled:
            options = [disnake.SelectOption(label="Nenhum campo disponível", value="none")]

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return {
                "embed": disnake.Embed(description=f"-# Criar Gift > **{pname}** > Selecione o campo", **_ekw()),
                "components": [
                    disnake.ui.ActionRow(disnake.ui.StringSelect(placeholder="Selecione o campo", custom_id=f"GiftMgr_SelecionarCampo:{product_id}", options=options, disabled=disabled)),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_CriarGift")),
                ],
            }
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Criar Gift > **{pname}**"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(disnake.ui.StringSelect(placeholder="Selecione o campo", custom_id=f"GiftMgr_SelecionarCampo:{product_id}", options=options, disabled=disabled)),
                **_ckw(),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_CriarGift")),
        ]}

    @staticmethod
    def painel_confirmar_infinito(inter, product_id: str, field_id: str) -> dict:
        """
        Quando o campo tem estoque infinito, pergunta ao admin se o gift
        deve entregar o item ou ser inútil (dummy).
        """
        pname = _product_name(product_id)
        fname = _field_name(product_id, field_id)

        desc = (
            f"-# Criar Gift > **{pname}** > **{fname}**\n\n"
            f"O campo selecionado possui **estoque infinito**.\n\n"
            f"Escolha o comportamento do gift:\n"
            f"**Entregar item** — ao resgatar, o usuário recebe o valor configurado no estoque infinito.\n"
            f"**Inútil (dummy)** — o código pode ser resgatado mas nada é entregue. Útil para testes."
        )
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return {
                "embed": disnake.Embed(description=desc, **_ekw()),
                "components": [
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Entregar item",  style=disnake.ButtonStyle.green,     custom_id=f"GiftMgr_ConfInfinito:entregar:{product_id}:{field_id}"),
                        disnake.ui.Button(label="Inútil (dummy)", style=disnake.ButtonStyle.secondary, custom_id=f"GiftMgr_ConfInfinito:dummy:{product_id}:{field_id}"),
                    ),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiftMgr_VoltarCampo:{product_id}")),
                ],
            }
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Criar Gift > **{pname}** > **{fname}**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(desc),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Entregar item",  style=disnake.ButtonStyle.green,     custom_id=f"GiftMgr_ConfInfinito:entregar:{product_id}:{field_id}"),
                    disnake.ui.Button(label="Inútil (dummy)", style=disnake.ButtonStyle.secondary, custom_id=f"GiftMgr_ConfInfinito:dummy:{product_id}:{field_id}"),
                ),
                **_ckw(),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiftMgr_VoltarCampo:{product_id}")),
        ]}

    # ── Listar ────────────────────────────────────────────────────────────────

    @staticmethod
    def painel_listar(inter, page: int = 0) -> dict:
        gifts     = db.get_document("gifts_data") or {}
        gift_list = sorted(gifts.items(), key=lambda x: x[1].get("created_at", 0), reverse=True)

        PER_PAGE    = 10
        total       = len(gift_list)
        total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page        = max(0, min(page, total_pages - 1))
        slice_      = gift_list[page * PER_PAGE:(page + 1) * PER_PAGE]

        redeemed_count = sum(1 for g in gifts.values() if g.get("redeemed"))
        active_count   = total - redeemed_count

        options = []
        for code, g in slice_:
            status = f"{emoji.gift2}" if g.get("redeemed") else f"{emoji.gift}"
            pname  = _product_name(g.get("product_id", ""))[:35]
            fname  = _field_name(g.get("product_id", ""), g.get("field_id", ""))[:25]
            dtype  = " [dummy]" if g.get("dummy") else ""
            options.append(disnake.SelectOption(
                label=code, value=code,
                description=f"{status} {pname} > {fname}{dtype}"[:100],
            ))
        if not options:
            options = [disnake.SelectOption(label="Nenhum gift encontrado", value="none")]

        has_redeemed = redeemed_count > 0
        nav_row = disnake.ui.ActionRow(
            disnake.ui.Button(label="◀", style=disnake.ButtonStyle.secondary, custom_id=f"GiftMgr_Pag:{page-1}", disabled=page == 0),
            disnake.ui.Button(label=f"{page+1}/{total_pages}", style=disnake.ButtonStyle.secondary, custom_id="GiftMgr_PagInfo", disabled=True),
            disnake.ui.Button(label="▶", style=disnake.ButtonStyle.secondary, custom_id=f"GiftMgr_Pag:{page+1}", disabled=page >= total_pages - 1),
        )
        summary = f"-# Total: `{total}` | Ativos: `{active_count}` | Resgatados: `{redeemed_count}`"

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return {
                "embed": disnake.Embed(description=f"-# Painel > Loja > Gifts > **Gerenciar**\n\n{summary}", **_ekw()),
                "components": [
                    disnake.ui.ActionRow(disnake.ui.StringSelect(placeholder="Selecione um gift", custom_id="GiftMgr_SelecionarGift", options=options, disabled=options[0].value == "none")),
                    nav_row,
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Apagar Resgatados", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="GiftMgr_ApagarResgatados", disabled=not has_redeemed),
                        disnake.ui.Button(label="Apagar Todos",       style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="GiftMgr_ApagarTodos",       disabled=total == 0),
                    ),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
                ],
            }
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Gifts > **Gerenciar**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(summary),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(disnake.ui.StringSelect(placeholder="Selecione um gift", custom_id="GiftMgr_SelecionarGift", options=options, disabled=options[0].value == "none")),
                nav_row,
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Apagar Resgatados", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="GiftMgr_ApagarResgatados", disabled=not has_redeemed),
                    disnake.ui.Button(label="Apagar Todos",       style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="GiftMgr_ApagarTodos",       disabled=total == 0),
                ),
                **_ckw(),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_VoltarPainel")),
        ]}

    # ── Detalhe ───────────────────────────────────────────────────────────────

    @staticmethod
    def painel_detalhe(inter, code: str) -> dict:
        gifts = db.get_document("gifts_data") or {}
        g = gifts.get(code)
        if not g:
            return GiftManager.painel_listar(inter)

        pname       = _product_name(g.get("product_id", ""))
        fname       = _field_name(g.get("product_id", ""), g.get("field_id", ""))
        status      = f"{emoji.gift2} Resgatado" if g.get("redeemed") else f"{emoji.gift} Ativo"
        dummy_txt   = "\n-# Tipo: `Inútil (dummy)`" if g.get("dummy") else ""
        redeemed_by = f"<@{g['redeemed_by']}>" if g.get("redeemed_by") else "`Ninguém`"
        obs         = g.get("observacao") or "`Sem observação`"
        ts = lambda v: f"<t:{int(v)}:f>" if v else "`—`"

        info = (
            f"**Código:** `{code}`\n"
            f"**Status:** {status}{dummy_txt}\n"
            f"**Produto:** `{pname}` > `{fname}`\n"
            f"**Observação:** {obs}\n"
            f"**Criado em:** {ts(g.get('created_at'))}\n"
            f"**Resgatado em:** {ts(g.get('redeemed_at'))}\n"
            f"**Resgatado por:** {redeemed_by}"
        )

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return {
                "embed": disnake.Embed(description=f"-# Gerenciar > **{code}**\n\n{info}", **_ekw()),
                "components": [
                    disnake.ui.ActionRow(disnake.ui.Button(label="Apagar Gift", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"GiftMgr_ApagarGift:{code}")),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_Gerenciar")),
                ],
            }
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gifts > **{code}**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(info),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(disnake.ui.Button(label="Apagar Gift", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"GiftMgr_ApagarGift:{code}")),
                **_ckw(),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Gifts_Gerenciar")),
        ]}

    # ── Criar gifts na DB ─────────────────────────────────────────────────────

    @staticmethod
    def criar_gifts(product_id: str, field_id: str, quantidade: int, observacao: str, dummy: bool = False) -> list[str]:
        """
        Cria N gifts. Para estoque normal remove N itens do estoque agora.
        Para infinito, `dummy` define se entrega ou não.
        Retorna os códigos gerados.
        """
        # Verificar se é infinito
        products = db.get_document("loja_products") or {}
        campo = ((products.get(product_id) or {}).get("campos") or {}).get(field_id) or {}
        is_infinite = (campo.get("infinite_stock") or {}).get("enabled", False)

        reserved_items: list[str] = []
        if not is_infinite:
            # Reservar itens do estoque
            available = StockManager.get_available_stock(product_id, field_id)
            if available < quantidade:
                raise ValueError(f"Estoque insuficiente. Disponível: {available}, solicitado: {quantidade}")
            reserved_items = StockManager.get_stock_items(product_id, field_id, quantidade) or []
            if len(reserved_items) < quantidade:
                raise ValueError("Não foi possível reservar todos os itens do estoque.")

        gifts = db.get_document("gifts_data") or {}
        now   = int(time.time())
        codes = []

        for i in range(quantidade):
            code = _codigo_unico()
            gift_data = {
                "product_id":  product_id,
                "field_id":    field_id,
                "observacao":  observacao or None,
                "dummy":       dummy if is_infinite else False,
                "redeemed":    False,
                "redeemed_by": None,
                "redeemed_at": None,
                "created_at":  now,
            }
            # Para estoque normal: guarda o item reservado no gift
            if not is_infinite and i < len(reserved_items):
                gift_data["reserved_item"] = reserved_items[i]
            gifts[code] = gift_data
            codes.append(code)
            # Garante unicidade na próxima iteração
            db.save_document("gifts_data", {}, gifts)

        return codes


# ─── Cog ─────────────────────────────────────────────────────────────────────

class GiftManagerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _nav(self, inter: disnake.MessageInteraction, panel_data: dict):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if "embed" in panel_data:
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("GiftMgr_"):
            return

        if cid.startswith("GiftMgr_Pag:"):
            page = int(cid.split(":")[1])
            await self._nav(inter, GiftManager.painel_listar(inter, page=page))

        elif cid.startswith("GiftMgr_ApagarGift:"):
            code = cid.split(":", 1)[1]
            gifts = db.get_document("gifts_data") or {}
            g = gifts.pop(code, None)
            # Se o gift tinha item reservado e ainda não foi resgatado, devolver ao estoque
            if g and not g.get("redeemed") and g.get("reserved_item"):
                StockManager.add_stock_items(g["product_id"], g["field_id"], [g["reserved_item"]])
            db.save_document("gifts_data", {}, gifts)
            await self._nav(inter, GiftManager.painel_listar(inter))

        elif cid == "GiftMgr_ApagarResgatados":
            gifts = db.get_document("gifts_data") or {}
            gifts = {k: v for k, v in gifts.items() if not v.get("redeemed")}
            db.save_document("gifts_data", {}, gifts)
            await self._nav(inter, GiftManager.painel_listar(inter))

        elif cid == "GiftMgr_ApagarTodos":
            # Devolver itens reservados não resgatados
            gifts = db.get_document("gifts_data") or {}
            for g in gifts.values():
                if not g.get("redeemed") and g.get("reserved_item"):
                    StockManager.add_stock_items(g["product_id"], g["field_id"], [g["reserved_item"]])
            db.save_document("gifts_data", {}, {})
            await self._nav(inter, GiftManager.painel_listar(inter))

        elif cid.startswith("GiftMgr_ConfInfinito:"):
            # GiftMgr_ConfInfinito:entregar|dummy:product_id:field_id
            parts      = cid.split(":")
            choice     = parts[1]        # "entregar" ou "dummy"
            product_id = parts[2]
            field_id   = parts[3]
            dummy      = (choice == "dummy")
            await inter.response.send_modal(CriarGiftModal(product_id, field_id, is_infinite=True))
            # Guardar escolha dummy em memória temporária usando o custom_id do modal
            # (resolvido no modal_submit via flag no modal custom_id)
            # Recriar modal com info dummy embutida no custom_id
            # — na verdade enviamos modal com dummy no custom_id:
            class _DummyModal(CriarGiftModal):
                pass
            modal = CriarGiftModal(product_id, field_id, is_infinite=True)
            modal.custom_id = f"GiftMgr_CriarModal:{product_id}:{field_id}:{'dummy' if dummy else 'entregar'}"
            await inter.response.send_modal(modal)

        elif cid.startswith("GiftMgr_VoltarCampo:"):
            product_id = cid.split(":")[1]
            await self._nav(inter, GiftManager.painel_selecionar_campo(inter, product_id))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("GiftMgr_"):
            return

        if cid == "GiftMgr_SelecionarProduto":
            product_id = inter.values[0]
            if product_id == "none":
                return
            await self._nav(inter, GiftManager.painel_selecionar_campo(inter, product_id))

        elif cid.startswith("GiftMgr_SelecionarCampo:"):
            product_id = cid.split(":")[1]
            field_id   = inter.values[0]
            if field_id == "none":
                return
            # Verificar se campo é infinito
            products = db.get_document("loja_products") or {}
            campo    = ((products.get(product_id) or {}).get("campos") or {}).get(field_id) or {}
            is_inf   = (campo.get("infinite_stock") or {}).get("enabled", False)
            if is_inf:
                await self._nav(inter, GiftManager.painel_confirmar_infinito(inter, product_id, field_id))
            else:
                await inter.response.send_modal(CriarGiftModal(product_id, field_id, is_infinite=False))

        elif cid == "GiftMgr_SelecionarGift":
            code = inter.values[0]
            if code == "none":
                return
            await self._nav(inter, GiftManager.painel_detalhe(inter, code))

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("GiftMgr_CriarModal:"):
            return

        # custom_id = GiftMgr_CriarModal:product_id:field_id[:dummy|entregar]
        parts      = cid.split(":")
        product_id = parts[1]
        field_id   = parts[2]
        dummy      = len(parts) > 3 and parts[3] == "dummy"

        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message

        try:
            quantidade = int(inter.text_values.get("quantidade", "1").strip())
            if not (1 <= quantidade <= 500):
                raise ValueError
        except (ValueError, TypeError):
            await inter.response.defer(ephemeral=True)
            await inter.followup.send(f"{emoji.warn} Quantidade inválida. Use entre 1 e 500.", ephemeral=True)
            return

        obs = inter.text_values.get("observacao", "").strip()

        try:
            codes = GiftManager.criar_gifts(product_id, field_id, quantidade, obs, dummy=dummy)
        except ValueError as e:
            await inter.response.defer(ephemeral=True)
            await inter.followup.send(f"{emoji.wrong} {e}", ephemeral=True)
            return

        await msg_handler.wait(inter, send=False)

        pname = _product_name(product_id)
        fname = _field_name(product_id, field_id)
        codes_txt = "\n".join(f"`{c}`" for c in codes[:25])
        if len(codes) > 25:
            codes_txt += f"\n-# ... e mais `{len(codes) - 25}` código(s)"
        dummy_txt = "\n-# Tipo: `Inútil (dummy)`" if dummy else ""

        if mode == "embed":
            embed = disnake.Embed(
                description=(
                    f"✅ **{len(codes)} gift(s) criado(s)**{dummy_txt}\n"
                    f"-# Produto: **{pname}** > **{fname}**\n\n{codes_txt}"
                ),
                **_ekw(),
            )
            await inter.edit_original_message(content=None, embed=embed, components=[
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Gerenciar Gifts", style=disnake.ButtonStyle.secondary, emoji=emoji.edit,  custom_id="Gifts_Gerenciar"),
                    disnake.ui.Button(label="Voltar ao Painel", style=disnake.ButtonStyle.grey,      emoji=emoji.back, custom_id="Gifts_VoltarPainel"),
                ),
            ])
        else:
            await inter.edit_original_message(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gifts criados com sucesso!"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"✅ **{len(codes)} gift(s) criado(s)**{dummy_txt}\n"
                            f"-# Produto: **{pname}** > **{fname}**"
                        ),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.TextDisplay(codes_txt),
                        **_ckw(),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Gerenciar Gifts", style=disnake.ButtonStyle.secondary, emoji=emoji.edit,  custom_id="Gifts_Gerenciar"),
                        disnake.ui.Button(label="Voltar ao Painel", style=disnake.ButtonStyle.grey,      emoji=emoji.back, custom_id="Gifts_VoltarPainel"),
                    ),
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )


def setup(bot: commands.Bot):
    bot.add_cog(GiftManagerCog(bot))
"""
roblox_auto_delivery.py
-----------------------
Cliente assíncrono para a API de entrega automática de Robux.
Usado por delivery_robux.py quando a extensão roblox_auto está ativa e configurada.

Endpoints da API:
  POST /login            → autentica o cookie
  GET  /balance          → saldo da conta
  POST /group/funds      → distribui Robux via Group Funds
  POST /item/buy         → compra uma Gamepass
  GET  /calculator       → calculadora de preços (não usado aqui, mas disponível)
"""

from __future__ import annotations

import aiohttp
from functions.database import database as db

_API_BASE = "http://127.0.0.1:5000"
_TIMEOUT  = aiohttp.ClientTimeout(total=20)


def _get_cookie() -> str | None:
    cfg = db.get_document("roblox_auto_config") or {}
    return cfg.get("cookie") or None


def is_auto_delivery_active() -> bool:
    """True se a extensão foi comprada E está habilitada E tem cookie configurado."""
    from modules.settings.extensions.subscription_manager import is_extension_active
    if not is_extension_active("roblox_auto"):
        return False
    cfg = db.get_document("roblox_auto_config") or {}
    if not cfg.get("enabled", True):
        return False
    return bool(cfg.get("cookie"))


class RobloxAutoClient:
    """
    Wrapper assíncrono sobre a API de entrega.
    Cada chamada abre e fecha sua própria sessão aiohttp para ser safe em contextos de task.
    """

    def __init__(self, cookie: str | None = None):
        self.cookie = cookie or _get_cookie()

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.cookie}"}

    # ── Autenticação ──────────────────────────────────────────────────────────

    async def login(self) -> tuple[bool, str]:
        """
        Testa o cookie contra POST /login.
        Retorna (True, "") em caso de sucesso ou (False, mensagem_de_erro).
        """
        if not self.cookie:
            return False, "Cookie não configurado"
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
                async with session.post(
                    f"{_API_BASE}/login",
                    json={"cookie": self.cookie},
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("success", True) is not False:
                        return True, ""
                    return False, data.get("message", data.get("error", f"HTTP {resp.status}"))
        except Exception as e:
            return False, str(e)

    # ── Saldo ─────────────────────────────────────────────────────────────────

    async def get_balance(self) -> tuple[int | None, str]:
        """
        Retorna (saldo_em_robux, "") ou (None, mensagem_de_erro).
        """
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
                async with session.get(
                    f"{_API_BASE}/balance",
                    headers=self._auth_headers(),
                ) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        balance = data.get("balance") or data.get("robux") or data.get("data", {}).get("balance")
                        return int(balance), ""
                    return None, data.get("message", f"HTTP {resp.status}")
        except Exception as e:
            return None, str(e)

    # ── Entrega via Group Funds ───────────────────────────────────────────────

    async def distribute_group_funds(
        self,
        group_id: int,
        roblox_user_id: int,
        amount: int,
    ) -> tuple[bool, str]:
        """
        Distribui `amount` Robux para `roblox_user_id` via Group Funds do `group_id`.
        Retorna (True, "") ou (False, mensagem_de_erro).
        """
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
                async with session.post(
                    f"{_API_BASE}/group/funds",
                    headers={**self._auth_headers(), "Content-Type": "application/json"},
                    json={
                        "group_id": group_id,
                        "user_id": roblox_user_id,
                        "amount": amount,
                    },
                ) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("success", True) is not False:
                        return True, ""
                    return False, data.get("message", data.get("error", f"HTTP {resp.status}"))
        except Exception as e:
            return False, str(e)

    # ── Compra de Gamepass ────────────────────────────────────────────────────

    async def buy_gamepass(
        self,
        gamepass_id: int,
        price: int,
    ) -> tuple[bool, str]:
        """
        Compra a Gamepass de ID `gamepass_id` pelo preço `price` (em Robux).
        Retorna (True, "") ou (False, mensagem_de_erro).
        """
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
                async with session.post(
                    f"{_API_BASE}/item/buy",
                    headers={**self._auth_headers(), "Content-Type": "application/json"},
                    json={
                        "item_type": "gamepass",
                        "item_id": gamepass_id,
                        "price": price,
                    },
                ) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("success", True) is not False:
                        return True, ""
                    return False, data.get("message", data.get("error", f"HTTP {resp.status}"))
        except Exception as e:
            return False, str(e)


# ── Função de alto nível usada pelo delivery_robux.py ────────────────────────

async def tentar_entrega_automatica(order: dict) -> tuple[bool, str]:
    """
    Tenta realizar a entrega automaticamente com base no tipo do pedido e no
    método de entrega configurado.

    Retorna:
        (True, "")                → entregue com sucesso
        (False, motivo)           → falhou — o sistema deve continuar no modo manual
    """
    if not is_auto_delivery_active():
        return False, "Entrega automática não está ativa"

    from .config import get_roblox_config
    config     = get_roblox_config()
    order_type = order.get("order_type", "robux")
    extra      = order.get("extra", {})

    client = RobloxAutoClient()

    # ── Gamepass: compra a gamepass criada pelo comprador ─────────────────────
    if order_type == "gamepass":
        gamepass_id  = extra.get("gamepass_id")
        robux_bruto  = order.get("robux_bruto", 0)

        if not gamepass_id:
            return False, "ID da Gamepass não informado no pedido"

        ok, err = await client.buy_gamepass(
            gamepass_id=int(gamepass_id),
            price=int(robux_bruto),
        )
        if not ok:
            return False, f"Falha ao comprar Gamepass: {err}"
        return True, ""

    # ── Robux via Group Funds ─────────────────────────────────────────────────
    delivery_method = config.get("delivery_method", "gamepass")
    if delivery_method == "group":
        group_id       = config.get("group_id")
        roblox_user_id = order.get("roblox_user_id", 0)
        quantity       = order.get("quantity", 0)  # robux líquidos que o comprador deve receber

        if not group_id:
            return False, "Group ID não configurado"
        if not roblox_user_id:
            return False, "roblox_user_id não encontrado no pedido"

        ok, err = await client.distribute_group_funds(
            group_id=int(group_id),
            roblox_user_id=int(roblox_user_id),
            amount=int(quantity),
        )
        if not ok:
            return False, f"Falha ao distribuir Group Funds: {err}"
        return True, ""

    # Método gamepass para pedido de tipo robux: não aplicável automaticamente
    return False, "Método de entrega 'gamepass' para pedido Robux requer ação manual"

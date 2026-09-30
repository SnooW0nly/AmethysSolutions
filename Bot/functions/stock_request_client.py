"""
functions/stock_request_client.py
───────────────────────────────────
Client-side do sistema de estoque cross-bot via API da plataforma.

Usado pelo bot revendedor para pedir itens do estoque do bot dono.
A API valida o botToken, acessa o MongoDB do bot dono e retorna os itens.
"""
import requests as _requests
from functions.database import database as db


def request_stock_items(
    owner_bot_id: str,
    product_id: str,
    campo_id: str,
    quantity: int,
) -> list | None:
    """
    Solicita itens do estoque do bot dono via API da plataforma.

    POST {apiURL}/api/bot/{botID}/stock/request
    Headers: authorization: <botToken>
    Body: { owner_bot_id, product_id, campo_id, quantity }

    Retorna lista de itens ou None se sem estoque / erro.
    """
    config = db.obter("config.json")
    api_url   = config.get("apiURL", "").rstrip("/")
    bot_id    = config.get("botID")
    bot_token = config.get("botToken")

    if not api_url or not bot_id or not bot_token:
        print("[StockRequestClient] apiURL/botID/botToken não configurados")
        return None

    url = f"{api_url}/api/bot/{bot_id}/stock/request"
    headers = {
        "authorization": bot_token,
        "content-type": "application/json",
    }
    body = {
        "owner_bot_id": owner_bot_id,
        "product_id":   product_id,
        "campo_id":     campo_id,
        "quantity":     quantity,
    }

    try:
        resp = _requests.post(url, json=body, headers=headers, timeout=15)
    except Exception as e:
        print(f"[StockRequestClient] Erro de conexão: {e}")
        return None

    print(f"[StockRequestClient] Resposta da API: {resp.status_code} → {resp.text[:300]}")

    if resp.status_code == 200:
        return resp.json().get("items")

    if resp.status_code == 409:
        print(f"[StockRequestClient] Estoque insuficiente no bot '{owner_bot_id}'")
        return None

    print(f"[StockRequestClient] Erro {resp.status_code}: {resp.text[:200]}")
    return None
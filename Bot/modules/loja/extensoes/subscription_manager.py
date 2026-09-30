import aiohttp
import json
import uuid
from datetime import datetime
from functions.database import database as db

MISTIC_PAY_API = "https://api.misticpay.com/api"
MISTIC_CLIENT_ID = "ci_q3qwzpofc7304a9"
MISTIC_CLIENT_SECRET = "cs_olqkn1hshs73yquk8tze1xtku"

PURCHASABLE_EXTENSIONS = {
    "boost": {
        "name": "Sync Boost",
        "price": 50.00,
        "description": "Sistema de venda de boosts para servidores"
    },
    "nitrada": {
        "name": "Nitrada Automática",
        "price": 70.00,
        "description": "Sistema automatizado de ativação de Nitro"
    },
    "roblox_auto": {
        "name": "Entrega Automática de Robux",
        "price": 40.00,
        "description": "Entrega automática de Robux e Gamepass via cookie Roblox"
    },
}

def _get_db_path(extension_id: str = None) -> str:
    if extension_id == "boost":
        return "database/extensions/syncboost/subscriptions.json"
    if extension_id == "nitrada":
        return "database/extensions/nitrada/subscriptions.json"
    if extension_id == "roblox_auto":
        return "database/extensions/roblox_auto/subscriptions.json"
    return "database/extensions/subscriptions.json"

def _mistic_headers() -> dict:
    """Retorna os headers de autenticação corretos da MisticPay (ci/cs)."""
    return {
        "ci": MISTIC_CLIENT_ID,
        "cs": MISTIC_CLIENT_SECRET,
        "Content-Type": "application/json"
    }

def get_subscriptions(extension_id: str = None) -> dict:
    return db.obter(_get_db_path(extension_id))

def save_subscriptions(data: dict, extension_id: str = None):
    db.salvar(_get_db_path(extension_id), data)

def get_extension_subscription(extension_id: str) -> dict:
    subs = get_subscriptions(extension_id)
    return subs.get(extension_id, {})

def is_extension_active(extension_id: str) -> bool:
    sub = get_extension_subscription(extension_id)
    if not sub:
        return False
    return sub.get("active", False)

def get_expiry_date(extension_id: str) -> str:
    sub = get_extension_subscription(extension_id)
    if not sub:
        return None
    return "Permanente"

def get_days_remaining(extension_id: str) -> int:
    sub = get_extension_subscription(extension_id)
    if not sub:
        return 0
    return 9999

def activate_extension(extension_id: str, payment_id: str):
    subs = get_subscriptions(extension_id)
    now = datetime.now()

    subs[extension_id] = {
        "active": True,
        "permanent": True,
        "activated_at": now.isoformat(),
        "payment_id": payment_id,
        "payments": subs.get(extension_id, {}).get("payments", []) + [payment_id]
    }

    save_subscriptions(subs, extension_id)

    config = db.obter("configs/config_extensions.json")
    config[extension_id] = True
    db.salvar("configs/config_extensions.json", config)

    return "Permanente"

async def create_payment(extension_id: str, user_id: str, payer_name: str, payer_document: str) -> dict:
    """
    Cria uma transação PIX na MisticPay.

    Parâmetros obrigatórios pela API:
        - amount
        - payerName
        - payerDocument (CPF sem formatação)
        - transactionId (ID único da sua aplicação)
        - description
    """
    extension = PURCHASABLE_EXTENSIONS.get(extension_id)
    if not extension:
        return {"success": False, "error": "Extensão não encontrada"}

    try:
        async with aiohttp.ClientSession() as session:
            transaction_id = f"{extension_id}-{user_id}-{uuid.uuid4().hex[:8]}"

            payload = {
                "amount": extension["price"],
                "payerName": payer_name,
                "payerDocument": payer_document,
                "transactionId": transaction_id,
                "description": f"Compra Permanente {extension['name']}"
            }

            async with session.post(
                f"{MISTIC_PAY_API}/transactions/create",
                headers=_mistic_headers(),
                json=payload
            ) as response:
                data = await response.json()

                # A MisticPay retorna os dados em data["data"]
                payment_data = data.get("data", {})

                if payment_data.get("transactionId"):
                    pending = db.obter("database/extensions/pending_payments.json")
                    pending[payment_data["transactionId"]] = {
                        "extension_id": extension_id,
                        "user_id": user_id,
                        "value": extension["price"],
                        "created_at": datetime.now().isoformat(),
                        "status": "PENDENTE"
                    }
                    db.salvar("database/extensions/pending_payments.json", pending)

                    return {
                        "success": True,
                        "payment_id": payment_data["transactionId"],
                        "qrcode_url": payment_data.get("qrcodeUrl"),
                        "qrcode_base64": payment_data.get("qrCodeBase64"),
                        "copy_paste": payment_data.get("copyPaste"),
                        "value": extension["price"]
                    }
                else:
                    return {"success": False, "error": data.get("message", "Erro ao criar pagamento")}

    except Exception as e:
        return {"success": False, "error": str(e)}

def get_payment_history() -> dict:
    return db.obter("database/extensions/payment_history.json")

def save_payment_history(data: dict):
    db.salvar("database/extensions/payment_history.json", data)

def get_user_payments(user_id: str) -> dict:
    pending = db.obter("database/extensions/pending_payments.json")
    history = get_payment_history()

    user_pending = []
    for p_id, p in pending.items():
        if p.get("user_id") == user_id:
            p["id"] = p_id
            user_pending.append(p)

    user_history = []
    for h_id, h in history.items():
        if h.get("user_id") == user_id:
            h["id"] = h_id
            user_history.append(h)

    user_pending.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    user_history.sort(key=lambda x: x.get("completed_at", ""), reverse=True)

    return {"pending": user_pending, "history": user_history}

async def check_payment(payment_id: str) -> dict:
    """
    Verifica o status de uma transação na MisticPay.
    Endpoint: GET /api/transactions/{transactionId}
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MISTIC_PAY_API}/transactions/{payment_id}",
                headers=_mistic_headers()
            ) as response:
                data = await response.json()
                payment_data = data.get("data", {})

                if not payment_data:
                    return {"success": False, "error": data.get("message", "Erro ao verificar pagamento")}

                # O status da MisticPay é em português: PENDENTE, CONCLUIDA, CANCELADA
                status = payment_data.get("transactionState", "PENDENTE")

                if status == "CONCLUIDA":
                    pending = db.obter("database/extensions/pending_payments.json")
                    if payment_id in pending:
                        payment_info = pending[payment_id]
                        extension_id = payment_info["extension_id"]
                        activate_extension(extension_id, payment_id)

                        history = get_payment_history()
                        payment_info["status"] = "CONCLUIDA"
                        payment_info["completed_at"] = datetime.now().isoformat()
                        payment_info["expires_at"] = "Permanente"
                        history[payment_id] = payment_info
                        save_payment_history(history)

                        del pending[payment_id]
                        db.salvar("database/extensions/pending_payments.json", pending)

                        return {
                            "success": True,
                            "status": "CONCLUIDA",
                            "extension_id": extension_id,
                            "expires_at": "Permanente"
                        }

                return {"success": True, "status": status}

    except Exception as e:
        return {"success": False, "error": str(e)}

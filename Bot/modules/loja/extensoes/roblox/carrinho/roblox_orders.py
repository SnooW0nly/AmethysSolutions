import random
import string
import disnake
from typing import Optional, Dict, Any
from functions.database import database as db


DB_KEY = "roblox_orders"


def _load_orders() -> dict:
    data = db.get_document(DB_KEY) or {}
    if "orders" not in data:
        data["orders"] = {}
    return data


def _save_orders(data: dict):
    db.save_document(DB_KEY, data)


def generate_order_id(length: int = 10) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def create_order(
    user_id: int,
    guild_id: int,
    order_type: str,
    roblox_username: str,
    roblox_user_id: int,
    quantity: int,
    robux_bruto: int,
    total_price: float,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    data = _load_orders()
    order_id = generate_order_id()
    while order_id in data["orders"]:
        order_id = generate_order_id()

    now_ts = int(disnake.utils.utcnow().timestamp())
    order = {
        "order_id": order_id,
        "user_id": user_id,
        "guild_id": guild_id,
        "order_type": order_type,
        "roblox_username": roblox_username,
        "roblox_user_id": roblox_user_id,
        "quantity": quantity,
        "robux_bruto": robux_bruto,
        "total_price": total_price,
        "status": "pending_payment",
        "payment_data": {},
        "thread_channel_id": None,
        "created_at": now_ts,
        "updated_at": now_ts,
        "extra": extra or {},
    }
    data["orders"][order_id] = order
    _save_orders(data)
    return order_id


def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    data = _load_orders()
    return data["orders"].get(order_id)


def update_order(order_id: str, updates: Dict[str, Any]):
    data = _load_orders()
    if order_id not in data["orders"]:
        return
    now_ts = int(disnake.utils.utcnow().timestamp())
    data["orders"][order_id].update(updates)
    data["orders"][order_id]["updated_at"] = now_ts
    _save_orders(data)


def get_order_by_thread(thread_channel_id: int) -> Optional[Dict[str, Any]]:
    data = _load_orders()
    for order in data["orders"].values():
        if order.get("thread_channel_id") == thread_channel_id:
            return order
    return None


def get_user_active_order(user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
    data = _load_orders()
    for order in data["orders"].values():
        if (
            str(order.get("user_id")) == str(user_id)
            and str(order.get("guild_id")) == str(guild_id)
            and order.get("status") in ("pending_payment", "payment_approved", "pending_delivery")
        ):
            return order
    return None


def delete_order(order_id: str):
    data = _load_orders()
    if order_id in data["orders"]:
        del data["orders"][order_id]
        _save_orders(data)
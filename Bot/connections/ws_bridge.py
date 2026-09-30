"""
ws_bridge.py
============
Marketplace WS connection disabled.
All functions are no-ops kept for import compatibility.
"""

import logging

logger = logging.getLogger(__name__)


def get_ws_client():
    return None


def setup(bot) -> None:
    logger.info("[WSBridge] Marketplace desabilitado — nenhuma conexão iniciada")


async def start(bot) -> None:
    pass


async def push_payment_created(cart_id: str, payment_data: dict) -> None:
    pass


async def push_payment_approved(cart_id: str) -> None:
    pass


async def push_payment_failed(cart_id: str, reason: str = "") -> None:
    pass
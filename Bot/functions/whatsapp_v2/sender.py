import aiohttp
import asyncio
import json
from functions.database import database as db

# CONFIGURAÇÕES HARDCODED (PRIVADAS)
WHATSAPP_API_URL = "https://zynxpix.discloud.app"
WHATSAPP_API_KEY = "zynxnot12$"
WHATSAPP_INSTANCE = "zynx_bot"

async def send_whatsapp_v2(number: str, message: str):
    """
    Envia uma notificação via WhatsApp usando a Evolution API v2.
    Configurações hardcoded para máxima segurança e privacidade.
    """
    try:
        # Limpa o número (remove caracteres não numéricos)
        clean_number = "".join(filter(str.isdigit, number))
        
        # Formata a URL e o Payload para Evolution API v2
        url = f"{WHATSAPP_API_URL.rstrip('/')}/message/sendText/{WHATSAPP_INSTANCE}"
        
        payload = {
            "number": clean_number,
            "text": message,
            "delay": 1200,
            "linkPreview": True
        }
        
        headers = {
            "Content-Type": "application/json",
            "apikey": WHATSAPP_API_KEY
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                if response.status in [200, 201]:
                    return True
                else:
                    return False

    except Exception:
        return False

async def notify_sale_v2(user_id: str, product_name: str, value: str, buyer_name: str):
    """Helper específico para notificações de venda"""
    # Busca o número configurado para receber notificações (privado por usuário)
    notif_config = db.get_document(f"notif_config_{user_id}") or {}
    
    if not notif_config.get("enabled"):
        return

    ddd = notif_config.get("ddd", "")
    num = notif_config.get("number", "")
    
    if not ddd or not num:
        return
        
    full_number = f"55{ddd}{num}"
    
    msg = (
        f"🚀 *Nova Venda Realizada!*\n\n"
        f"📦 *Produto:* {product_name}\n"
        f"💰 *Valor:* {value}\n"
        f"👤 *Comprador:* {buyer_name}\n\n"
        f"📅 _Enviado automaticamente pelo seu Bot._"
    )
    
    await send_whatsapp_v2(full_number, msg)

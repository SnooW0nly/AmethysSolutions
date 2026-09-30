import aiohttp
import asyncio
from functions.database import database as db

async def send_whatsapp_notification(product_name: str, value: str, buyer_name: str):
    """Envia notificação de venda para a API do WhatsApp"""
    try:
        # Obter configuração de notificação
        notif_config = db.get_document("notifications_config") or {}
        
        if not notif_config.get("enabled"):
            return
            
        ddd = notif_config.get("ddd")
        number = notif_config.get("number")
        
        if not ddd or not number:
            return
            
        url = "https://notify.syncapplications.com.br/notify-sale"
        data = {
            "productName": product_name,
            "value": value,
            "buyerName": buyer_name,
            "ddd": ddd,
            "number": number
        }
        
        print(f"[WhatsApp] Tentando enviar notificação: {data}")
        # Timeout curto para não travar o bot
        t = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=t) as session:
            async with session.post(url, json=data) as resp:
                status = resp.status
                text = await resp.text()
                print(f"[WhatsApp] Status: {status} | Resposta: {text}")
                if status != 200:
                    print(f"[WhatsApp] ❌ Falha na API: {status} - {text}")
                else:
                    print(f"[WhatsApp] ✅ Notificação enviada com sucesso!")
    except Exception as e:
        print(f"[WhatsApp] Erro ao enviar notificação: {e}")

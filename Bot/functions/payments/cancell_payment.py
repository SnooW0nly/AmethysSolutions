import aiohttp
from typing import Any, Dict, Optional
import json

from functions.database import database as db

BASE_URL = "https://amethyspayments.stackr.lat/api/v1"


def _sanitize_error_message(error_msg: str) -> str:
    """
    Remove informações técnicas (URLs, rotas de API, códigos HTTP) de mensagens de erro
    e retorna apenas mensagens amigáveis ao usuário
    """
    import re
    
    msg = str(error_msg)
    
    # Tentar extrair mensagem de erro de JSON se existir
    try:
        json_match = re.search(r'\{[^{}]*"mensagem"[^{}]*\}', msg, re.IGNORECASE)
        if json_match:
            json_str = json_match.group(0)
            json_data = json.loads(json_str)
            if isinstance(json_data, dict) and "mensagem" in json_data:
                return json_data["mensagem"]
    except:
        pass
    
    # Tentar extrair mensagem de erro de JSON com "message"
    try:
        json_match = re.search(r'\{[^{}]*"message"[^{}]*\}', msg, re.IGNORECASE)
        if json_match:
            json_str = json_match.group(0)
            json_data = json.loads(json_str)
            if isinstance(json_data, dict):
                if "message" in json_data:
                    msg_data = json_data["message"]
                    if isinstance(msg_data, dict) and "mensagem" in msg_data:
                        return msg_data["mensagem"]
                    elif isinstance(msg_data, str):
                        return msg_data
    except:
        pass
    
    # Remover URLs (http://, https://)
    msg = re.sub(r'https?://[^\s]+', '', msg)
    
    # Remover rotas de API (ex: /api/v1/create-efi-payment)
    msg = re.sub(r'/api/v\d+/[^\s]+', '', msg)
    msg = re.sub(r'/api/[^\s]+', '', msg)
    
    # Remover códigos HTTP no início (ex: 500, 400)
    msg = re.sub(r'^\d+\s+', '', msg)
    
    # Remover referências a BASE_URL ou URLs específicas
    msg = re.sub(r'pay\.syncapplications\.com\.br[^\s]*', '', msg, flags=re.IGNORECASE)
    
    # Limpar espaços múltiplos
    msg = re.sub(r'\s+', ' ', msg)
    
    # Remover dois pontos duplos ou pontos isolados no início
    msg = re.sub(r'^:\s*', '', msg)
    msg = msg.strip()
    
    # Se a mensagem ficou vazia ou muito curta, retornar mensagem genérica
    if not msg or len(msg) < 3:
        return "Erro ao processar pagamento. Verifique as configurações."
    
    return msg


async def _post_json(path: str, payload: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    url = f"{BASE_URL}/{path}"
    t = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=t) as session:
        async with session.post(url, json=payload) as resp:
            text = await resp.text()
            try:
                data = json.loads(text)
            except Exception:
                data = None
            if resp.status >= 400:
                # Sanitizar mensagem de erro antes de lançar exceção
                sanitized_msg = _sanitize_error_message(text)
                raise RuntimeError(sanitized_msg)
            if data is None:
                raise RuntimeError("Resposta inválida do servidor")
            return data


# PicPay - Cancelar Pagamento
async def cancel_picpay_payment(token_picpay: str, payment_id: str) -> Dict[str, Any]:
    return await _post_json("cancel-picpay-payment", {"token_picpay": token_picpay, "payment_id": payment_id})


def _load_config() -> dict:
    """Carrega configurações de pagamento do database"""
    return db.get_document("payment_configs") or {}


def _require(value: Optional[str], what: str) -> str:
    if not value:
        raise ValueError(f"Missing {what} in payment settings.")
    return value


async def cancel_picpay_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    token = _require((_load_config().get("picpay") or {}).get("token_picpay"), "PicPay token")
    return await cancel_picpay_payment(token, payment_id)


__all__ = [
    "cancel_picpay_payment",
    "cancel_picpay_payment_from_settings",
]

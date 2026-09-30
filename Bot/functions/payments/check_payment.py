import aiohttp
from typing import Any, Dict, Optional
import json
from pathlib import Path

from functions.database import database as db
import base64

# Carregar URL da API do config_api.json
def _get_api_url() -> str:
    """Carrega URL da API de config_api.json"""
    try:
        import json
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent / "configs" / "config_api.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_url = config.get("payments", "localhost:22222")
                # Adicionar http:// se não tiver
                if not api_url.startswith(("http://", "https://")):
                    api_url = f"http://{api_url}"
                return api_url.rstrip("/")
    except Exception as e:
        print(f"⚠️ Erro ao carregar config_api.json: {e}")
    
    # Fallback para API antiga
    return "https://amethyspayments.stackr.lat"

BASE_URL = f"{_get_api_url()}/api/v1"


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


# Mercado Pago
async def check_mp_payment(token_mp: str, payment_id: str) -> Dict[str, Any]:
    return await _post_json("check-mp-payment", {"token_mp": token_mp, "payment_id": payment_id})


# EfiBank (Efí)
async def check_efi_payment(
    client_id: str,
    client_secret: str,
    certificate: str,
    payment_id: str,
    passphrase: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "certificate": certificate,
        "payment_id": payment_id,
    }
    if passphrase is not None:
        payload["passphrase"] = passphrase
    
    result = await _post_json("check-efi-payment", payload)
    
    # Converter camelCase para snake_case para compatibilidade
    if result:
        converted = {}
        
        # Campos diretos
        if "paymentId" in result:
            converted["payment_id"] = result["paymentId"]
            converted["txid"] = result["paymentId"]  # Efi usa txid
        if "status" in result:
            converted["status"] = result["status"]
        if "statusDetail" in result:
            converted["status_detail"] = result["statusDetail"]
        if "amount" in result:
            converted["amount"] = result["amount"]
        if "paidAt" in result:
            converted["paid_at"] = result["paidAt"]
        if "checkedAt" in result:
            converted["checked_at"] = result["checkedAt"]
            
        return converted if converted else result
    
    return result


# PagBank
async def check_pagbank_payment(token_pagbank: str, payment_id: str, environment: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"token_pagbank": token_pagbank, "payment_id": payment_id}
    if environment is not None:
        payload["environment"] = environment
    return await _post_json("check-pagbank-payment", payload)


# PicPay
async def check_picpay_payment(token_picpay: str, payment_id: str) -> Dict[str, Any]:
    return await _post_json("check-picpay-payment", {"token_picpay": token_picpay, "payment_id": payment_id})


# PushinPay
async def check_pushinpay_payment(token_pushinpay: str, payment_id: str) -> Dict[str, Any]:
    return await _post_json("check-pushinpay-payment", {"token_pushinpay": token_pushinpay, "payment_id": payment_id})


# Stripe
async def check_stripe_payment(token_stripe: str, payment_id: str) -> Dict[str, Any]:
    return await _post_json("check-stripe-payment", {"token_stripe": token_stripe, "payment_id": payment_id})


# PayPal
async def check_paypal_payment(
    client_id: str,
    client_secret: str,
    payment_id: str,
    environment: Optional[str] = None,
    sandbox: Optional[bool] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "payment_id": payment_id,
    }
    if environment is not None:
        payload["environment"] = environment
    if sandbox is not None:
        payload["sandbox"] = sandbox
    return await _post_json("check-paypal-payment", payload)


# Asaas
async def check_asaas_payment(token_asaas: str, payment_id: str, environment: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"token_asaas": token_asaas, "payment_id": payment_id}
    if environment is not None:
        payload["environment"] = environment
    return await _post_json("check-asaas-payment", payload)


# Coinbase Commerce
async def check_coinbase_payment(token_coinbase: str, payment_id: str) -> Dict[str, Any]:
    return await _post_json("check-coinbase-payment", {"token_coinbase": token_coinbase, "payment_id": payment_id})


# NOWPayments
async def check_nowpayments_invoice(token_nowpayments: str, payment_id: str) -> Dict[str, Any]:
    return await _post_json("check-nowpayments-invoice", {"token_nowpayments": token_nowpayments, "payment_id": payment_id})


__all__ = [
    "check_mp_payment",
    "check_efi_payment",
    "check_pagbank_payment",
    "check_picpay_payment",
    "check_pushinpay_payment",
    "check_stripe_payment",
    "check_paypal_payment",
    "check_asaas_payment",
    "check_coinbase_payment",
    "check_nowpayments_invoice",
]


def _load_config() -> dict:
    """Carrega configurações de pagamento do database"""
    return db.get_document("payment_configs") or {}


def _require(value: Optional[str], what: str) -> str:
    if not value:
        raise ValueError(f"Missing {what} in payment settings.")
    return value


def _efi_credentials() -> Dict[str, str]:
    from pathlib import Path  # Import local para garantir disponibilidade
    cfg = _load_config().get("efibank") or {}
    client_id = cfg.get("client_id") or cfg.get("client")
    client_secret = cfg.get("client_secret") or cfg.get("token")
    cert_file = cfg.get("cert_file")
    cert_b64: Optional[str] = None
    if cert_file and isinstance(cert_file, str) and cert_file.strip():
        cert_path = Path(cert_file)
        if cert_path.exists():
            try:
                data = cert_path.read_bytes()
                cert_b64 = base64.b64encode(data).decode("ascii")
            except Exception:
                cert_b64 = None
    return {
        "client_id": _require(client_id, "Efi client_id"),
        "client_secret": _require(client_secret, "Efi client_secret"),
        "certificate": _require(cert_b64, "Efi certificate (.p12)"),
    }


# Settings-backed wrappers

async def check_mp_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    token = _require((_load_config().get("mercado_pago") or {}).get("access_token"), "Mercado Pago access_token")
    return await check_mp_payment(token, payment_id)


async def check_efi_payment_from_settings(payment_id: str, passphrase: Optional[str] = None) -> Dict[str, Any]:
    creds = _efi_credentials()
    return await check_efi_payment(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        certificate=creds["certificate"],
        payment_id=payment_id,
        passphrase=passphrase,
    )


async def check_pagbank_payment_from_settings(payment_id: str, environment: Optional[str] = None) -> Dict[str, Any]:
    token = _require((_load_config().get("pagbank") or {}).get("token_pagbank"), "PagBank token")
    return await check_pagbank_payment(token, payment_id, environment=environment)


async def check_picpay_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    token = _require((_load_config().get("picpay") or {}).get("token_picpay"), "PicPay token")
    return await check_picpay_payment(token, payment_id)


async def check_pushinpay_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    token = _require((_load_config().get("pushinpay") or {}).get("token_pushinpay"), "PushinPay token")
    return await check_pushinpay_payment(token, payment_id)


async def check_stripe_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    token = _require((_load_config().get("stripe") or {}).get("token_stripe"), "Stripe token")
    return await check_stripe_payment(token, payment_id)


async def check_paypal_payment_from_settings(payment_id: str, environment: Optional[str] = None, sandbox: Optional[bool] = None) -> Dict[str, Any]:
    cfg = _load_config().get("paypal") or {}
    client_id = _require(cfg.get("client_id"), "PayPal client_id")
    client_secret = _require(cfg.get("client_secret"), "PayPal client_secret")
    return await check_paypal_payment(client_id, client_secret, payment_id, environment=environment, sandbox=sandbox)


async def check_asaas_payment_from_settings(payment_id: str, environment: Optional[str] = None) -> Dict[str, Any]:
    token = _require((_load_config().get("asaas") or {}).get("token_asaas"), "Asaas token")
    return await check_asaas_payment(token, payment_id, environment=environment)


async def check_coinbase_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    token = _require((_load_config().get("coinbase") or {}).get("token_coinbase"), "Coinbase token")
    return await check_coinbase_payment(token, payment_id)


async def check_nowpayments_invoice_from_settings(payment_id: str) -> Dict[str, Any]:
    token = _require((_load_config().get("nowpayments") or {}).get("token_nowpayments"), "NOWPayments token")
    return await check_nowpayments_invoice(token, payment_id)


__all__ += [
    "check_mp_payment_from_settings",
    "check_efi_payment_from_settings",
    "check_pagbank_payment_from_settings",
    "check_picpay_payment_from_settings",
    "check_pushinpay_payment_from_settings",
    "check_stripe_payment_from_settings",
    "check_paypal_payment_from_settings",
    "check_asaas_payment_from_settings",
    "check_coinbase_payment_from_settings",
    "check_nowpayments_invoice_from_settings",
]

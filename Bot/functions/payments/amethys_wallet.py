"""
Amethys Wallet Payment Integration
Integração com Amethys Pay API para pagamentos PIX e gerenciamento de carteira virtual
"""

import aiohttp
import os
from typing import Any, Dict, Optional
import json

from functions.database import database as db
from modules.loja.personalization.qr_customization import QRCodeGenerator


# URL base da Amethys Pay API (pode ser configurada via env ou settings)
def _get_amethys_pay_url() -> str:
    """Retorna a URL base da Amethys Pay API"""
    # Tentar pegar do .env primeiro
    url = "https://api.amethys.lat"
    return url.rstrip("/")


def _sanitize_error_message(error_msg: str) -> str:
    """
    Remove informações técnicas de mensagens de erro
    e retorna apenas mensagens amigáveis ao usuário
    """
    import re
    
    msg = str(error_msg)
    
    # Tentar extrair mensagem de erro de JSON
    try:
        json_match = re.search(r'\{[^{}]*"error"[^{}]*\}', msg, re.IGNORECASE)
        if json_match:
            json_str = json_match.group(0)
            json_data = json.loads(json_str)
            if isinstance(json_data, dict):
                if "error" in json_data:
                    return json_data["error"]
                if "message" in json_data:
                    return json_data["message"]
    except:
        pass
    
    # Remover URLs
    msg = re.sub(r'https?://[^\s]+', '', msg)
    msg = re.sub(r'localhost:\d+[^\s]*', '', msg)
    
    # Remover rotas de API
    msg = re.sub(r'/api/v\d+/[^\s]+', '', msg)
    
    # Remover códigos HTTP
    msg = re.sub(r'^\d+\s+', '', msg)
    
    # Limpar espaços múltiplos
    msg = re.sub(r'\s+', ' ', msg)
    msg = msg.strip()
    
    if not msg or len(msg) < 3:
        return "Erro ao processar com Amethys Wallet. Verifique as configurações."
    
    return msg


async def _request(
    method: str,
    path: str,
    api_key: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 20
) -> Dict[str, Any]:
    """Faz requisição HTTP para a Amethys Pay API"""
    base_url = _get_amethys_pay_url()
    url = f"{base_url}/{path}"
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    
    t = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=t) as session:
        async with session.request(method, url, json=payload, headers=headers) as resp:
            text = await resp.text()
            try:
                data = json.loads(text)
            except Exception:
                data = None
            
            if resp.status >= 400:
                sanitized_msg = _sanitize_error_message(text)
                raise RuntimeError(sanitized_msg)
            
            if data is None:
                raise RuntimeError("Resposta inválida do servidor Amethys Pay")
            
            return data


def _load_config() -> dict:
    """Carrega configurações de pagamento do database"""
    return db.get_document("payment_configs") or {}


def _require(value: Optional[str], what: str) -> str:
    """Valida que um valor obrigatório está presente"""
    if not value:
        raise ValueError(f"Missing {what} in Amethys Wallet settings.")
    return value


def _get_api_key() -> str:
    """Retorna a API Key da Amethys Wallet das configurações"""
    config = _load_config()
    sync_config = config.get("amethys_wallet") or {}
    api_key = sync_config.get("api_key")
    return _require(api_key, "Amethys Wallet API Key")


# ==================== PAGAMENTOS ====================

async def create_amethys_payment(
    api_key: str,
    value: float,
    description: Optional[str] = None,
    cover_fee: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Cria uma cobrança PIX via Amethys Wallet
    
    Args:
        api_key: API Key do usuário na Amethys Wallet
        value: Valor em reais (ex: 100.00)
        description: Descrição opcional do pagamento
        cover_fee: Se True, o valor informado é o valor líquido (taxa será adicionada). 
                   Se False, o valor informado é o valor total (taxa será deduzida).
    
    Returns:
        Dict com dados do pagamento incluindo QR Code
    """
    payload: Dict[str, Any] = {"value": value}
    if description:
        payload["description"] = description
    if cover_fee is not None:
        payload["coverFee"] = cover_fee
    
    result = await _request("POST", "api/v1/payment/create", api_key=api_key, payload=payload)
    
    # Extrair dados do pagamento
    if result.get("success") and result.get("data"):
        payment_data = result["data"]
        
        # Extrair código PIX da resposta (prioridade: qrCode, depois copyPaste)
        pix_code = payment_data.get("qrCode") or payment_data.get("copyPaste") or payment_data.get("pixCopyPaste")
        
        # Normalizar campos para compatibilidade
        if pix_code:
            payment_data["copy_paste"] = pix_code
            payment_data["pix_copia_cola"] = pix_code
        
        # Tratar qrcodeUrl (pode ser base64 ou URL)
        qrcode_url = payment_data.get("qrcodeUrl")
        if qrcode_url:
            payment_data["qr_code_url"] = qrcode_url
            
            # Se for base64 data URL, extrair os bytes
            if isinstance(qrcode_url, str) and qrcode_url.startswith("data:image"):
                try:
                    # Formato: data:image/png;base64,<base64_data>
                    if "," in qrcode_url:
                        base64_data = qrcode_url.split(",", 1)[1]
                        import base64 as b64
                        qr_bytes = b64.b64decode(base64_data)
                        payment_data["qr_code_bytes"] = qr_bytes
                        payment_data["qr_code_base64"] = base64_data
                except Exception as e:
                    print(f"❌ Amethys Wallet erro ao decodificar QR base64: {e}")
        
        # Gerar QR Code customizado se houver código PIX (prioridade sobre qrcodeUrl)
        if pix_code:
            try:
                qr_bytes = await QRCodeGenerator.generate_custom_qr(pix_code)
                payment_data["qr_code_bytes"] = qr_bytes
            except Exception as e:
                print(f"❌ Amethys Wallet erro ao gerar QR customizado: {e}")
        
        # Garantir que temos o ID do pagamento
        if not payment_data.get("payment_id") and payment_data.get("id"):
            payment_data["payment_id"] = payment_data["id"]
        
        return payment_data
    
    return result


async def check_amethys_payment(api_key: str, payment_id: str) -> Dict[str, Any]:
    """
    Verifica o status de um pagamento na Amethys Wallet
    
    Args:
        api_key: API Key do usuário
        payment_id: ID do pagamento ou correlationID
    
    Returns:
        Dict com dados atualizados do pagamento
    """
    result = await _request("GET", f"api/v1/payment/get/{payment_id}", api_key=api_key)
    
    if result.get("success") and result.get("data"):
        payment_data = result["data"]
        
        # Normalizar campos para compatibilidade
        if "copyPaste" in payment_data:
            payment_data["copy_paste"] = payment_data["copyPaste"]
            payment_data["pix_copia_cola"] = payment_data["copyPaste"]
        
        if "qrcodeUrl" in payment_data:
            payment_data["qr_code_url"] = payment_data["qrcodeUrl"]
        
        # Normalizar status: usar transactionState se status não estiver presente ou for diferente
        if "transactionState" in payment_data:
            transaction_state = payment_data["transactionState"]
            # Mapear estados da API para status padrão
            state_mapping = {
                "COMPLETO": "COMPLETED",
                "PENDENTE": "PENDING",
                "FALHA": "FAILED",
                "CANCELADO": "CANCELLED"
            }
            normalized_state = state_mapping.get(transaction_state.upper(), transaction_state.upper())
            
            # Se não tiver status ou se transactionState for mais específico, usar transactionState
            if "status" not in payment_data or payment_data.get("status") == "PENDING":
                payment_data["status"] = normalized_state
        
        # Garantir que temos o ID do pagamento
        if not payment_data.get("payment_id") and payment_data.get("id"):
            payment_data["payment_id"] = payment_data["id"]
        
        return payment_data
    
    return result


async def list_amethys_payments(
    api_key: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Lista pagamentos do usuário
    
    Args:
        api_key: API Key do usuário
        status: Filtrar por status (ACTIVE, COMPLETED, etc)
        limit: Número de resultados
        offset: Offset para paginação
    
    Returns:
        Dict com lista de pagamentos e estatísticas
    """
    path = f"api/v1/payment/list?limit={limit}&offset={offset}"
    if status:
        path += f"&status={status}"
    
    result = await _request("GET", path, api_key=api_key)
    
    if result.get("success") and result.get("data"):
        return result["data"]
    
    return result


async def cancel_amethys_payment(api_key: str, payment_id: str) -> Dict[str, Any]:
    """
    Cancela uma cobrança PIX que ainda não foi paga
    
    Args:
        api_key: API Key do usuário
        payment_id: ID do pagamento
    
    Returns:
        Dict com confirmação do cancelamento
    """
    result = await _request("DELETE", f"api/v1/payment/cancel/{payment_id}", api_key=api_key)
    
    if result.get("success"):
        return result.get("data", {})
    
    return result


async def refund_amethys_payment(
    api_key: str,
    payment_id: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reembolsa um pagamento já concluído
    
    Args:
        api_key: API Key do usuário
        payment_id: ID do pagamento
        reason: Motivo do reembolso
    
    Returns:
        Dict com confirmação do reembolso
    """
    payload: Dict[str, Any] = {}
    if reason:
        payload["reason"] = reason
    
    result = await _request("POST", f"api/v1/payment/refund/{payment_id}", api_key=api_key, payload=payload)
    
    if result.get("success"):
        return result.get("data", {})
    
    return result


# ==================== SAQUES ====================

async def create_sync_withdraw(
    api_key: str,
    amount: float,
    pix_key: Optional[str] = None,
    pix_key_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria uma solicitação de saque
    
    Args:
        api_key: API Key do usuário
        amount: Valor em reais (mínimo R$ 5.00)
        pix_key: Chave PIX de destino (opcional, usa a do cadastro se não fornecida)
        pix_key_type: Tipo da chave PIX (CPF, CNPJ, EMAIL, PHONE, RANDOM)
    
    Returns:
        Dict com dados do saque criado
    """
    payload: Dict[str, Any] = {"amount": amount}
    if pix_key:
        payload["pixKey"] = pix_key
    if pix_key_type:
        payload["pixKeyType"] = pix_key_type
    
    result = await _request("POST", "api/v1/withdraw/create", api_key=api_key, payload=payload)
    
    if result.get("success") and result.get("data"):
        return result["data"]
    
    return result


async def get_sync_withdraw(api_key: str, withdraw_id: str) -> Dict[str, Any]:
    """
    Busca um saque específico e sincroniza com a API
    
    Args:
        api_key: API Key do usuário
        withdraw_id: ID do saque
    
    Returns:
        Dict com dados do saque
    """
    result = await _request("GET", f"api/v1/withdraw/get/{withdraw_id}", api_key=api_key)
    
    if result.get("success") and result.get("data"):
        return result["data"]
    
    return result


async def list_sync_withdraws(
    api_key: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sync: bool = False
) -> Dict[str, Any]:
    """
    Lista saques do usuário
    
    Args:
        api_key: API Key do usuário
        status: Filtrar por status (PENDING, COMPLETED, etc)
        limit: Número de resultados
        offset: Offset para paginação
        sync: Sincronizar com Woovi
    
    Returns:
        Dict com lista de saques e estatísticas
    """
    path = f"api/v1/withdraw/list?limit={limit}&offset={offset}"
    if status:
        path += f"&status={status}"
    if sync:
        path += "&sync=true"
    
    result = await _request("GET", path, api_key=api_key)
    
    if result.get("success") and result.get("data"):
        return result["data"]
    
    return result


# ==================== USUÁRIO ====================

async def register_sync_user(
    name: str,
    email: str,
    tax_id: str,
    phone: Optional[str] = None,
    pix_key: Optional[str] = None,
    pix_key_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Registra um novo usuário na Amethys Wallet
    
    Args:
        name: Nome completo
        email: Email válido
        tax_id: CPF (11 dígitos) ou CNPJ (14 dígitos)
        phone: Telefone (opcional)
        pix_key: Chave PIX para saques (opcional)
        pix_key_type: Tipo da chave PIX (opcional)
    
    Returns:
        Dict com dados do usuário e API Key gerada
    """
    payload: Dict[str, Any] = {
        "name": name,
        "email": email,
        "taxID": tax_id
    }
    if phone:
        payload["phone"] = phone
    if pix_key:
        payload["pixKey"] = pix_key
    if pix_key_type:
        payload["pixKeyType"] = pix_key_type
    
    result = await _request("POST", "api/v1/user/register", payload=payload)
    
    if result.get("success") and result.get("data"):
        return result["data"]
    
    return result


async def get_sync_user(api_key: str) -> Dict[str, Any]:
    """
    Busca dados do usuário autenticado
    
    Args:
        api_key: API Key do usuário
    
    Returns:
        Dict com dados do usuário
    """
    result = await _request("GET", "api/v1/user/get", api_key=api_key)
    
    if result.get("success") and result.get("data"):
        return result["data"]
    
    return result


async def update_sync_user(
    api_key: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    pix_key: Optional[str] = None,
    pix_key_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Atualiza dados do usuário
    
    Args:
        api_key: API Key do usuário
        name: Novo nome (opcional)
        email: Novo email (opcional)
        phone: Novo telefone (opcional)
        pix_key: Nova chave PIX (opcional)
        pix_key_type: Novo tipo de chave PIX (opcional)
    
    Returns:
        Dict com dados atualizados
    """
    payload: Dict[str, Any] = {}
    if name:
        payload["name"] = name
    if email:
        payload["email"] = email
    if phone:
        payload["phone"] = phone
    if pix_key:
        payload["pixKey"] = pix_key
    if pix_key_type:
        payload["pixKeyType"] = pix_key_type
    
    result = await _request("PUT", "api/v1/user/update", api_key=api_key, payload=payload)
    
    if result.get("success") and result.get("data"):
        return result["data"]
    
    return result


async def get_sync_balance(api_key: str) -> Dict[str, Any]:
    """
    Retorna saldo e estatísticas do usuário
    
    Args:
        api_key: API Key do usuário
    
    Returns:
        Dict com saldo disponível, pendente e estatísticas
    """
    result = await _request("GET", "api/v1/user/balance", api_key=api_key)
    
    if result.get("success") and result.get("data"):
        return result["data"]
    
    return result


# ==================== WRAPPERS COM SETTINGS ====================

async def create_amethys_payment_from_settings(
    value: float,
    description: Optional[str] = None,
    comment: Optional[str] = None,  # Mantido para compatibilidade
    cover_fee: Optional[bool] = None
) -> Dict[str, Any]:
    """Cria pagamento usando API Key das configurações"""
    api_key = _get_api_key()
    # Usar description se fornecido, senão usar comment (compatibilidade)
    desc = description or comment
    
    # Se cover_fee não foi fornecido, buscar das configurações
    if cover_fee is None:
        config = _load_config()
        sync_config = config.get("amethys_wallet") or {}
        cover_fee = sync_config.get("cover_fee", False)
    
    return await create_amethys_payment(api_key, value, desc, cover_fee)


async def check_amethys_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    """Verifica pagamento usando API Key das configurações"""
    api_key = _get_api_key()
    return await check_amethys_payment(api_key, payment_id)


async def list_amethys_payments_from_settings(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """Lista pagamentos usando API Key das configurações"""
    api_key = _get_api_key()
    return await list_amethys_payments(api_key, status, limit, offset)


async def cancel_amethys_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    """Cancela pagamento usando API Key das configurações"""
    api_key = _get_api_key()
    return await cancel_amethys_payment(api_key, payment_id)


async def refund_amethys_payment_from_settings(
    payment_id: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """Reembolsa pagamento usando API Key das configurações"""
    api_key = _get_api_key()
    return await refund_amethys_payment(api_key, payment_id, reason)


async def create_sync_withdraw_from_settings(
    amount: float,
    pix_key: Optional[str] = None,
    pix_key_type: Optional[str] = None
) -> Dict[str, Any]:
    """Cria saque usando API Key das configurações"""
    api_key = _get_api_key()
    return await create_sync_withdraw(api_key, amount, pix_key, pix_key_type)


async def get_sync_withdraw_from_settings(withdraw_id: str) -> Dict[str, Any]:
    """Busca saque usando API Key das configurações"""
    api_key = _get_api_key()
    return await get_sync_withdraw(api_key, withdraw_id)


async def list_sync_withdraws_from_settings(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sync: bool = False
) -> Dict[str, Any]:
    """Lista saques usando API Key das configurações"""
    api_key = _get_api_key()
    return await list_sync_withdraws(api_key, status, limit, offset, sync)


async def get_sync_user_from_settings() -> Dict[str, Any]:
    """Busca dados do usuário usando API Key das configurações"""
    api_key = _get_api_key()
    return await get_sync_user(api_key)


async def update_sync_user_from_settings(
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    pix_key: Optional[str] = None,
    pix_key_type: Optional[str] = None
) -> Dict[str, Any]:
    """Atualiza usuário usando API Key das configurações"""
    api_key = _get_api_key()
    return await update_sync_user(api_key, name, email, phone, pix_key, pix_key_type)


async def get_sync_balance_from_settings() -> Dict[str, Any]:
    """Busca saldo usando API Key das configurações"""
    api_key = _get_api_key()
    return await get_sync_balance(api_key)


__all__ = [
    # Pagamentos
    "create_amethys_payment",
    "check_amethys_payment",
    "list_amethys_payments",
    "cancel_amethys_payment",
    "refund_amethys_payment",
    # Saques
    "create_sync_withdraw",
    "get_sync_withdraw",
    "list_sync_withdraws",
    # Usuário
    "register_sync_user",
    "get_sync_user",
    "update_sync_user",
    "get_sync_balance",
    # Wrappers com settings
    "create_amethys_payment_from_settings",
    "check_amethys_payment_from_settings",
    "list_amethys_payments_from_settings",
    "cancel_amethys_payment_from_settings",
    "refund_amethys_payment_from_settings",
    "create_sync_withdraw_from_settings",
    "get_sync_withdraw_from_settings",
    "list_sync_withdraws_from_settings",
    "get_sync_user_from_settings",
    "update_sync_user_from_settings",
    "get_sync_balance_from_settings",
]

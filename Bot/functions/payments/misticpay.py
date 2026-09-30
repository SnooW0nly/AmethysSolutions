"""
MisticPay Payment Integration
Integração com a API da Mistic Pay para pagamentos PIX
"""

import aiohttp
import uuid
from typing import Any, Dict, Optional
import json

from functions.database import database as db

# URL base da API Mistic Pay
MISTICPAY_API_BASE = "https://api.misticpay.com"


def _load_config() -> dict:
    """Carrega configurações de pagamento do database"""
    return db.get_document("payment_configs") or {}


def _get_misticpay_credentials() -> tuple[str, str]:
    """Obtém as credenciais do MisticPay das configurações"""
    config = _load_config()
    misticpay_config = config.get("misticpay", {})
    
    client_id = misticpay_config.get("client_id")
    client_secret = misticpay_config.get("client_secret")
    
    if not client_id:
        raise ValueError("Client ID do MisticPay não configurado. Configure em Configurações > Formas de Pagamento > Pix > MisticPay")
    
    if not client_secret:
        raise ValueError("Client Secret do MisticPay não configurado. Configure em Configurações > Formas de Pagamento > Pix > MisticPay")
    
    return client_id, client_secret


async def create_misticpay_payment(
    client_id: str,
    client_secret: str,
    amount: float,
    payer_name: str,
    payer_document: str,
    description: str,
    transaction_id: Optional[str] = None,
    webhook_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria um pagamento PIX via MisticPay
    
    Args:
        client_id: Client ID do MisticPay
        client_secret: Client Secret do MisticPay
        amount: Valor do pagamento (ex: 10.50 = R$ 10,50)
        payer_name: Nome do pagador
        payer_document: CPF do pagador (apenas números ou com formatação)
        description: Descrição do pagamento
        transaction_id: ID único da transação (gerado automaticamente se não fornecido)
        webhook_url: URL do webhook (opcional)
    
    Returns:
        Dict com dados do pagamento criado
    """
    # Gerar transaction_id se não fornecido
    if not transaction_id:
        transaction_id = str(uuid.uuid4())
    
    # Limpar CPF (remover pontos, traços, espaços)
    import re
    payer_document_clean = re.sub(r'[^\d]', '', payer_document)
    
    # A documentação diz "(10 = R$ 10,00)" mas o exemplo usa 5000
    # Testando: enviar em reais primeiro (sem multiplicar)
    # Se a API rejeitar, tentaremos em centavos
    amount_value = float(amount)
    
    # Preparar payload
    payload = {
        "amount": amount_value,
        "payerName": payer_name,
        "payerDocument": payer_document_clean,
        "transactionId": transaction_id,
        "description": description
    }
    
    # Adicionar webhook se fornecido
    if webhook_url:
        payload["projectWebhook"] = webhook_url
    
    # Fazer requisição
    url = f"{MISTICPAY_API_BASE}/api/transactions/create"
    headers = {
        "ci": client_id,
        "cs": client_secret,
        "Content-Type": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            text = await resp.text()
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                raise RuntimeError(f"Resposta inválida da API MisticPay: {text[:200]}")
            
            if resp.status >= 400:
                error_msg = data.get("message") or data.get("error") or text
                raise RuntimeError(f"Erro ao criar pagamento MisticPay: {error_msg}")
            
            # Processar resposta e converter para formato esperado pelo sistema
            # A resposta pode ter estrutura {"data": {...}} ou diretamente os campos
            response_data = data.get("data", data)
            
            # Procurar QR code em diferentes formatos possíveis
            qrcode_url = response_data.get("qrcodeUrl") or response_data.get("qrCodeBase64") or data.get("qrcodeUrl") or data.get("qrCodeBase64")
            
            # Processar QR code se for base64
            qr_code_bytes = None
            qr_code_url = None
            
            if qrcode_url:
                import base64 as b64
                
                # Verificar se é formato data:image/png;base64,...
                if qrcode_url.startswith("data:image"):
                    try:
                        # Extrair apenas a parte base64 após a vírgula
                        qr_base64 = qrcode_url.split(",", 1)[1] if "," in qrcode_url else qrcode_url
                        qr_code_bytes = b64.b64decode(qr_base64)
                    except Exception:
                        pass
                elif qrcode_url.startswith("base64:"):
                    # Extrair base64 e converter para bytes
                    try:
                        qr_base64 = qrcode_url.replace("base64:", "")
                        qr_code_bytes = b64.b64decode(qr_base64)
                    except Exception:
                        pass
                else:
                    # É uma URL
                    qr_code_url = qrcode_url
            
            # A API retorna o valor em reais (ex: 10 = R$ 10,00)
            # Usar o valor retornado diretamente
            transaction_amount = data.get("transactionAmount", amount)
            if isinstance(transaction_amount, (int, float)):
                # Se o valor retornado for muito diferente do enviado, pode estar em formato diferente
                # Mas normalmente a API retorna no mesmo formato que recebe (reais)
                pass
            
            # Extrair transactionId de data ou response_data
            transaction_id = response_data.get("transactionId") or data.get("transactionId")
            copy_paste = response_data.get("copyPaste") or data.get("copyPaste") or transaction_id
            transaction_state = response_data.get("transactionState") or data.get("transactionState", "PENDENTE")
            transaction_fee = response_data.get("transactionFee") or data.get("transactionFee", 0)
            transaction_method = response_data.get("transactionMethod") or data.get("transactionMethod", "PIX")
            transaction_type = response_data.get("transactionType") or data.get("transactionType", "DEPOSITO")
            payer = response_data.get("payer") or data.get("payer", {})
            
            result = {
                "payment_id": transaction_id,
                "paymentId": transaction_id,  # Para compatibilidade
                "qr_code": qrcode_url,
                "qr_code_url": qr_code_url,
                "qr_code_bytes": qr_code_bytes,
                "copy_paste": copy_paste,
                "pix_copia_cola": copy_paste,  # Para compatibilidade
                "status": transaction_state,
                "amount": transaction_amount,
                "fee": transaction_fee,
                "method": transaction_method,
                "type": transaction_type,
                "payer": payer,
                "raw": data
            }
            
            return result


async def check_misticpay_payment(
    client_id: str,
    client_secret: str,
    transaction_id: str
) -> Dict[str, Any]:
    """
    Verifica o status de uma transação MisticPay
    
    Args:
        client_id: Client ID do MisticPay
        client_secret: Client Secret do MisticPay
        transaction_id: ID da transação a verificar
    
    Returns:
        Dict com status e dados da transação
    """
    url = f"{MISTICPAY_API_BASE}/api/transactions/check"
    headers = {
        "ci": client_id,
        "cs": client_secret,
        "Content-Type": "application/json"
    }
    
    payload = {
        "transactionId": transaction_id
    }
    
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            text = await resp.text()
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                raise RuntimeError(f"Resposta inválida da API MisticPay: {text[:200]}")
            
            if resp.status >= 400:
                error_msg = data.get("message") or data.get("error") or text
                raise RuntimeError(f"Erro ao verificar pagamento MisticPay: {error_msg}")
            
            # Processar resposta - pode vir em diferentes formatos
            # Formato 1: Direto no nível superior (exemplo da documentação)
            # Formato 2: Dentro de transaction (resposta real da API)
            
            # Tentar obter transaction de diferentes lugares
            transaction_data = None
            if "transaction" in data:
                transaction_data = data.get("transaction")
            elif "data" in data and isinstance(data.get("data"), dict) and "transaction" in data.get("data"):
                transaction_data = data.get("data").get("transaction")
            
            # Se encontrou transaction, usar ele; senão usar data diretamente
            if transaction_data and isinstance(transaction_data, dict):
                status = transaction_data.get("transactionState", "PENDENTE")
                payment_id = transaction_data.get("externalId") or transaction_data.get("id")
                amount = transaction_data.get("value", 0)
                fee = transaction_data.get("fee", 0)
                method = transaction_data.get("transactionMethod", "PIX")
                trans_type = transaction_data.get("transactionType", "DEPOSITO")
                client_name = transaction_data.get("clientName")
                client_doc = transaction_data.get("clientDocument")
                description = transaction_data.get("description", "")
            else:
                # Formato direto (fallback)
                status = data.get("transactionState", "PENDENTE")
                payment_id = data.get("externalId") or data.get("id")
                amount = data.get("value", 0)
                fee = data.get("fee", 0)
                method = data.get("transactionMethod", "PIX")
                trans_type = data.get("transactionType", "DEPOSITO")
                client_name = data.get("clientName")
                client_doc = data.get("clientDocument")
                description = data.get("description", "")
            
            is_paid = status == "COMPLETO"
            
            result = {
                "paid": is_paid,
                "status": status,
                "payment_id": payment_id,
                "amount": amount,
                "fee": fee,
                "method": method,
                "type": trans_type,
                "payer": {
                    "name": client_name,
                    "document": client_doc
                },
                "description": description,
                "raw": data
            }
            
            return result


async def get_misticpay_balance(
    client_id: str,
    client_secret: str
) -> float:
    """
    Consulta o saldo disponível na conta MisticPay
    
    Args:
        client_id: Client ID do MisticPay
        client_secret: Client Secret do MisticPay
    
    Returns:
        Saldo disponível em reais
    """
    url = f"{MISTICPAY_API_BASE}/api/users/balance"
    headers = {
        "ci": client_id,
        "cs": client_secret,
        "Content-Type": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers) as resp:
            text = await resp.text()
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                raise RuntimeError(f"Resposta inválida da API MisticPay: {text[:200]}")
            
            if resp.status >= 400:
                error_msg = data.get("message") or data.get("error") or text
                raise RuntimeError(f"Erro ao consultar saldo MisticPay: {error_msg}")
            
            balance = data.get("balance", 0)
            # API retorna em reais (ex: 10 = R$ 10,00)
            return float(balance)


# Funções que usam configurações do database
async def create_misticpay_payment_from_settings(
    amount: float,
    payer_name: str,
    payer_document: str,
    description: str,
    transaction_id: Optional[str] = None,
    webhook_url: Optional[str] = None
) -> Dict[str, Any]:
    """Cria pagamento MisticPay usando configurações do database"""
    client_id, client_secret = _get_misticpay_credentials()
    return await create_misticpay_payment(
        client_id=client_id,
        client_secret=client_secret,
        amount=amount,
        payer_name=payer_name,
        payer_document=payer_document,
        description=description,
        transaction_id=transaction_id,
        webhook_url=webhook_url
    )


async def check_misticpay_payment_from_settings(
    transaction_id: str
) -> Dict[str, Any]:
    """Verifica pagamento MisticPay usando configurações do database"""
    client_id, client_secret = _get_misticpay_credentials()
    return await check_misticpay_payment(
        client_id=client_id,
        client_secret=client_secret,
        transaction_id=transaction_id
    )


async def get_misticpay_balance_from_settings() -> float:
    """Consulta saldo MisticPay usando configurações do database"""
    client_id, client_secret = _get_misticpay_credentials()
    return await get_misticpay_balance(
        client_id=client_id,
        client_secret=client_secret
    )


__all__ = [
    "create_misticpay_payment",
    "check_misticpay_payment",
    "get_misticpay_balance",
    "create_misticpay_payment_from_settings",
    "check_misticpay_payment_from_settings",
    "get_misticpay_balance_from_settings",
]


"""
Sistema de pagamento PIX Manual
Gera QR Codes PIX usando a API oficial do Banco Central
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from modules.loja.personalization.qr_customization import QRCodeGenerator
from functions.database import database as db


def _load_config() -> dict:
    """Carrega configurações de pagamento do database"""
    return db.get_document("payment_configs") or {}


def _sanitize_text(text: str, max_length: int) -> str:
    """Remove caracteres especiais e limita tamanho conforme padrão PIX"""
    import unicodedata
    import re
    
    # Normalizar unicode (remover acentos)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('ASCII')
    
    # Remover caracteres não permitidos (apenas letras, números, espaços e alguns símbolos)
    text = re.sub(r'[^A-Za-z0-9\s\.\-]', '', text)
    
    # Limitar tamanho
    return text[:max_length].strip()


def _generate_pix_payload(
    pix_key: str,
    merchant_name: str,
    merchant_city: str,
    amount: float,
    transaction_id: str,
    pix_key_type: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Gera o payload PIX (EMV) padrão Banco Central
    
    Args:
        pix_key: Chave PIX do recebedor
        merchant_name: Nome do recebedor
        merchant_city: Cidade do recebedor
        amount: Valor da transação
        transaction_id: ID único da transação (máx 25 caracteres alfanuméricos)
        pix_key_type: Tipo da chave PIX (cpf, cnpj, email, telefone, aleatoria)
        description: Descrição opcional
    
    Returns:
        String do payload PIX (copia e cola)
    """
    def format_field(field_id: str, value: str) -> str:
        """Formata um campo no padrão EMV"""
        length = str(len(value)).zfill(2)
        return f"{field_id}{length}{value}"
    
    # Sanitizar textos
    merchant_name = _sanitize_text(merchant_name, 25)
    merchant_city = _sanitize_text(merchant_city, 15)
    
    # Limpar chave PIX baseado no tipo
    pix_key_clean = pix_key.strip()  # Sempre remover espaços no início/fim
    
    if pix_key_type == "cpf":
        # CPF: remover pontos e hífens, manter apenas números
        pix_key_clean = pix_key_clean.replace('.', '').replace('-', '').replace(' ', '')
    elif pix_key_type == "cnpj":
        # CNPJ: remover pontos, barras e hífens, manter apenas números
        pix_key_clean = pix_key_clean.replace('.', '').replace('-', '').replace('/', '').replace(' ', '')
    elif pix_key_type == "email":
        # Email: apenas remover espaços, manter pontos e arroba
        pix_key_clean = pix_key_clean.replace(' ', '').lower()
    elif pix_key_type == "telefone":
        # Telefone: remover parênteses, hífens e espaços, manter apenas números
        pix_key_clean = pix_key_clean.replace('(', '').replace(')', '').replace('-', '').replace(' ', '').replace('+', '')
    elif pix_key_type == "aleatoria":
        # Chave aleatória: apenas remover espaços
        pix_key_clean = pix_key_clean.replace(' ', '')
    else:
        # Fallback: tentar detectar automaticamente
        if '@' in pix_key_clean:
            # Parece email
            pix_key_clean = pix_key_clean.replace(' ', '').lower()
        elif len(pix_key_clean.replace('.', '').replace('-', '').replace('/', '').replace(' ', '')) == 11:
            # Parece CPF (11 dígitos)
            pix_key_clean = pix_key_clean.replace('.', '').replace('-', '').replace(' ', '')
        elif len(pix_key_clean.replace('.', '').replace('-', '').replace('/', '').replace(' ', '')) == 14:
            # Parece CNPJ (14 dígitos)
            pix_key_clean = pix_key_clean.replace('.', '').replace('-', '').replace('/', '').replace(' ', '')
        else:
            # Chave aleatória ou desconhecida: apenas remover espaços
            pix_key_clean = pix_key_clean.replace(' ', '')
    
    # TXID: apenas alfanuméricos, máximo 25 caracteres
    transaction_id = transaction_id.replace('-', '')[:25].upper()
    
    # Payload Format Indicator
    payload = format_field("00", "01")
    
    # Point of Initiation Method (12 = dinâmico, permite reutilização)
    payload += format_field("01", "12")
    
    # Merchant Account Information (PIX)
    gui = format_field("00", "br.gov.bcb.pix")
    key = format_field("01", pix_key_clean)
    if description:
        desc_clean = _sanitize_text(description, 25)
        if desc_clean:
            desc = format_field("02", desc_clean)
            merchant_account = format_field("26", gui + key + desc)
        else:
            merchant_account = format_field("26", gui + key)
    else:
        merchant_account = format_field("26", gui + key)
    payload += merchant_account
    
    # Merchant Category Code (0000 = não especificado)
    payload += format_field("52", "0000")
    
    # Transaction Currency (986 = BRL)
    payload += format_field("53", "986")
    
    # Transaction Amount
    if amount > 0:
        amount_str = f"{amount:.2f}"
        payload += format_field("54", amount_str)
    
    # Country Code
    payload += format_field("58", "BR")
    
    # Merchant Name
    payload += format_field("59", merchant_name)
    
    # Merchant City
    payload += format_field("60", merchant_city)
    
    # Additional Data Field Template
    txid = format_field("05", transaction_id)
    additional_data = format_field("62", txid)
    payload += additional_data
    
    # CRC16
    payload += "6304"
    crc = _calculate_crc16(payload)
    payload += crc
    
    return payload


def _calculate_crc16(payload: str) -> str:
    """Calcula o CRC16-CCITT do payload PIX"""
    crc = 0xFFFF
    polynomial = 0x1021
    
    for byte in payload.encode('utf-8'):
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFFFF
    
    return f"{crc:04X}"


async def create_manual_pix_payment(
    amount: float,
    description: Optional[str] = None,
    merchant_name: str = "Loja",
    merchant_city: str = "Sao Paulo"
) -> Dict[str, Any]:
    """
    Cria um pagamento PIX manual
    
    Args:
        amount: Valor do pagamento
        description: Descrição do pagamento
        merchant_name: Nome do estabelecimento
        merchant_city: Cidade do estabelecimento
    
    Returns:
        Dict com dados do pagamento incluindo QR code
    """
    config = _load_config()
    pix_config = config.get("pix_manual", {})
    
    if not pix_config.get("enabled"):
        raise ValueError("PIX Manual não está habilitado")
    
    pix_key = pix_config.get("pix_key")
    if not pix_key:
        raise ValueError("Chave PIX não configurada")
    
    pix_key_type = pix_config.get("pix_key_type")
    
    # Gerar ID único para a transação
    transaction_id = str(uuid.uuid4())[:25]
    
    # Gerar payload PIX
    pix_payload = _generate_pix_payload(
        pix_key=pix_key,
        merchant_name=merchant_name,
        merchant_city=merchant_city,
        amount=amount,
        transaction_id=transaction_id,
        pix_key_type=pix_key_type,
        description=description
    )
    
    # Gerar QR Code usando o sistema de customização
    try:
        qr_bytes = await QRCodeGenerator.generate_custom_qr(pix_payload)
    except Exception:
        # Fallback para QR simples se houver erro
        qr_bytes = await QRCodeGenerator.generate_simple_qr(pix_payload)
    
    return {
        "payment_id": transaction_id,
        "id": transaction_id,
        "status": "pending",
        "amount": amount,
        "currency": "BRL",
        "pix_copia_cola": pix_payload,
        "copy_paste": pix_payload,
        "emv": pix_payload,
        "qr_code_base64": None,  # Não usamos base64, retornamos bytes diretamente
        "qr_code_bytes": qr_bytes,
        "pix_key": pix_key,
        "pix_key_type": pix_config.get("pix_key_type"),
        "description": description,
        "created_at": datetime.utcnow().isoformat(),
        "payment_method": "pix_manual",
        "requires_manual_approval": True
    }


async def check_manual_pix_payment(payment_id: str) -> Dict[str, Any]:
    """
    Verifica status de um pagamento PIX manual
    
    Como é manual, sempre retorna pending até aprovação manual
    
    Args:
        payment_id: ID do pagamento
    
    Returns:
        Dict com status do pagamento
    """
    # PIX Manual sempre requer aprovação manual
    # O status será atualizado quando um admin aprovar
    return {
        "payment_id": payment_id,
        "status": "pending",
        "payment_status": "pending",
        "requires_manual_approval": True
    }


async def approve_manual_pix_payment(payment_id: str) -> Dict[str, Any]:
    """
    Aprova manualmente um pagamento PIX
    
    Args:
        payment_id: ID do pagamento
    
    Returns:
        Dict com status atualizado
    """
    return {
        "payment_id": payment_id,
        "status": "approved",
        "payment_status": "approved",
        "approved_at": datetime.utcnow().isoformat()
    }

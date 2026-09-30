"""
Sistema de pagamento PIX via Nubank com aprovação automática por IMAP
Gera QR Codes PIX e monitora emails do Nubank para aprovar pagamentos automaticamente
"""
import imaplib
import email
from email.header import decode_header
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

from modules.loja.personalization.qr_customization import QRCodeGenerator
from functions.database import database as db


def _load_config() -> dict:
    """Carrega configurações de pagamento do database"""
    return db.get_document("payment_configs") or {}


def _sanitize_text(text: str, max_length: int) -> str:
    """Remove caracteres especiais e limita tamanho conforme padrão PIX"""
    import unicodedata
    
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


async def create_nubank_imap_payment(
    amount: float,
    cart_id: str,
    description: Optional[str] = None,
    merchant_name: str = "Loja",
    merchant_city: str = "Sao Paulo"
) -> Dict[str, Any]:
    """
    Cria um pagamento PIX via Nubank IMAP
    
    Args:
        amount: Valor do pagamento
        cart_id: ID do carrinho (usado como TXID para rastreamento)
        description: Descrição do pagamento
        merchant_name: Nome do estabelecimento
        merchant_city: Cidade do estabelecimento
    
    Returns:
        Dict com dados do pagamento incluindo QR code
    """
    config = _load_config()
    nubank_config = config.get("nubank_imap", {})
    
    if not nubank_config.get("enabled"):
        raise ValueError("Nubank IMAP não está habilitado")
    
    pix_key = nubank_config.get("pix_key")
    if not pix_key:
        raise ValueError("Chave PIX não configurada no Nubank IMAP")
    
    pix_key_type = nubank_config.get("pix_key_type")
    
    email_address = nubank_config.get("email")
    if not email_address:
        raise ValueError("Email não configurado no Nubank IMAP")
    
    # Usar o cart_id como TXID para rastreamento
    # Limpar e garantir que seja alfanumérico
    transaction_id = re.sub(r'[^A-Za-z0-9]', '', str(cart_id))[:25].upper()
    
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
    except Exception as e:
        print(f"❌ Erro ao gerar QR customizado: {e}")
        # Fallback para QR simples se houver erro
        qr_bytes = await QRCodeGenerator.generate_simple_qr(pix_payload)
    
    # Salvar informações do pagamento pendente no database
    payment_data = {
        "payment_id": transaction_id,
        "cart_id": cart_id,
        "txid": transaction_id,
        "status": "pending",
        "amount": amount,
        "currency": "BRL",
        "pix_copia_cola": pix_payload,
        "pix_key": pix_key,
        "pix_key_type": nubank_config.get("pix_key_type"),
        "description": description,
        "created_at": datetime.utcnow().isoformat(),
        "payment_method": "nubank_imap",
        "requires_manual_approval": False,  # Será aprovado automaticamente pelo IMAP
        "imap_monitored": True
    }
    
    # Salvar no database para rastreamento
    _save_pending_payment(transaction_id, payment_data)
    
    return {
        **payment_data,
        "id": transaction_id,
        "copy_paste": pix_payload,
        "emv": pix_payload,
        "qr_code_base64": None,
        "qr_code_bytes": qr_bytes,
    }


def _save_pending_payment(payment_id: str, payment_data: Dict[str, Any]) -> None:
    """Salva um pagamento pendente no database"""
    pending_payments = db.get_document("nubank_pending_payments") or {}
    pending_payments[payment_id] = payment_data
    db.save_document("nubank_pending_payments", {}, pending_payments)


def _get_pending_payment(payment_id: str) -> Optional[Dict[str, Any]]:
    """Recupera um pagamento pendente do database"""
    pending_payments = db.get_document("nubank_pending_payments") or {}
    return pending_payments.get(payment_id)


def _update_payment_status(payment_id: str, status: str, extra_data: Optional[Dict] = None) -> None:
    """Atualiza o status de um pagamento"""
    pending_payments = db.get_document("nubank_pending_payments") or {}
    if payment_id in pending_payments:
        pending_payments[payment_id]["status"] = status
        pending_payments[payment_id]["updated_at"] = datetime.utcnow().isoformat()
        if extra_data:
            pending_payments[payment_id].update(extra_data)
        db.save_document("nubank_pending_payments", {}, pending_payments)


def _connect_imap(email_address: str, password: str) -> imaplib.IMAP4_SSL:
    """
    Conecta ao servidor IMAP do Gmail
    
    Args:
        email_address: Endereço de email
        password: Senha de app do Gmail
    
    Returns:
        Conexão IMAP
    """
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email_address, password)
        return mail
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar ao IMAP: {str(e)}")


def _decode_email_header(header: str) -> str:
    """Decodifica header de email que pode estar em formato encoded"""
    if not header:
        return ""
    
    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
        else:
            decoded_parts.append(str(part))
    return ''.join(decoded_parts)


def _extract_email_body(msg: email.message.Message) -> str:
    """Extrai o corpo de texto de um email (prefere HTML, converte para texto limpo)"""
    html_body = ""
    plain_body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if "attachment" in content_disposition:
                continue
            
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload and not plain_body:
                        plain_body = payload.decode('utf-8', errors='ignore')
                except Exception:
                    continue
            elif content_type == "text/html":
                try:
                    payload = part.get_payload(decode=True)
                    if payload and not html_body:
                        html_body = payload.decode('utf-8', errors='ignore')
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                content_type = msg.get_content_type()
                raw = payload.decode('utf-8', errors='ignore')
                if content_type == "text/html":
                    html_body = raw
                else:
                    plain_body = raw
        except Exception:
            pass
    
    # Prefer HTML and strip tags for richer content (Nubank emails are HTML)
    if html_body:
        # Remove style/script blocks
        clean = re.sub(r'<style[^>]*>.*?</style>', ' ', html_body, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<script[^>]*>.*?</script>', ' ', clean, flags=re.DOTALL | re.IGNORECASE)
        # Replace block-level tags with newlines
        clean = re.sub(r'<(?:br|p|div|tr|td|th|li)[^>]*>', '\n', clean, flags=re.IGNORECASE)
        # Strip remaining tags
        clean = re.sub(r'<[^>]+>', ' ', clean)
        # Decode HTML entities
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&#xA0;', ' ')
        # Collapse whitespace
        clean = re.sub(r'[ \t]+', ' ', clean)
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        # Append plain body too so patterns have more data to work with
        return clean.strip() + ("\n\n" + plain_body if plain_body else "")
    
    return plain_body


def _parse_nubank_pix_email(subject: str, body: str) -> Optional[Dict[str, Any]]:
    """
    Extrai informações de um email de PIX recebido do Nubank.
    Suporta os formatos HTML/texto reais dos emails do Nubank.
    """
    subject_lower = subject.lower()
    body_lower = body.lower()

    # Verificar se é email de PIX
    if "pix" not in subject_lower and "pix" not in body_lower:
        return None

    # Verificar recebimento vs envio
    has_sent = (
        "enviado" in subject_lower or
        "você enviou" in body_lower or
        "você pagou" in body_lower or
        "pagamento realizado" in body_lower
    )
    has_received = (
        "recebido" in subject_lower or
        "recebeu" in subject_lower or
        "você recebeu" in body_lower or
        "entrou na sua conta" in body_lower or
        "entrou em sua conta" in body_lower or
        "creditado" in body_lower or
        "recebimento" in body_lower
    )

    if has_sent and not has_received:
        return None

    info = {}

    # -----------------------------------------------------------------------
    # Extrair VALOR
    # O Nubank exibe o valor de formas diferentes dependendo da versão do email:
    #   "Você recebeu R$ 50,00 de João"
    #   "Valor: R$ 50,00"
    #   "R$ 50,00"
    # -----------------------------------------------------------------------
    value_patterns = [
        # "recebeu R$ X,XX" ou "recebeu R$X,XX"
        r'recebeu\s+R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
        r'recebeu\s+R\$\s*(\d+(?:,\d{2})?)',
        # "Valor Recebido: R$ X,XX"
        r'Valor\s+Recebido[:\s]*R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
        # "Valor: R$ X,XX"
        r'[Vv]alor[:\s]+R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
        # Genérico "R$ X,XX"
        r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})',
        r'R\$\s*(\d+,\d{2})',
        r'R\$\s*(\d+\.\d{2})',
    ]

    for pattern in value_patterns:
        matches = re.findall(pattern, body, re.IGNORECASE)
        if matches:
            for value_str in matches:
                if isinstance(value_str, tuple):
                    value_str = value_str[0]
                original = value_str
                if '.' in value_str and ',' in value_str:
                    parts = value_str.split(',')
                    if len(parts) == 2 and len(parts[1]) == 2:
                        value_str = value_str.replace('.', '').replace(',', '.')
                    else:
                        value_str = value_str.replace(',', '')
                elif ',' in value_str:
                    value_str = value_str.replace(',', '.')
                try:
                    amount = float(value_str)
                    if 0.01 <= amount <= 1_000_000:
                        info['amount'] = amount
                        break
                except (ValueError, TypeError):
                    continue
            if 'amount' in info:
                break

    # -----------------------------------------------------------------------
    # Extrair TXID / EndToEndId
    # O Nubank normalmente inclui o ID da transação como EndToEnd (E2E)
    # Formato: E + 32 chars alfanuméricos (ex: E1234567820241204...)
    # Também pode aparecer como "ID da transação", "Código", etc.
    # -----------------------------------------------------------------------
    txid_patterns = [
        # EndToEnd ID do Pix (formato oficial BACEN: E + 32 chars)
        r'\b(E[0-9]{8}[A-Z0-9]{22,32})\b',
        # TXID alfanumérico simples (8-35 chars)
        r'(?:txid|endtoendid|end.to.end|E2E|ID\s+da\s+transa[çc][ãa]o|c[óo]digo\s+da\s+transa[çc][ãa]o|identificador)[:\s]*([A-Za-z0-9]{8,35})',
        r'(?:ID|Código|Identificador)[:\s]+([A-Z0-9]{10,35})',
    ]

    for pattern in txid_patterns:
        matches = re.findall(pattern, body, re.IGNORECASE)
        if matches:
            txid_candidate = matches[0] if isinstance(matches[0], str) else matches[0][0] if matches[0] else None
            if txid_candidate and len(txid_candidate) >= 8:
                info['txid'] = txid_candidate.upper().strip()
                break

    # -----------------------------------------------------------------------
    # Extrair NOME DO PAGADOR
    # "Você recebeu um Pix de NOME e o valor..."
    # "de NOME"
    # -----------------------------------------------------------------------
    name_patterns = [
        r'[Vv]oc[êe]\s+recebeu\s+(?:um\s+)?[Pp]ix\s+de\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{2,60}?)(?:\s+e\s+o\s+valor|\s+no\s+valor|\.|,|\n|<)',
        r'recebeu\s+de\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{2,50}?)(?:\s+R\$|\s+o\s+valor|\n|<|\.|,)',
        r'[Dd]e[:\s]+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{2,50}?)(?:\n|R\$|\.|,|<)',
        r'[Pp]agador[:\s]+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{2,50}?)(?:\n|R\$|\.|,|<)',
    ]

    for pattern in name_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name = re.sub(r'\s+', ' ', name).strip()
            if len(name) >= 3 and not name.isdigit():
                info['payer_name'] = name
                break

    if 'amount' in info:
        return info

    return None


def _check_imap_for_payments(
    email_address: str,
    password: str,
    since_datetime: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Verifica emails do Nubank em busca de notificações de PIX.
    Filtra por data/hora a partir de `since_datetime` para evitar processar
    emails antigos desnecessariamente.

    Args:
        email_address: Email configurado
        password: Senha de app
        since_datetime: Só processar emails recebidos a partir deste momento.
                        Se None, usa 1 hora atrás como fallback.

    Returns:
        Lista de pagamentos detectados
    """
    from datetime import datetime as _dt, timedelta
    import email as _email_module

    detected_payments = []
    processed_ids = []

    # Definir janela de tempo: emails a partir de since_datetime (com 2 min de margem)
    if since_datetime is None:
        since_datetime = _dt.utcnow() - timedelta(hours=1)

    # Subtrair 2 minutos de margem para compensar pequenos desalinhamentos de relógio
    search_since = since_datetime - timedelta(minutes=2)

    # O IMAP SINCE aceita apenas data (sem hora), então usamos a data do since_since
    since_date_str = search_since.strftime("%d-%b-%Y")

    try:
        mail = _connect_imap(email_address, password)
        mail.select("inbox")

        all_mail_ids = []

        # Buscar emails do Nubank a partir da data calculada
        search_strategies = [
            (
                f'(FROM "nubank.com.br" SINCE {since_date_str})',
                f'Domínio nubank.com.br desde {since_date_str}'
            ),
            (
                f'(FROM "meajuda@nubank.com.br" SINCE {since_date_str})',
                f'meajuda@ desde {since_date_str}'
            ),
            (
                f'(FROM "no-reply@nubank.com.br" SINCE {since_date_str})',
                f'no-reply@ desde {since_date_str}'
            ),
            (
                f'(FROM "noreply@nubank.com.br" SINCE {since_date_str})',
                f'noreply@ desde {since_date_str}'
            ),
            (
                f'(SINCE {since_date_str} SUBJECT "Pix")',
                f'Assunto Pix desde {since_date_str}'
            ),
        ]

        for search_query, description in search_strategies:
            try:
                status, messages = mail.search(None, search_query)
                if status == "OK" and messages[0]:
                    found_ids = messages[0].split()
                    for mid in found_ids:
                        if mid not in all_mail_ids:
                            all_mail_ids.append(mid)
            except Exception as e:
                print(f"   ⚠️ Erro na busca '{description}': {e}")
                continue

        # Remover duplicatas e ordenar (mais recentes primeiro)
        unique_ids = set()
        for mid in all_mail_ids:
            unique_ids.add(mid.decode() if isinstance(mid, bytes) else str(mid))

        mail_ids = [mid.encode() if isinstance(mid, str) else mid for mid in unique_ids]
        try:
            mail_ids.sort(key=lambda x: int(x.decode() if isinstance(x, bytes) else x), reverse=True)
        except Exception:
            pass

        if not mail_ids:
            mail.close()
            mail.logout()
            return detected_payments

        print(f"📬 Nubank IMAP: {len(mail_ids)} email(s) encontrado(s) desde {since_date_str}")

        nubank_count = 0
        pix_count = 0

        for mail_id in mail_ids:
            try:
                # Buscar headers + DATA para filtrar por horário exato
                status, headers = mail.fetch(mail_id, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')

                if status != "OK":
                    continue

                header_data = headers[0][1].decode('utf-8', errors='ignore')

                # Verificar se é do Nubank
                if "nubank.com.br" not in header_data.lower():
                    continue

                # Verificar horário do email vs horário do pagamento mais antigo
                date_match = re.search(r'Date:\s*(.+)', header_data, re.IGNORECASE)
                if date_match:
                    try:
                        from email.utils import parsedate_to_datetime
                        email_dt = parsedate_to_datetime(date_match.group(1).strip())
                        # Converter para UTC sem timezone para comparação
                        import calendar
                        email_dt_utc = _dt.utcfromtimestamp(calendar.timegm(email_dt.utctimetuple()))
                        if email_dt_utc < search_since:
                            # Email mais antigo que o pagamento pendente mais antigo, pular
                            continue
                    except Exception:
                        pass  # Se não conseguir parsear a data, processa mesmo assim

                # Verificar assunto
                subject_match = re.search(r'Subject:\s*(.+)', header_data, re.IGNORECASE)
                if not subject_match:
                    continue

                subject = subject_match.group(1).strip()
                subject_decoded = _decode_email_header(subject)
                subject_lower = subject_decoded.lower()

                is_pix_email = (
                    "pix" in subject_lower or
                    "recebido" in subject_lower or
                    "recebeu" in subject_lower or
                    "entrou" in subject_lower
                )

                if not is_pix_email:
                    continue

                nubank_count += 1
                print(f"   📧 Email PIX do Nubank: {subject_decoded[:80]}")

                # Buscar corpo completo
                status, msg_data = mail.fetch(mail_id, '(BODY.PEEK[])')
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = _email_module.message_from_bytes(raw_email)
                body = _extract_email_body(msg)

                payment_info = _parse_nubank_pix_email(subject_decoded, body)

                if payment_info:
                    payment_info['email_id'] = mail_id.decode() if isinstance(mail_id, bytes) else str(mail_id)
                    payment_info['received_at'] = _dt.utcnow().isoformat()
                    detected_payments.append(payment_info)
                    processed_ids.append(mail_id)
                    pix_count += 1
                    txid = payment_info.get('txid', 'N/A')
                    amount = payment_info.get('amount', 0)
                    payer = payment_info.get('payer_name', 'N/A')
                    print(f"   ✅ PIX detectado: TXID={txid}, Valor=R${amount:.2f}, Pagador={payer}")
                else:
                    print(f"   ⚠️ Email PIX não parseado: {subject_decoded[:60]}")

            except Exception as e:
                print(f"⚠️ Erro ao processar email {mail_id}: {e}")
                continue

        if nubank_count > 0:
            print(f"📊 Processados: {nubank_count} email(s) do Nubank, {pix_count} PIX detectado(s)")

        mail.close()
        mail.logout()

    except Exception as e:
        import traceback
        print(f"❌ Erro ao verificar IMAP: {e}")
        print(f"   Traceback: {traceback.format_exc()}")

    return detected_payments


async def check_nubank_imap_payment(payment_id: str) -> Dict[str, Any]:
    """
    Verifica status de um pagamento PIX via Nubank IMAP
    
    Esta função monitora emails do Nubank em busca de confirmação de pagamento
    
    Args:
        payment_id: ID do pagamento (TXID)
    
    Returns:
        Dict com status do pagamento
    """
    # Buscar informações do pagamento pendente
    payment_data = _get_pending_payment(payment_id)
    
    if not payment_data:
        return {
            "payment_id": payment_id,
            "status": "not_found",
            "payment_status": "not_found",
            "error": "Pagamento não encontrado"
        }
    
    # Se já foi aprovado, retornar status
    if payment_data.get("status") == "approved":
        return {
            "payment_id": payment_id,
            "status": "approved",
            "payment_status": "approved",
            "approved_at": payment_data.get("approved_at"),
            "amount": payment_data.get("amount")
        }
    
    # Verificar emails em busca de confirmação
    config = _load_config()
    nubank_config = config.get("nubank_imap", {})
    
    email_address = nubank_config.get("email")
    password = nubank_config.get("password")
    
    if not email_address or not password:
        return {
            "payment_id": payment_id,
            "status": "pending",
            "payment_status": "pending",
            "error": "Credenciais IMAP não configuradas"
        }
    
    # Executar verificação IMAP em thread separada para não bloquear
    # Usar created_at do pagamento como ponto de partida da busca
    from datetime import timedelta as _timedelta
    created_at_str = payment_data.get("created_at")
    since_dt = None
    if created_at_str:
        try:
            since_dt = datetime.fromisoformat(created_at_str)
        except Exception:
            pass
    if since_dt is None:
        since_dt = datetime.utcnow() - _timedelta(hours=1)

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        detected_payments = await loop.run_in_executor(
            executor,
            _check_imap_for_payments,
            email_address,
            password,
            since_dt
        )
    
    # Procurar por pagamento correspondente
    expected_amount = payment_data.get("amount")
    
    for detected in detected_payments:
        detected_txid = detected.get("txid", "")
        detected_amount = detected.get("amount")
        
        # Verificar se o TXID ou valor correspondem
        if detected_txid == payment_id or (detected_amount == expected_amount):
            # Pagamento confirmado!
            _update_payment_status(
                payment_id,
                "approved",
                {
                    "approved_at": datetime.utcnow().isoformat(),
                    "payer_name": detected.get("payer_name"),
                    "detected_amount": detected_amount
                }
            )
            
            return {
                "payment_id": payment_id,
                "status": "approved",
                "payment_status": "approved",
                "approved_at": datetime.utcnow().isoformat(),
                "amount": detected_amount or expected_amount,
                "payer_name": detected.get("payer_name")
            }
    
    # Ainda pendente
    return {
        "payment_id": payment_id,
        "status": "pending",
        "payment_status": "pending",
        "amount": expected_amount
    }


async def monitor_nubank_imap_payments() -> List[Dict[str, Any]]:
    """
    Monitora continuamente emails do Nubank em busca de pagamentos
    
    Esta função deve ser executada periodicamente (ex: a cada 30 segundos)
    
    Returns:
        Lista de pagamentos aprovados nesta verificação
    """
    config = _load_config()
    nubank_config = config.get("nubank_imap", {})
    
    if not nubank_config.get("enabled"):
        return []
    
    email_address = nubank_config.get("email")
    password = nubank_config.get("password")
    
    if not email_address or not password:
        print("⚠️ Nubank IMAP: credenciais não configuradas")
        return []
    
    try:
        # Calcular o horário do pagamento pendente mais antigo para limitar a busca de emails
        from datetime import timedelta as _timedelta
        pending_payments_all = db.get_document("nubank_pending_payments") or {}
        oldest_dt: Optional[datetime] = None
        for _pid, _pdata in pending_payments_all.items():
            if not isinstance(_pdata, dict) or _pdata.get("status") != "pending":
                continue
            _created = _pdata.get("created_at")
            if _created:
                try:
                    _dt = datetime.fromisoformat(_created)
                    if oldest_dt is None or _dt < oldest_dt:
                        oldest_dt = _dt
                except Exception:
                    pass
        # Fallback: 1 hora atrás
        since_dt = oldest_dt or (datetime.utcnow() - _timedelta(hours=1))

        # Verificar emails em thread separada
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            detected_payments = await loop.run_in_executor(
                executor,
                _check_imap_for_payments,
                email_address,
                password,
                since_dt
            )
        
        if detected_payments:
            print(f"📧 Nubank IMAP: {len(detected_payments)} email(s) de PIX detectado(s)")
        
        approved_payments = []
        
        # Buscar pagamentos pendentes
        pending_payments = db.get_document("nubank_pending_payments") or {}
        pending_list = [
            (payment_id, data)
            for payment_id, data in pending_payments.items()
            if isinstance(data, dict) and data.get("status") == "pending"
        ]
        pending_count = len(pending_list)
        
        if pending_count > 0:
            print(f"🔍 Nubank IMAP: Comparando {len(detected_payments)} PIX detectado(s) com {pending_count} pagamento(s) pendente(s)...")
        
        # Se não há emails detectados nem pendentes, retornar vazio
        if not detected_payments and not pending_list:
            return approved_payments
        
        # Criar índice de pagamentos pendentes para busca rápida
        # Índice por valor (mais comum)
        pending_by_amount = {}
        # Índice por TXID
        pending_by_txid = {}
        # Lista completa para fallback
        pending_full_list = []
        
        for payment_id, payment_data in pending_list:
            amount = payment_data.get("amount")
            txid = payment_data.get("txid") or payment_data.get("payment_id")
            
            if amount:
                amount_key = f"{amount:.2f}"
                if amount_key not in pending_by_amount:
                    pending_by_amount[amount_key] = []
                pending_by_amount[amount_key].append((payment_id, payment_data))
            
            if txid:
                txid_clean = re.sub(r'[^A-Z0-9]', '', str(txid).upper())
                if txid_clean:
                    pending_by_txid[txid_clean] = (payment_id, payment_data)
            
            pending_full_list.append((payment_id, payment_data))
        
        # Processar pagamentos detectados em batch
        for detected in detected_payments:
            detected_txid = detected.get("txid")
            detected_amount = detected.get("amount")
            
            print(f"   📨 Processando PIX: TXID={detected_txid or 'N/A'}, Valor=R${detected_amount:.2f}")
            
            # Normalizar TXID detectado
            detected_txid_clean = re.sub(r'[^A-Z0-9]', '', str(detected_txid or '').upper())
            
            matched_payment = None
            match_type = None
            
            # Busca rápida por TXID primeiro (mais preciso)
            if detected_txid_clean:
                # Match exato por TXID
                if detected_txid_clean in pending_by_txid:
                    matched_payment = pending_by_txid[detected_txid_clean]
                    match_type = "TXID (exato)"
                else:
                    # Match parcial (últimos 8 caracteres)
                    if len(detected_txid_clean) >= 8:
                        txid_suffix = detected_txid_clean[-8:]
                        for txid_key, payment_data in pending_by_txid.items():
                            if len(txid_key) >= 8 and txid_key[-8:] == txid_suffix:
                                matched_payment = payment_data
                                match_type = "TXID (parcial)"
                                break
            
            # Se não encontrou por TXID, buscar por valor
            if not matched_payment and detected_amount:
                amount_key = f"{detected_amount:.2f}"
                if amount_key in pending_by_amount:
                    # Se houver múltiplos com mesmo valor, pegar o primeiro pendente
                    matched_payment = pending_by_amount[amount_key][0]
                    match_type = "Valor"
            
            # Se encontrou correspondência
            if matched_payment:
                payment_id, payment_data = matched_payment
                expected_amount = payment_data.get("amount")
                expected_txid = payment_data.get("txid") or payment_data.get("payment_id")
                expected_txid_clean = re.sub(r'[^A-Z0-9]', '', str(expected_txid or '').upper())
                
                print(f"   ✅ Correspondência por {match_type}! Payment ID: {payment_id}")
                print(f"      Esperado: TXID={expected_txid_clean}, Valor=R${expected_amount:.2f}")
                print(f"      Detectado: TXID={detected_txid_clean}, Valor=R${detected_amount:.2f}")
                
                # Aprovar pagamento
                _update_payment_status(
                    payment_id,
                    "approved",
                    {
                        "approved_at": datetime.utcnow().isoformat(),
                        "payer_name": detected.get("payer_name"),
                        "detected_amount": detected_amount,
                        "detected_txid": detected_txid
                    }
                )
                
                approved_payments.append({
                    "payment_id": payment_id,
                    "cart_id": payment_data.get("cart_id"),
                    "amount": detected_amount or expected_amount,
                    "payer_name": detected.get("payer_name"),
                    "approved_at": datetime.utcnow().isoformat()
                })
                
                print(f"✅ Pagamento aprovado automaticamente: {payment_id}")
                
                # Remover do índice para não processar novamente
                if detected_txid_clean in pending_by_txid:
                    del pending_by_txid[detected_txid_clean]
                if detected_amount:
                    amount_key = f"{detected_amount:.2f}"
                    if amount_key in pending_by_amount:
                        pending_by_amount[amount_key] = [
                            p for p in pending_by_amount[amount_key] 
                            if p[0] != payment_id
                        ]
            else:
                print(f"   ⚠️ Nenhum pagamento pendente correspondente encontrado para este PIX")
        
        return approved_payments
    
    except Exception as e:
        import traceback
        print(f"❌ Erro ao monitorar Nubank IMAP: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return []


__all__ = [
    "create_nubank_imap_payment",
    "check_nubank_imap_payment",
    "monitor_nubank_imap_payments",
]
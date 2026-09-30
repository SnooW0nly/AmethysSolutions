"""
functions/email_utils.py

Envia emails de notificação de venda usando as credenciais SMTP
definidas em  configs/notification.json  (arquivo colocado pelo dono).

Formato esperado do notification.json:
{
    "email_destino": "dono@exemplo.com",
    "smtp_server":   "smtp.gmail.com",
    "smtp_port":     587,
    "smtp_user":     "remetente@gmail.com",
    "smtp_pass":     "senha-de-app",
    "use_tls":       true,
    "enabled":       true
}

O usuário do Discord configura APENAS o "email_destino" pelo painel.
As demais credenciais ficam fixas no arquivo JSON do servidor.
"""

import json
import re
import ssl
import time
import smtplib
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

NOTIFICATION_FILE = "configs/notification.json"

# ── Cooldown global para "Testar Email" (por guild_id)  ─────────────────────
_test_cooldowns: dict[int, float] = {}
TEST_COOLDOWN_SECONDS = 60          # 1 minuto entre testes por guild


# ── Cooldown global para emails de venda (evitar spam em bulk) ──────────────
_sale_last_sent: float = 0.0
SALE_COOLDOWN_SECONDS = 5           # no máximo 1 email a cada 5 s


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _load_smtp_config() -> dict:
    """Lê configs/notification.json. Retorna {} se não existir/inválido."""
    try:
        with open(NOTIFICATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_dest_email(dest_email: str) -> bool:
    """Salva apenas o campo email_destino no notification.json."""
    cfg = _load_smtp_config()
    cfg["email_destino"] = dest_email
    try:
        with open(NOTIFICATION_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_dest_email() -> Optional[str]:
    return _load_smtp_config().get("email_destino")


def is_email_enabled() -> bool:
    cfg = _load_smtp_config()
    return bool(cfg.get("enabled", False) and cfg.get("email_destino"))


# ────────────────────────────────────────────────────────────────────────────
# Core — envio síncrono (roda em executor)
# ────────────────────────────────────────────────────────────────────────────

def _send_email_sync(subject: str, body_text: str, body_html: Optional[str] = None) -> tuple[bool, str]:
    cfg = _load_smtp_config()

    if not cfg.get("enabled", False):
        return False, "Notificações por email desativadas em notification.json."

    dest    = cfg.get("email_destino")
    server  = cfg.get("smtp_server")
    port    = cfg.get("smtp_port", 587)
    user    = cfg.get("smtp_user")
    passw   = cfg.get("smtp_pass")
    use_tls = cfg.get("use_tls", True)

    if not all([dest, server, port, user, passw]):
        return False, "notification.json incompleto (faltam campos SMTP)."

    if not is_valid_email(dest):
        return False, f"Email de destino inválido: {dest}"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Bot Vendas <{user}>"
        msg["To"]      = dest

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP(server, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls(context=ctx)
            smtp.login(user, passw)
            smtp.sendmail(user, dest, msg.as_string())

        return True, "Email enviado com sucesso."
    except smtplib.SMTPAuthenticationError:
        return False, "Autenticação SMTP falhou. Verifique smtp_user e smtp_pass."
    except smtplib.SMTPConnectError:
        return False, f"Não foi possível conectar em {server}:{port}."
    except Exception as e:
        return False, f"Erro ao enviar email: {e}"


# ────────────────────────────────────────────────────────────────────────────
# Templates HTML
# ────────────────────────────────────────────────────────────────────────────

def _html_sale_product(product_name: str, value: str, buyer_name: str, items_count: int = 1) -> tuple[str, str]:
    """Retorna (subject, html) para venda de produto."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    subject = f"💰 Nova Venda — {product_name}"
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{margin:0;padding:0;background:#0f0f0f;font-family:'Segoe UI',sans-serif;color:#e0e0e0}}
  .wrap{{max-width:560px;margin:32px auto;background:#1a1a2e;border-radius:12px;overflow:hidden;border:1px solid #2a2a4a}}
  .header{{background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px 32px;text-align:center}}
  .header h1{{margin:0;font-size:22px;color:#fff;letter-spacing:.5px}}
  .header .sub{{color:#c4b5fd;font-size:13px;margin-top:4px}}
  .body{{padding:28px 32px}}
  .card{{background:#16213e;border-radius:8px;padding:18px 20px;margin-bottom:14px;border-left:3px solid #4f46e5}}
  .label{{font-size:11px;color:#8888aa;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px}}
  .value{{font-size:16px;color:#e0e0e0;font-weight:600}}
  .value.money{{color:#34d399;font-size:20px}}
  .footer{{padding:16px 32px;text-align:center;font-size:11px;color:#555;border-top:1px solid #2a2a4a}}
</style></head>
<body>
<div class="wrap">
  <div class="header">
    <h1>💰 Nova Venda Realizada</h1>
    <div class="sub">{now}</div>
  </div>
  <div class="body">
    <div class="card">
      <div class="label">Produto</div>
      <div class="value">{product_name}</div>
    </div>
    <div class="card">
      <div class="label">Comprador</div>
      <div class="value">{buyer_name}</div>
    </div>
    {"" if items_count <= 1 else f'<div class="card"><div class="label">Itens</div><div class="value">{items_count}</div></div>'}
    <div class="card">
      <div class="label">Valor Total</div>
      <div class="value money">{value}</div>
    </div>
  </div>
  <div class="footer">Notificação automática do seu bot de vendas</div>
</div>
</body></html>"""
    text = f"Nova venda!\nProduto: {product_name}\nComprador: {buyer_name}\nValor: {value}\n{now}"
    return subject, html, text


def _html_sale_robux(roblox_user: str, quantity: int, value: float,
                     order_type: str = "robux", gamepass_name: str = "") -> tuple[str, str, str]:
    """Retorna (subject, html, text) para venda de Robux."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    type_label = "Gamepass" if gamepass_name else order_type.title()
    subject = f"🎮 Venda Robux — {roblox_user} | R$ {value:.2f}"
    extra_card = ""
    if gamepass_name:
        extra_card = f'<div class="card"><div class="label">Gamepass</div><div class="value">{gamepass_name}</div></div>'
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{margin:0;padding:0;background:#0f0f0f;font-family:'Segoe UI',sans-serif;color:#e0e0e0}}
  .wrap{{max-width:560px;margin:32px auto;background:#1a1a2e;border-radius:12px;overflow:hidden;border:1px solid #2a2a4a}}
  .header{{background:linear-gradient(135deg,#dc2626,#ea580c);padding:28px 32px;text-align:center}}
  .header h1{{margin:0;font-size:22px;color:#fff;letter-spacing:.5px}}
  .header .sub{{color:#fca5a5;font-size:13px;margin-top:4px}}
  .body{{padding:28px 32px}}
  .card{{background:#16213e;border-radius:8px;padding:18px 20px;margin-bottom:14px;border-left:3px solid #dc2626}}
  .label{{font-size:11px;color:#8888aa;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px}}
  .value{{font-size:16px;color:#e0e0e0;font-weight:600}}
  .value.money{{color:#34d399;font-size:20px}}
  .value.robux{{color:#fbbf24}}
  .footer{{padding:16px 32px;text-align:center;font-size:11px;color:#555;border-top:1px solid #2a2a4a}}
</style></head>
<body>
<div class="wrap">
  <div class="header">
    <h1>🎮 Venda de Robux</h1>
    <div class="sub">{now}</div>
  </div>
  <div class="body">
    <div class="card">
      <div class="label">Tipo</div>
      <div class="value">{type_label}</div>
    </div>
    <div class="card">
      <div class="label">Usuário Roblox</div>
      <div class="value">{roblox_user}</div>
    </div>
    {extra_card}
    <div class="card">
      <div class="label">Robux</div>
      <div class="value robux">R$ {quantity:,}</div>
    </div>
    <div class="card">
      <div class="label">Valor Pago</div>
      <div class="value money">R$ {value:.2f}</div>
    </div>
  </div>
  <div class="footer">Notificação automática do seu bot de vendas</div>
</div>
</body></html>"""
    text = (f"Venda Robux!\nTipo: {type_label}\nRoblox: {roblox_user}\n"
            f"{'Gamepass: ' + gamepass_name + chr(10) if gamepass_name else ''}"
            f"Robux: {quantity:,}\nValor: R$ {value:.2f}\n{now}")
    return subject, html, text


def _html_test(dest: str) -> tuple[str, str, str]:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    subject = "✅ Teste de Email — Bot de Vendas"
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8">
<style>
  body{{margin:0;padding:0;background:#0f0f0f;font-family:'Segoe UI',sans-serif}}
  .wrap{{max-width:480px;margin:32px auto;background:#1a1a2e;border-radius:12px;overflow:hidden;border:1px solid #2a2a4a;text-align:center}}
  .header{{background:linear-gradient(135deg,#059669,#10b981);padding:32px}}
  .header h1{{margin:0;color:#fff;font-size:22px}}
  .body{{padding:28px 32px;color:#d1d5db}}
  .dest{{background:#16213e;border-radius:8px;padding:12px 16px;margin-top:12px;font-size:14px;color:#34d399;word-break:break-all}}
  .footer{{padding:14px;font-size:11px;color:#555;border-top:1px solid #2a2a4a}}
</style></head>
<body>
<div class="wrap">
  <div class="header"><h1>✅ Email Configurado!</h1></div>
  <div class="body">
    <p>As notificações de venda serão enviadas para:</p>
    <div class="dest">{dest}</div>
    <p style="margin-top:16px;font-size:13px;color:#9ca3af">Testado em {now}</p>
  </div>
  <div class="footer">Bot de Vendas — Notificações</div>
</div>
</body></html>"""
    text = f"Email de teste enviado com sucesso para {dest} em {now}."
    return subject, html, text


# ────────────────────────────────────────────────────────────────────────────
# API pública — assíncrona
# ────────────────────────────────────────────────────────────────────────────

async def send_sale_email_product(product_name: str, value: str, buyer_name: str, items_count: int = 1):
    """
    Chamada fire-and-forget após venda de produto.
    Tem cooldown interno de SALE_COOLDOWN_SECONDS.
    """
    global _sale_last_sent
    if not is_email_enabled():
        return

    now = time.time()
    if now - _sale_last_sent < SALE_COOLDOWN_SECONDS:
        return
    _sale_last_sent = now

    subject, html, text = _html_sale_product(product_name, value, buyer_name, items_count)
    loop = asyncio.get_event_loop()
    ok, msg = await loop.run_in_executor(None, _send_email_sync, subject, text, html)
    if ok:
        print(f"[Email] ✅ Notificação de produto enviada: {product_name}")
    else:
        print(f"[Email] ❌ Falha na notificação de produto: {msg}")


async def send_sale_email_robux(roblox_user: str, quantity: int, value: float,
                                 order_type: str = "robux", gamepass_name: str = ""):
    """
    Chamada fire-and-forget após venda de Robux.
    """
    global _sale_last_sent
    if not is_email_enabled():
        return

    now = time.time()
    if now - _sale_last_sent < SALE_COOLDOWN_SECONDS:
        return
    _sale_last_sent = now

    subject, html, text = _html_sale_robux(roblox_user, quantity, value, order_type, gamepass_name)
    loop = asyncio.get_event_loop()
    ok, msg = await loop.run_in_executor(None, _send_email_sync, subject, text, html)
    if ok:
        print(f"[Email] ✅ Notificação Robux enviada: {roblox_user} | R$ {value:.2f}")
    else:
        print(f"[Email] ❌ Falha na notificação Robux: {msg}")


async def send_test_email(guild_id: int) -> tuple[bool, str]:
    """
    Envia email de teste com cooldown por guild.
    Retorna (ok, mensagem).
    """
    now = time.time()
    last = _test_cooldowns.get(guild_id, 0)
    remaining = TEST_COOLDOWN_SECONDS - (now - last)
    if remaining > 0:
        secs = int(remaining)
        return False, f"Aguarde **{secs}s** antes de testar novamente."

    if not is_email_enabled():
        cfg = _load_smtp_config()
        if not cfg.get("enabled", False):
            return False, "Email não está habilitado em `notification.json`."
        return False, "Nenhum email de destino configurado."

    dest = get_dest_email()
    subject, html, text = _html_test(dest)

    loop = asyncio.get_event_loop()
    ok, msg = await loop.run_in_executor(None, _send_email_sync, subject, text, html)

    if ok:
        _test_cooldowns[guild_id] = now

    return ok, msg


def configure_dest_email(email: str) -> tuple[bool, str]:
    """Salva o email de destino no notification.json. Retorna (ok, msg)."""
    if not is_valid_email(email):
        return False, "Email inválido."
    ok = _save_dest_email(email)
    if ok:
        return True, f"Email `{email}` salvo com sucesso."
    return False, "Erro ao salvar no arquivo notification.json."

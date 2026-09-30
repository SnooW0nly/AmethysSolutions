import asyncio
import base64
import io
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import disnake
from disnake.ext import commands
import aiohttp

from functions.message import message, embed_message
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from functions.perms import perms

from functions.payments import (
    create_mp_payment_from_settings,
    create_mp_site_payment_from_settings,
    create_efi_payment_from_settings,
    create_pagbank_payment_from_settings,
    create_picpay_payment_from_settings,
    create_pushinpay_payment_from_settings,
    create_stripe_payment_from_settings,
    create_paypal_payment_from_settings,
    create_asaas_payment_link_from_settings,
    create_asaas_pix_payment_from_settings,
    create_coinbase_payment_from_settings,
    create_nowpayments_invoice_from_settings,
    create_manual_pix_payment,
    check_mp_payment_from_settings,
    check_efi_payment_from_settings,
    check_pagbank_payment_from_settings,
    check_picpay_payment_from_settings,
    check_pushinpay_payment_from_settings,
    check_stripe_payment_from_settings,
    check_paypal_payment_from_settings,
    check_asaas_payment_from_settings,
    check_coinbase_payment_from_settings,
    check_nowpayments_invoice_from_settings,
    check_manual_pix_payment,
)
from functions.payments.create_payment import BASE_URL as PAY_API_BASE
from functions.database import database as db
from modules.loja.cart.purchase_manager import PurchaseManager
from functions.payments.misticpay import (
    create_misticpay_payment_from_settings,
    check_misticpay_payment_from_settings,
)
from functions.payments.amethys_wallet import (
    check_amethys_payment_from_settings,
)
from functions.plan import is_free, should_allow_payment_provider


def _generate_valid_cpf() -> str:
    """Gera um CPF válido aleatório."""
    def calculate_digit(cpf_partial: List[int], weight_start: int) -> int:
        total = sum(cpf_partial[i] * (weight_start - i) for i in range(len(cpf_partial)))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder
    
    # Gera os 9 primeiros dígitos aleatoriamente
    cpf_digits = [random.randint(0, 9) for _ in range(9)]
    
    # Calcula o primeiro dígito verificador
    first_digit = calculate_digit(cpf_digits, 10)
    cpf_digits.append(first_digit)
    
    # Calcula o segundo dígito verificador
    second_digit = calculate_digit(cpf_digits, 11)
    cpf_digits.append(second_digit)
    
    # Retorna o CPF como string
    return ''.join(map(str, cpf_digits))


def _load_config() -> Dict[str, Any]:
    """Carrega configurações de pagamento do database"""
    return db.get_document("payment_configs") or {}


def _load_payments() -> Dict[str, Any]:
    """Carrega rastreamento de pagamentos do database"""
    return db.get_document("payment_tracking") or {"items": {}}


def _save_payments(data: Dict[str, Any]) -> None:
    """Salva rastreamento de pagamentos no database"""
    db.save_document("payment_tracking", data)


def _providers_coming_soon() -> List[str]:
    """Lista de provedores que estão em breve (não devem ser usados)"""
    return [
        "pagbank", "picpay", "stripe", "nowpayments", 
        "coinbase", "asaas", "asaas_link", "asaas_pix", "paypal", 
        "inter", "bitcoin", "litecoin", 
        "ethereum", "livepix"
    ]


def _providers_all() -> List[Tuple[str, str]]:
    return [
        ("sync_wallet", "Sync Wallet"),
        ("mercado_pago", "Mercado Pago"),
        ("efibank", "EfiBank"),
        ("misticpay", "MisticPay"),
        ("pagbank", "PagBank (Em breve)"),
        ("picpay", "PicPay (Em breve)"),
        ("pushinpay", "PushinPay"),
        ("stripe", "Stripe (Em breve)"),
        ("paypal", "PayPal (Em breve)"),
        ("asaas_link", "Asaas Link (Em breve)"),
        ("asaas_pix", "Asaas Pix (Em breve)"),
        ("coinbase", "Coinbase (Em breve)"),
        ("nowpayments", "NOWPayments (Em breve)"),
        ("pix_manual", "PIX Manual"),
    ]


def _configured_providers() -> List[str]:
    cfg = _load_config()
    configured: List[str] = []
    def has(x: Optional[str]) -> bool:
        return bool(x and str(x).strip())
    # Mercado Pago
    if has((cfg.get("mercado_pago") or {}).get("access_token")):
        configured.append("mercado_pago")
    # EfiBank
    efi = cfg.get("efibank") or {}
    if has(efi.get("client_id") or efi.get("client")) and has(efi.get("client_secret") or efi.get("token")) and has(efi.get("pix_key")) and has(efi.get("cert_file")) and Path(str(efi.get("cert_file"))).exists():
        configured.append("efibank")
    # MisticPay
    mp = cfg.get("misticpay") or {}
    if has(mp.get("client_id")) and has(mp.get("client_secret")):
        configured.append("misticpay")
    # PagBank
    if has((cfg.get("pagbank") or {}).get("token_pagbank")):
        configured.append("pagbank")
    # PicPay
    if has((cfg.get("picpay") or {}).get("token_picpay")):
        configured.append("picpay")
    # PushinPay
    if has((cfg.get("pushinpay") or {}).get("token_pushinpay")):
        configured.append("pushinpay")
    # Stripe
    if has((cfg.get("stripe") or {}).get("token_stripe")):
        configured.append("stripe")
    # PayPal
    p = cfg.get("paypal") or {}
    if has(p.get("client_id")) and has(p.get("client_secret")):
        configured.append("paypal")
    # Asaas
    if has((cfg.get("asaas") or {}).get("token_asaas")):
        configured.append("asaas")
    # Coinbase
    if has((cfg.get("coinbase") or {}).get("token_coinbase")):
        configured.append("coinbase")
    # NOWPayments
    if has((cfg.get("nowpayments") or {}).get("token_nowpayments")):
        configured.append("nowpayments")
    # Sync Wallet
    if has((cfg.get("sync_wallet") or {}).get("api_key")):
        configured.append("sync_wallet")
    # PIX Manual
    pm = cfg.get("pix_manual") or {}
    if has(pm.get("pix_key")) and has(pm.get("pix_key_type")):
        configured.append("pix_manual")
    return configured


def _find_first(data: Any, keys: List[str]) -> Optional[Any]:
    if isinstance(data, dict):
        for k in keys:
            if k in data and data[k]:
                return data[k]
        for v in data.values():
            r = _find_first(v, keys)
            if r:
                return r
    elif isinstance(data, list):
        for it in data:
            r = _find_first(it, keys)
            if r:
                return r
    return None


def _extract_urls(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    checkout = _find_first(data, [
        "checkout_url",
        "url",
        "init_point",
        "init_url",
        "invoice_url",
        "payment_url",
        "hosted_url",
        "ticket_url",
        "link",
        "redirect_url",
    ])
    copy_code = _find_first(data, [
        "copy_paste",
        "pix_copia_cola",
        "emv",
        "code",
        "qr_code_text",
        "qrcode_text",
    ])
    return str(checkout) if checkout else None, str(copy_code) if copy_code else None


def _extract_qr_image(data: Dict[str, Any]) -> Tuple[Optional[bytes], Optional[str]]:
    # Primeiro tentar qr_code_bytes direto (PIX Manual, PushinPay, PagBank)
    qr_bytes = _find_first(data, ["qr_code_bytes"])
    if isinstance(qr_bytes, bytes):
        return qr_bytes, None
    
    # Tentar base64
    b64 = _find_first(data, [
        "qr_code_base64",
        "qrcode_base64",
        "qr_base64",
        "base64",
    ])
    if isinstance(b64, str):
        try:
            if b64.startswith("data:") and "," in b64:
                b64 = b64.split(",", 1)[1]
            raw = base64.b64decode(b64)
            return raw, "qrcode.png"
        except Exception:
            pass
    
    # Tentar URL
    url = _find_first(data, ["qr_code_url", "qrcode_url", "qr_url", "image", "qr_code_image", "qr_code_image_url"])
    return None, str(url) if url else None


def _api_base_root() -> str:
    base = PAY_API_BASE.rstrip("/")
    if "/api/" in base:
        return base.split("/api/", 1)[0]
    return base


async def _http_get_bytes(url: str, timeout: int = 15) -> Optional[bytes]:
    try:
        t = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=t) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception:
        return None
    return None


def _extract_payment_ids(data: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k in ["payment_id", "id", "payment_intent", "charge", "preference_id", "invoice_id"]:
        v = _find_first(data, [k])
        if v:
            out[k] = str(v)
    return out


def _status_approved(status: str) -> bool:
    s = status.lower()
    return s in {"approved", "paid", "completed", "succeeded", "accredited", "completo"}


def _status_final_failed(status: str) -> bool:
    s = status.lower()
    return s in {"canceled", "cancelled", "expired", "failed", "refunded", "chargeback"}


class PaymentCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def metodo_autocomplete(self, inter: disnake.AppCmdInter, string: str) -> List[str]:
        items = _providers_all()
        labels = [label for _, label in items]
        if string:
            labels = [l for l in labels if string.lower() in l.lower()]
        return labels[:25]

    def _resolve_method_key(self, label: str) -> Optional[str]:
        for key, lbl in _providers_all():
            if lbl.lower() == label.lower():
                return key
        return None

    @commands.slash_command(name="pagamento", description="Criar um pagamento", guild_ids=[utils.obter_server_principal()])
    async def pagamento(
        self,
        inter: disnake.AppCmdInter,
        metodo: str = commands.Param(autocomplete=metodo_autocomplete),
        valor: float = commands.Param(gt=0),
        user: disnake.Member = commands.Param(name="usuario"),
        descricao: Optional[str] = None,
    ):
        await embed_message.wait(inter, send=False)
        
        if not await perms.check(inter.user.id):
            await embed_message.error(inter, "Você não tem permissão para usar este comando", send=False)
            return
        
        key = self._resolve_method_key(metodo)
        if not key:
            await embed_message.error(inter, "Método não disponível.")
            return
        
        # Verificar se é um provedor "em breve"
        coming_soon = _providers_coming_soon()
        if key in coming_soon:
            await embed_message.error(
                inter, 
                f"{emoji.information} Essa forma de pagamento estará disponível em breve nas próximas atualizações."
            )
            return
        
        # Verificar se o plano permite este método de pagamento
        if not should_allow_payment_provider(key):
            await embed_message.error(
                inter, 
                f"{emoji.information} No plano atual, apenas **Sync Wallet** está disponível como forma de pagamento. Para usar outros métodos, faça upgrade do seu plano."
            )
            return
        
        base_key = key.split("_")[0] if key.startswith("asaas_") else key
        configured = set(_configured_providers())
        if base_key not in configured:
            conf_labels = []
            for k, lbl in _providers_all():
                b = k.split("_")[0] if k.startswith("asaas_") else k
                if b in configured and lbl not in conf_labels and k not in coming_soon:
                    conf_labels.append(lbl)
            names = ", ".join(conf_labels) if conf_labels else "Nenhum"
            await embed_message.error(inter, f"Método não configurado. Configurados: {names}")
            return
        try:
            if key == "sync_wallet":
                from functions.payments.sync_wallet import create_sync_payment_from_settings
                data = await create_sync_payment_from_settings(valor, description=descricao or f"Pagamento para {user.display_name}")
            elif key == "mercado_pago":
                data_pix = await create_mp_payment_from_settings(valor)
                data_site = await create_mp_site_payment_from_settings(valor)
                data = {"pix": data_pix, "site": data_site}
            elif key == "efibank":
                data = await create_efi_payment_from_settings(price=valor, nome_pagador=user.display_name, cpf_pagador=_generate_valid_cpf())
            elif key == "misticpay":
                data = await create_misticpay_payment_from_settings(
                    amount=valor,
                    payer_name=user.display_name,
                    payer_document=_generate_valid_cpf(),
                    description=descricao or f"Pagamento para {user.display_name}"
                )
            elif key == "pagbank":
                data = await create_pagbank_payment_from_settings(valor)
            elif key == "picpay":
                data = await create_picpay_payment_from_settings(valor)
            elif key == "pushinpay":
                data = await create_pushinpay_payment_from_settings(int(round(valor * 100)))
            elif key == "stripe":
                data = await create_stripe_payment_from_settings(valor)
            elif key == "paypal":
                data = await create_paypal_payment_from_settings(valor)
            elif key == "asaas_link":
                data = await create_asaas_payment_link_from_settings(valor)
            elif key == "asaas_pix":
                data = await create_asaas_pix_payment_from_settings(valor, customer=str(user.id))
            elif key == "coinbase":
                data = await create_coinbase_payment_from_settings(valor)
            elif key == "nowpayments":
                data = await create_nowpayments_invoice_from_settings(valor)
            elif key == "pix_manual":
                data = await create_manual_pix_payment(valor, description=descricao)
            else:
                await embed_message.error(inter, "Método não suportado.")
                return
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Erro ao criar pagamento {key}:")
            print(error_details)
            # Remover detalhes técnicos da mensagem exibida ao usuário
            error_msg = str(e)
            # Remover URLs e rotas de API da mensagem
            import re
            error_msg = re.sub(r'https?://[^\s]+', '', error_msg)
            error_msg = re.sub(r'/api/v\d+/[^\s]+', '', error_msg)
            error_msg = re.sub(r'/api/[^\s]+', '', error_msg)
            error_msg = re.sub(r'^\d+\s+', '', error_msg)  # Remover códigos HTTP
            error_msg = re.sub(r'pay\.syncapplications\.com\.br[^\s]*', '', error_msg, flags=re.IGNORECASE)
            error_msg = re.sub(r'\s+', ' ', error_msg).strip()
            
            # Se a mensagem ainda contém informações técnicas, usar mensagem genérica
            if not error_msg or len(error_msg) < 3 or 'http' in error_msg.lower() or '/api' in error_msg.lower():
                await embed_message.error(inter, "Erro ao criar pagamento. Verifique as configurações e tente novamente.")
            else:
                await embed_message.error(inter, f"Erro ao criar pagamento. Verifique as configurações e tente novamente.\n\n{error_msg}")
            return

        # Debug: mostrar dados recebidos
        print(f"📋 Dados do pagamento {key}:")
        print(f"  - Keys disponíveis: {list(data.keys()) if data else 'None'}")
        
        checkout_url, copy_code = _extract_urls(data or {})
        qr_bytes, qr_url = _extract_qr_image(data or {})
        ids = _extract_payment_ids(data or {})
        
        print(f"  - checkout_url: {checkout_url}")
        print(f"  - copy_code: {copy_code[:50] if copy_code else None}...")
        print(f"  - qr_bytes: {len(qr_bytes) if qr_bytes else 0} bytes")
        print(f"  - qr_url: {qr_url}")

        embed = disnake.Embed(title=f"Pagamento - {metodo}", description=descricao or "")
        embed.add_field(name="Valor", value=f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), inline=True)
        embed.add_field(name="Usuário", value=user.mention, inline=True)
        if ids:
            embed.add_field(name="Referências", value="\n".join(f"{k}: {v}" for k, v in ids.items()), inline=False)
        if qr_url:
            base_root = _api_base_root()
            full_url = str(qr_url)
            if full_url.startswith("/"):
                full_url = base_root + full_url
            fetched = await _http_get_bytes(full_url)
            if fetched:
                qr_bytes = fetched
                qr_url = None

        components: List[disnake.ui.ActionRow] = []
        row = []
        if copy_code:
            row.append(disnake.ui.Button(label="Copiar código", emoji=emoji.pix, style=disnake.ButtonStyle.grey, custom_id=f"pag_copy:{inter.id}"))
        if checkout_url:
            row.append(disnake.ui.Button(label="Abrir Checkout", style=disnake.ButtonStyle.url, url=str(checkout_url)))
        if row:
            components.append(disnake.ui.ActionRow(*row))

        files = None
        if qr_bytes and not qr_url:
            file = disnake.File(io.BytesIO(qr_bytes), filename="qrcode.png")
            embed.set_image(url="attachment://qrcode.png")
            files = [file]

        if files:
            await inter.edit_original_message(content=None, embed=embed, components=components, files=files)
        else:
            await inter.edit_original_message(content=None, embed=embed, components=components)
        msg = await inter.original_message()

        payments = _load_payments()
        payments.setdefault("items", {})
        rec_id = str(msg.id)
        payments["items"][rec_id] = {
            "message_id": msg.id,
            "channel_id": msg.channel.id,
            "guild_id": msg.guild.id if msg.guild else None,
            "user_id": user.id,
            "created_by": inter.author.id,
            "provider": key,
            "method_label": metodo,
            "amount": valor,
            "description": descricao,
            "status": "pending",
            "checkout_url": checkout_url,
            "copy_code": copy_code,
            "qr_url": qr_url,
            "ids": ids,
            "raw": data,
        }
        _save_payments(payments)

        if copy_code:
            async def on_copy_button(i: disnake.MessageInteraction):
                if i.component.custom_id == f"pag_copy:{inter.id}":
                    await embed_message.plain(i, copy_code, send=True, component=[])

            self.bot.add_listener(on_copy_button, "on_button_click")

        asyncio.create_task(self._monitor_payment(rec_id))

    async def _monitor_payment(self, rec_id: str):
        try:
            for _ in range(180):
                await asyncio.sleep(10)
                payments = _load_payments()
                rec = (payments.get("items") or {}).get(rec_id)
                if not rec:
                    return
                if rec.get("status") in {"approved", "paid", "completed"}:
                    return
                key = rec.get("provider")
                pid = rec.get("ids") or {}
                payment_id = pid.get("payment_id") or pid.get("id") or pid.get("payment_intent") or pid.get("invoice_id")
                if not payment_id:
                    continue
                try:
                    if key == "mercado_pago":
                        chk = await check_mp_payment_from_settings(payment_id)
                    elif key == "efibank":
                        chk = await check_efi_payment_from_settings(payment_id)
                    elif key == "misticpay":
                        chk = await check_misticpay_payment_from_settings(payment_id)
                    elif key == "pagbank":
                        chk = await check_pagbank_payment_from_settings(payment_id)
                    elif key == "picpay":
                        chk = await check_picpay_payment_from_settings(payment_id)
                    elif key == "pushinpay":
                        chk = await check_pushinpay_payment_from_settings(payment_id)
                    elif key == "stripe":
                        chk = await check_stripe_payment_from_settings(payment_id)
                    elif key == "paypal":
                        chk = await check_paypal_payment_from_settings(payment_id)
                    elif key == "asaas_link" or key == "asaas_pix":
                        chk = await check_asaas_payment_from_settings(payment_id)
                    elif key == "coinbase":
                        chk = await check_coinbase_payment_from_settings(payment_id)
                    elif key == "nowpayments":
                        chk = await check_nowpayments_invoice_from_settings(payment_id)
                    elif key == "pix_manual":
                        chk = await check_manual_pix_payment(payment_id)
                    elif key == "sync_wallet":
                        chk = await check_sync_payment_from_settings(payment_id)
                    else:
                        chk = {}
                except Exception:
                    chk = {}
                status = _find_first(chk, ["status", "payment_status", "state"]) or "pending"
                if isinstance(status, str) and _status_approved(status):
                    rec["status"] = "approved"
                    payments["items"][rec_id] = rec
                    _save_payments(payments)
                    
                    # Registrar pagamento no sistema de rendimentos
                    try:
                        user_id = rec.get("user_id")
                        amount = rec.get("amount") or 0
                        method_label = rec.get("method_label") or rec.get("provider", "unknown")
                        description = rec.get("description") or f"Pagamento via /pagamento - {method_label}"
                        payment_id = rec.get("ids", {}).get("payment_id") or rec.get("ids", {}).get("id")
                        
                        PurchaseManager.register_generic_payment(
                            user_id=user_id,
                            amount=amount,
                            payment_method=method_label,
                            description=description,
                            payment_id=payment_id,
                            metadata={
                                "source": "command_payment",
                                "message_id": rec_id,
                                "channel_id": rec.get("channel_id"),
                                "guild_id": rec.get("guild_id")
                            }
                        )
                    except Exception as e:
                        # Não bloquear o fluxo se houver erro no registro
                        print(f"Erro ao registrar pagamento no sistema de rendimentos: {e}")
                    
                    chan = self.bot.get_channel(rec.get("channel_id"))
                    if chan:
                        try:
                            msg = await chan.fetch_message(int(rec_id))
                            embed = msg.embeds[0] if msg.embeds else disnake.Embed(title="Pagamento")
                            embed.color = disnake.Color.green()
                            embed.add_field(name="Status", value=f"{emoji.correct} Aprovado", inline=False)
                            try:
                                embed.set_image(url=None)
                            except Exception:
                                pass
                            await msg.edit(embed=embed, components=[], attachments=[])
                        except Exception:
                            pass
                    try:
                        u = self.bot.get_user(rec.get("user_id"))
                        if u:
                            url = f"https://discord.com/channels/{rec.get('guild_id')}/{rec.get('channel_id')}/{rec_id}"
                            amount = rec.get("amount") or 0
                            amount_str = f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            title = f"Pagamento - {rec.get('method_label') or 'Pagamento'}"
                            desc = rec.get("description") or ""
                            dm_embed = disnake.Embed(title=title, description=desc, color=disnake.Color.green())
                            dm_embed.add_field(name="Valor", value=amount_str, inline=True)
                            dm_embed.add_field(name="Status", value=f"{emoji.correct} Aprovado", inline=False)
                            dm_row = disnake.ui.ActionRow(
                                disnake.ui.Button(label="Ir para a Mensagem", style=disnake.ButtonStyle.url, url=url)
                            )
                            await u.send(embed=dm_embed, components=[dm_row])
                    except Exception:
                        pass
                    return
                if isinstance(status, str) and _status_final_failed(status):
                    rec["status"] = status
                    payments["items"][rec_id] = rec
                    _save_payments(payments)
                    return
        except Exception:
            return


def setup(bot: commands.Bot):
    bot.add_cog(PaymentCog(bot))
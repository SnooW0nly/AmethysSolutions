"""
Utilitários compartilhados do carrinho.
Arquivo separado para evitar imports circulares entre buy_modal e checkout.
"""
import time
import json
from pathlib import Path
from typing import Dict, Union

import disnake
from functions.database import database as db
from functions.emoji import emoji

# Cache simples para métodos de pagamento (TTL de 30 segundos)
_payment_methods_cache = {"data": None, "timestamp": 0, "ttl": 30}


# ── Lê config_payments.json (mesmo padrão do cog de configuração) ─────────────
def _all_providers_enabled() -> bool:
    """Retorna True se todos os provedores estão liberados, False se modo restrito."""
    try:
        config_path = Path(__file__).parent
        for _ in range(6):
            candidate = config_path / "configs" / "config_payments.json"
            if candidate.exists():
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return bool(data.get("all_providers", True))
            config_path = config_path.parent
    except Exception:
        pass
    return True  # fallback: liberar tudo

_PROVIDERS_RESTRICTED = {"amethys_wallet", "pix_manual"}


def ensure_emoji(
    emoji_value: Union[str, disnake.PartialEmoji, disnake.Emoji, None]
) -> Union[str, disnake.PartialEmoji]:
    """
    Garante que o emoji seja convertido para PartialEmoji quando necessário.
    Isso permite que emojis de qualquer servidor funcionem em selects e botões.
    Se o emoji for inválido, retorna emoji.cardbox como fallback.
    """
    def _get_fallback():
        """Retorna o emoji.cardbox processado como fallback."""
        fallback = emoji.cardbox
        if isinstance(fallback, str) and fallback.startswith("<"):
            try:
                return disnake.PartialEmoji.from_str(fallback)
            except:
                pass
        return fallback

    # Se for None, usar fallback
    if emoji_value is None:
        return _get_fallback()

    # Se já for um objeto PartialEmoji ou Emoji, validar antes de retornar
    if isinstance(emoji_value, (disnake.PartialEmoji, disnake.Emoji)):
        try:
            if isinstance(emoji_value, disnake.Emoji):
                if not emoji_value.name or not emoji_value.id:
                    return _get_fallback()
                return disnake.PartialEmoji(name=emoji_value.name, id=emoji_value.id, animated=emoji_value.animated)
            else:
                if not emoji_value.name or not emoji_value.id:
                    return _get_fallback()
                return emoji_value
        except Exception:
            return _get_fallback()

    # Se for string que começa com < (emoji customizado)
    if isinstance(emoji_value, str) and emoji_value.startswith("<"):
        try:
            parsed = disnake.PartialEmoji.from_str(emoji_value)
            if not parsed.name or not parsed.id:
                return _get_fallback()
            return parsed
        except Exception:
            return _get_fallback()

    # Se for string Unicode (emoji padrão), validar se não está vazia
    if isinstance(emoji_value, str):
        if not emoji_value.strip():
            return _get_fallback()
        return emoji_value

    return _get_fallback()


def get_available_payment_methods() -> Dict[str, Dict[str, Union[str, disnake.PartialEmoji]]]:
    """Retorna os métodos de pagamento disponíveis e habilitados."""
    global _payment_methods_cache
    current_time = time.time()
    if (
        _payment_methods_cache["data"] is not None
        and (current_time - _payment_methods_cache["timestamp"]) < _payment_methods_cache["ttl"]
    ):
        return _payment_methods_cache["data"]

    # Lista de provedores que estão "em breve" (não devem aparecer)
    providers_coming_soon = [
        "pagbank", "picpay", "stripe", "nowpayments",
        "coinbase", "asaas", "paypal",
        "inter", "bitcoin", "litecoin", "ethereum", "livepix"
    ]

    all_methods = {
        "pix": {
            "label": "PIX",
            "description": "Pagamento instantâneo via PIX",
            "emoji": emoji.pix,
            "providers": ["amethys_wallet", "mercado_pago", "efibank", "pagbank", "picpay", "pushinpay", "misticpay", "asaas", "pix_manual", "nubank_imap"]
        },
        "card": {
            "label": "Cartão de Crédito",
            "description": "Pagamento via cartão de crédito",
            "emoji": emoji.card,
            "providers": ["stripe", "paypal", "asaas"]
        },
        "crypto": {
            "label": "Criptomoeda",
            "description": "Pagamento via criptomoedas",
            "emoji": emoji.coin,
            "providers": ["coinbase", "nowpayments"]
        }
    }

    pagamentos_doc = db.get_document("pagamentos") or {}
    payment_configs = db.get_document("payment_configs") or {}

    # Se modo restrito, só amethys_wallet e pix_manual são aceitos —
    # qualquer outro provider ativo no banco é ignorado.
    all_enabled = _all_providers_enabled()

    available: Dict[str, Dict[str, Union[str, disnake.PartialEmoji]]] = {}

    for method_key, method_info in all_methods.items():
        has_provider = False
        for provider in method_info["providers"]:
            if provider in providers_coming_soon:
                continue

            # Modo restrito: bloquear tudo que não seja amethys_wallet/pix_manual
            if not all_enabled and provider not in _PROVIDERS_RESTRICTED:
                continue

            provider_config = payment_configs.get(provider, {})

            is_enabled = False
            if isinstance(provider_config, dict):
                is_enabled = bool(provider_config.get("enabled", False))
            if not is_enabled:
                is_enabled = bool(pagamentos_doc.get(provider, False))

            has_valid_config = False
            if provider == "amethys_wallet":
                has_valid_config = bool(
                    (isinstance(provider_config, dict) and (provider_config.get("api_key") or provider_config.get("token") or provider_config.get("access_token")))
                    or is_enabled
                )
            elif isinstance(provider_config, dict) and provider_config:
                if provider == "mercado_pago":
                    has_valid_config = bool(provider_config.get("access_token"))
                elif provider == "efibank":
                    cert_path = provider_config.get("cert_file")
                    cert_ok = bool(cert_path) and Path(cert_path).exists()
                    has_client = bool(provider_config.get("client_id") or provider_config.get("client"))
                    has_secret = bool(provider_config.get("client_secret") or provider_config.get("token"))
                    has_pix = bool(provider_config.get("pix_key"))
                    has_valid_config = bool(has_client and has_secret and has_pix and cert_ok)
                elif provider in {"pagbank", "picpay", "pushinpay", "asaas", "stripe", "coinbase", "nowpayments"}:
                    token_key = {
                        "pagbank": "token_pagbank",
                        "picpay": "token_picpay",
                        "pushinpay": "token_pushinpay",
                        "asaas": "token_asaas",
                        "stripe": "token_stripe",
                        "coinbase": "token_coinbase",
                        "nowpayments": "token_nowpayments",
                    }.get(provider)
                    has_valid_config = bool(token_key and provider_config.get(token_key))
                elif provider == "paypal":
                    has_valid_config = bool(provider_config.get("client_id") and provider_config.get("client_secret"))
                elif provider == "misticpay":
                    client_id = provider_config.get("client_id")
                    client_secret = provider_config.get("client_secret")
                    has_valid_config = bool(client_id and client_secret)
                elif provider == "amethys_wallet":
                    has_valid_config = bool(provider_config.get("api_key") or provider_config.get("token") or provider_config.get("access_token"))
                elif provider == "sync_wallet":
                    has_valid_config = bool(provider_config.get("api_key"))
                elif provider == "pix_manual":
                    has_valid_config = bool(provider_config.get("pix_key") and provider_config.get("pix_key_type"))
                elif provider == "nubank_imap":
                    has_valid_config = bool(provider_config.get("email") and provider_config.get("password") and provider_config.get("pix_key"))
                else:
                    important_keys = [
                        "access_token", "client_id", "client_secret", "api_key",
                        "public_key", "secret_key", "token", "pix_key"
                    ]
                    has_valid_config = any(provider_config.get(key) for key in important_keys)

            if is_enabled and has_valid_config:
                has_provider = True
                break

        if has_provider:
            available[method_key] = {
                "label": method_info["label"],
                "description": method_info["description"],
                "emoji": method_info["emoji"],
            }

    _payment_methods_cache["data"] = available
    _payment_methods_cache["timestamp"] = current_time

    return available
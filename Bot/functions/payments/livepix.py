"""
LivePix Payment Integration
Integração genérica com a API LivePix via servidor Node.js.

ATENÇÃO: Quando obtiver a documentação oficial da LivePix, atualize:
  - O campo de credencial (token_livepix)
  - Os campos de resposta mapeados em create_livepix_payment_from_settings

A estrutura segue o mesmo padrão dos outros provedores (PushinPay, etc.):
o bot Python chama o servidor Node.js local, que faz a chamada real à API.
"""

import aiohttp
from typing import Any, Dict, Optional
import json

from functions.database import database as db


def _get_api_url() -> str:
    """Carrega URL da API de config_api.json"""
    try:
        import json as _json
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent / "configs" / "config_api.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = _json.load(f)
                api_url = config.get("payments", "localhost:22222")
                if not api_url.startswith(("http://", "https://")):
                    api_url = f"http://{api_url}"
                return api_url.rstrip("/")
    except Exception:
        pass
    return "https://amethyspayments.stackr.lat"


BASE_URL = f"{_get_api_url()}/api/v1"


def _load_config() -> dict:
    return db.get_document("payment_configs") or {}


def _require(value: Optional[str], what: str) -> str:
    if not value:
        raise ValueError(f"Missing {what} in LivePix settings.")
    return value


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
                raise RuntimeError(text)
            if data is None:
                raise RuntimeError("Resposta inválida do servidor")
            return data


# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------

async def create_livepix_payment(
    token_livepix: str,
    value: float,
    description: Optional[str] = None,
    expiration: int = 30,
) -> Dict[str, Any]:
    """
    Cria cobrança PIX via LivePix.

    Args:
        token_livepix: API key / access token da LivePix
        value: Valor em reais
        description: Descrição do pagamento (opcional)
        expiration: Minutos para expiração (padrão 30)

    Returns:
        Dict com payment_id, copy_paste, qr_code_image_url, checkout_url
    """
    import math
    value = math.ceil(value * 100) / 100

    payload: Dict[str, Any] = {
        "token_livepix": token_livepix,
        "value": value,
    }
    if description:
        payload["description"] = description
    if expiration:
        payload["expiration"] = expiration

    result = await _post_json("create-livepix-payment", payload)

    # Normalizar campos para compatibilidade com checkout.py
    if result:
        result.setdefault("_provider", "livepix")
        # Mapear copy_paste → pix_copia_cola se necessário
        if result.get("copy_paste") and not result.get("pix_copia_cola"):
            result["pix_copia_cola"] = result["copy_paste"]

        # Gerar QR Code bytes localmente se a rota do servidor retornou uma URL
        qr_url = result.get("qr_code_image_url")
        if qr_url and not result.get("qr_code_bytes"):
            try:
                from modules.loja.personalization.qr_customization import QRCodeGenerator
                pix_code = result.get("copy_paste") or result.get("pix_copia_cola")
                if pix_code:
                    result["qr_code_bytes"] = await QRCodeGenerator.generate_custom_qr(pix_code)
            except Exception:
                pass

    return result


async def check_livepix_payment(
    token_livepix: str,
    payment_id: str,
) -> Dict[str, Any]:
    """
    Verifica status de uma cobrança LivePix.

    Returns:
        Dict com campo 'status': 'approved' | 'cancelled' | 'pending'
    """
    return await _post_json("check-livepix-payment", {
        "token_livepix": token_livepix,
        "payment_id": payment_id,
    })


# ---------------------------------------------------------------------------
# Wrappers usando configurações salvas no database
# ---------------------------------------------------------------------------

async def create_livepix_payment_from_settings(
    value: float,
    description: Optional[str] = None,
    expiration: int = 30,
) -> Dict[str, Any]:
    """Cria pagamento LivePix usando token salvo nas configurações."""
    cfg = _load_config().get("livepix") or {}
    token = _require(cfg.get("token_livepix"), "LivePix token_livepix")
    return await create_livepix_payment(token, value, description=description, expiration=expiration)


async def check_livepix_payment_from_settings(payment_id: str) -> Dict[str, Any]:
    """Verifica pagamento LivePix usando token salvo nas configurações."""
    cfg = _load_config().get("livepix") or {}
    token = _require(cfg.get("token_livepix"), "LivePix token_livepix")
    return await check_livepix_payment(token, payment_id)


__all__ = [
    "create_livepix_payment",
    "check_livepix_payment",
    "create_livepix_payment_from_settings",
    "check_livepix_payment_from_settings",
]
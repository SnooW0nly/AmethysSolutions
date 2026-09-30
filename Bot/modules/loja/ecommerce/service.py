import aiohttp
import json
from typing import Tuple, Optional


def _get_api_base_url() -> str:
    try:
        with open("configs/config_api.json", "r", encoding="utf-8") as f:
            return json.load(f).get("marketplace", "https://amethysmarcktplace.stackr.lat").rstrip("/")
    except Exception:
        return "https://amethysmarcktplace.stackr.lat"


def _get_api_secret() -> str:
    try:
        with open("configs/config_api.json", "r", encoding="utf-8") as f:
            return json.load(f).get("marketplace_secret", "")
    except Exception:
        return ""


def _get_collection_id() -> str:
    try:
        with open("configs/config.json", "r", encoding="utf-8") as f:
            return json.load(f).get("botID", "")
    except Exception:
        return ""


class MarketplaceService:

    @staticmethod
    def _headers() -> dict:
        return {
            "Authorization": f"Bearer {_get_api_secret()}",
            "Content-Type": "application/json",
        }

    @staticmethod
    async def _post(path: str, payload: dict) -> Tuple[bool, Optional[dict], Optional[str]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{_get_api_base_url()}/api/v1{path}",
                    json=payload,
                    headers=MarketplaceService._headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    try:
                        body = await resp.json(content_type=None)
                    except Exception:
                        body = {}
                    body = body if isinstance(body, dict) else {}
                    if resp.status in (200, 201):
                        return True, body.get("data"), None
                    return False, None, body.get("error", f"HTTP {resp.status}")
        except Exception as e:
            return False, None, str(e)

    @staticmethod
    async def ensure_registered(bot_id: str, bot_name: str) -> Tuple[bool, Optional[str]]:
        """Registra o bot na API se ainda não existir."""
        ok, _, err = await MarketplaceService._post(
            "/ecommerce/register",
            {"bot_id": bot_id, "bot_name": bot_name, "collection_id": _get_collection_id()},
        )
        return (True, None) if ok else (False, err)

    @staticmethod
    async def generate_link_code(bot_id: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Gera um código temporário de vinculação bot ↔ loja (válido 10 min)."""
        return await MarketplaceService._post(f"/ecommerce/{bot_id}/link-code", {})
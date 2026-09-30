"""
Cliente para a nova API de Pagamentos (localhost:22222)
Substitui as chamadas para pay.syncapplications.com.br
"""
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from functions.database import database as db

class PaymentAPIClient:
    """Cliente HTTP para API de Pagamentos"""
    
    def __init__(self):
        self.base_url = self._get_api_url()
        self.session: Optional[aiohttp.ClientSession] = None
    
    def _get_api_url(self) -> str:
        """Obtém URL da API do config"""
        try:
            config = db.obter("configs/config_api.json") or {}
            api_url = config.get("payments", "localhost:22222")
            
            # Adicionar http:// se não tiver
            if not api_url.startswith("http"):
                api_url = f"http://{api_url}"
            
            return api_url
        except Exception:
            return "https://amethyspayments.stackr.lat"
    
    async def _ensure_session(self):
        """Garante que a sessão HTTP existe"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Fecha a sessão HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _post_json(self, path: str, payload: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
        """Faz requisição POST para a API"""
        await self._ensure_session()
        
        url = f"{self.base_url}/api/v1/{path}"
        
        try:
            async with self.session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                text = await resp.text()
                
                if resp.status >= 400:
                    raise RuntimeError(f"Erro na API: {text}")
                
                try:
                    return await resp.json()
                except Exception:
                    raise RuntimeError("Resposta inválida do servidor")
        
        except asyncio.TimeoutError:
            raise RuntimeError(f"Timeout ao conectar com API ({timeout}s)")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Erro de conexão com API: {str(e)}")
    
    # ==================== MERCADO PAGO ====================
    
    async def create_mp_payment(self, token_mp: str, value: float, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Cria pagamento Mercado Pago
        
        Args:
            token_mp: Token de acesso do Mercado Pago
            value: Valor do pagamento
            webhook_url: URL para notificar quando pagamento for aprovado (opcional)
        
        Returns:
            Dict com dados do pagamento
        """
        payload = {
            "token_mp": token_mp,
            "value": value
        }
        
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        return await self._post_json("create-mp-payment", payload)
    
    async def check_mp_payment(self, token_mp: str, payment_id: str) -> Dict[str, Any]:
        """
        Verifica status de pagamento Mercado Pago
        
        Args:
            token_mp: Token de acesso do Mercado Pago
            payment_id: ID do pagamento
        
        Returns:
            Dict com status do pagamento
        """
        return await self._post_json("check-mp-payment", {
            "token_mp": token_mp,
            "payment_id": payment_id
        })


# Instância global
_api_client: Optional[PaymentAPIClient] = None


def get_api_client() -> PaymentAPIClient:
    """Obtém instância global do cliente"""
    global _api_client
    if _api_client is None:
        _api_client = PaymentAPIClient()
    return _api_client


# ==================== FUNÇÕES COMPATÍVEIS ====================
# Mantém compatibilidade com código existente

async def create_mp_payment_from_api(value: float, webhook_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Cria pagamento MP via nova API (compatível com código existente)
    
    Args:
        value: Valor do pagamento
        webhook_url: URL para notificar quando pagamento for aprovado (opcional)
    """
    # Obter token das configurações
    payment_configs = db.get_document("payment_configs") or {}
    mp_config = payment_configs.get("mercado_pago", {})
    token_mp = mp_config.get("access_token")
    
    if not token_mp:
        raise ValueError("Token do Mercado Pago não configurado")
    
    client = get_api_client()
    return await client.create_mp_payment(token_mp, value, webhook_url)


async def check_mp_payment_from_api(payment_id: str) -> Dict[str, Any]:
    """
    Verifica pagamento MP via nova API (compatível com código existente)
    """
    # Obter token das configurações
    payment_configs = db.get_document("payment_configs") or {}
    mp_config = payment_configs.get("mercado_pago", {})
    token_mp = mp_config.get("access_token")
    
    if not token_mp:
        raise ValueError("Token do Mercado Pago não configurado")
    
    client = get_api_client()
    return await client.check_mp_payment(token_mp, payment_id)

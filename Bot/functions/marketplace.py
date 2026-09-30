"""
functions/marketplace.py
────────────────────────
Utilitários para o Marketplace de Revenda.

Responsabilidade única: varrer TODOS os documentos `loja_products`
de TODOS os bots na database compartilhada e retornar somente os
produtos com `info.resale == True`.

A conexão aponta para a collection global (mesma usada pelo bot_collection),
mas faz uma query direta no MongoDB sem passar pelo cache local da `database`,
pois os dados pertencem a outros bots e não devem ser cacheados junto
com os documentos locais.

NOTAS DE CONCORRÊNCIA
─────────────────────
• fetch_resale_products() é síncrona e bloqueante (pymongo).
  Nunca a chame diretamente de uma coroutine — use sempre:
      await asyncio.to_thread(fetch_resale_products, force_refresh=True)
• _MarketplaceCache usa threading.Lock porque fetch_resale_products()
  é executada em threads de I/O via asyncio.to_thread.  Dentro de
  coroutines use apenas as funções de leitura (get/set/invalidate) —
  elas são breves o suficiente para não impactar o event loop.
"""

from __future__ import annotations

import time
import threading
import copy
import datetime
from dataclasses import dataclass, field

from connections.mongo_db import collection as bot_collection, database as mongo_database


# ──────────────────────────────────────────────────────────────────────────────
#  Estrutura de dados
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ResaleProduct:
    """Representa um produto com revenda ativa de qualquer bot."""

    # Identificação
    product_id: str
    bot_id: str          # _id do documento `loja_products` que o originou
    name: str

    # Informações exibíveis
    description: str | None = None
    banner: str | None = None
    hex_color: str | None = None
    delivery_type: str = "manual"   # "automatic" | "manual"

    # Stats
    total_paid: float = 0.0
    purchases: int = 0

    # Comissão do revendedor em % (ex: 10.0 = 10%)
    resale_commission: float = 0.0

    # Categorias disponíveis (lista de dicts com name/price/stock/resale_price)
    categorias: list[dict] = field(default_factory=list)

    # ── helpers ──────────────────────────────────────────────────────────────

    @property
    def delivery_label(self) -> str:
        return "Automático" if self.delivery_type == "automatic" else "Manual"

    @property
    def commission_label(self) -> str:
        """Comissão formatada para exibição."""
        return f"{self.resale_commission:g}%"

    @staticmethod
    def apply_commission(price: float, commission: float) -> float:
        """Retorna o preço com a comissão do revendedor aplicada."""
        return round(price * (1 + commission / 100), 2)

    @property
    def select_label(self) -> str:
        """Label truncado para caber em SelectOption (máx 100 chars)."""
        label = self.name
        return label[:97] + "..." if len(label) > 100 else label

    @property
    def select_description(self) -> str:
        """Descrição truncada para SelectOption (máx 100 chars)."""
        base = (self.description or "Sem descrição").replace("\n", " ").strip()
        return base[:97] + "..." if len(base) > 97 else base

    @property
    def select_value(self) -> str:
        """Valor único para o SelectOption: bot_id::product_id."""
        return f"{self.bot_id}::{self.product_id}"


# ──────────────────────────────────────────────────────────────────────────────
#  Cache dedicado para o marketplace (TTL curto — dados externos)
# ──────────────────────────────────────────────────────────────────────────────

class _MarketplaceCache:
    """
    Cache thread-safe para a lista de produtos de revenda.

    Usa threading.Lock porque fetch_resale_products() roda em threads de I/O
    (asyncio.to_thread).  As operações de leitura/escrita são O(1) e muito
    rápidas — o lock nunca ficará contido por mais de microssegundos.
    """

    _CACHE_TTL: float = 120.0  # 2 minutos

    _data: list[ResaleProduct] | None = None
    _expiry: float = 0.0
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get(cls) -> list[ResaleProduct] | None:
        with cls._lock:
            if cls._data is not None and time.monotonic() < cls._expiry:
                return copy.copy(cls._data)   # shallow copy — lista nova, objetos imutáveis
            return None

    @classmethod
    def set(cls, products: list[ResaleProduct]) -> None:
        with cls._lock:
            cls._data = products
            cls._expiry = time.monotonic() + cls._CACHE_TTL

    @classmethod
    def invalidate(cls) -> None:
        with cls._lock:
            cls._data = None
            cls._expiry = 0.0

    @classmethod
    def is_warm(cls) -> bool:
        """True se o cache tem dados válidos (sem adquirir lock externo)."""
        with cls._lock:
            return cls._data is not None and time.monotonic() < cls._expiry


_marketplace_cache = _MarketplaceCache()


# ──────────────────────────────────────────────────────────────────────────────
#  Parser interno
# ──────────────────────────────────────────────────────────────────────────────

def _parse_products_doc(raw_doc: dict) -> list[ResaleProduct]:
    """
    Converte um documento `loja_products` bruto em lista de ResaleProduct.
    Filtra apenas produtos com info.resale == True.
    """
    bot_id: str = str(raw_doc.get("_id", "unknown"))
    products: list[ResaleProduct] = []

    for product_id, product_data in raw_doc.items():
        if product_id.startswith("_"):
            continue
        if not isinstance(product_data, dict):
            continue

        info: dict = product_data.get("info", {})

        # ── filtros principais ────────────────────────────────────────────────
        if not info.get("resale", False):
            continue
        if info.get("is_subscription", False):
            continue

        commission = float(info.get("resale_commission", 0))

        # ── extrai campos (exclui assinaturas) ───────────────────────────────
        raw_campos: dict = product_data.get("campos", {})
        categorias: list[dict] = []
        for campo_id, campo_data in raw_campos.items():
            if not isinstance(campo_data, dict):
                continue
            if campo_data.get("is_subscription", False):
                continue
            base_price = float(campo_data.get("price", 0.0))
            resale_price = ResaleProduct.apply_commission(base_price, commission)
            infinite = campo_data.get("infinite_stock", {}).get("enabled", False)
            categorias.append({
                "id": campo_id,
                "name": campo_data.get("name", campo_id),
                "price": base_price,
                "resale_price": resale_price,
                "stock": -1 if infinite else 0,
            })

        if not categorias:
            continue

        products.append(ResaleProduct(
            product_id=product_id,
            bot_id=bot_id,
            name=product_data.get("name", "Sem nome"),
            description=info.get("description"),
            banner=info.get("banner"),
            hex_color=info.get("hex_color"),
            delivery_type=info.get("delivery_type", "manual"),
            total_paid=float(info.get("total_paid", 0)),
            purchases=len(info.get("purchasesIds", [])),
            resale_commission=commission,
            categorias=categorias,
        ))

    return products


# ──────────────────────────────────────────────────────────────────────────────
#  Funções públicas — fetch e cache
# ──────────────────────────────────────────────────────────────────────────────

def fetch_resale_products(*, force_refresh: bool = False) -> list[ResaleProduct]:
    """
    Retorna todos os produtos com revenda ativa de todos os bots.

    ⚠️  BLOQUEANTE — usa pymongo síncrono.
    Dentro de coroutines, chame sempre via:
        await asyncio.to_thread(fetch_resale_products, force_refresh=True)

    Itera todas as collections do banco (cada uma = um bot) e busca o documento
    `loja_products` em cada uma.  Usa cache interno de 2 minutos.
    Passe `force_refresh=True` para ignorar o cache.
    """
    if not force_refresh:
        cached = _marketplace_cache.get()
        if cached is not None:
            return cached

    products: list[ResaleProduct] = []

    try:
        collection_names: list[str] = mongo_database.list_collection_names()
    except Exception as e:
        print(f"[Marketplace] Erro ao listar collections: {e}")
        # Retorna cache expirado se disponível, evita tela vazia
        with _marketplace_cache._lock:
            return copy.copy(_marketplace_cache._data) if _marketplace_cache._data else []

    for col_name in collection_names:
        if col_name.startswith("_") or col_name.startswith("system."):
            continue
        try:
            col = mongo_database[col_name]
            raw_doc = col.find_one({"_id": "loja_products"})
            if raw_doc is None:
                continue
            raw_doc["_id"] = col_name
            products.extend(_parse_products_doc(raw_doc))
        except Exception as e:
            print(f"[Marketplace] Erro ao ler collection '{col_name}': {e}")

    products.sort(key=lambda p: p.name.lower())
    _marketplace_cache.set(products)
    return products


def get_owner_amethys_config(owner_bot_id: str) -> dict | None:
    """
    Busca a configuração da Amethys Wallet do bot dono do produto.

    ⚠️  BLOQUEANTE — use asyncio.to_thread se chamado de coroutine.
    """
    try:
        col = mongo_database[owner_bot_id]
        doc = col.find_one({"_id": "payment_configs"})
        if not doc:
            return None
        aw_cfg = doc.get("amethys_wallet")
        if not isinstance(aw_cfg, dict):
            return None
        if not aw_cfg.get("api_key"):
            return None
        return aw_cfg
    except Exception as e:
        print(f"[Marketplace] Erro ao buscar payment_configs do bot '{owner_bot_id}': {e}")
        return None


def invalidate_marketplace_cache() -> None:
    """
    Invalida o cache do marketplace.
    Chamar após qualquer alteração no toggle de revenda de um produto.
    """
    _marketplace_cache.invalidate()


def paginate_products(
    products: list[ResaleProduct],
    page: int,
    page_size: int = 20,
) -> tuple[list[ResaleProduct], int, int]:
    """
    Pagina a lista de produtos.
    Retorna: (produtos_da_página, total_páginas, página_atual_clampada)
    """
    total = len(products)
    if total == 0:
        return [], 0, 0

    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return products[start:start + page_size], total_pages, page


# ──────────────────────────────────────────────────────────────────────────────
#  Estrutura de revendas ativas (marketplace_resellers)
# ──────────────────────────────────────────────────────────────────────────────
#
#  Documento salvo na database local do bot com chave "marketplace_resellers".
#  Estrutura:
#  {
#    "{user_id}": {
#      "{bot_id}::{product_id}": {
#        "user_id": str,
#        "guild_id": str,
#        "guild_name": str,
#        "channel_id": str,
#        "product_name": str,
#        "bot_id": str,
#        "product_id": str,
#        "started_at": int (timestamp Unix),
#        "cooldown_until": int (timestamp Unix, 0 = sem cooldown),
#      }
#    }
#  }

_COOLDOWN_SECONDS = 30 * 60  # 30 minutos


def get_reseller_doc() -> dict:
    from functions.database import database as db
    return db.get_document("marketplace_resellers") or {}


def save_reseller_doc(doc: dict) -> None:
    from functions.database import database as db
    db.save_document("marketplace_resellers", doc)


def get_user_resales(user_id: str) -> dict:
    """Retorna todas as revendas ativas de um usuário. {select_value: {...}}"""
    return get_reseller_doc().get(str(user_id), {})


def is_in_cooldown(user_id: str | int, select_value: str) -> tuple[bool, int]:
    """
    Verifica se o usuário ainda está em cooldown para aquele produto.
    Retorna (em_cooldown, segundos_restantes).
    """
    doc = get_reseller_doc()
    entry = doc.get(str(user_id), {}).get(select_value, {})
    cooldown_until = entry.get("cooldown_until", 0)
    now = int(time.time())
    if cooldown_until > now:
        return True, cooldown_until - now
    return False, 0


def start_resale(
    user_id: str,
    guild_id: str,
    guild_name: str,
    channel_id: str,
    product: ResaleProduct,
) -> bool:
    """
    Registra uma revenda ativa. Retorna False se em cooldown.
    """
    key = product.select_value
    in_cd, _ = is_in_cooldown(user_id, key)
    if in_cd:
        return False

    doc = get_reseller_doc()
    user_entry = doc.setdefault(str(user_id), {})
    user_entry[key] = {
        "user_id": str(user_id),
        "guild_id": str(guild_id),
        "guild_name": guild_name,
        "channel_id": str(channel_id),
        "product_name": product.name,
        "bot_id": product.bot_id,
        "product_id": product.product_id,
        "started_at": int(time.time()),
        "cooldown_until": 0,
    }
    save_reseller_doc(doc)
    return True


def stop_resale(user_id: str | int, select_value: str) -> dict | None:
    """
    Para uma revenda ativa e aplica cooldown de 30 min.
    Retorna o registro removido (para notificação) ou None se não encontrado.
    """
    doc = get_reseller_doc()
    user_entry = doc.get(str(user_id), {})
    entry = user_entry.pop(select_value, None)
    if entry is None:
        return None

    # Guarda registro "fantasma" apenas com o cooldown
    user_entry[select_value] = {
        "cooldown_until": int(time.time()) + _COOLDOWN_SECONDS,
    }
    doc[str(user_id)] = user_entry
    save_reseller_doc(doc)
    return entry


def is_already_reselling(user_id: str | int, select_value: str) -> bool:
    """Verifica se o usuário já está revendendo aquele produto."""
    doc = get_reseller_doc()
    entry = doc.get(str(user_id), {}).get(select_value, {})
    return "started_at" in entry
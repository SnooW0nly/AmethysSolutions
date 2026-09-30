"""
modules/automations/random_usernames/functions.py

Geração e validação de usernames disponíveis no Discord via user token (Full HTTPS).

Sobre o modo Repeat:
  - OFF (padrão): cada char é diferente do anterior — ex: "a3b", "x9y2"
  - ON:  permite chars REPETIDOS consecutivos — ex: "aaaa", "7d7d", "kkkk", "aabb"
         Isso inclui padrões tipo KKKK ou sequências alternadas.
"""
from __future__ import annotations

import asyncio
import logging
import random
import string
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"

# Chars permitidos pelo Discord em usernames
_CHARS       = string.ascii_lowercase + string.digits + "_."
_CHARS_INICIO = string.ascii_lowercase + string.digits   # não pode iniciar com . ou _


# ══════════════════════════════════════════════════════════════════════════════
# Geração de usernames
# ══════════════════════════════════════════════════════════════════════════════

def gerar_username(comprimento: int, repeat: bool) -> str:
    """
    Gera um username aleatório.

    repeat=False → cada char é obrigatoriamente diferente do anterior
                   (sem repetições consecutivas: "abc", "a3b2")
    repeat=True  → sem restrição de repetição — pode gerar "aaaa",
                   "7d7d7d", "kkkk", "aabb", etc.
    """
    if comprimento < 2:
        comprimento = 2

    resultado: list[str] = [random.choice(_CHARS_INICIO)]

    for _ in range(comprimento - 1):
        if repeat:
            # Qualquer char, inclusive repetido
            c = random.choice(_CHARS)
        else:
            # Diferente do último
            ultimo    = resultado[-1]
            candidatos = [c for c in _CHARS if c != ultimo]
            c         = random.choice(candidatos)
        resultado.append(c)

    # Não pode terminar com . ou _
    if resultado[-1] in (".", "_"):
        resultado[-1] = random.choice(string.ascii_lowercase + string.digits)

    return "".join(resultado)


def gerar_lote(comprimento: int, repeat: bool, quantidade: int = 20) -> list[str]:
    """Gera um lote de usernames únicos."""
    gerados: set[str] = set()
    limite  = quantidade * 60

    for _ in range(limite):
        if len(gerados) >= quantidade:
            break
        gerados.add(gerar_username(comprimento, repeat))

    return list(gerados)


# ══════════════════════════════════════════════════════════════════════════════
# Validação via Discord API
# ══════════════════════════════════════════════════════════════════════════════

async def verificar_username_disponivel(
    session: aiohttp.ClientSession,
    token: str,
    username: str,
) -> bool:
    """
    Testa se um username está disponível via endpoint pomelo do Discord.
    GET /users/@me/pomelo-attempt?username=...
    Retorna True se disponível, False caso contrário.
    Não altera nada na conta.
    """
    headers = {"Authorization": token}
    url     = f"{DISCORD_API_BASE}/users/@me/pomelo-attempt"
    params  = {"username": username}

    try:
        async with session.get(
            url,
            headers=headers,
            params=params,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:

            if resp.status == 200:
                data  = await resp.json(content_type=None)
                taken = data.get("taken", True)
                return not taken

            if resp.status == 401:
                log.warning("[RandomUsernames] Token inválido/expirado.")
                return False

            if resp.status == 429:
                try:
                    retry_after = float((await resp.json(content_type=None)).get("retry_after", 5))
                except Exception:
                    retry_after = 5.0
                log.warning("[RandomUsernames] Rate limit — aguardando %.1fs.", retry_after)
                await asyncio.sleep(retry_after)
                return False

            log.debug("[RandomUsernames] Status %s para '%s'.", resp.status, username)
            return False

    except asyncio.TimeoutError:
        log.warning("[RandomUsernames] Timeout ao verificar '%s'.", username)
        return False
    except aiohttp.ClientError as e:
        log.warning("[RandomUsernames] Erro de rede ao verificar '%s': %s", username, e)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Escaneamento em lote
# ══════════════════════════════════════════════════════════════════════════════

async def escanear_usernames(
    token: str,
    comprimentos_ativos: list[int],
    repeat: bool,
    quantidade_por_comprimento: int = 10,
    delay_entre_requests: float = 1.2,
) -> list[dict]:
    """
    Escaneia usernames para cada comprimento ativo.

    Retorna lista de dicts:
        {"username": str, "comprimento": int, "disponivel": bool}
    """
    if not comprimentos_ativos:
        return []

    resultados: list[dict] = []

    connector = aiohttp.TCPConnector(
        ssl=True,          # Full HTTPS / TLS verificado
        limit=5,
        ttl_dns_cache=300,
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        for comprimento in comprimentos_ativos:
            lote = gerar_lote(comprimento, repeat, quantidade_por_comprimento)

            for username in lote:
                disponivel = await verificar_username_disponivel(session, token, username)

                resultados.append({
                    "username":    username,
                    "comprimento": comprimento,
                    "disponivel":  disponivel,
                })

                log.debug(
                    "[RandomUsernames] '%s' (%dl) → %s",
                    username,
                    comprimento,
                    "✅" if disponivel else "❌",
                )

                await asyncio.sleep(delay_entre_requests)

    return resultados


def filtrar_disponiveis(resultados: list[dict]) -> list[dict]:
    return [r for r in resultados if r.get("disponivel")]
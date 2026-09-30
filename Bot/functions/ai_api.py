"""
Função centralizada para chamadas à API de IA.

Fluxo:
  1. Tenta a API CyM (própria) via API Key de owner
  2. Fallback automático para Groq direto se CyM falhar
"""
import aiohttp
import asyncio
import os

# ─── Configurações da API CyM (primária) ─────────────────────────────────────

CYM_BASE_URL = os.getenv("CYM_BASE_URL", "")
CYM_API_KEY = os.getenv("CYM_API_KEY", "")
CYM_AI_URL    = f"{CYM_BASE_URL}/api/ai/generate"
CYM_MODEL     = "CyM Pro"                       # Único com vision e melhor qualidade

# ─── Configurações do Groq (fallback) ────────────────────────────────────────

GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEYS = [key for key in os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", "")).split(",") if key]

# Modelos Groq ordenados do mais barato ao mais caro (só acionados no fallback)
GROQ_MODELS = [
    "llama-3.1-8b-instant",          # $0.05/$0.08 — mais rápido
    "openai/gpt-oss-20b",            # $0.075/$0.30
    "openai/gpt-oss-120b",           # $0.15/$0.60
    "llama-3.3-70b-versatile",       # $0.59/$0.79 — mais potente
]

# ─── Rotação de chaves Groq ───────────────────────────────────────────────────

_groq_key_index = 0

def _get_next_groq_key() -> str:
    global _groq_key_index
    if not GROQ_API_KEYS:
        return ""
    key = GROQ_API_KEYS[_groq_key_index]
    _groq_key_index = (_groq_key_index + 1) % len(GROQ_API_KEYS)
    return key

# ─── Chamada à API CyM ────────────────────────────────────────────────────────

async def _call_cym(
    conteudo: str,
    module_name: str = "IA",
    system_prompt: str | None = None,
    model: str = CYM_MODEL,
) -> tuple[str, bool]:
    """
    Chama POST /api/ai/generate da API CyM.

    Formato aceito pelo hybridAuthMiddleware:
        Header: X-API-Key: cym-xxx
    
    Formato do body (aiController.js):
        { model: str, messages: [ { role, content }, ... ] }

    Retorna (resposta, sucesso).
    """
    messages: list[dict] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": conteudo})

    payload = {
        "model":    model,
        "messages": messages,
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key":    CYM_API_KEY,      # hybridAuthMiddleware lê este header
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                CYM_AI_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as resp:

                # ── Erros conhecidos da API ──────────────────────────────────
                if resp.status == 401:
                    text = await resp.text()
                    print(f"❌ CyM API Key inválida/expirada ({module_name}): {text[:200]}")
                    return ("", False)

                if resp.status == 403:
                    text = await resp.text()
                    print(f"❌ CyM sem permissão ({module_name}): {text[:200]}")
                    # requirePermission('ai.generate') falhou — API Key não tem a permissão
                    return ("", False)

                if resp.status == 402:
                    # Créditos insuficientes — não deveria ocorrer com owner key,
                    # mas tratamos por segurança
                    print(f"⚠️ CyM créditos insuficientes ({module_name}) — usando fallback Groq")
                    return ("", False)

                if resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    print(f"⚠️ CyM rate limit ({module_name}) — aguardando {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    return ("", False)

                if resp.status >= 500:
                    text = await resp.text()
                    print(f"⚠️ CyM erro do servidor {resp.status} ({module_name}): {text[:200]}")
                    return ("", False)

                if resp.status != 200:
                    text = await resp.text()
                    print(f"⚠️ CyM status inesperado {resp.status} ({module_name}): {text[:200]}")
                    return ("", False)

                # ── Decode JSON ──────────────────────────────────────────────
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    text = await resp.text()
                    print(f"⚠️ CyM resposta não é JSON ({module_name}): {text[:200]}")
                    return ("", False)

                try:
                    data = await resp.json()
                    # aiController retorna { reply, creditsRemaining, modelUsed, visionUsed }
                    reply = data.get("reply", "").strip()
                    if reply:
                        return (reply, True)
                    print(f"⚠️ CyM retornou reply vazio ({module_name})")
                    return ("", False)
                except Exception as e:
                    print(f"⚠️ CyM erro ao decodificar JSON ({module_name}): {e}")
                    return ("", False)

    except aiohttp.ClientError as e:
        print(f"⚠️ CyM erro de conexão ({module_name}): {e}")
        return ("", False)
    except asyncio.TimeoutError:
        print(f"⚠️ CyM timeout ({module_name}) — usando fallback Groq")
        return ("", False)
    except Exception as e:
        print(f"⚠️ CyM erro inesperado ({module_name}): {type(e).__name__}: {e}")
        return ("", False)

# ─── Fallback Groq ────────────────────────────────────────────────────────────

async def _call_groq(
    conteudo: str,
    module_name: str = "IA",
    max_retries: int = 3,
    system_prompt: str | None = None,
) -> str:
    """
    Fallback: chama a API Groq diretamente com retry + fallback de modelos.
    Retorna a resposta ou string vazia em caso de falha total.
    """
    for model_index, model in enumerate(GROQ_MODELS):
        for attempt in range(max_retries):
            try:
                api_key = _get_next_groq_key()

                messages: list[dict] = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": conteudo})

                max_tokens = 1024 if "llama-guard" in model else 2048

                payload = {
                    "model":       model,
                    "messages":    messages,
                    "temperature": 0.7,
                    "max_tokens":  max_tokens,
                }

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type":  "application/json",
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        GROQ_URL,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:

                        if resp.status == 200:
                            try:
                                data    = await resp.json()
                                content = (
                                    data.get("choices", [{}])[0]
                                        .get("message", {})
                                        .get("content", "")
                                )
                                if content:
                                    if model_index > 0:
                                        print(f"✅ Groq ({module_name}): sucesso com modelo fallback {model}")
                                    elif attempt > 0:
                                        print(f"✅ Groq ({module_name}): sucesso após {attempt + 1} tentativa(s)")
                                    return content.strip()
                            except Exception as e:
                                print(f"⚠️ Groq erro ao decodificar resposta ({module_name}): {e}")

                        elif resp.status == 400:
                            try:
                                error_data = await resp.json()
                                error_msg  = error_data.get("error", {}).get("message", "")
                                if "decommissioned" in error_msg.lower() or "no longer supported" in error_msg.lower():
                                    print(f"⚠️ Groq modelo {model} descontinuado ({module_name}) — próximo modelo...")
                                    break  # próximo modelo
                                print(f"⚠️ Groq erro 400 ({module_name}): {error_msg}")
                            except Exception:
                                pass
                            if attempt < max_retries - 1:
                                await asyncio.sleep(min(2 ** attempt, 5))
                                continue
                            return ""

                        elif resp.status == 401 or resp.status == 403:
                            print(f"❌ Groq autenticação falhou ({module_name}): status {resp.status}")
                            return ""

                        elif resp.status == 429:
                            retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
                            wait = min(retry_after, 60)
                            if attempt < max_retries - 1:
                                print(f"⚠️ Groq rate limit ({module_name}) — aguardando {wait}s...")
                                await asyncio.sleep(wait)
                                continue
                            if model_index < len(GROQ_MODELS) - 1:
                                print(f"⚠️ Groq rate limit esgotado ({module_name}) — próximo modelo...")
                                break
                            print(f"❌ Groq rate limit ({module_name}) — sem mais modelos")
                            return ""

                        elif resp.status >= 500:
                            wait = min(2 ** attempt, 10)
                            if attempt < max_retries - 1:
                                print(f"⚠️ Groq erro {resp.status} ({module_name}) — tentando em {wait}s...")
                                await asyncio.sleep(wait)
                                continue
                            if model_index < len(GROQ_MODELS) - 1:
                                break
                            return ""

                        else:
                            print(f"⚠️ Groq status inesperado {resp.status} ({module_name})")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(min(2 ** attempt, 5))
                                continue
                            if model_index < len(GROQ_MODELS) - 1:
                                break
                            return ""

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    wait = min(2 ** attempt, 5)
                    print(f"⚠️ Groq conexão ({module_name}) — tentando em {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                if model_index < len(GROQ_MODELS) - 1:
                    break
                print(f"⚠️ Groq erro de conexão ({module_name}): {e}")
                return ""

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    wait = min(2 ** attempt, 5)
                    print(f"⚠️ Groq timeout ({module_name}) — tentando em {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                if model_index < len(GROQ_MODELS) - 1:
                    break
                print(f"⚠️ Groq timeout ({module_name}) — esgotadas todas as tentativas")
                return ""

            except Exception as e:
                print(f"⚠️ Groq erro inesperado ({module_name}): {type(e).__name__}: {e}")
                if model_index < len(GROQ_MODELS) - 1:
                    break
                return ""

    print(f"❌ Todos os modelos Groq falharam ({module_name})")
    return ""

# ─── Função pública ───────────────────────────────────────────────────────────

async def chamar_ia(
    conteudo: str,
    module_name: str = "IA",
    system_prompt: str | None = None,
    model: str = CYM_MODEL,
    force_groq: bool = False,
) -> str:
    """
    Chama a IA com fallback automático.

    Fluxo:
        CyM API (owner key, créditos infinitos) → Groq (fallback)

    Args:
        conteudo:      Prompt/mensagem do usuário.
        module_name:   Nome do módulo para logs (ex: "Feedbacks", "Tickets").
        system_prompt: System prompt opcional (enviado como role=system).
        model:         Modelo CyM a usar (padrão: "CyM Pro").
        force_groq:    Se True, pula a CyM e vai direto pro Groq (útil em testes).

    Returns:
        Resposta da IA, ou string vazia se tudo falhar.
    """
    if not force_groq:
        resposta, sucesso = await _call_cym(conteudo, module_name, system_prompt, model)
        if sucesso and resposta:
            return resposta

        print(f"🔄 CyM falhou — ativando fallback Groq ({module_name})...")

    resposta_groq = await _call_groq(conteudo, module_name, system_prompt=system_prompt)

    if resposta_groq:
        print(f"✅ Fallback Groq bem-sucedido ({module_name})")
        return resposta_groq

    print(f"❌ Todas as APIs falharam ({module_name})")
    return ""
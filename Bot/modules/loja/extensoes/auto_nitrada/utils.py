from __future__ import annotations
import asyncio, logging
import aiohttp, os
from typing import Optional, Dict, List
from .helpers import load_contas, load_config, update_conta, get_links_ativos, add_log, incrementar_uso_link, update_config_stat, reset_contas_travadas

logger = logging.getLogger("nitro_auto")

# ── Discord Utils ─────────────────────────────────────────
DISCORD_API = "https://discord.com/api/v9"
_TIMEOUT    = aiohttp.ClientTimeout(total=30, connect=10)
_HEADERS    = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Discord-Locale": "pt-BR", "X-Discord-Timezone": "America/Sao_Paulo",
    "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6InB0LUJSIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjYyMTYzLCJuYXRpdmVfYnVpbGRfbnVtYmVyIjpudWxsLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ==",
    "Origin": "https://discord.com", "Referer": "https://discord.com/channels/@me",
}

async def _req(session, method, url, headers, retries=3, **kw):
    for i in range(1, retries+1):
        try:
            r = await session.request(method, url, headers=headers, timeout=_TIMEOUT, **kw)
            if r.status == 429:
                await asyncio.sleep(float(r.headers.get("Retry-After", "5")) + 1); continue
            return r
        except (asyncio.TimeoutError, aiohttp.ClientConnectionError):
            if i < retries: await asyncio.sleep(min(2**i, 10))
    return None

async def validate_token(token: str) -> Dict:
    async with aiohttp.ClientSession() as s:
        r = await _req(s, "GET", f"{DISCORD_API}/users/@me", {**_HEADERS, "Authorization": token}, retries=2)
        if r and r.status == 200:
            d = await r.json()
            return {"valid": True, "user_id": d.get("id"), "username": d.get("username"),
                    "avatar": f"https://cdn.discordapp.com/avatars/{d.get('id')}/{d.get('avatar')}.png" if d.get("avatar") else None}
        return {"valid": False, "erro": f"HTTP {r.status if r else 'sem resposta'}"}

async def check_nitro_eligibility(token: str) -> Dict:
    async with aiohttp.ClientSession() as s:
        r = await _req(s, "GET", f"{DISCORD_API}/users/@me/subscriptions", {**_HEADERS, "Authorization": token})
        try:
            if r and r.status == 200:
                for sub in await r.json():
                    if "Nitro" in str(sub.get("name","")) or sub.get("status") == "active":
                        return {"elegivel": False, "motivo": "já possui Nitro ativo"}
        except: pass
        return {"elegivel": True, "motivo": ""}

# ── API Client ────────────────────────────────────────────
def _api_url():
    try:
        import json
        p = 'configs/config_api.json'
        if os.path.exists(p):
            cfg = json.load(open(p, encoding='utf-8'))
            u = cfg.get('autonitro') or cfg.get('api')
            if u: return u.rstrip('/')
    except: pass
    return os.getenv("NITRO_API_URL", "http://localhost:3000")

def _api_key():
    try:
        import json
        p = 'configs/config_api.json'
        if os.path.exists(p):
            cfg = json.load(open(p, encoding='utf-8'))
            k = cfg.get('autonitro_key') or cfg.get('api_key')
            if k: return k
    except: pass
    return os.getenv("NITRO_API_KEY", "")

class NitroAPIClient:
    def __init__(self):
        self.base_url = _api_url()
        self.api_key  = _api_key()
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(headers={"X-API-Key": self.api_key}, timeout=aiohttp.ClientTimeout(total=60))

    async def close(self):
        if self.session and not self.session.closed: await self.session.close()

    async def _req(self, method, endpoint, **kw):
        await self._ensure()
        try:
            async with self.session.request(method, f"{self.base_url}{endpoint}", **kw) as r:
                data = await r.json()
                return data if r.status < 400 else {"success": False, "error": data.get("error", "Erro")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_card_stats(self): return await self._req("GET", "/api/v1/cards/stats")
    async def health(self):         return await self._req("GET", "/api/v1/health")
    async def activate_batch(self, accounts: List[dict]): return await self._req("POST", "/api/v1/activate", json={"accounts": accounts})

# ── Queue ─────────────────────────────────────────────────
class NitroQueue:
    def __init__(self):
        self._q   = asyncio.Queue()
        self._set = set()
        self._lk  = asyncio.Lock()

    async def popular(self):
        async with self._lk:
            cfg, max_t = load_config(), load_config().get("max_tentativas_por_conta", 3)
            pendentes  = sorted([c for c in load_contas() if c["status"]=="pendente" and c.get("tentativas",0)<max_t and c["id"] not in self._set], key=lambda c: c.get("created_at",0))
            for c in pendentes:
                await self._q.put(c); self._set.add(c["id"])
            return len(pendentes)

    async def dequeue(self, timeout=2.0):
        try: return await asyncio.wait_for(self._q.get(), timeout=timeout)
        except asyncio.TimeoutError: return None

    def concluida(self, cid):
        self._set.discard(cid)
        try: self._q.task_done()
        except ValueError: pass

    def limpar(self):
        while not self._q.empty():
            try: self._q.get_nowait(); self._q.task_done()
            except: break
        self._set.clear()

    def stats(self): return {"na_fila": self._q.qsize(), "em_processo": len(self._set)}

_queue: Optional[NitroQueue] = None
def get_queue():
    global _queue
    if not _queue: _queue = NitroQueue()
    return _queue
def reset_queue():
    global _queue
    if _queue: _queue.limpar()
    _queue = NitroQueue()

# ── Workers ───────────────────────────────────────────────
class NitroWorker:
    def __init__(self, wid, api_client):
        self.id, self.api = wid, api_client
        self.running = False

    async def run(self):
        self.running = True
        fila = get_queue()
        sem  = asyncio.Semaphore(load_config().get("max_concurrent_requests", 3))
        while self.running:
            try:
                if not load_config().get("enabled"): await asyncio.sleep(3); continue
                conta = await fila.dequeue(2.0)
                if not conta: await fila.popular(); await asyncio.sleep(2); continue
                update_conta(conta["id"], {"worker_id": self.id, "status": "processando"})
                try: await self._processar(conta, sem)
                finally: fila.concluida(conta["id"])
                await asyncio.sleep(load_config().get("delay_entre_contas", 3))
            except asyncio.CancelledError: break
            except Exception as e: logger.exception(e); await asyncio.sleep(5)

    async def _processar(self, conta, sem):
        token = conta.get("token_raw", "")
        async with sem: info = await validate_token(token)
        if not info["valid"]:
            update_conta(conta["id"], {"status": "falha", "motivo_inelegivel": info.get("erro","")})
            add_log("error", f"Token inválido: {info.get('erro')}", conta_id=conta["id"], worker_id=self.id); return

        update_conta(conta["id"], {"username": info.get("username"), "user_id": info.get("user_id")})
        async with sem: elig = await check_nitro_eligibility(token)
        if not elig["elegivel"]:
            update_conta(conta["id"], {"status": "inelegivel", "motivo_inelegivel": elig["motivo"]})
            await update_config_stat("total_inelegiveis"); return

        links = get_links_ativos()
        if not links: update_conta(conta["id"], {"status": "pendente"}); add_log("warn", "Sem links ativos", worker_id=self.id); return
        if not self.api: update_conta(conta["id"], {"status": "pendente"}); add_log("error", "API indisponível", conta_id=conta["id"]); return

        payload = [{"token": token, "trial": l.get("tipo")=="trial", **( {"link": {"url": l["url"], "meses": l.get("meses",3)}} if l.get("tipo")!="trial" else {})} for l in links]
        res = await self.api.activate_batch(payload)
        if not res.get("success"):
            update_conta(conta["id"], {"status": "falha"}); await update_config_stat("total_falhas")
            add_log("error", f"Erro API: {res.get('error')}", conta_id=conta["id"], worker_id=self.id); return

        ativado = next((r for r in res.get("results",[]) if r.get("success")), None)
        if ativado:
            idx = res["results"].index(ativado)
            link = links[idx] if idx < len(links) else links[0]
            update_conta(conta["id"], {"status":"nitrada","nitro_ativo":True,"resultado":{"sucesso":True,"link_usado":link["id"],"expiracao_nitro":ativado.get("expiration")}})
            incrementar_uso_link(link["id"]); await update_config_stat("total_nitradas")
            add_log("success", f"Nitro ativado! {info.get('username')} via {link['nome']}", conta_id=conta["id"], worker_id=self.id)
        else:
            update_conta(conta["id"], {"status": "falha"}); await update_config_stat("total_falhas")
            add_log("error", f"Falha ativação: {res.get('results',[{}])[0].get('error','?')}", conta_id=conta["id"], worker_id=self.id)

class WorkerManager:
    def __init__(self): self.workers=[]; self.tasks=[]; self.running=False

    async def start(self, api_client):
        if self.running: return
        if not api_client: add_log("error","API client não disponível"); return
        reset_contas_travadas(); await get_queue().popular()
        cfg = load_config()
        for i in range(1, cfg.get("workers",2)+1):
            w = NitroWorker(i, api_client); t = asyncio.create_task(w.run())
            self.workers.append(w); self.tasks.append(t)
        self.running = True; add_log("info", f"{len(self.workers)} workers iniciados")

    async def stop(self):
        if not self.running: return
        for w in self.workers: w.running = False
        for t in self.tasks: t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        reset_queue(); self.workers.clear(); self.tasks.clear(); self.running = False
        add_log("info","Workers parados")

    def stats(self): return {"running":self.running,"workers":len(self.workers),"fila":get_queue().stats()}

_manager = WorkerManager()
async def start_workers(api): await _manager.start(api)
async def stop_workers():     await _manager.stop()
def get_worker_stats():       return _manager.stats()
def workers_running():        return _manager.running

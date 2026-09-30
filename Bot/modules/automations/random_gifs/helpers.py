from typing import Optional
from functions.database import database as db
from functions.emoji import emoji

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES COMPARTILHADAS
# ══════════════════════════════════════════════════════════════════════════════

MAX_CANAIS = 25  # limite por sistema (teto do SelectMenu do Discord)

NIGHT_API_ENDPOINTS = {
    "gif":    "https://api.waifu.pics/nsfw/gif",   # ajuste as URLs reais
    "icone":  "https://api.waifu.pics/nsfw/waifu",
    "banner": "https://api.waifu.pics/nsfw/waifu",
}

def formatar_canais(canais: list) -> str:
    if not canais:
        return "`Nenhum canal configurado`"
    return "  ".join(f"<#{c}>" for c in canais)


def formatar_canais_curto(canais: list) -> str:
    """Versão compacta pra resumos: mostra até 3 e indica o restante."""
    if not canais:
        return "`Sem canais`"
    visiveis = canais[:3]
    resto = len(canais) - len(visiveis)
    base = " ".join(f"<#{c}>" for c in visiveis)
    return base + (f" `+{resto}`" if resto else "")


# ══════════════════════════════════════════════════════════════════════════════
# RANDOM GIFS SFW
# ══════════════════════════════════════════════════════════════════════════════

SISTEMAS = ["gifs", "avatar", "banners"]

_LABELS_SFW = {
    "gifs":    "GIFs",
    "avatar":  "Avatar",
    "banners": "Banners",
}

_DB_KEY_SFW = "random_gifs_config"

# modo: "embed" (clássico) ou "container" (components v2)
_DEFAULT_SISTEMA: dict = {"ligado": False, "tempo_segundos": 60, "canais": [], "modo": "embed"}


# ── Normalização ──────────────────────────────────────────────────────────────

def _normalizar_sistema(base: dict, incoming: dict) -> dict:
    merged = {**base, **(incoming or {})}
    merged["tempo_segundos"] = max(1, int(merged.get("tempo_segundos") or base["tempo_segundos"]))
    merged["ligado"] = bool(merged.get("ligado", False))
    merged["modo"] = merged.get("modo", "embed") if merged.get("modo") in ("embed", "container") else "embed"

    raw = merged.get("canais") or []
    if isinstance(raw, str):
        raw = [raw]
    merged["canais"] = list(dict.fromkeys(
        str(c).strip() for c in raw if str(c).strip().isdigit()
    ))[:MAX_CANAIS]
    return merged


def _merge_defaults_sfw(raw: dict) -> dict:
    cfg = raw if isinstance(raw, dict) else {}
    sistemas_raw = cfg.get("sistemas") or {}

    # Migração de formato legado (canais como dict separado)
    legado = cfg.get("canais") or {}

    resultado: dict = {"sistemas": {}}
    for s in SISTEMAS:
        base = _normalizar_sistema(_DEFAULT_SISTEMA, sistemas_raw.get(s) or {})
        canal_legado = legado.get(s)
        if canal_legado and not base["canais"]:
            base["canais"] = [str(canal_legado).strip()]
        resultado["sistemas"][s] = base
    return resultado


# ── CRUD ──────────────────────────────────────────────────────────────────────

def ler_config() -> dict:
    raw = db.get_document(_DB_KEY_SFW) or {}
    return _merge_defaults_sfw(raw)


def salvar_config(cfg: dict) -> dict:
    safe = _merge_defaults_sfw(cfg)
    db.save_document(_DB_KEY_SFW, {}, safe)
    return safe


def atualizar_config(updater) -> dict:
    atual = ler_config()
    proximo = updater(atual)
    return salvar_config(proximo or atual)


# ── Canais SFW ────────────────────────────────────────────────────────────────

def adicionar_canal(tipo: str, channel_id: str) -> tuple[bool, str]:
    """Retorna (sucesso, mensagem_feedback)."""
    cid = str(channel_id).strip()
    if not cid.isdigit():
        return False, "ID inválido. Informe apenas números."

    r: dict = {"ok": False, "msg": ""}

    def up(cfg):
        canais = cfg["sistemas"][tipo]["canais"]
        if cid in canais:
            r["ok"] = False
            r["msg"] = "Esse canal já está na lista."
        elif len(canais) >= MAX_CANAIS:
            r["ok"] = False
            r["msg"] = f"Limite de {MAX_CANAIS} canais atingido."
        else:
            canais.append(cid)
            r["ok"] = True
            r["msg"] = f"Canal <#{cid}> adicionado com sucesso."
        return cfg

    atualizar_config(up)
    return r["ok"], r["msg"]


def remover_canal(tipo: str, channel_id: str) -> bool:
    cid = str(channel_id).strip()
    r: dict = {"ok": False}

    def up(cfg):
        canais = cfg["sistemas"][tipo]["canais"]
        if cid in canais:
            canais.remove(cid)
            r["ok"] = True
        return cfg

    atualizar_config(up)
    return r["ok"]


# ── Toggle, tempo e modo ──────────────────────────────────────────────────────

def toggle_sistema(tipo: str) -> bool:
    novo: dict = {"estado": None}

    def up(cfg):
        atual = bool(cfg["sistemas"][tipo].get("ligado", False))
        cfg["sistemas"][tipo]["ligado"] = not atual
        novo["estado"] = not atual
        return cfg

    atualizar_config(up)
    return novo["estado"]  # type: ignore[return-value]


def set_tempo(tipo: str, segundos: int) -> dict:
    def up(cfg):
        cfg["sistemas"][tipo]["tempo_segundos"] = max(1, int(segundos))
        return cfg
    return atualizar_config(up)


def set_modo(tipo: str, modo: str) -> dict:
    """Define o modo de envio: 'embed' ou 'container'."""
    assert modo in ("embed", "container")
    def up(cfg):
        cfg["sistemas"][tipo]["modo"] = modo
        return cfg
    return atualizar_config(up)


# ── Exibição SFW ─────────────────────────────────────────────────────────────

def label_sistema(tipo: str) -> str:
    return _LABELS_SFW.get(tipo, tipo.upper())


def resumo_sistemas(cfg: dict) -> str:
    linhas = []
    for tipo in SISTEMAS:
        s = cfg["sistemas"][tipo]
        status = f"{emoji.on}" if s["ligado"] else f"{emoji.off}"
        n = len(s["canais"])
        canais_str = f"`{n} canal{'is' if n != 1 else ''}`" if n else "`Sem canais`"
        modo_str = "`container`" if s.get("modo") == "container" else "`embed`"
        linhas.append(
            f"{status} **{label_sistema(tipo)}** — {canais_str} — `{s['tempo_segundos']}s` — {modo_str}"
        )
    return "\n".join(linhas)


# ══════════════════════════════════════════════════════════════════════════════
# RANDOM GIFS NSFW
# ══════════════════════════════════════════════════════════════════════════════
#
# Tipos: gif, icone, banner — mesma estrutura do SFW, intervalo fixo de 30s.
#
# Roteamento por tipo:
#   gif    → avatares animados
#   icone  → avatares estáticos
#   banner → banners de usuário
# ══════════════════════════════════════════════════════════════════════════════

TIPOS_NSFW = ["gif", "icone", "banner"]

_LABELS_NSFW = {
    "gif":    "GIF",
    "icone":  "Ícone",
    "banner": "Banner",
}

_DB_KEY_NSFW = "random_gifs_nsfw_config"

_DEFAULT_NSFW: dict = {"ligado": False, "canais": [], "modo": "embed"}

NSFW_INTERVALO_SEGUNDOS = 30


# ── Normalização ──────────────────────────────────────────────────────────────

def _normalizar_nsfw(base: dict, incoming: dict) -> dict:
    merged = {**base, **(incoming or {})}
    merged["ligado"] = bool(merged.get("ligado", False))
    merged["modo"] = merged.get("modo", "embed") if merged.get("modo") in ("embed", "container") else "embed"

    raw = merged.get("canais") or []
    if isinstance(raw, str):
        raw = [raw]
    merged["canais"] = list(dict.fromkeys(
        str(c).strip() for c in raw if str(c).strip().isdigit()
    ))[:MAX_CANAIS]
    return merged


def _merge_defaults_nsfw(raw: dict) -> dict:
    cfg = raw if isinstance(raw, dict) else {}
    sistemas_raw = cfg.get("sistemas") or {}
    return {
        "sistemas": {
            t: _normalizar_nsfw(_DEFAULT_NSFW, sistemas_raw.get(t) or {})
            for t in TIPOS_NSFW
        }
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

def ler_config_nsfw() -> dict:
    raw = db.get_document(_DB_KEY_NSFW) or {}
    return _merge_defaults_nsfw(raw)


def salvar_config_nsfw(cfg: dict) -> dict:
    safe = _merge_defaults_nsfw(cfg)
    db.save_document(_DB_KEY_NSFW, {}, safe)
    return safe


def atualizar_config_nsfw(updater) -> dict:
    atual = ler_config_nsfw()
    proximo = updater(atual)
    return salvar_config_nsfw(proximo or atual)


# ── Canais NSFW ───────────────────────────────────────────────────────────────

def adicionar_canal_nsfw(tipo: str, channel_id: str) -> tuple[bool, str]:
    cid = str(channel_id).strip()
    if not cid.isdigit():
        return False, "ID inválido. Informe apenas números."

    r: dict = {"ok": False, "msg": ""}

    def up(cfg):
        canais = cfg["sistemas"][tipo]["canais"]
        if cid in canais:
            r["ok"] = False
            r["msg"] = "Esse canal já está na lista."
        elif len(canais) >= MAX_CANAIS:
            r["ok"] = False
            r["msg"] = f"Limite de {MAX_CANAIS} canais atingido."
        else:
            canais.append(cid)
            r["ok"] = True
            r["msg"] = f"Canal <#{cid}> adicionado com sucesso."
        return cfg

    atualizar_config_nsfw(up)
    return r["ok"], r["msg"]


def remover_canal_nsfw(tipo: str, channel_id: str) -> bool:
    cid = str(channel_id).strip()
    r: dict = {"ok": False}

    def up(cfg):
        canais = cfg["sistemas"][tipo]["canais"]
        if cid in canais:
            canais.remove(cid)
            r["ok"] = True
        return cfg

    atualizar_config_nsfw(up)
    return r["ok"]


# ── Toggle e modo NSFW ────────────────────────────────────────────────────────

def toggle_nsfw(tipo: str) -> bool:
    novo: dict = {"estado": None}

    def up(cfg):
        atual = bool(cfg["sistemas"][tipo].get("ligado", False))
        cfg["sistemas"][tipo]["ligado"] = not atual
        novo["estado"] = not atual
        return cfg

    atualizar_config_nsfw(up)
    return novo["estado"]  # type: ignore[return-value]


def set_ligado_nsfw(tipo: str, ligado: bool) -> dict:
    def up(cfg):
        cfg["sistemas"][tipo]["ligado"] = bool(ligado)
        return cfg
    return atualizar_config_nsfw(up)


# ══════════════════════════════════════════════════════════════════════════════
# TASKS — sistema de tasks nomeadas (SFW)
# ══════════════════════════════════════════════════════════════════════════════

_DB_KEY_TASKS = "random_gifs_tasks"

PINTEREST_TEMAS = {
    "girl icons":    "girl aesthetic icons",
    "boy icons":     "boy aesthetic icons",
    "anime icons":   "anime pfp aesthetic",
    "dark icons":    "dark aesthetic icons",
    "soft icons":    "soft aesthetic icons",
    "banners":       "aesthetic banner discord",
    "wallpapers":    "aesthetic wallpaper 4k",
    "headers":       "twitter header aesthetic",
    "nature":        "nature aesthetic photography",
    "vintage":       "vintage aesthetic photography",
}

_DEFAULT_TASK: dict = {
    "nome": "",
    "ligado": False,
    "canais": [],
    "modo": "embed",
    "tempo_segundos": 60,
    "pinterest_tema": None,   # None = usar membros do servidor; str = tema Pinterest
    "nsfw": False,            # True = task envia em canais NSFW
}


def _normalizar_task(t: dict) -> dict:
    base = {**_DEFAULT_TASK, **(t or {})}
    base["ligado"] = bool(base.get("ligado", False))
    base["nsfw"]   = bool(base.get("nsfw", False))
    base["modo"] = base.get("modo") if base.get("modo") in ("embed", "container") else "embed"
    base["tempo_segundos"] = max(1, int(base.get("tempo_segundos") or 60))
    raw = base.get("canais") or []
    if isinstance(raw, str):
        raw = [raw]
    base["canais"] = list(dict.fromkeys(
        str(c).strip() for c in raw if str(c).strip().isdigit()
    ))[:MAX_CANAIS]
    return base


def ler_tasks() -> dict:
    """Retorna dict {task_id: task_dict}."""
    raw = db.get_document(_DB_KEY_TASKS) or {}
    return {k: _normalizar_task(v) for k, v in raw.items() if isinstance(v, dict)}


def salvar_tasks(tasks: dict) -> dict:
    safe = {k: _normalizar_task(v) for k, v in tasks.items()}
    db.save_document(_DB_KEY_TASKS, {}, safe)
    return safe


def criar_task(nome: str, nsfw: bool = False) -> tuple[str, dict]:
    """Cria nova task, retorna (task_id, task)."""
    import uuid
    tasks = ler_tasks()
    tid = str(uuid.uuid4())[:8]
    task = _normalizar_task({"nome": nome.strip()[:50], "nsfw": nsfw})
    tasks[tid] = task
    salvar_tasks(tasks)
    return tid, task


def deletar_task(task_id: str) -> bool:
    tasks = ler_tasks()
    if task_id not in tasks:
        return False
    del tasks[task_id]
    salvar_tasks(tasks)
    return True


def atualizar_task(task_id: str, updater) -> dict:
    tasks = ler_tasks()
    if task_id not in tasks:
        return {}
    tasks[task_id] = _normalizar_task(updater(tasks[task_id]))
    return salvar_tasks(tasks)[task_id]


def toggle_task(task_id: str) -> bool:
    novo: dict = {"estado": None}
    def up(t):
        t["ligado"] = not t["ligado"]
        novo["estado"] = t["ligado"]
        return t
    atualizar_task(task_id, up)
    return novo["estado"]


def adicionar_canal_task(task_id: str, channel_id: str) -> tuple[bool, str]:
    cid = str(channel_id).strip()
    if not cid.isdigit():
        return False, "ID inválido."
    r: dict = {"ok": False, "msg": ""}
    def up(t):
        if cid in t["canais"]:
            r["ok"] = False; r["msg"] = "Canal já está na lista."
        elif len(t["canais"]) >= MAX_CANAIS:
            r["ok"] = False; r["msg"] = f"Limite de {MAX_CANAIS} atingido."
        else:
            t["canais"].append(cid)
            r["ok"] = True; r["msg"] = f"Canal <#{cid}> adicionado."
        return t
    atualizar_task(task_id, up)
    return r["ok"], r["msg"]


def remover_canal_task(task_id: str, channel_id: str) -> bool:
    cid = str(channel_id).strip()
    r: dict = {"ok": False}
    def up(t):
        if cid in t["canais"]:
            t["canais"].remove(cid)
            r["ok"] = True
        return t
    atualizar_task(task_id, up)
    return r["ok"]


def set_tema_pinterest(task_id: str, tema: str | None) -> dict:
    def up(t):
        t["pinterest_tema"] = tema
        return t
    return atualizar_task(task_id, up)


def set_tempo_task(task_id: str, segundos: int) -> dict:
    def up(t):
        t["tempo_segundos"] = max(1, int(segundos))
        return t
    return atualizar_task(task_id, up)


def set_modo_task(task_id: str, modo: str) -> dict:
    assert modo in ("embed", "container")
    def up(t):
        t["modo"] = modo
        return t
    return atualizar_task(task_id, up)


def resumo_task(task: dict) -> str:
    status = f"{emoji.on}" if task["ligado"] else f"{emoji.off}"
    n = len(task["canais"])
    canais_str = f"`{n} canal{'is' if n != 1 else ''}`" if n else "`Sem canais`"
    tema = f"`Pinterest: {task['pinterest_tema']}`" if task.get("pinterest_tema") else "`Membros do servidor`"
    nsfw_str = " · `NSFW`" if task.get("nsfw") else ""
    return f"{status} **{task['nome']}** — {canais_str} — `{task['tempo_segundos']}s` — {tema}{nsfw_str}"


def set_modo_nsfw(tipo: str, modo: str) -> dict:
    """Define o modo de envio: 'embed' ou 'container'."""
    assert modo in ("embed", "container")
    def up(cfg):
        cfg["sistemas"][tipo]["modo"] = modo
        return cfg
    return atualizar_config_nsfw(up)


# ── Exibição NSFW ─────────────────────────────────────────────────────────────

def label_nsfw(tipo: str) -> str:
    return _LABELS_NSFW.get(tipo, tipo.upper())


def resumo_nsfw(cfg: dict) -> str:
    linhas = []
    for tipo in TIPOS_NSFW:
        s = cfg["sistemas"][tipo]
        status = f"{emoji.on}" if s["ligado"] else f"{emoji.off}"
        n = len(s["canais"])
        canais_str = f"`{n} canal{'is' if n != 1 else ''}`" if n else "`Sem canais`"
        modo_str = "`container`" if s.get("modo") == "container" else "`embed`"
        linhas.append(
            f"{status} **{label_nsfw(tipo)}** — {canais_str} — `{NSFW_INTERVALO_SEGUNDOS}s` — {modo_str}"
        )
    return "\n".join(linhas)
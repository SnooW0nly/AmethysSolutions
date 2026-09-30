"""
modules/utilitarios/comunidade/familia/helpers.py

Config, JSON helpers, voice session management e utilitários do sistema de família.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from typing import Optional

import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY          = "comunidade_familia"
_DB_PATH        = "database/utilitarios/comunidade/familia"
FAMILIAS_JSON   = f"{_DB_PATH}/familias.json"
VOICE_JSON      = f"{_DB_PATH}/voice_sessions.json"

MAX_REPRESENTANTES = 5


# ─── JSON helpers ─────────────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def gerar_familia_id() -> str:
    return str(int(time.time() * 1000))


# ─── Config ───────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("canal_logs_id", None)
    dados.setdefault("canal_rank_id", None)
    dados.setdefault("inatividade_dias", 0)
    dados.setdefault("rank_message_id", None)
    return dados


def salvar_config(data: dict) -> None:
    db.save_document(DB_KEY, {}, data)


# ─── Família CRUD ─────────────────────────────────────────────────────────────

def get_familia(familia_id: str) -> dict | None:
    return load_json(FAMILIAS_JSON).get(familia_id)


def get_all_familias() -> dict:
    return load_json(FAMILIAS_JSON)


def save_familia(familia_id: str, data: dict):
    familias = load_json(FAMILIAS_JSON)
    familias[familia_id] = data
    save_json(FAMILIAS_JSON, familias)


def delete_familia(familia_id: str):
    familias = load_json(FAMILIAS_JSON)
    familias.pop(familia_id, None)
    save_json(FAMILIAS_JSON, familias)
    voice = load_json(VOICE_JSON)
    voice.pop(familia_id, None)
    save_json(VOICE_JSON, voice)


def get_familia_by_dono(user_id: int) -> tuple[str, dict] | tuple[None, None]:
    for fid, fdata in load_json(FAMILIAS_JSON).items():
        if fdata.get("dono_id") == user_id:
            return fid, fdata
    return None, None


def get_familia_by_membro(user_id: int) -> tuple[str, dict] | tuple[None, None]:
    for fid, fdata in load_json(FAMILIAS_JSON).items():
        if user_id in fdata.get("membros", []):
            return fid, fdata
    return None, None


def get_familia_by_canal_voz(canal_id: int) -> tuple[str, dict] | tuple[None, None]:
    for fid, fdata in load_json(FAMILIAS_JSON).items():
        if fdata.get("canal_voz_id") == canal_id:
            return fid, fdata
    return None, None


def pode_gerenciar(user_id: int, familia_data: dict) -> bool:
    """Dono, representante ou VIP com integração ativa pode gerenciar (add/rm membros)."""
    if user_id == familia_data.get("dono_id") or user_id in familia_data.get("representantes", []):
        return True
    
    try:
        from modules.loja.cart.subscription_manager import SubscriptionManager
        if SubscriptionManager.is_vip(user_id, "familia"):
            return True
    except:
        pass
        
    return False


# ─── Voice sessions ───────────────────────────────────────────────────────────

def open_voice_session(familia_id: str, user_id: int):
    voice = load_json(VOICE_JSON)
    voice.setdefault(familia_id, {})[str(user_id)] = {"last_join": time.time()}
    save_json(VOICE_JSON, voice)


def close_voice_session(familia_id: str, user_id: int) -> int:
    """Fecha sessão, acumula tempo na família. Retorna segundos da sessão."""
    voice   = load_json(VOICE_JSON)
    uid_str = str(user_id)
    sess    = voice.get(familia_id, {}).pop(uid_str, None)
    save_json(VOICE_JSON, voice)
    if not sess:
        return 0
    elapsed = max(0, int(time.time() - sess.get("last_join", time.time())))
    if elapsed > 0:
        familias = load_json(FAMILIAS_JSON)
        if familia_id in familias:
            familias[familia_id]["tempo_total_segundos"] = (
                familias[familia_id].get("tempo_total_segundos", 0) + elapsed
            )
            familias[familia_id]["ultima_atividade"] = datetime.now().isoformat()
            save_json(FAMILIAS_JSON, familias)
    return elapsed


def flush_voice_session(familia_id: str, user_id: int) -> int:
    """Acumula tempo parcial SEM fechar sessão (para task de 5min). Retorna segundos."""
    voice   = load_json(VOICE_JSON)
    uid_str = str(user_id)
    sess    = voice.get(familia_id, {}).get(uid_str)
    if not sess:
        return 0
    now     = time.time()
    elapsed = max(0, int(now - sess.get("last_join", now)))
    voice[familia_id][uid_str]["last_join"] = now
    save_json(VOICE_JSON, voice)
    if elapsed > 0:
        familias = load_json(FAMILIAS_JSON)
        if familia_id in familias:
            familias[familia_id]["tempo_total_segundos"] = (
                familias[familia_id].get("tempo_total_segundos", 0) + elapsed
            )
            familias[familia_id]["ultima_atividade"] = datetime.now().isoformat()
            save_json(FAMILIAS_JSON, familias)
    return elapsed


def get_familia_tempo_efetivo(familia_id: str, familia_data: dict) -> int:
    """Tempo total incluindo sessões ativas no momento."""
    total   = familia_data.get("tempo_total_segundos", 0)
    voice   = load_json(VOICE_JSON)
    now     = time.time()
    for sess in voice.get(familia_id, {}).values():
        last = sess.get("last_join")
        if last:
            total += int(now - last)
    return total


def update_ultima_atividade(familia_id: str):
    familias = load_json(FAMILIAS_JSON)
    if familia_id in familias:
        familias[familia_id]["ultima_atividade"] = datetime.now().isoformat()
        save_json(FAMILIAS_JSON, familias)


# ─── Formatação ───────────────────────────────────────────────────────────────

def formatar_tempo(segundos: int) -> str:
    if segundos <= 0:
        return "`0m`"
    m = segundos // 60
    h = m // 60
    d = h // 24
    h = h % 24
    m = m % 60
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    return "`" + " ".join(parts) + "`" if parts else "`0m`"


def build_rank_text(familias: dict) -> str:
    if not familias:
        return "_Nenhuma família registrada ainda._"
    ranking = sorted(
        familias.items(),
        key=lambda x: get_familia_tempo_efetivo(x[0], x[1]),
        reverse=True,
    )[:10]
    medals  = ["🥇", "🥈", "🥉"]
    linhas  = []
    for i, (fid, fdata) in enumerate(ranking, 1):
        medal    = medals[i - 1] if i <= 3 else f"`#{i:02}`"
        tempo    = formatar_tempo(get_familia_tempo_efetivo(fid, fdata))
        dono_id  = fdata.get("dono_id")
        reps     = fdata.get("representantes", [])
        reps_txt = ", ".join(f"<@{r}>" for r in reps[:3]) if reps else "`-`"
        linhas.append(
            f"{medal} **{fdata['nome']}** — Dono: <@{dono_id}> | "
            f"Reps: {reps_txt} | ⏱️ {tempo}"
        )
    return "\n".join(linhas)


# ─── UI helpers ───────────────────────────────────────────────────────────────

def accent(primary_hex: str | None = None) -> dict:
    if not primary_hex:
        primary_hex = (db.get_document("custom_colors") or {}).get("primary")
    if primary_hex:
        return {"accent_colour": disnake.Colour(int(primary_hex.replace("#", ""), 16))}
    return {}


def color(primary_hex: str | None = None) -> Optional[disnake.Colour]:
    if not primary_hex:
        primary_hex = (db.get_document("custom_colors") or {}).get("primary")
    if primary_hex:
        return disnake.Colour(int(primary_hex.replace("#", ""), 16))
    return None


def _mode() -> str:
    return (db.get_document("custom_mode") or {}).get("mode", "components")


def _primary_hex() -> str | None:
    return (db.get_document("custom_colors") or {}).get("primary")


# ─── Log helper ───────────────────────────────────────────────────────────────

async def enviar_log(bot, titulo: str, descricao: str, erro: bool = False):
    try:
        config   = carregar_config()
        canal_id = config.get("canal_logs_id")
        if not canal_id:
            return
        canal = bot.get_channel(int(canal_id))
        if not isinstance(canal, disnake.TextChannel):
            return

        ph         = _primary_hex()
        colors_doc = db.get_document("custom_colors") or {}
        danger_hex = colors_doc.get("danger", "#dc3545")
        cor_hex    = danger_hex if erro else (ph or "#5865F2")
        cor        = disnake.Colour(int(cor_hex.replace("#", ""), 16))
        mode       = _mode()
        icone      = emoji.wrong if erro else emoji.correct

        if mode == "embed":
            emb = disnake.Embed(
                title=f"{icone} {titulo}",
                description=descricao,
                color=cor,
            )
            await canal.send(embed=emb)
        else:
            kw = accent(ph)
            await canal.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"## {icone} {titulo}\n{descricao}"),
                        **kw,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
    except Exception:
        pass
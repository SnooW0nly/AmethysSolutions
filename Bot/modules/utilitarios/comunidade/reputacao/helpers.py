"""
modules/utilitarios/comunidade/reputacao/helpers.py

Helpers, config e utilitários do sistema de Reputação.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import Optional

import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY = "comunidade_reputacao"
_DB_PATH = "database/utilitarios/comunidade/reputacao"
AVALIACOES_JSON = f"{_DB_PATH}/avaliacoes.json"

BUTTON_STYLE_MAP = {
    "gray":  disnake.ButtonStyle.gray,
    "grey":  disnake.ButtonStyle.gray,
    "green": disnake.ButtonStyle.green,
    "red":   disnake.ButtonStyle.red,
    "blue":  disnake.ButtonStyle.blurple,
}


# ─── JSON ─────────────────────────────────────────────────────────────────────

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


# ─── Config ───────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("ativado", False)
    dados.setdefault("canal_pesquisa", None)       # Canal p/ enviar painel de busca
    dados.setdefault("canal_ranking", None)         # Canal p/ enviar ranking
    dados.setdefault("intervalo_ranking", 60)       # Minutos entre atualização do ranking
    dados.setdefault("mensagem_pesquisa_id", None)  # ID da msg do painel de busca
    dados.setdefault("mensagem_ranking_id", None)   # ID da msg do ranking
    dados.setdefault("nota_minima_cargo", {})       # {"cargo_id": nota_minima} ex: {"123": 8.0}
    dados.setdefault("cargo_top1", None)            # Cargo dado ao Top 1
    dados.setdefault("mensagem_pesquisa", {})       # Config do Builder p/ painel de busca
    dados.setdefault("mensagem_ranking", {})        # Config do Builder p/ painel de ranking
    dados.setdefault("permitir_auto_avaliacao", False)  # Se pode avaliar a si mesmo
    dados.setdefault("nota_anonima", False)         # Se a avaliação é anônima
    return dados


def salvar_config(data: dict) -> None:
    db.save_document(DB_KEY, {}, data)


# ─── Avaliações ───────────────────────────────────────────────────────────────

def carregar_avaliacoes() -> dict:
    """
    Estrutura:
    {
      "user_id": {
        "avaliacoes": {"avaliador_id": nota, ...},  # nota: 1-10
        "total": float,
        "count": int,
        "media": float
      }
    }
    """
    return load_json(AVALIACOES_JSON)


def salvar_avaliacoes(data: dict) -> None:
    save_json(AVALIACOES_JSON, data)


def registrar_avaliacao(avaliado_id: str, avaliador_id: str, nota: int) -> dict:
    """
    Registra ou atualiza avaliação. Retorna dict com:
    - sucesso: bool
    - ja_avaliou: bool
    - media: float
    - count: int
    """
    avaliacoes = carregar_avaliacoes()

    if avaliado_id not in avaliacoes:
        avaliacoes[avaliado_id] = {"avaliacoes": {}, "total": 0.0, "count": 0, "media": 0.0}

    usuario = avaliacoes[avaliado_id]
    ja_avaliou = avaliador_id in usuario["avaliacoes"]

    if ja_avaliou:
        nota_antiga = usuario["avaliacoes"][avaliador_id]
        usuario["total"] = usuario["total"] - nota_antiga + nota
    else:
        usuario["total"] += nota
        usuario["count"] += 1

    usuario["avaliacoes"][avaliador_id] = nota
    usuario["media"] = round(usuario["total"] / usuario["count"], 2) if usuario["count"] > 0 else 0.0

    salvar_avaliacoes(avaliacoes)
    return {
        "sucesso": True,
        "ja_avaliou": ja_avaliou,
        "media": usuario["media"],
        "count": usuario["count"],
    }


def obter_perfil(user_id: str) -> dict:
    avaliacoes = carregar_avaliacoes()
    return avaliacoes.get(user_id, {"avaliacoes": {}, "total": 0.0, "count": 0, "media": 0.0})


def gerar_ranking(limit: int = 20) -> list[dict]:
    """Retorna lista de {user_id, media, count} ordenada por média desc."""
    avaliacoes = carregar_avaliacoes()
    ranking = []
    for uid, dados in avaliacoes.items():
        if dados.get("count", 0) >= 1:
            ranking.append({
                "user_id": uid,
                "media": dados.get("media", 0.0),
                "count": dados.get("count", 0),
            })
    ranking.sort(key=lambda x: (-x["media"], -x["count"]))
    return ranking[:limit]


# ─── Barra de nota visual ─────────────────────────────────────────────────────

def barra_nota(media: float) -> str:
    """Gera barra visual de 10 blocos representando a nota."""
    preenchidos = round(media)
    return "█" * preenchidos + "░" * (10 - preenchidos)


def estrelas_nota(media: float) -> str:
    """Converte nota para representação de estrelas (máx 5)."""
    estrelas = round(media / 2)
    return "⭐" * estrelas + "☆" * (5 - estrelas)


# ─── Helpers visuais ──────────────────────────────────────────────────────────

def _mode() -> str:
    return (db.get_document("custom_mode") or {}).get("mode", "components")


def _primary_hex() -> Optional[str]:
    return (db.get_document("custom_colors") or {}).get("primary")


def color() -> int:
    h = _primary_hex()
    return int(h.replace("#", ""), 16) if h else 0x5865F2


def accent() -> dict:
    c = color()
    return {"accent_colour": disnake.Colour(c)} if c else {}


def nota_cor(media: float) -> str:
    """Cor descritiva baseada na média."""
    if media >= 9.0:
        return "🟢"
    elif media >= 7.0:
        return "🟡"
    elif media >= 5.0:
        return "🟠"
    else:
        return "🔴"

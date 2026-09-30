"""
modules/utilitarios/comunidade/formulario/bateponto/helpers.py

Configuração e helpers de banco de dados para o sistema de Bate Ponto.
"""
from __future__ import annotations

import uuid
import datetime
import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY = "automations_bateponto"

# ─── Configuração ────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("sistemas", {})
    return dados

def salvar_config(data: dict) -> None:
    db.save_document(DB_KEY, data)

def criar_bateponto(nome: str) -> str:
    """Cria um novo sistema de bate-ponto e retorna seu ID."""
    config = carregar_config()
    bp_id = str(uuid.uuid4())[:8]
    config["sistemas"][bp_id] = {
        "id": bp_id,
        "nome": nome,
        "ativado": False,
        "canal_painel_id": None,
        "canal_logs_id": None,
        "cargos_permitidos": [],
        "cargos_notificar": [],
        "embed_titulo": f"Sistema de Bate Ponto - {nome}",
        "embed_descricao": "Clique no botão abaixo para iniciar ou finalizar seu turno.",
        "embed_cor": None,
        "botao_entrada_label": "Bater Ponto (Entrada)",
        "botao_entrada_emoji": f"{emoji.on}",
        "botao_entrada_estilo": "green",
        "botao_saida_label": "Bater Ponto (Saída)",
        "botao_saida_emoji": f"{emoji.off}",
        "botao_saida_estilo": "red",
        "mensagem_sucesso": "✅ Seu ponto foi registrado com sucesso!",
        "anunciar_editor": {}, # Dados do Editor de Anúncios
        "registros": {}, # user_id: {status: 'on'|'off', start_time: iso, total_today: seconds}
        "historico": [], # lista de logs formatados
    }
    salvar_config(config)
    return bp_id

def get_bateponto(bp_id: str) -> dict | None:
    config = carregar_config()
    return config.get("sistemas", {}).get(bp_id)

def salvar_bateponto(bp_id: str, data: dict) -> None:
    config = carregar_config()
    config["sistemas"][bp_id] = data
    salvar_config(config)

def deletar_bateponto(bp_id: str) -> None:
    config = carregar_config()
    config["sistemas"].pop(bp_id, None)
    salvar_config(config)

# ─── Helpers de UI e Cores ───────────────────────────────────────────────────

def get_colors() -> tuple[str | None, dict]:
    from ..helpers import get_colors as get_base_colors
    return get_base_colors()

def estilo_para_disnake(estilo: str) -> disnake.ButtonStyle:
    from ..helpers import estilo_para_disnake as base_estilo
    return base_estilo(estilo)

def listar_batepontos_select() -> list[disnake.SelectOption]:
    config = carregar_config()
    sistemas = config.get("sistemas", {})
    options = []
    for bid, b in sistemas.items():
        status = f"{emoji.correct}" if b.get("ativado") else f"{emoji.wrong}"
        options.append(disnake.SelectOption(
            label=b.get("nome", "Sem nome")[:100],
            value=bid,
            description=f"{status} Sistema de Bate Ponto",
            emoji=emoji.time,
        ))
    if not options:
        options.append(disnake.SelectOption(
            label="Nenhum sistema de bate-ponto criado",
            value="__none__",
            emoji=emoji.wrong,
        ))
    return options

def format_duration(seconds: float) -> str:
    """Formata segundos em HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

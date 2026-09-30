"""
Helpers do sistema de afiliados.
Gerencia relações, comissões, saques e notificações pendentes.
"""
import os
from datetime import datetime
from typing import Optional
from functions.database import database as db

AFILIADOS_FILE = "database/loja/afiliados.json"


# ──────────────────────────────────────────────────────────
# Utilitários internos
# ──────────────────────────────────────────────────────────

def _garantir_arquivo() -> None:
    """Garante que o arquivo de dados existe com estrutura válida."""
    os.makedirs(os.path.dirname(AFILIADOS_FILE), exist_ok=True)
    try:
        existing = db.obter(AFILIADOS_FILE)
        if existing is None:
            raise ValueError
    except Exception:
        db.salvar(AFILIADOS_FILE, {
            "membros": {},
            "relacoes": {},
            "pending_notifications": []
        })


def _get_or_create_membro(dados: dict, user_id: str) -> dict:
    """Garante que o membro existe no dicionário e retorna seus dados."""
    uid = str(user_id)
    if uid not in dados["membros"]:
        dados["membros"][uid] = {
            "convidados": [],
            "saldo": 0.0,
            "pix": None,
            "notificar_dm": True,
            "saques": []
        }
    return dados["membros"][uid]


# ──────────────────────────────────────────────────────────
# Config (admin)
# ──────────────────────────────────────────────────────────

def carregar_config() -> dict:
    data = db.get_document("loja_afiliados_config") or {}
    data.setdefault("ativado", False)
    data.setdefault("comissao_percentual", 5.0)
    data.setdefault("canal_saque_id", None)
    return data


def salvar_config(data: dict) -> None:
    db.save_document("loja_afiliados_config", data)


# ──────────────────────────────────────────────────────────
# Dados dos afiliados
# ──────────────────────────────────────────────────────────

def carregar_dados() -> dict:
    _garantir_arquivo()
    data = db.obter(AFILIADOS_FILE) or {}
    data.setdefault("membros", {})
    data.setdefault("relacoes", {})
    data.setdefault("pending_notifications", [])
    return data


def salvar_dados(data: dict) -> None:
    db.salvar(AFILIADOS_FILE, data)


def get_membro(user_id: str) -> dict:
    """Retorna dados do membro, criando se não existir."""
    dados = carregar_dados()
    membro = _get_or_create_membro(dados, str(user_id))
    salvar_dados(dados)
    return membro


def salvar_membro(user_id: str, membro_data: dict) -> None:
    dados = carregar_dados()
    dados["membros"][str(user_id)] = membro_data
    salvar_dados(dados)


# ──────────────────────────────────────────────────────────
# Rastreamento de convites
# ──────────────────────────────────────────────────────────

def registrar_entrada(member_id: str, inviter_id: str) -> None:
    """
    Registra que member_id foi convidado por inviter_id.
    - Ignora Vanity URL (não gera comissão).
    - Se o membro já tinha um inviter diferente, remove do anterior.
    - Não registra auto-convite.
    """
    mid = str(member_id)
    iid = str(inviter_id)

    if iid in ("Vanity Url", "None", "") or iid == mid:
        return

    dados = carregar_dados()

    # Remover relação anterior se existir e for diferente
    old_inviter = dados["relacoes"].get(mid)
    if old_inviter and old_inviter != iid:
        old_data = dados["membros"].get(old_inviter, {})
        old_convidados = old_data.get("convidados", [])
        if mid in old_convidados:
            old_convidados.remove(mid)
        if old_inviter in dados["membros"]:
            dados["membros"][old_inviter]["convidados"] = old_convidados

    # Registrar nova relação
    dados["relacoes"][mid] = iid

    # Garantir que o inviter existe e adicionar o membro à lista
    inviter_data = _get_or_create_membro(dados, iid)
    convidados = inviter_data.get("convidados", [])
    if mid not in convidados:
        convidados.append(mid)
    inviter_data["convidados"] = convidados

    salvar_dados(dados)


# ──────────────────────────────────────────────────────────
# Comissões
# ──────────────────────────────────────────────────────────

def registrar_comissao(buyer_id: str, valor_compra: float, produto_nome: str = "Produto") -> tuple[Optional[str], float]:
    """
    Calcula e registra comissão para o afiliado que convidou o comprador.
    - Adiciona notificação pendente de DM se configurado.
    - Retorna (inviter_id, valor_comissao) ou (None, 0.0).
    """
    config = carregar_config()
    if not config.get("ativado") or valor_compra <= 0:
        return None, 0.0

    percentual = float(config.get("comissao_percentual", 5.0))
    if percentual <= 0:
        return None, 0.0

    dados = carregar_dados()
    inviter_id = dados["relacoes"].get(str(buyer_id))

    if not inviter_id or inviter_id in ("Vanity Url", "None", ""):
        return None, 0.0

    if str(inviter_id) == str(buyer_id):
        return None, 0.0

    comissao = round(valor_compra * (percentual / 100), 2)
    if comissao <= 0:
        return None, 0.0

    inviter_data = _get_or_create_membro(dados, inviter_id)
    inviter_data["saldo"] = round(inviter_data.get("saldo", 0.0) + comissao, 2)

    # Enfileirar notificação DM se o afiliado quiser receber
    if inviter_data.get("notificar_dm", True):
        notif = {
            "user_id": inviter_id,
            "comissao": comissao,
            "produto": produto_nome,
            "timestamp": datetime.now().isoformat()
        }
        pending = dados.get("pending_notifications", [])
        pending.append(notif)
        # Limitar fila a 500 notificações para evitar crescimento ilimitado
        dados["pending_notifications"] = pending[-500:]

    salvar_dados(dados)
    return inviter_id, comissao


def pop_pending_notifications() -> list:
    """Remove e retorna todas as notificações pendentes de uma vez."""
    dados = carregar_dados()
    pending = dados.get("pending_notifications", [])
    if not pending:
        return []
    dados["pending_notifications"] = []
    salvar_dados(dados)
    return pending


# ──────────────────────────────────────────────────────────
# Saques
# ──────────────────────────────────────────────────────────

def solicitar_saque(user_id: str, valor: float) -> bool:
    """
    Debita o saldo e registra o saque como pendente.
    Retorna True se bem-sucedido, False se saldo insuficiente.
    """
    dados = carregar_dados()
    membro = _get_or_create_membro(dados, str(user_id))

    saldo = membro.get("saldo", 0.0)
    if valor <= 0 or round(valor, 2) > round(saldo, 2):
        return False

    membro["saldo"] = round(saldo - valor, 2)

    saque = {
        "valor": valor,
        "pix": membro.get("pix"),
        "timestamp": datetime.now().isoformat(),
        "status": "pendente"
    }

    saques = membro.get("saques", [])
    saques.append(saque)
    membro["saques"] = saques[-50:]  # manter apenas os 50 mais recentes

    salvar_dados(dados)
    return True
"""
modules/utilitarios/comunidade/formulario/staff_manager.py

Sistema de Gerenciamento de Staff integrado ao formulário.
- Gerencia staff (adicionar/remover/editar)
- Sistema de pontuação por ações (ticket assumido, formulário aprovado, etc.)
- Ranking de staff com pontuação personalizável
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

import disnake
from functions.database import database as db
from functions.emoji import emoji

STAFF_DB_KEY      = "formulario_staff"
PONTUACAO_DB_KEY  = "formulario_pontuacao"
CONFIG_PONT_KEY   = "formulario_pontuacao_config"

# ─── Ações pontuáveis (podem ser personalizadas) ──────────────────────────────

ACOES_PADRAO: dict[str, dict] = {
    "ticket_assumido":    {"label": "Ticket Assumido",        "emoji": "🎫", "pontos": 10,  "descricao": "Pontos ao assumir um ticket"},
    "ticket_fechado":     {"label": "Ticket Fechado",         "emoji": "✅", "pontos": 5,   "descricao": "Pontos ao fechar um ticket"},
    "form_aprovado":      {"label": "Formulário Aprovado",    "emoji": "📋", "pontos": 15,  "descricao": "Pontos ao aprovar uma resposta de formulário"},
    "form_rejeitado":     {"label": "Formulário Rejeitado",   "emoji": "❌", "pontos": 3,   "descricao": "Pontos ao rejeitar uma resposta de formulário"},
    "resposta_rapida":    {"label": "Resposta Rápida (<5min)","emoji": "⚡", "pontos": 8,   "descricao": "Bônus por responder em menos de 5 minutos"},
    "avaliacao_positiva": {"label": "Avaliação Positiva",     "emoji": "⭐", "pontos": 20,  "descricao": "Pontos por avaliação positiva do usuário"},
    "notificou_usuario":  {"label": "Notificação Enviada",    "emoji": "🔔", "pontos": 2,   "descricao": "Pontos ao notificar um usuário"},
    "call_criada":        {"label": "Call Criada",            "emoji": "📞", "pontos": 5,   "descricao": "Pontos ao criar uma call para o ticket"},
    "bonus_manual":       {"label": "Bônus Manual",           "emoji": "🎁", "pontos": 0,   "descricao": "Bônus adicionado manualmente por admin"},
    "penalidade_manual":  {"label": "Penalidade Manual",      "emoji": "⚠️", "pontos": 0,   "descricao": "Penalidade adicionada manualmente por admin"},
}


# ─── Helpers de configuração de pontuação ────────────────────────────────────

def carregar_config_pontuacao() -> dict:
    cfg = db.get_document(CONFIG_PONT_KEY) or {}
    cfg.setdefault("ativo", True)
    cfg.setdefault("acoes", {k: v["pontos"] for k, v in ACOES_PADRAO.items()})
    cfg.setdefault("multiplicadores", {})   # cargo_id → float
    cfg.setdefault("canal_ranking_id", None)
    cfg.setdefault("cargo_staff_ids", [])   # cargos que contam como staff
    cfg.setdefault("reset_period", "nunca") # diario / semanal / mensal / nunca
    cfg.setdefault("mostrar_pontos_usuario", True)
    return cfg


def salvar_config_pontuacao(cfg: dict) -> None:
    db.save_document(CONFIG_PONT_KEY, cfg)


def get_pontos_acao(acao: str) -> int:
    cfg = carregar_config_pontuacao()
    acoes = cfg.get("acoes", {})
    return acoes.get(acao, ACOES_PADRAO.get(acao, {}).get("pontos", 0))


# ─── Helpers de staff ─────────────────────────────────────────────────────────

def carregar_staff() -> dict:
    """Retorna {user_id_str: {dados do staff}}"""
    return db.get_document(STAFF_DB_KEY) or {}


def salvar_staff(data: dict) -> None:
    db.save_document(STAFF_DB_KEY, data)


def get_membro_staff(user_id: int) -> Optional[dict]:
    staff = carregar_staff()
    return staff.get(str(user_id))


def adicionar_staff(user_id: int, nome: str, cargo: str = "", obs: str = "") -> dict:
    staff = carregar_staff()
    uid = str(user_id)
    if uid not in staff:
        staff[uid] = {
            "user_id": user_id,
            "nome": nome,
            "cargo_titulo": cargo,
            "observacoes": obs,
            "adicionado_em": int(time.time()),
            "ativo": True,
        }
    else:
        staff[uid].update({"nome": nome, "cargo_titulo": cargo, "observacoes": obs, "ativo": True})
    salvar_staff(staff)
    return staff[uid]


def remover_staff(user_id: int) -> bool:
    staff = carregar_staff()
    uid = str(user_id)
    if uid in staff:
        staff[uid]["ativo"] = False
        salvar_staff(staff)
        return True
    return False


def toggle_staff_ativo(user_id: int) -> bool:
    """Alterna ativo/inativo. Retorna novo estado."""
    staff = carregar_staff()
    uid = str(user_id)
    if uid not in staff:
        return False
    staff[uid]["ativo"] = not staff[uid].get("ativo", True)
    salvar_staff(staff)
    return staff[uid]["ativo"]


# ─── Helpers de pontuação ─────────────────────────────────────────────────────

def carregar_pontuacao() -> dict:
    """Retorna {user_id_str: {pontos, historico, ...}}"""
    return db.get_document(PONTUACAO_DB_KEY) or {}


def salvar_pontuacao(data: dict) -> None:
    db.save_document(PONTUACAO_DB_KEY, data)


def registrar_ponto(
    user_id: int,
    acao: str,
    pontos_override: Optional[int] = None,
    detalhes: str = "",
    guild = None,
) -> int:
    """
    Adiciona pontos ao staff member.
    Retorna o total de pontos após a operação.
    """
    cfg = carregar_config_pontuacao()
    if not cfg.get("ativo", True):
        return 0

    pontos_base = pontos_override if pontos_override is not None else get_pontos_acao(acao)

    # Aplicar multiplicador de cargo se guild disponível
    if guild and pontos_base != 0:
        multiplicadores = cfg.get("multiplicadores", {})
        try:
            member = guild.get_member(user_id)
            if member:
                for role in member.roles:
                    mult = multiplicadores.get(str(role.id))
                    if mult:
                        pontos_base = int(pontos_base * float(mult))
                        break
        except Exception:
            pass

    dados = carregar_pontuacao()
    uid = str(user_id)
    if uid not in dados:
        dados[uid] = {"pontos_total": 0, "pontos_periodo": 0, "historico": [], "ultimo_reset": int(time.time())}

    dados[uid]["pontos_total"]   = dados[uid].get("pontos_total", 0)   + pontos_base
    dados[uid]["pontos_periodo"] = dados[uid].get("pontos_periodo", 0) + pontos_base

    historico = dados[uid].get("historico", [])
    historico.append({
        "acao": acao,
        "pontos": pontos_base,
        "detalhes": detalhes,
        "timestamp": int(time.time()),
    })
    # Manter apenas os últimos 100 registros no histórico
    dados[uid]["historico"] = historico[-100:]
    salvar_pontuacao(dados)
    return dados[uid]["pontos_total"]


def get_pontuacao_membro(user_id: int) -> dict:
    dados = carregar_pontuacao()
    return dados.get(str(user_id), {"pontos_total": 0, "pontos_periodo": 0, "historico": []})


def get_ranking(limite: int = 10, por_periodo: bool = False) -> list[tuple[str, int]]:
    """Retorna lista de (user_id_str, pontos) ordenada por pontos."""
    dados = carregar_pontuacao()
    chave = "pontos_periodo" if por_periodo else "pontos_total"
    ranking = [(uid, d.get(chave, 0)) for uid, d in dados.items() if d.get(chave, 0) > 0]
    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking[:limite]


def resetar_pontos_periodo() -> int:
    """Reseta pontos_periodo de todos. Retorna quantidade de membros resetados."""
    dados = carregar_pontuacao()
    count = 0
    for uid in dados:
        if dados[uid].get("pontos_periodo", 0) > 0:
            dados[uid]["pontos_periodo"] = 0
            dados[uid]["ultimo_reset"] = int(time.time())
            count += 1
    salvar_pontuacao(dados)
    return count


def ajustar_pontos_manual(user_id: int, pontos: int, motivo: str = "", admin_id: int = 0) -> int:
    """Adiciona ou remove pontos manualmente (pode ser negativo)."""
    acao = "bonus_manual" if pontos >= 0 else "penalidade_manual"
    detalhes = f"Por <@{admin_id}>: {motivo}" if motivo else f"Por <@{admin_id}>"
    return registrar_ponto(user_id, acao, pontos_override=pontos, detalhes=detalhes)


# ─── Painéis de Staff Manager ─────────────────────────────────────────────────

def painel_staff_principal_components() -> list:
    from .helpers import get_colors
    _, ck = get_colors()
    staff = carregar_staff()
    ativos = sum(1 for s in staff.values() if s.get("ativo", True))
    cfg = carregar_config_pontuacao()

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                "-# Formulários > **Gerenciar Staff**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                f"{emoji.shield_star} **Staff cadastrado:** `{len(staff)}`\n"
                f"{emoji.on} **Staff ativo:** `{ativos}`\n"
                f"{emoji.coupon} **Sistema de pontuação:** `{'Ativo' if cfg.get('ativo') else 'Inativo'}`"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Staff", emoji=emoji.plus,
                                  style=disnake.ButtonStyle.green, custom_id="Staff_Adicionar"),
                disnake.ui.Button(label="Ver Staff", emoji=emoji.members,
                                  style=disnake.ButtonStyle.blurple, custom_id="Staff_VerLista",
                                  disabled=len(staff) == 0),
                disnake.ui.Button(label="Ranking", emoji=emoji.coupon,
                                  style=disnake.ButtonStyle.grey, custom_id="Staff_Ranking"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Config Pontuação", emoji=emoji.settings2,
                                  style=disnake.ButtonStyle.grey, custom_id="Staff_ConfigPontuacao"),
                disnake.ui.Button(label="Ajuste Manual", emoji=emoji.wand,
                                  style=disnake.ButtonStyle.grey, custom_id="Staff_AjusteManual",
                                  disabled=len(staff) == 0),
                disnake.ui.Button(label="Resetar Período", emoji=emoji.reload,
                                  style=disnake.ButtonStyle.red, custom_id="Staff_ResetarPeriodo",
                                  disabled=len(staff) == 0),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Form_VoltarPrincipal"),
        ),
    ]


def painel_staff_lista_components(page: int = 0) -> list:
    from .helpers import get_colors
    _, ck = get_colors()
    staff = carregar_staff()
    pontuacoes = carregar_pontuacao()

    membros = sorted(staff.values(), key=lambda s: s.get("adicionado_em", 0), reverse=True)
    por_pagina = 6
    inicio = page * por_pagina
    fim = min(inicio + por_pagina, len(membros))
    pagina = membros[inicio:fim]
    total_pages = max(1, (len(membros) + por_pagina - 1) // por_pagina)

    linhas = []
    for s in pagina:
        uid = str(s["user_id"])
        pts = pontuacoes.get(uid, {}).get("pontos_total", 0)
        status = emoji.on if s.get("ativo", True) else emoji.off
        cargo_titulo = f" — *{s['cargo_titulo']}*" if s.get("cargo_titulo") else ""
        linhas.append(f"{status} <@{s['user_id']}>{cargo_titulo} · **{pts}pts**")

    conteudo = "\n".join(linhas) if linhas else "Nenhum staff cadastrado."

    opcoes_staff = [
        disnake.SelectOption(
            label=s.get("nome", f"ID:{s['user_id']}")[:50],
            value=str(s["user_id"]),
            description=f"{'✅ Ativo' if s.get('ativo', True) else '🔴 Inativo'} · {pontuacoes.get(str(s['user_id']), {}).get('pontos_total', 0)}pts",
            emoji=emoji.shield_star,
        )
        for s in pagina
    ] or [disnake.SelectOption(label="Nenhum staff", value="__none__")]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Staff > **Lista** (Página {page+1}/{total_pages})"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(conteudo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Staff_SelecionarMembro",
                    placeholder="Selecione um membro para gerenciar...",
                    options=opcoes_staff,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="◀", style=disnake.ButtonStyle.grey,
                                  custom_id=f"Staff_ListaPrev:{page}", disabled=page == 0),
                disnake.ui.Button(label="▶", style=disnake.ButtonStyle.grey,
                                  custom_id=f"Staff_ListaNext:{page}", disabled=fim >= len(membros)),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Staff_Principal"),
        ),
    ]


def painel_staff_membro_components(user_id: int) -> list:
    from .helpers import get_colors
    _, ck = get_colors()
    membro = get_membro_staff(user_id)
    if not membro:
        return painel_staff_principal_components()

    pont = get_pontuacao_membro(user_id)
    historico = pont.get("historico", [])[-5:]

    uid = str(user_id)
    pts_total  = pont.get("pontos_total", 0)
    pts_periodo = pont.get("pontos_periodo", 0)
    ativo = membro.get("ativo", True)
    cargo_titulo = membro.get("cargo_titulo") or "Não definido"
    obs = membro.get("observacoes") or "Nenhuma"

    hist_str = ""
    for h in reversed(historico):
        acao_info = ACOES_PADRAO.get(h["acao"], {})
        sinal = "+" if h["pontos"] >= 0 else ""
        ts = f"<t:{h['timestamp']}:R>" if h.get("timestamp") else ""
        hist_str += f"`{sinal}{h['pontos']}pts` · {acao_info.get('emoji','')} {acao_info.get('label', h['acao'])} {ts}\n"

    info = (
        f"{emoji.on if ativo else emoji.off} **Status:** `{'Ativo' if ativo else 'Inativo'}`\n"
        f"{emoji.shield_star} **Cargo/Título:** `{cargo_titulo}`\n"
        f"{emoji.coupon} **Pontos totais:** `{pts_total}`\n"
        f"{emoji.time} **Pontos do período:** `{pts_periodo}`\n"
        f"{emoji.message} **Observações:** `{obs[:80]}`"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Staff > <@{user_id}>"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**{emoji.clock} Últimas ações:**\n{hist_str or 'Nenhuma ação registrada.'}"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Toggle Ativo", emoji=emoji.power,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"Staff_ToggleAtivo:{user_id}"),
                disnake.ui.Button(label="Editar", emoji=emoji.edit,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id=f"Staff_EditarMembro:{user_id}"),
                disnake.ui.Button(label="Ajuste de Pontos", emoji=emoji.coupon,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"Staff_AjustePontosMembro:{user_id}"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete,
                                  style=disnake.ButtonStyle.red,
                                  custom_id=f"Staff_RemoverMembro:{user_id}"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Staff_VerLista"),
        ),
    ]


def painel_ranking_components(por_periodo: bool = False) -> list:
    from .helpers import get_colors
    _, ck = get_colors()
    ranking = get_ranking(limite=15, por_periodo=por_periodo)

    medalhas = ["🥇", "🥈", "🥉"]
    linhas = []
    for i, (uid, pts) in enumerate(ranking):
        medal = medalhas[i] if i < 3 else f"`{i+1}.`"
        staff_info = get_membro_staff(int(uid))
        cargo = f" *({staff_info['cargo_titulo']})*" if staff_info and staff_info.get("cargo_titulo") else ""
        linhas.append(f"{medal} <@{uid}>{cargo} — **{pts}pts**")

    conteudo = "\n".join(linhas) if linhas else "Nenhum dado de pontuação ainda."
    tipo_label = "Período Atual" if por_periodo else "Todos os Tempos"
    outro_cid  = "Staff_RankingTotal" if por_periodo else "Staff_RankingPeriodo"
    outro_label = "Ver Todos os Tempos" if por_periodo else "Ver Período Atual"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Staff > **Ranking — {tipo_label}**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(conteudo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=outro_label, emoji=emoji.reload,
                                  style=disnake.ButtonStyle.blurple, custom_id=outro_cid),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Staff_Principal"),
        ),
    ]


def painel_config_pontuacao_components() -> list:
    from .helpers import get_colors
    _, ck = get_colors()
    cfg = carregar_config_pontuacao()
    acoes_cfg = cfg.get("acoes", {})

    linhas_acoes = []
    for key, info in ACOES_PADRAO.items():
        pts_atual = acoes_cfg.get(key, info["pontos"])
        linhas_acoes.append(
            f"{info['emoji']} **{info['label']}:** `{pts_atual}pts` — *{info['descricao']}*"
        )

    canal_id = cfg.get("canal_ranking_id")
    canal_str = f"<#{canal_id}>" if canal_id else "`Não definido`"
    reset_map = {"diario": "Diário", "semanal": "Semanal", "mensal": "Mensal", "nunca": "Nunca"}
    reset_str = reset_map.get(cfg.get("reset_period", "nunca"), "Nunca")

    info_topo = (
        f"{emoji.on if cfg.get('ativo') else emoji.off} **Sistema:** `{'Ativo' if cfg.get('ativo') else 'Inativo'}`\n"
        f"{emoji.textc} **Canal de ranking:** {canal_str}\n"
        f"{emoji.reload} **Reset automático:** `{reset_str}`\n"
        f"{emoji.member} **Mostrar pontos ao usuário:** `{'Sim' if cfg.get('mostrar_pontos_usuario', True) else 'Não'}`\n\n"
        f"**{emoji.coupon} Pontos por ação:**\n" + "\n".join(linhas_acoes)
    )

    opcoes_reset = [
        disnake.SelectOption(label="Nunca resetar", value="nunca", default=cfg.get("reset_period") == "nunca"),
        disnake.SelectOption(label="Resetar Diariamente", value="diario", default=cfg.get("reset_period") == "diario"),
        disnake.SelectOption(label="Resetar Semanalmente", value="semanal", default=cfg.get("reset_period") == "semanal"),
        disnake.SelectOption(label="Resetar Mensalmente", value="mensal", default=cfg.get("reset_period") == "mensal"),
    ]

    opcoes_acoes = [
        disnake.SelectOption(
            label=f"{info['emoji']} {info['label']}",
            value=key,
            description=f"Atual: {acoes_cfg.get(key, info['pontos'])}pts"
        )
        for key, info in ACOES_PADRAO.items()
    ]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                "-# Staff > **Configuração de Pontuação**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info_topo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Toggle Sistema", emoji=emoji.power,
                                  style=disnake.ButtonStyle.grey, custom_id="Staff_ToggleSistemaPontos"),
                disnake.ui.Button(label="Toggle Mostrar ao Usuário", emoji=emoji.member,
                                  style=disnake.ButtonStyle.grey, custom_id="Staff_ToggleMostrarPontos"),
                disnake.ui.Button(label="Definir Canal Ranking", emoji=emoji.textc,
                                  style=disnake.ButtonStyle.blurple, custom_id="Staff_SetCanalRanking"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Staff_SetResetPeriod",
                    placeholder="Período de reset dos pontos...",
                    options=opcoes_reset,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Staff_EditarAcao",
                    placeholder="Selecionar ação para editar pontuação...",
                    options=opcoes_acoes,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Config Multiplicadores", emoji=emoji.wand,
                                  style=disnake.ButtonStyle.grey, custom_id="Staff_ConfigMultiplicadores"),
            ),
            **ck,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey, custom_id="Staff_Principal"),
        ),
    ]
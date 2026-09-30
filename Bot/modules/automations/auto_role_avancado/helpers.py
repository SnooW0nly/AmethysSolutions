"""
modules/automations/auto_role_avancado/helpers.py

Helpers do sistema Auto Rolê Avançado.
Suporta múltiplos tipos de gatilho para concessão automática de cargos:
  - impulsos     : quantidade de boosts dados ao servidor
  - mensagens    : total de mensagens enviadas
  - tempo_call   : tempo acumulado em call (em minutos)
  - tempo_servidor: dias desde que entrou no servidor
  - nivel_xp     : nível/XP (integração futura)
  - cargos_possuidos: se possui determinado cargo
  - reacoes      : total de reações dadas
  - convites     : total de convites válidos
"""
from __future__ import annotations

import asyncio
from typing import Optional

import disnake

from functions.database import database as db

DB_KEY = "automations_auto_role_avancado"

# ──────────────────────────────────────────────────────────────────────────────
# Tipos de gatilho disponíveis
# ──────────────────────────────────────────────────────────────────────────────

TIPOS_GATILHO = {
    "impulsos":          "🚀 Impulsos dados ao servidor",
    "mensagens":         "💬 Total de mensagens enviadas",
    "tempo_call":        "🎙️ Tempo em call (minutos)",
    "tempo_servidor":    "📅 Dias no servidor",
    "convites":          "✉️ Convites válidos",
    "reacoes":           "❤️ Reações dadas",
    "cargos_possuidos":  "🎖️ Possui determinado cargo",
}

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("ativado", False)
    dados.setdefault("regras", [])          # lista de regras
    dados.setdefault("logs_ativados", False)
    dados.setdefault("canal_logs_id", None)
    dados.setdefault("remover_ao_perder", False)  # remove cargo se condição não atendida
    dados.setdefault("mensagens_contagem", {})    # {guild_id: {user_id: count}}
    dados.setdefault("reacoes_contagem", {})      # {guild_id: {user_id: count}}
    return dados


def salvar_config(data: dict) -> None:
    db.save_document(DB_KEY, {}, data)


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura de uma regra
# ──────────────────────────────────────────────────────────────────────────────
# {
#   "id":         str (uuid curto),
#   "nome":       str (label amigável),
#   "tipo":       str (chave de TIPOS_GATILHO),
#   "cargo_id":   int (cargo a conceder),
#   "valor":      int/str (threshold numérico ou cargo_id para tipo cargos_possuidos),
#   "remover_outros": bool (remove outros cargos da mesma regra ao conceder este),
#   "remover_ao_perder": bool (override local),
#   "ativo":      bool,
# }

def nova_regra(nome: str, tipo: str, cargo_id: int, valor, remover_outros: bool = False) -> dict:
    import time
    return {
        "id":              str(int(time.time() * 1000))[-8:],
        "nome":            nome,
        "tipo":            tipo,
        "cargo_id":        cargo_id,
        "valor":           valor,
        "remover_outros":  remover_outros,
        "ativo":           True,
    }


def regras_por_tipo(config: dict, tipo: str) -> list[dict]:
    return [r for r in config.get("regras", []) if r.get("tipo") == tipo and r.get("ativo", True)]


def regra_por_id(config: dict, regra_id: str) -> Optional[dict]:
    for r in config.get("regras", []):
        if r.get("id") == regra_id:
            return r
    return None


def remover_regra(config: dict, regra_id: str) -> bool:
    antes = len(config["regras"])
    config["regras"] = [r for r in config["regras"] if r.get("id") != regra_id]
    return len(config["regras"]) < antes


# ──────────────────────────────────────────────────────────────────────────────
# Contadores internos (mensagens e reações)
# ──────────────────────────────────────────────────────────────────────────────

def incrementar_mensagens(guild_id: int, user_id: int) -> int:
    config = carregar_config()
    gid = str(guild_id)
    uid = str(user_id)
    config["mensagens_contagem"].setdefault(gid, {})
    config["mensagens_contagem"][gid][uid] = config["mensagens_contagem"][gid].get(uid, 0) + 1
    salvar_config(config)
    return config["mensagens_contagem"][gid][uid]


def get_mensagens(guild_id: int, user_id: int) -> int:
    config = carregar_config()
    return config.get("mensagens_contagem", {}).get(str(guild_id), {}).get(str(user_id), 0)


def incrementar_reacoes(guild_id: int, user_id: int) -> int:
    config = carregar_config()
    gid = str(guild_id)
    uid = str(user_id)
    config["reacoes_contagem"].setdefault(gid, {})
    config["reacoes_contagem"][gid][uid] = config["reacoes_contagem"][gid].get(uid, 0) + 1
    salvar_config(config)
    return config["reacoes_contagem"][gid][uid]


def get_reacoes(guild_id: int, user_id: int) -> int:
    config = carregar_config()
    return config.get("reacoes_contagem", {}).get(str(guild_id), {}).get(str(user_id), 0)


# ──────────────────────────────────────────────────────────────────────────────
# Avaliação de gatilhos
# ──────────────────────────────────────────────────────────────────────────────

async def obter_valor_gatilho(
    membro: disnake.Member,
    tipo: str,
    bot,
) -> int | None:
    """Retorna o valor atual do membro para o tipo de gatilho."""
    try:
        guild = membro.guild

        if tipo == "impulsos":
            return membro.premium_since is not None and 1 or 0  # fallback simples

        elif tipo == "mensagens":
            return get_mensagens(guild.id, membro.id)

        elif tipo == "tempo_call":
            # Integração com TempCallTask se existir
            try:
                from modules.automations.temp_em_call.helpers import get_all_voice_data
                all_data = get_all_voice_data()
                udata = all_data.get(str(guild.id), {}).get(str(membro.id), {})
                return int(udata.get("total_seconds", 0) // 60)
            except Exception:
                return 0

        elif tipo == "tempo_servidor":
            if membro.joined_at:
                import datetime
                delta = disnake.utils.utcnow() - membro.joined_at
                return delta.days
            return 0

        elif tipo == "convites":
            # Integração com InviteTracker se existir
            try:
                from modules.automations.invite_tracker.helpers import get_invites_data
                data = get_invites_data()
                gid = str(guild.id)
                uid = str(membro.id)
                return data.get(gid, {}).get("invites", {}).get(uid, {}).get("valid", 0)
            except Exception:
                return 0

        elif tipo == "reacoes":
            return get_reacoes(guild.id, membro.id)

        elif tipo == "cargos_possuidos":
            # valor é o cargo_id que o membro precisa ter
            return 1  # avaliado externamente em verificar_regra

    except Exception:
        return 0

    return 0


async def verificar_regra(
    membro: disnake.Member,
    regra: dict,
    bot,
) -> bool:
    """Retorna True se o membro satisfaz a condição da regra."""
    tipo  = regra.get("tipo")
    valor = regra.get("valor")

    if tipo == "cargos_possuidos":
        try:
            role_ids = [r.id for r in membro.roles]
            return int(valor) in role_ids
        except Exception:
            return False

    if tipo == "impulsos":
        # Contar impulsos reais via guild.premium_subscribers
        count = sum(1 for m in membro.guild.premium_subscribers if m.id == membro.id)
        # premium_subscription_count não é por usuário, mas premium_since indica ativo
        # Para múltiplos impulsos precisamos da API, mas podemos usar premium_since
        try:
            count = membro.guild.premium_subscribers.count(membro) if hasattr(membro.guild.premium_subscribers, "count") else (1 if membro.premium_since else 0)
        except Exception:
            count = 1 if membro.premium_since else 0
        return count >= int(valor)

    atual = await obter_valor_gatilho(membro, tipo, bot)
    if atual is None:
        return False

    try:
        return int(atual) >= int(valor)
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Aplicação de regras a um membro
# ──────────────────────────────────────────────────────────────────────────────

async def aplicar_regras_membro(
    membro: disnake.Member,
    bot,
    tipos_verificar: list[str] | None = None,
) -> list[disnake.Role]:
    """
    Verifica todas as regras para o membro e aplica/remove cargos conforme necessário.
    Retorna lista de cargos concedidos nesta execução.
    """
    config = carregar_config()
    if not config.get("ativado", False):
        return []

    concedidos: list[disnake.Role] = []
    regras = config.get("regras", [])

    for regra in regras:
        if not regra.get("ativo", True):
            continue
        if tipos_verificar and regra.get("tipo") not in tipos_verificar:
            continue

        cargo_id = regra.get("cargo_id")
        if not cargo_id:
            continue

        role = membro.guild.get_role(int(cargo_id))
        if not role:
            continue

        satisfaz = await verificar_regra(membro, regra, bot)

        if satisfaz and role not in membro.roles:
            try:
                await membro.add_roles(role, reason=f"Auto Rolê Avançado: {regra.get('nome', regra.get('id'))}")
                concedidos.append(role)
                await _log_concessao(bot, membro, role, regra, config)
            except disnake.HTTPException:
                pass

        elif not satisfaz and role in membro.roles:
            remove_global = config.get("remover_ao_perder", False)
            remove_local  = regra.get("remover_ao_perder", remove_global)
            if remove_local:
                try:
                    await membro.remove_roles(role, reason=f"Auto Rolê Avançado: condição não atendida")
                except disnake.HTTPException:
                    pass

    return concedidos


# ──────────────────────────────────────────────────────────────────────────────
# Logs
# ──────────────────────────────────────────────────────────────────────────────

async def _log_concessao(bot, membro: disnake.Member, role: disnake.Role, regra: dict, config: dict):
    try:
        if not config.get("logs_ativados", False):
            return
        canal_id = config.get("canal_logs_id")
        if not canal_id:
            return
        canal = bot.get_channel(int(canal_id))
        if not canal:
            return

        from functions.database import database as db_inner
        mode        = db_inner.get_document("custom_mode").get("mode")
        primary_hex = db_inner.get_document("custom_colors").get("primary", "#5c5ef0")
        tipo_label  = TIPOS_GATILHO.get(regra.get("tipo", ""), regra.get("tipo", "?"))

        desc = (
            f"**Membro:** {membro.mention} (`{membro.id}`)\n"
            f"**Cargo concedido:** {role.mention}\n"
            f"**Regra:** `{regra.get('nome', regra.get('id'))}`\n"
            f"**Gatilho:** {tipo_label} ≥ `{regra.get('valor')}`"
        )

        if mode == "embed":
            embed = disnake.Embed(
                title="🎖️ Auto Rolê Avançado — Cargo Concedido",
                description=desc,
                color=disnake.Colour(int(primary_hex.replace("#", ""), 16)),
            )
            await canal.send(embed=embed)
        else:
            cor = disnake.Colour(int(primary_hex.replace("#", ""), 16))
            await canal.send(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# 🎖️ Auto Rolê Avançado\n-# Cargo concedido"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(desc),
                    accent_colour=cor,
                )
            ], flags=disnake.MessageFlags(is_components_v2=True))
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Formatação de resumo de regras (para exibição no painel)
# ──────────────────────────────────────────────────────────────────────────────

def resumo_regras(config: dict, max_exibir: int = 8) -> str:
    regras = config.get("regras", [])
    if not regras:
        return "`Nenhuma regra configurada`"

    linhas = []
    for r in regras[:max_exibir]:
        ativo   = "🟢" if r.get("ativo", True) else "🔴"
        tipo    = TIPOS_GATILHO.get(r.get("tipo", ""), r.get("tipo", "?"))
        cargo   = f"<@&{r['cargo_id']}>" if r.get("cargo_id") else "`?`"
        valor   = r.get("valor", "?")
        nome    = r.get("nome", r.get("id", "?"))
        linhas.append(f"{ativo} **{nome}** — {tipo} ≥ `{valor}` → {cargo}")

    if len(regras) > max_exibir:
        linhas.append(f"*...e mais {len(regras) - max_exibir} regra(s)*")

    return "\n".join(linhas)
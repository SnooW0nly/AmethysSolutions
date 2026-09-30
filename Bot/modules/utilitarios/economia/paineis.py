"""
modules/utilitarios/economia/paineis.py

Todos os builders de UI da economia (containers, embeds, modais).
Sem lógica de negócio — apenas constrói e retorna componentes/embeds.
"""

from __future__ import annotations

from datetime import datetime

import disnake

from functions.database import database as db
from functions.emoji import emoji
from .helper import EconomyHelper
from .guard import EconomyGuard


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES (espelhadas do cog para uso nos selects/labels)
# ─────────────────────────────────────────────────────────────────────────────

ECONOMY_COMMANDS = [
    "daily", "weekly", "monthly", "work", "crime", "rob",
    "fish", "mine", "hunt", "balance", "pay", "leaderboard",
    "slots", "coinflip", "shop", "buy", "inventory",
    "bank", "marriage", "rep_ship", "family", "interactions", "bff"
]
CMD_LABELS = {
    "daily": "Daily", "weekly": "Weekly", "monthly": "Monthly",
    "work": "Trabalhar", "crime": "Crime", "rob": "Roubar",
    "fish": "Pescar", "mine": "Minerar", "hunt": "Caçar",
    "balance": "Saldo", "pay": "Pagar", "leaderboard": "Ranking",
    "slots": "Slots", "coinflip": "CoinFlip", "shop": "Loja",
    "buy": "Comprar", "inventory": "Inventário",
    "bank": "Banco", "marriage": "Casamento", "rep_ship": "Social/Rep",
    "family": "Família", "interactions": "Interações", "bff": "Melhor Amigo"
}
CMD_EMOJIS = {
    "daily": "📅", "weekly": "📆", "monthly": "🗓️", "work": "💼",
    "crime": "🔫", "rob": "🥷", "fish": "🎣", "mine": "⛏️",
    "hunt": "🏹", "balance": "💰", "pay": "💸", "leaderboard": "🏆",
    "slots": "🎰", "coinflip": "🪙", "shop": "🛒", "buy": "🛍️",
    "inventory": "🎒",
    "bank": "🏦", "marriage": "💍", "rep_ship": "💞",
    "family": "👪", "interactions": "🫂", "bff": "⭐"
}
EVENT_TARGETS = [
    "global", "work", "daily", "weekly", "monthly",
    "crime", "rob", "fish", "mine", "hunt", "slots", "coinflip",
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _color() -> int:
    h = (db.get_document("custom_colors") or {}).get("primary")
    return int(h.replace("#", ""), 16) if h else 0x5865F2


def _ck() -> dict:
    c = _color()
    return {"accent_colour": disnake.Colour(c)} if c else {}


def _main_text() -> str:
    s      = EconomyHelper.get_economy_settings()
    on     = s.get("enabled", False)
    logs   = s.get("logs_enabled", False)
    rst    = s.get("reset_time", 0)
    events = EconomyHelper.get_active_events()
    ev_str = f"`{len(events)} ativo(s)`" if events else "`Nenhum`"
    rm     = EconomyHelper.get_role_multipliers()
    lc     = f"<#{s['log_channel']}>" if s.get("log_channel") else "Não configurado"
    return (
        f"**Status:** {f'{emoji.correct} ATIVADO' if on else '{emoji.wrong} DESATIVADO'}\n"
        f"**Moeda:** `{s.get('currency_emoji',f'{emoji.coin}')} {s.get('currency_name','Coin')}`\n"
        f"**Multiplicador Global:** `{s.get('multiplier', 1.0)}x`\n"
        f"**Multiplicadores de Cargo:** `{len(rm)} configurado(s)`\n"
        f"**Eventos Ativos:** {ev_str}\n"
        f"**Reset de Coins:** `{'Nunca' if rst == 0 else EconomyHelper.format_cooldown(rst)}`\n"
        f"**Logs:** {'{emoji.correct}' if logs else '{emoji.wrong}'} {lc}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAINEL PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

def economy_components(inter=None) -> list:
    s    = EconomyHelper.get_economy_settings()
    on   = s.get("enabled", False)
    logs = s.get("logs_enabled", False)
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Sistema de Economia\n-# Painel > **Economia**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(_main_text()),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Economia_Select",
                placeholder="Navegar…",
                options=[
                    disnake.SelectOption(label="Voltar", value="voltar", emoji=emoji.back),
                ],
            )),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Desativar" if on else "Ativar",
                style=disnake.ButtonStyle.red if on else disnake.ButtonStyle.green,
                custom_id="Economia_Toggle",
                emoji=emoji.off if on else emoji.on,
            ),
            disnake.ui.Button(label="Moeda",           style=disnake.ButtonStyle.grey,    custom_id="Economia_Config_Moeda",      emoji=emoji.coin),
            disnake.ui.Button(label="Multiplicadores", style=disnake.ButtonStyle.grey,    custom_id="Economia_Multipliers",       emoji=emoji.chart),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Eventos",         style=disnake.ButtonStyle.blurple, custom_id="Economia_Events",            emoji=emoji.giveaway),
            disnake.ui.Button(label="Usuários",        style=disnake.ButtonStyle.blurple, custom_id="Economia_Users",             emoji=emoji.members),
            disnake.ui.Button(label="Empregos",        style=disnake.ButtonStyle.blurple, custom_id="Economia_Jobs_Config",       emoji=emoji.hammer),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Tempo Reset",     style=disnake.ButtonStyle.grey,    custom_id="Economia_Config_Reset",      emoji=emoji.clock),
            disnake.ui.Button(
                label=f"Logs: {'ON' if logs else 'OFF'}",
                style=disnake.ButtonStyle.grey,
                custom_id="Economia_Toggle_Logs",
                emoji=emoji.power,
            ),
            disnake.ui.Button(label="Canal Logs",      style=disnake.ButtonStyle.grey,    custom_id="Economia_Config_LogChannel", emoji=emoji.textc),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Comandos",        style=disnake.ButtonStyle.grey,    custom_id="Economia_Comandos",          emoji=emoji.commands),
            disnake.ui.Button(label="Loja",            style=disnake.ButtonStyle.grey,    custom_id="Economia_Shop_Config",       emoji=emoji.cart),
            disnake.ui.Button(label="Resetar Tudo",    style=disnake.ButtonStyle.red,     custom_id="Economia_Reset_All",         emoji=emoji.delete),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Guard",           style=disnake.ButtonStyle.blurple, custom_id="Economia_Guard",             emoji=emoji.shield),
        ),
    ]


def economy_embed(inter=None) -> tuple[disnake.Embed, list]:
    s    = EconomyHelper.get_economy_settings()
    on   = s.get("enabled", False)
    logs = s.get("logs_enabled", False)

    embed = disnake.Embed(
        title="Sistema de Economia",
        description=_main_text(),
        color=_color(),
    )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Desativar" if on else "Ativar",
                style=disnake.ButtonStyle.red if on else disnake.ButtonStyle.green,
                custom_id="Economia_Toggle",
                emoji=emoji.off if on else emoji.on,
            ),
            disnake.ui.Button(label="Moeda",           style=disnake.ButtonStyle.grey,    custom_id="Economia_Config_Moeda",      emoji=emoji.coin),
            disnake.ui.Button(label="Multiplicadores", style=disnake.ButtonStyle.grey,    custom_id="Economia_Multipliers",       emoji=emoji.chart),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Eventos",         style=disnake.ButtonStyle.blurple, custom_id="Economia_Events",            emoji=emoji.giveaway),
            disnake.ui.Button(label="Usuários",        style=disnake.ButtonStyle.blurple, custom_id="Economia_Users",             emoji=emoji.members),
            disnake.ui.Button(label="Empregos",        style=disnake.ButtonStyle.blurple, custom_id="Economia_Jobs_Config",       emoji=emoji.hammer),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Tempo Reset",     style=disnake.ButtonStyle.grey,    custom_id="Economia_Config_Reset",      emoji=emoji.clock),
            disnake.ui.Button(
                label=f"Logs: {'ON' if logs else 'OFF'}",
                style=disnake.ButtonStyle.grey,
                custom_id="Economia_Toggle_Logs",
                emoji=emoji.power,
            ),
            disnake.ui.Button(label="Canal Logs",      style=disnake.ButtonStyle.grey,    custom_id="Economia_Config_LogChannel", emoji=emoji.textc),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Comandos",        style=disnake.ButtonStyle.grey,    custom_id="Economia_Comandos",          emoji=emoji.commands),
            disnake.ui.Button(label="Loja",            style=disnake.ButtonStyle.grey,    custom_id="Economia_Shop_Config",       emoji=emoji.cart),
            disnake.ui.Button(label="Resetar Tudo",    style=disnake.ButtonStyle.red,     custom_id="Economia_Reset_All",         emoji=emoji.delete),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Guard",           style=disnake.ButtonStyle.blurple, custom_id="Economia_Guard",             emoji=emoji.shield),
        ),
    ]
    return embed, components


# ═════════════════════════════════════════════════════════════════════════════
# MULTIPLICADORES
# ═════════════════════════════════════════════════════════════════════════════

def multipliers_components(inter=None, guild=None) -> list:
    s  = EconomyHelper.get_economy_settings()
    gm = s.get("multiplier", 1.0)
    rm = s.get("role_multipliers", {})

    role_lines = []
    if rm and guild:
        for rid, val in rm.items():
            role = guild.get_role(int(rid))
            name = role.mention if role else f"Cargo `{rid}`"
            role_lines.append(f"{name} → `{val}x`")
    elif rm:
        for rid, val in rm.items():
            role_lines.append(f"Cargo `{rid}` → `{val}x`")

    rm_text = "\n".join(role_lines) if role_lines else "_Nenhum cargo configurado_"

    remove_opts = [
        disnake.SelectOption(
            label=f"Cargo {rid}",
            value=f"rm_role_{rid}",
            description=f"Remover multiplicador {val}x",
        )
        for rid, val in rm.items()
    ] if rm else [disnake.SelectOption(label="Nenhum cargo", value="none")]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Multiplicadores\n-# Painel > Economia > **Multiplicadores**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                f"**Multiplicador Global:** `{gm}x`\n"
                f"-# Aplicado a **todos** os usuários em **todos** os comandos.\n\n"
                f"**Multiplicadores por Cargo:**\n{rm_text}\n\n"
                f"-# O maior cargo vence. Combinado com o global e eventos."
            ),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Eco_Mult_RemoveRole",
                placeholder="Selecionar cargo para remover multiplicador…",
                options=remove_opts,
            )),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar",               style=disnake.ButtonStyle.grey,    custom_id="Painel_Economia",    emoji=emoji.back),
            disnake.ui.Button(label="Multiplicador Global", style=disnake.ButtonStyle.grey,    custom_id="Eco_Mult_SetGlobal", emoji=emoji.planet),
            disnake.ui.Button(label="Adicionar por Cargo",  style=disnake.ButtonStyle.blurple, custom_id="Eco_Mult_AddRole",   emoji=emoji.role),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# EVENTOS
# ═════════════════════════════════════════════════════════════════════════════

def events_components(inter=None) -> list:
    EconomyHelper.clear_expired_events()
    events = EconomyHelper.get_events()
    now    = datetime.now()

    if events:
        lines = []
        for ev in events:
            end = ev.get("ends_at")
            if end:
                remaining = (datetime.fromisoformat(end) - now).total_seconds()
                time_str = f"{emoji.clock} `{EconomyHelper.format_cooldown(int(remaining))}`" if remaining > 0 else f"{emoji.wrong} Expirado"
            else:
                time_str = "Permanente"
            lines.append(
                f"**{ev['name']}** `{ev['id']}`\n"
                f"-# Alvo: `{ev['target']}` · `{ev['multiplier']}x` · {time_str}"
            )
        ev_text = "\n\n".join(lines)
    else:
        ev_text = "_Nenhum evento criado ainda._"

    remove_opts = [
        disnake.SelectOption(
            label=f"{ev['name']} ({ev['target']} · {ev['multiplier']}x)",
            value=f"rm_ev_{ev['id']}",
            description=f"ID: {ev['id']}",
        )
        for ev in events
    ] if events else [disnake.SelectOption(label="Nenhum evento", value="none")]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Eventos\n-# Painel > Economia > **Eventos**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(ev_text),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Eco_Events_Remove",
                placeholder="Selecionar evento para remover…",
                options=remove_opts,
            )),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar",       style=disnake.ButtonStyle.grey,  custom_id="Painel_Economia",   emoji=emoji.back),
            disnake.ui.Button(label="Criar Evento", style=disnake.ButtonStyle.green, custom_id="Eco_Events_Create", emoji=emoji.plus),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# USUÁRIOS
# ═════════════════════════════════════════════════════════════════════════════

def users_components(inter=None) -> list:
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Gerenciar Usuários\n-# Painel > Economia > **Usuários**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Pesquise um usuário pelo ID para ver o perfil completo e gerenciar "
                "coins, cooldowns, emprego e inventário."
            ),
            disnake.ui.Separator(),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar",         style=disnake.ButtonStyle.grey,    custom_id="Painel_Economia", emoji=emoji.back),
            disnake.ui.Button(label="Buscar Usuário", style=disnake.ButtonStyle.blurple, custom_id="Eco_User_Search", emoji=emoji.search),
        ),
    ]


def user_profile_components(user_id: int, guild=None) -> list:
    p        = EconomyHelper.get_user_profile(user_id)
    s        = EconomyHelper.get_economy_settings()
    cur_name = s.get("currency_name", "Coin")
    cur_em   = s.get("currency_emoji", f"{emoji.coin}")

    job       = p["job"]
    job_str   = f"{job['emoji']} **{job['name']}**" if job else "_Desempregado_"
    streak    = p["streak"]
    streak_str = f"{emoji.fire} {streak['count']} dias" if streak.get("count", 0) > 0 else "_Sem streak_"
    inv       = p["inventory"]
    inv_count = sum(inv.values()) if inv else 0

    cd_lines = []
    for cmd, ts in p["cooldowns"].items():
        last      = datetime.fromisoformat(ts)
        cd_secs   = s.get(cmd, {}).get("cooldown", 0)
        remaining = max(0, int(cd_secs - (datetime.now() - last).total_seconds()))
        if remaining > 0:
            cd_lines.append(f"`{cmd}`: {EconomyHelper.format_cooldown(remaining)}")

    cd_text = "\n".join(cd_lines) if cd_lines else "_Nenhum cooldown ativo_"

    try:
        member       = guild.get_member(user_id) if guild else None
        user_display = f"**{member.display_name}**" if member else f"ID `{user_id}`"
    except Exception:
        user_display = f"ID `{user_id}`"

    text = (
        f"## {emoji.member} {user_display}\n"
        f"{emoji.dolar} **Coins:** `{p['coins']:,}` {cur_em}\n"
        f"{emoji.hammer} **Emprego:** {job_str}\n"
        f"{emoji.fire} **Streak Daily:** {streak_str}\n"
        f"{emoji.dir} **Itens no inventário:** `{inv_count}`\n\n"
        f"**Cooldowns ativos:**\n{cd_text}"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(f"# Perfil\n-# Painel > Economia > Usuários > **{user_id}**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(text),
            disnake.ui.Separator(),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar",          style=disnake.ButtonStyle.grey,  custom_id="Economia_Users",                emoji=emoji.back),
            disnake.ui.Button(label="Setar Coins",     style=disnake.ButtonStyle.grey,  custom_id=f"Eco_User_SetCoins_{user_id}",   emoji=emoji.coins),
            disnake.ui.Button(label="Adicionar Coins", style=disnake.ButtonStyle.green, custom_id=f"Eco_User_AddCoins_{user_id}",   emoji=emoji.plus),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Remover Coins",     style=disnake.ButtonStyle.red,  custom_id=f"Eco_User_RemCoins_{user_id}",    emoji=emoji.minus),
            disnake.ui.Button(label="Resetar Cooldowns", style=disnake.ButtonStyle.grey, custom_id=f"Eco_User_ResetCD_{user_id}",     emoji=emoji.clock),
            disnake.ui.Button(label="Mudar Emprego",     style=disnake.ButtonStyle.grey, custom_id=f"Eco_User_SetJob_{user_id}",      emoji=emoji.hammer),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Resetar Streak",    style=disnake.ButtonStyle.grey, custom_id=f"Eco_User_ResetStreak_{user_id}", emoji=emoji.delete),
            disnake.ui.Button(label="Zerar Inventário",  style=disnake.ButtonStyle.red,  custom_id=f"Eco_User_ClearInv_{user_id}",    emoji=emoji.delete),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# EMPREGOS
# ═════════════════════════════════════════════════════════════════════════════

def jobs_config_components(inter=None) -> list:
    all_jobs = EconomyHelper.get_all_jobs()
    custom   = EconomyHelper.get_economy_settings().get("custom_jobs", {})

    lines = []
    for jid, job in all_jobs.items():
        tag = "*(custom)*" if jid in custom else "*(padrão)*"
        lines.append(
            f"{job['emoji']} **{job['name']}** {tag}\n"
            f"-# Chance: `{job['accept_chance']}%` · Pay: `{job['min_pay']:,}`–`{job['max_pay']:,}`"
        )
    text = "\n\n".join(lines) if lines else "_Nenhum emprego configurado._"

    remove_opts = [
        disnake.SelectOption(
            label=job["name"],
            value=f"rm_job_{jid}",
            emoji=job["emoji"],
            description=f"Remover emprego custom ({jid})",
        )
        for jid, job in custom.items()
    ] if custom else [disnake.SelectOption(label="Nenhum emprego custom", value="none")]

    edit_opts = [
        disnake.SelectOption(
            label=job["name"],
            value=f"edit_job_{jid}",
            emoji=job["emoji"],
            description=f"Editar {job['name']} — {jid}",
        )
        for jid, job in all_jobs.items()
    ] if all_jobs else [disnake.SelectOption(label="Nenhum emprego", value="none")]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Empregos\n-# Painel > Economia > **Empregos**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(text),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Eco_Jobs_Remove",
                placeholder="Remover emprego customizado…",
                options=remove_opts,
            )),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Eco_Jobs_Edit_Select",
                placeholder="Selecionar emprego para editar…",
                options=edit_opts,
            )),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar",            style=disnake.ButtonStyle.grey,  custom_id="Painel_Economia",        emoji=emoji.back),
            disnake.ui.Button(label="Adicionar Emprego", style=disnake.ButtonStyle.green, custom_id="Eco_Jobs_Add",           emoji=emoji.plus),
            disnake.ui.Button(label="Restaurar Padrões", style=disnake.ButtonStyle.grey,  custom_id="Eco_Jobs_ResetDefaults", emoji=emoji.reload),
        ),
    ]


def job_edit_components(jid: str) -> list:
    all_jobs = EconomyHelper.get_all_jobs()
    job      = all_jobs.get(jid)
    if not job:
        return []

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {job['emoji']} Editar: {job['name']}\n"
                f"-# Painel > Economia > Empregos > **{job['name']}**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                f"**ID:** `{jid}`\n"
                f"**Emoji:** {job['emoji']}\n"
                f"**Descrição:** {job.get('description','—')}\n"
                f"**Chance de aceitar:** `{job['accept_chance']}%`\n"
                f"**Salário mín:** `{job['min_pay']:,}` · **máx:** `{job['max_pay']:,}`\n"
                f"**Nível necessário:** `{job.get('level_required', 0)}`"
            ),
            disnake.ui.Separator(),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar",         style=disnake.ButtonStyle.grey,    custom_id="Economia_Jobs_Config",        emoji=emoji.back),
            disnake.ui.Button(label="Editar Tudo",    style=disnake.ButtonStyle.blurple, custom_id=f"Eco_Jobs_EditFull_{jid}",    emoji=emoji.edit),
            disnake.ui.Button(label="Editar Salário", style=disnake.ButtonStyle.grey,    custom_id=f"Eco_Jobs_EditPay_{jid}",     emoji=emoji.coin),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Editar Chance",  style=disnake.ButtonStyle.grey,    custom_id=f"Eco_Jobs_EditChance_{jid}",  emoji=emoji.science),
            disnake.ui.Button(label="Editar Emoji",   style=disnake.ButtonStyle.grey,    custom_id=f"Eco_Jobs_EditEmoji_{jid}",   emoji=emoji.reaction),
            disnake.ui.Button(label="Editar Nível",   style=disnake.ButtonStyle.grey,    custom_id=f"Eco_Jobs_EditLevel_{jid}",   emoji=emoji.sparkles),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# COMANDOS
# ═════════════════════════════════════════════════════════════════════════════

def comandos_components(inter=None) -> list:
    lines = [
        f"{CMD_EMOJIS.get(c,f'{emoji.settings}')} **{CMD_LABELS.get(c,c)}** — "
        f"{f'{emoji.correct}' if EconomyHelper.get_command_status(c) else f'{emoji.wrong}'}"
        for c in ECONOMY_COMMANDS
    ]
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Gerenciar Comandos\n-# Painel > Economia > **Comandos**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("\n".join(lines)),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Economia_Cmd_Select",
                placeholder="Selecione um comando para configurar…",
                options=[
                    disnake.SelectOption(
                        label=CMD_LABELS.get(c, c),
                        value=f"cmd_{c}",
                        emoji=CMD_EMOJIS.get(c, f"{emoji.settings}"),
                        description=f"{'{emoji.correct} Ativado' if EconomyHelper.get_command_status(c) else '{emoji.wrong} Desativado'} — configurar",
                    )
                    for c in ECONOMY_COMMANDS
                ],
            )),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, custom_id="Painel_Economia", emoji=emoji.back)
        ),
    ]


def cmd_config_components(cmd: str) -> list:
    s     = EconomyHelper.get_economy_settings()
    cfg   = s.get(cmd, {})
    on    = EconomyHelper.get_command_status(cmd)
    em    = CMD_EMOJIS.get(cmd, f"{emoji.settings}")
    label = CMD_LABELS.get(cmd, cmd)

    lines = [f"**Status:** {f'{emoji.correct} Ativado' if on else '{emoji.wrong} Desativado'}"]
    for key, display in [
        ("min_reward",            "Recompensa mín"),
        ("max_reward",            "Recompensa máx"),
        ("cooldown",              "Cooldown"),
        ("success_chance",        "Chance sucesso %"),
        ("fine_min",              "Multa mín"),
        ("fine_max",              "Multa máx"),
        ("min_steal_percent",     "Roubo mín %"),
        ("max_steal_percent",     "Roubo máx %"),
        ("fine_percent",          "Multa falha %"),
        ("min_target_balance",    "Saldo mín alvo"),
        ("min_bet",               "Aposta mín"),
        ("max_bet",               "Aposta máx"),
        ("tax_percent",           "Taxa %"),
        ("max_per_day",           "Máx/dia"),
        ("jackpot_multiplier",    "Jackpot mult"),
        ("three_match_multiplier","3 iguais mult"),
        ("two_match_multiplier",  "2 iguais mult"),
        ("streak_bonus",          "Streak bônus"),
    ]:
        if key in cfg:
            val = cfg[key]
            if key == "cooldown":
                val = EconomyHelper.format_cooldown(val)
            elif key in ("min_reward","max_reward","fine_min","fine_max","min_bet","max_bet","min_target_balance") and isinstance(val, int):
                val = f"{val:,}"
            lines.append(f"**{display}:** `{val}`")

    btn_rows = _cmd_buttons(cmd, on)
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {em} {label}\n-# Painel > Economia > Comandos > **{label}**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("\n".join(lines)),
            disnake.ui.Separator(),
            *btn_rows,
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, custom_id="Economia_Comandos", emoji=emoji.back)
        ),
    ]


def _cmd_buttons(cmd: str, is_on: bool) -> list:
    rows = []
    tog  = disnake.ui.Button(
        label="Desativar" if is_on else "Ativar",
        style=disnake.ButtonStyle.red if is_on else disnake.ButtonStyle.green,
        custom_id=f"EcoCmd_Toggle_{cmd}",
        emoji=emoji.off if is_on else emoji.on,
    )
    if cmd in ("daily", "weekly", "monthly", "work", "fish", "mine", "hunt"):
        rows.append(disnake.ui.ActionRow(
            tog,
            disnake.ui.Button(label="Recompensa", style=disnake.ButtonStyle.grey, custom_id=f"EcoCmd_Reward_{cmd}",   emoji="💰"),
            disnake.ui.Button(label="Cooldown",   style=disnake.ButtonStyle.grey, custom_id=f"EcoCmd_Cooldown_{cmd}", emoji="⏱️"),
        ))
        if cmd == "daily":
            rows.append(disnake.ui.ActionRow(
                disnake.ui.Button(label="Toggle Streak", style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Toggle_Streak_daily", emoji="🔥")
            ))
    elif cmd == "crime":
        rows.append(disnake.ui.ActionRow(
            tog,
            disnake.ui.Button(label="Recompensa",     style=disnake.ButtonStyle.grey, custom_id=f"EcoCmd_Reward_{cmd}",   emoji="💰"),
            disnake.ui.Button(label="Cooldown",       style=disnake.ButtonStyle.grey, custom_id=f"EcoCmd_Cooldown_{cmd}", emoji="⏱️"),
        ))
        rows.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="Chance Sucesso", style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Crime_Chance", emoji="🎲"),
            disnake.ui.Button(label="Multa",          style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Crime_Fine",   emoji="👮"),
        ))
    elif cmd == "rob":
        rows.append(disnake.ui.ActionRow(
            tog,
            disnake.ui.Button(label="Chance Sucesso", style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Rob_Chance",      emoji="🎲"),
            disnake.ui.Button(label="Cooldown",       style=disnake.ButtonStyle.grey, custom_id=f"EcoCmd_Cooldown_{cmd}", emoji="⏱️"),
        ))
        rows.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="% Roubo", style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Rob_Steal", emoji="🥷"),
            disnake.ui.Button(label="% Multa", style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Rob_Fine",  emoji="👮"),
        ))
    elif cmd in ("slots", "coinflip"):
        rows.append(disnake.ui.ActionRow(
            tog,
            disnake.ui.Button(label="Apostas", style=disnake.ButtonStyle.grey, custom_id=f"EcoCmd_Bets_{cmd}", emoji="🎲"),
        ))
        if cmd == "slots":
            rows.append(disnake.ui.ActionRow(
                disnake.ui.Button(label="Multiplicadores", style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Slots_Mult", emoji="🎰")
            ))
    elif cmd == "pay":
        rows.append(disnake.ui.ActionRow(
            tog,
            disnake.ui.Button(label="Taxa %",        style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Pay_Tax",   emoji="💸"),
            disnake.ui.Button(label="Limite Diário", style=disnake.ButtonStyle.grey, custom_id="EcoCmd_Pay_Limit", emoji="📊"),
        ))
    else:
        rows.append(disnake.ui.ActionRow(tog))
    return rows


# ═════════════════════════════════════════════════════════════════════════════
# LOJA
# ═════════════════════════════════════════════════════════════════════════════

def shop_config_components(inter=None) -> list:
    items = EconomyHelper.get_shop_items()
    desc  = "\n".join(
        f"{i.get('emoji','📦')} **{i['name']}** — `{i['price']:,}` — {i['description']}"
        for i in items
    ) or "_Sem itens._"
    opts = [
        disnake.SelectOption(label=i["name"], value=f"remove_item_{i['id']}", emoji=i.get("emoji","📦"))
        for i in items
    ] or [disnake.SelectOption(label="Nenhum item", value="none")]

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay("# Loja\n-# Painel > Economia > **Loja**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(desc),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Economia_Shop_Remove_Select",
                placeholder="Remover item…",
                options=opts,
            )),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar",         style=disnake.ButtonStyle.grey,  custom_id="Painel_Economia",   emoji=emoji.back),
            disnake.ui.Button(label="Adicionar Item", style=disnake.ButtonStyle.green, custom_id="Economia_Shop_Add", emoji=emoji.plus),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# GUARD — painel principal
# ═════════════════════════════════════════════════════════════════════════════

def guard_main_components() -> list:
    rl  = EconomyGuard.get_ratelimit()
    bl  = EconomyGuard.get_blacklist()
    ch  = EconomyGuard.get_channels()

    rl_status  = f"{emoji.correct} Ativado" if rl.get("enabled") else f"{emoji.wrong} Desativado"
    rl_seconds = rl.get("seconds", 2.0)
    rl_bypass  = len(rl.get("bypass_roles", []))
    ch_allowed = ch.get("allowed", [])
    ch_blocked = ch.get("blocked", [])

    allowed_str = " ".join(f"<#{c}>" for c in ch_allowed[:5]) if ch_allowed else "`Qualquer canal`"
    blocked_str = " ".join(f"<#{c}>" for c in ch_blocked[:5]) if ch_blocked else "`Nenhum`"

    text = (
        "# Guard — Proteção de Comandos\n"
        "-# Painel > Economia > **Guard**\n\n"
        f"**⚡ Ratelimit:** `{rl_status}` · `{rl_seconds}s` entre comandos\n"
        f"**🔓 Cargos Bypass:** `{rl_bypass} cargo(s)` ignoram o ratelimit\n\n"
        f"**🚫 Blacklist:** `{len(bl.get('users',[]))} usuário(s)` · `{len(bl.get('roles',[]))} cargo(s)`\n\n"
        f"**📢 Canais Permitidos:** {allowed_str}\n"
        f"**🔒 Canais Bloqueados:** {blocked_str}"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(text),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Guard_Nav",
                placeholder="Navegar para…",
                options=[
                    disnake.SelectOption(label="Ratelimit", value="ratelimit", emoji="⚡", description="Intervalo e cargos bypass"),
                    disnake.SelectOption(label="Blacklist",  value="blacklist", emoji="🚫", description="Bloquear usuários ou cargos"),
                    disnake.SelectOption(label="Canais",     value="channels",  emoji="📢", description="Canais permitidos e bloqueados"),
                    disnake.SelectOption(label="← Voltar",   value="voltar",    emoji=emoji.back),
                ],
            )),
            **_ck(),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# GUARD — ratelimit
# ═════════════════════════════════════════════════════════════════════════════

def guard_ratelimit_components() -> list:
    rl      = EconomyGuard.get_ratelimit()
    enabled = rl.get("enabled", False)
    seconds = rl.get("seconds", 2.0)
    bypasses = rl.get("bypass_roles", [])
    bypass_str = " ".join(f"<@&{r}>" for r in bypasses[:10]) if bypasses else "`Nenhum cargo configurado`"

    text = (
        "# ⚡ Ratelimit\n"
        "-# Guard > **Ratelimit**\n\n"
        f"**Status:** {'`✅ Ativado`' if enabled else '`❌ Desativado`'}\n"
        f"**Intervalo:** `{seconds}s` entre cada comando\n\n"
        f"**Cargos Bypass** *(ignoram o ratelimit)*:\n{bypass_str}"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(text),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Desativar" if enabled else "Ativar",
                    style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
                    custom_id="Guard_RL_Toggle",
                    emoji=emoji.off if enabled else emoji.on,
                ),
                disnake.ui.Button(label="Definir Intervalo", style=disnake.ButtonStyle.grey,    custom_id="Guard_RL_SetSeconds",   emoji="⏱️"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Bypass",  style=disnake.ButtonStyle.blurple, custom_id="Guard_RL_AddBypass",    emoji="🔓"),
                disnake.ui.Button(label="Remover Bypass",    style=disnake.ButtonStyle.grey,    custom_id="Guard_RL_RemoveBypass", emoji="🗑️", disabled=not bypasses),
            ),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="← Voltar", style=disnake.ButtonStyle.grey, custom_id="Guard_Back", emoji=emoji.back),
            ),
            **_ck(),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# GUARD — blacklist
# ═════════════════════════════════════════════════════════════════════════════

def guard_blacklist_components() -> list:
    bl    = EconomyGuard.get_blacklist()
    users = bl.get("users", [])
    roles = bl.get("roles", [])
    users_str = " ".join(f"<@{u}>" for u in users[:15]) if users else "`Nenhum usuário`"
    roles_str = " ".join(f"<@&{r}>" for r in roles[:15]) if roles else "`Nenhum cargo`"

    text = (
        "# 🚫 Blacklist\n"
        "-# Guard > **Blacklist**\n\n"
        f"**Usuários bloqueados** `({len(users)})`:\n{users_str}\n\n"
        f"**Cargos bloqueados** `({len(roles)})`:\n{roles_str}"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(text),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Guard_BL_Action",
                placeholder="Ação na blacklist…",
                options=[
                    disnake.SelectOption(label="Adicionar Usuário", value="add_user",    emoji="➕"),
                    disnake.SelectOption(label="Remover Usuário",   value="remove_user", emoji="➖"),
                    disnake.SelectOption(label="Adicionar Cargo",   value="add_role",    emoji="➕"),
                    disnake.SelectOption(label="Remover Cargo",     value="remove_role", emoji="➖"),
                    disnake.SelectOption(label="Limpar Usuários",   value="clear_users", emoji="🗑️"),
                    disnake.SelectOption(label="Limpar Cargos",     value="clear_roles", emoji="🗑️"),
                ],
            )),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="← Voltar", style=disnake.ButtonStyle.grey, custom_id="Guard_Back", emoji=emoji.back),
            ),
            **_ck(),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# GUARD — canais
# ═════════════════════════════════════════════════════════════════════════════

def guard_channels_components() -> list:
    ch      = EconomyGuard.get_channels()
    allowed = ch.get("allowed", [])
    blocked = ch.get("blocked", [])
    allowed_str = " ".join(f"<#{c}>" for c in allowed[:10]) if allowed else "`Qualquer canal (sem restrição)`"
    blocked_str = " ".join(f"<#{c}>" for c in blocked[:10]) if blocked else "`Nenhum canal bloqueado`"

    text = (
        "# 📢 Canais\n"
        "-# Guard > **Canais**\n\n"
        "ℹ️ Se **Permitidos** tiver canais, comandos só funcionam *nesses* canais.\n"
        "Canais **Bloqueados** sempre impedem o uso, independente da lista acima.\n\n"
        f"**✅ Permitidos** `({len(allowed)})`:\n{allowed_str}\n\n"
        f"**🔒 Bloqueados** `({len(blocked)})`:\n{blocked_str}"
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(text),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(disnake.ui.StringSelect(
                custom_id="Guard_CH_Action",
                placeholder="Ação nos canais…",
                options=[
                    disnake.SelectOption(label="Permitir Canal",          value="allow",         emoji="✅"),
                    disnake.SelectOption(label="Remover Permissão",       value="unallow",       emoji="➖"),
                    disnake.SelectOption(label="Bloquear Canal",          value="block",         emoji="🔒"),
                    disnake.SelectOption(label="Desbloquear Canal",       value="unblock",       emoji="🔓"),
                    disnake.SelectOption(label="Limpar Lista Permitidos", value="clear_allowed", emoji="🗑️"),
                    disnake.SelectOption(label="Limpar Lista Bloqueados", value="clear_blocked", emoji="🗑️"),
                ],
            )),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="← Voltar", style=disnake.ButtonStyle.grey, custom_id="Guard_Back", emoji=emoji.back),
            ),
            **_ck(),
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# GUARD — modais
# ═════════════════════════════════════════════════════════════════════════════

def modal_guard_rl_seconds() -> disnake.ui.Modal:
    rl = EconomyGuard.get_ratelimit()
    return disnake.ui.Modal(
        title="Definir Intervalo do Ratelimit",
        custom_id="Modal_Guard_RL_Seconds",
        components=[disnake.ui.TextInput(label="Segundos entre comandos (mín. 0.5)", custom_id="seconds", placeholder=f"Atual: {rl.get('seconds', 2.0)}s", min_length=1, max_length=6)],
    )

def modal_guard_rl_add_bypass() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Ratelimit — Adicionar Cargo Bypass",
        custom_id="Modal_Guard_RL_AddBypass",
        components=[disnake.ui.TextInput(label="ID do Cargo", custom_id="role_id", placeholder="Ex: 987654321098765432", min_length=17, max_length=20)],
    )

def modal_guard_rl_remove_bypass() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Ratelimit — Remover Cargo Bypass",
        custom_id="Modal_Guard_RL_RemoveBypass",
        components=[disnake.ui.TextInput(label="ID do Cargo", custom_id="role_id", placeholder="Ex: 987654321098765432", min_length=17, max_length=20)],
    )

def modal_guard_bl_add_user() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Blacklist — Adicionar Usuário",
        custom_id="Modal_Guard_BL_AddUser",
        components=[disnake.ui.TextInput(label="ID do Usuário", custom_id="user_id", placeholder="Ex: 123456789012345678", min_length=17, max_length=20)],
    )

def modal_guard_bl_remove_user() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Blacklist — Remover Usuário",
        custom_id="Modal_Guard_BL_RemoveUser",
        components=[disnake.ui.TextInput(label="ID do Usuário", custom_id="user_id", placeholder="Ex: 123456789012345678", min_length=17, max_length=20)],
    )

def modal_guard_bl_add_role() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Blacklist — Adicionar Cargo",
        custom_id="Modal_Guard_BL_AddRole",
        components=[disnake.ui.TextInput(label="ID do Cargo", custom_id="role_id", placeholder="Ex: 987654321098765432", min_length=17, max_length=20)],
    )

def modal_guard_bl_remove_role() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Blacklist — Remover Cargo",
        custom_id="Modal_Guard_BL_RemoveRole",
        components=[disnake.ui.TextInput(label="ID do Cargo", custom_id="role_id", placeholder="Ex: 987654321098765432", min_length=17, max_length=20)],
    )

def modal_guard_ch_allow() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Canais — Permitir Canal",
        custom_id="Modal_Guard_CH_Allow",
        components=[disnake.ui.TextInput(label="ID do Canal", custom_id="channel_id", placeholder="Ex: 112233445566778899", min_length=17, max_length=20)],
    )

def modal_guard_ch_unallow() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Canais — Remover Permissão",
        custom_id="Modal_Guard_CH_Unallow",
        components=[disnake.ui.TextInput(label="ID do Canal", custom_id="channel_id", placeholder="Ex: 112233445566778899", min_length=17, max_length=20)],
    )

def modal_guard_ch_block() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Canais — Bloquear Canal",
        custom_id="Modal_Guard_CH_Block",
        components=[disnake.ui.TextInput(label="ID do Canal", custom_id="channel_id", placeholder="Ex: 112233445566778899", min_length=17, max_length=20)],
    )

def modal_guard_ch_unblock() -> disnake.ui.Modal:
    return disnake.ui.Modal(
        title="Canais — Desbloquear Canal",
        custom_id="Modal_Guard_CH_Unblock",
        components=[disnake.ui.TextInput(label="ID do Canal", custom_id="channel_id", placeholder="Ex: 112233445566778899", min_length=17, max_length=20)],
    )

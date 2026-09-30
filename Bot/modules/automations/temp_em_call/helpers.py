from __future__ import annotations

import json
import os
import re
import tempfile
import time
from typing import Any, Optional

import disnake

from functions.database import database as db

# ─── Caminhos ─────────────────────────────────────────────────────────────────
_DB_DIR   = "database/xp"
_VOICE_DB = f"{_DB_DIR}/temp_call_voice.json"

# ─── Defaults ─────────────────────────────────────────────────────────────────
_CONFIG_KEY = "automations_temp_em_call"

_DEFAULT_CONFIG: dict[str, Any] = {
    "ativado":                   False,
    "canal_ranking_id":          None,
    "ranking_message_id":        None,
    "ranking_titulo":            "🏆 Ranking de Voz",
    "ranking_subtitulo":         "Os membros com mais tempo em call.",
    "ranking_intervalo_minutos": 5,
    "ranking_top":               10,
    "thresholds":                [],       # [{segundos, cargo_id, label}]
    "contar_muted":              False,
    "contar_deafened":           False,
    "excluir_canais":            [],       # IDs de canais ignorados
    "incluir_apenas_canais":     [],       # Se preenchido, só conta esses canais
    "modo_envio":                "v2",     # "v2" | "embed"
    "ranking_cor":               None,     # hex sem #
    "log_cargo_canal_id":        None,     # canal de log ao dar cargo
    "resetar_cargo_ao_sair":     False,    # remove cargos se resetar XP
}


# ─── Config ───────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(_CONFIG_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    cfg = dict(_DEFAULT_CONFIG)
    cfg.update(dados)
    return cfg


def salvar_config(data: dict) -> None:
    atual = carregar_config()
    atual.update(data or {})
    db.save_document(_CONFIG_KEY, {}, atual)


# ─── Voice JSON (atomic write) ─────────────────────────────────────────────────
# Estrutura: { "guild_id": { "user_id": { total_seconds, last_join, assigned_roles } } }

def _load_voice() -> dict:
    os.makedirs(_DB_DIR, exist_ok=True)
    if not os.path.exists(_VOICE_DB):
        return {}
    try:
        with open(_VOICE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_voice(data: dict) -> None:
    os.makedirs(_DB_DIR, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=_DB_DIR, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, _VOICE_DB)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_all_voice_data() -> dict:
    return _load_voice()


def get_user_voice(guild_id: int, user_id: int) -> dict:
    data = _load_voice()
    gid, uid = str(guild_id), str(user_id)
    data.setdefault(gid, {})
    data[gid].setdefault(uid, {
        "total_seconds":  0,
        "last_join":      None,
        "assigned_roles": [],
    })
    return data[gid][uid]


def save_user_voice(guild_id: int, user_id: int, user_data: dict) -> None:
    data = _load_voice()
    gid, uid = str(guild_id), str(user_id)
    data.setdefault(gid, {})
    data[gid][uid] = user_data
    _save_voice(data)


def save_all_voice(data: dict) -> None:
    _save_voice(data)


def get_guild_ranking(guild_id: int) -> list[tuple[str, int]]:
    """Retorna lista ordenada de (user_id_str, total_seconds) para o guild."""
    data = _load_voice()
    gid = str(guild_id)
    guild_data = data.get(gid, {})
    ranking = [
        (uid, udata.get("total_seconds", 0))
        for uid, udata in guild_data.items()
    ]
    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking


def reset_user_voice(guild_id: int, user_id: int) -> None:
    data = _load_voice()
    gid, uid = str(guild_id), str(user_id)
    if gid in data and uid in data[gid]:
        data[gid][uid]["total_seconds"]  = 0
        data[gid][uid]["last_join"]      = None
        data[gid][uid]["assigned_roles"] = []
        _save_voice(data)


# ─── Session helpers ──────────────────────────────────────────────────────────

def open_session(user_data: dict) -> None:
    """Abre uma nova sessão de voz."""
    if user_data["last_join"] is None:
        user_data["last_join"] = time.time()


def update_session(user_data: dict) -> int:
    """Acumula tempo parcial e reseta last_join para continuar contando. Retorna segundos somados."""
    last = user_data.get("last_join")
    if last is None:
        return 0
    elapsed = max(0, int(time.time() - last))
    user_data["total_seconds"] += elapsed
    user_data["last_join"] = time.time()
    return elapsed


def close_session(user_data: dict) -> int:
    """Fecha sessão acumulando o tempo restante. Retorna segundos somados."""
    last = user_data.get("last_join")
    if last is None:
        return 0
    elapsed = max(0, int(time.time() - last))
    user_data["total_seconds"] += elapsed
    user_data["last_join"] = None
    return elapsed


# ─── Threshold helpers ────────────────────────────────────────────────────────

def parse_tempo_input(texto: str) -> Optional[int]:
    """
    Converte strings como '24h', '7d', '30m', '3600s', '1d12h' em segundos.
    Retorna None se inválido.
    """
    texto = texto.strip().lower()
    pattern = re.compile(r"(\d+)\s*(d|h|m|s|dias?|horas?|minutos?|segundos?)")
    matches = pattern.findall(texto)
    if not matches:
        # Tenta número puro como segundos
        if texto.isdigit():
            return int(texto)
        return None
    total = 0
    for valor, unidade in matches:
        v = int(valor)
        if unidade.startswith("d"):
            total += v * 86400
        elif unidade.startswith("h"):
            total += v * 3600
        elif unidade.startswith("m"):
            total += v * 60
        elif unidade.startswith("s"):
            total += v
    return total if total > 0 else None


def format_seconds(seconds: int) -> str:
    """Formata segundos em string legível: '2d 3h 15m'."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    hours   = minutes // 60
    days    = hours   // 24
    hours  %= 24
    minutes %= 60
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes and not days:
        parts.append(f"{minutes}m")
    return " ".join(parts) or "0m"


def get_sorted_thresholds(cfg: dict) -> list[dict]:
    """Retorna thresholds ordenados por segundos crescente."""
    return sorted(cfg.get("thresholds", []), key=lambda x: x.get("segundos", 0))


def canal_valido(channel: disnake.VoiceChannel, cfg: dict) -> bool:
    """Verifica se o canal deve ser contabilizado conforme config."""
    cid = channel.id
    incluir = [int(x) for x in cfg.get("incluir_apenas_canais", []) if str(x).isdigit()]
    excluir = [int(x) for x in cfg.get("excluir_canais", []) if str(x).isdigit()]
    if incluir and cid not in incluir:
        return False
    if cid in excluir:
        return False
    return True


def membro_deve_contar(member: disnake.Member, after: disnake.VoiceState, cfg: dict) -> bool:
    """Verifica se o estado do membro deve ser contabilizado."""
    if member.bot:
        return False
    
    # VIP com integração ativa ignora restrições de mute/deaf
    try:
        from modules.loja.cart.subscription_manager import SubscriptionManager
        if SubscriptionManager.is_vip(member.id, "tempcall"):
            return True
    except:
        pass

    if not cfg.get("contar_muted", False) and after.self_mute:
        return False
    if not cfg.get("contar_deafened", False) and after.self_deaf:
        return False
    return True


# ─── Ranking builders ──────────────────────────────────────────────────────────

def _get_primary_colour(cfg: dict) -> Optional[disnake.Colour]:
    cor = (cfg.get("ranking_cor") or "").strip().lstrip("#")
    if cor:
        try:
            return disnake.Colour(int(cor, 16))
        except ValueError:
            pass
    try:
        colors = db.get_document("custom_colors") or {}
        primary_hex = (colors.get("primary") or "").strip().lstrip("#")
        if primary_hex:
            return disnake.Colour(int(primary_hex, 16))
    except Exception:
        pass
    return None


_MEDAL = {0: "🥇", 1: "🥈", 2: "🥉"}


def _build_ranking_text(guild: disnake.Guild, cfg: dict) -> str:
    """Constrói o texto do ranking com os top N membros."""
    top_n   = max(1, min(25, int(cfg.get("ranking_top", 10))))
    ranking = get_guild_ranking(guild.id)

    # Soma tempo de sessões ativas (para ranking em tempo real)
    voice_data = get_all_voice_data()
    gid = str(guild.id)
    now = time.time()

    # Ajustar com sessões abertas
    adjusted: list[tuple[str, int]] = []
    for uid, base_secs in ranking:
        udata = (voice_data.get(gid) or {}).get(uid, {})
        last  = udata.get("last_join")
        extra = max(0, int(now - last)) if last else 0
        adjusted.append((uid, base_secs + extra))
    adjusted.sort(key=lambda x: x[1], reverse=True)

    lines: list[str] = []
    for i, (uid, secs) in enumerate(adjusted[:top_n]):
        if secs <= 0:
            continue
        member = guild.get_member(int(uid))
        nome   = member.display_name if member else f"Usuário ({uid})"
        medal  = _MEDAL.get(i, f"`#{i+1}`")
        tempo  = format_seconds(secs)
        lines.append(f"{medal} **{nome}** — {tempo}")

    if not lines:
        return "-# *Nenhum tempo registrado ainda.*"
    return "\n".join(lines)


def build_ranking_embed(guild: disnake.Guild, cfg: dict) -> disnake.Embed:
    titulo    = cfg.get("ranking_titulo") or "🏆 Ranking de Voz"
    subtitulo = cfg.get("ranking_subtitulo") or ""
    texto     = _build_ranking_text(guild, cfg)
    embed     = disnake.Embed(title=titulo, description=f"{subtitulo}\n\n{texto}".strip() if subtitulo else texto)
    cor       = _get_primary_colour(cfg)
    if cor:
        embed.colour = cor
    embed.set_footer(text="Atualizado automaticamente")
    return embed


def build_ranking_container(guild: disnake.Guild, cfg: dict) -> list:
    titulo    = cfg.get("ranking_titulo") or "🏆 Ranking de Voz"
    subtitulo = cfg.get("ranking_subtitulo") or ""
    texto     = _build_ranking_text(guild, cfg)
    cor       = _get_primary_colour(cfg)

    children  = [disnake.ui.TextDisplay(f"# {titulo}")]
    if subtitulo:
        children.append(disnake.ui.TextDisplay(f"-# {subtitulo}"))
    children.append(disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small))
    children.append(disnake.ui.TextDisplay(texto))
    children.append(disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small))
    children.append(disnake.ui.TextDisplay("-# Atualizado automaticamente"))

    container = (
        disnake.ui.Container(*children, accent_colour=cor)
        if cor else
        disnake.ui.Container(*children)
    )
    return [container]


async def enviar_ou_editar_ranking(
    bot: disnake.Client,
    guild: disnake.Guild,
    cfg: dict,
) -> Optional[int]:
    """
    Envia ou edita a mensagem de ranking no canal configurado.
    Retorna o message_id atualizado (ou None em falha).
    """
    canal_id = cfg.get("canal_ranking_id")
    if not canal_id:
        return None
    try:
        canal = guild.get_channel(int(canal_id))
        if not canal or not isinstance(canal, disnake.TextChannel):
            return None
    except Exception:
        return None

    modo       = cfg.get("modo_envio", "v2")
    message_id = cfg.get("ranking_message_id")

    # Tenta editar mensagem existente
    if message_id:
        try:
            msg = await canal.fetch_message(int(message_id))
            if modo == "embed":
                await msg.edit(embed=build_ranking_embed(guild, cfg), components=[])
            else:
                await msg.edit(
                    components=build_ranking_container(guild, cfg),
                    flags=disnake.MessageFlags(is_components_v2=True),
                )
            return int(message_id)
        except (disnake.NotFound, disnake.HTTPException):
            pass  # Mensagem sumiu, vamos recriar

    # Cria nova mensagem
    try:
        if modo == "embed":
            msg = await canal.send(embed=build_ranking_embed(guild, cfg))
        else:
            msg = await canal.send(
                components=build_ranking_container(guild, cfg),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        salvar_config({"ranking_message_id": str(msg.id)})
        return msg.id
    except disnake.HTTPException:
        return None


async def enviar_log_cargo(
    bot: disnake.Client,
    guild: disnake.Guild,
    member: disnake.Member,
    cargo: disnake.Role,
    threshold: dict,
    cfg: dict,
) -> None:
    """Envia log no canal configurado quando um cargo é concedido."""
    canal_id = cfg.get("log_cargo_canal_id")
    if not canal_id:
        return
    try:
        canal = guild.get_channel(int(canal_id))
        if not canal or not isinstance(canal, disnake.TextChannel):
            return
        tempo_label = threshold.get("label") or format_seconds(threshold.get("segundos", 0))
        modo        = db.get_document("custom_mode").get("mode")
        cor         = _get_primary_colour(cfg)

        if modo == "embed":
            embed = disnake.Embed(
                description=(
                    f"🎉 {member.mention} conquistou o cargo {cargo.mention}!\n"
                    f"-# Tempo acumulado em call: **{tempo_label}**"
                )
            )
            if cor:
                embed.colour = cor
            await canal.send(embed=embed)
        else:
            children = [disnake.ui.TextDisplay(
                f"🎉 {member.mention} conquistou o cargo {cargo.mention}!\n"
                f"-# Tempo acumulado em call: **{tempo_label}**"
            )]
            container = (
                disnake.ui.Container(*children, accent_colour=cor)
                if cor else
                disnake.ui.Container(*children)
            )
            await canal.send(
                components=[container],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
    except Exception:
        pass
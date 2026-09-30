import io
import json
from typing import Optional

import aiohttp
import disnake

from functions.database import database as db


# ─── Configuração Global ──────────────────────────────────────────────────────

def carregar_config() -> dict:
    """Carrega a configuração do banco de dados."""
    dados = db.get_document("automations_boas_vindas") or {}
    if not isinstance(dados, dict):
        dados = {}

    # Status e rota
    dados.setdefault("ativado", True)
    dados.setdefault("rota_envio", "canal")       # "canal" | "dm" | "canal_dm"
    dados.setdefault("ghost_ping_ativo", False)
    dados.setdefault("ghost_ping_canais", [])

    # Configuração da mensagem do canal
    if "canal" not in dados or not isinstance(dados.get("canal"), dict):
        dados["canal"] = {}
    dados["canal"].setdefault("tempo_segundos", 0)
    dados["canal"].setdefault("editor_data", {})

    # Configuração da mensagem da DM
    if "dm" not in dados or not isinstance(dados.get("dm"), dict):
        dados["dm"] = {}
    dados["dm"].setdefault("editor_data", {})

    return dados


def salvar_config(data: dict) -> None:
    """Salva a configuração no banco de dados (merge com o atual)."""
    atual = carregar_config()
    atual.update(data or {})
    db.save_document("automations_boas_vindas", {}, atual)


# ─── Editor de Dados por Rota ─────────────────────────────────────────────────

def get_editor_data(rota: str) -> dict:
    """Retorna o editor_data de uma rota ('canal' ou 'dm')."""
    config = carregar_config()
    return config.get(rota, {}).get("editor_data", {})


def set_editor_data(rota: str, editor_data: dict) -> None:
    """Salva o editor_data de uma rota ('canal' ou 'dm')."""
    config = carregar_config()
    config.setdefault(rota, {})["editor_data"] = editor_data
    db.save_document("automations_boas_vindas", {}, config)


def clear_editor_field(rota: str, field: str) -> None:
    """Remove um campo do editor_data de uma rota."""
    editor_data = get_editor_data(rota)
    editor_data.pop(field, None)
    set_editor_data(rota, editor_data)


def set_editor_field(rota: str, field: str, value) -> None:
    """Define um campo no editor_data de uma rota."""
    editor_data = get_editor_data(rota)
    editor_data[field] = value
    set_editor_data(rota, editor_data)


# ─── Helpers de Canal ─────────────────────────────────────────────────────────

def obter_canal_boas_vindas(guild: disnake.Guild) -> Optional[disnake.TextChannel]:
    """Obtém o canal de boas-vindas configurado para o servidor."""
    definicoes = db.get_document("canais") or {}
    canal_id = definicoes.get("canal_de_boas_vindas")
    try:
        canal_id_int = int(canal_id) if canal_id else None
    except Exception:
        canal_id_int = None
    if not canal_id_int:
        return None
    canal = guild.get_channel(canal_id_int)
    if isinstance(canal, disnake.TextChannel):
        return canal
    return None


# ─── Formatação ───────────────────────────────────────────────────────────────

def formatar_mensagem(template: str, member: disnake.Member) -> str:
    """Formata a mensagem de boas-vindas com as variáveis."""
    guild = member.guild
    substituicoes = {
        "{user}": member.mention,
        "{nameserver}": guild.name if guild else "servidor",
        "{nameuser}": getattr(member, "name", str(member.id)),
        "{servercount}": str(getattr(guild, "member_count", "")),
    }
    conteudo = template or ""
    for chave, valor in substituicoes.items():
        conteudo = conteudo.replace(chave, valor)
    return conteudo


# ─── Helpers de UI (badge, preview legado) ───────────────────────────────────

def parse_hex_to_colour(value: Optional[str]) -> Optional[disnake.Colour]:
    if not value:
        return None
    try:
        s = str(value).strip().lower().lstrip("0x").lstrip("#")
        if len(s) != 6:
            return None
        return disnake.Colour(int(s, 16))
    except Exception:
        return None


def system_badge_row() -> disnake.ui.ActionRow:
    return disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Mensagem do Sistema",
            style=disnake.ButtonStyle.grey,
            custom_id="BV_SystemBadge",
            disabled=True,
        )
    )


async def baixar_imagem(url: Optional[str]) -> Optional[disnake.File]:
    url = (url or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    bytes_data = await resp.read()
                    return disnake.File(io.BytesIO(bytes_data), filename="boas_vindas.png")
    except Exception:
        return None
    return None
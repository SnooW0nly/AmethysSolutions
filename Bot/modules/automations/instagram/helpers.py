"""
modules/automations/instagram/helpers.py

Configuração (load/save), log helpers e builders de UI do post.
Compartilhado entre cog.py (painel + interações) e tsk_instagram.py (task).
"""
from __future__ import annotations

import json
import os
import tempfile

import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY          = "automations_instagram"
_DB_PATH        = "database/automations/instagram"
REACTIONS_JSON  = f"{_DB_PATH}/reacoes.json"
COMMENTS_JSON   = f"{_DB_PATH}/comentarios.json"
POSTS_JSON      = f"{_DB_PATH}/posts.json"


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


# ─── Config ──────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("ativado", False)
    dados.setdefault("canal_id", None)
    dados.setdefault("cargo_id", None)
    dados.setdefault("logs_ativados", False)
    dados.setdefault("emojis", {
        "curtir":      f"{emoji.heart}",
        "comentarios": f"{emoji.speech2}",
        "comentar":    f"{emoji.mail2}",
        "apagar":      f"{emoji.delete}",
    })
    return dados


def salvar_config(data: dict) -> None:
    atual = carregar_config()
    atual.update(data or {})
    db.save_document(DB_KEY, {}, atual)


# ─── UI helpers ───────────────────────────────────────────────────────────────

def accent(primary_hex: str | None) -> dict:
    if primary_hex:
        return {"accent_colour": disnake.Colour(int(primary_hex.replace("#", ""), 16))}
    return {}


def color(primary_hex: str | None) -> disnake.Colour | None:
    if primary_hex:
        return disnake.Colour(int(primary_hex.replace("#", ""), 16))
    return None


# ─── Builders de post ─────────────────────────────────────────────────────────

def build_post_buttons(post_id: int | str, emojis: dict) -> disnake.ui.ActionRow:
    """Monta a ActionRow com os 4 botões de interação do post."""
    reactions = load_json(REACTIONS_JSON)
    comments  = load_json(COMMENTS_JSON)
    sid       = str(post_id)

    qtd_likes = len(reactions.get(sid, []))
    qtd_com   = len(comments.get(sid, []))

    e_curtir  = emojis.get("curtir",      f"{emoji.heart}")
    e_ver     = emojis.get("comentarios", f"{emoji.speech2}")
    e_add     = emojis.get("comentar",    f"{emoji.edit}")
    e_del     = emojis.get("apagar",      f"{emoji.delete}")

    disabled = not bool(post_id)

    return disnake.ui.ActionRow(
        disnake.ui.Button(
            emoji=e_curtir,
            label=str(qtd_likes) if qtd_likes else None,
            style=disnake.ButtonStyle.secondary,
            custom_id=f"IG_curtir_{sid}",
            disabled=disabled,
        ),
        disnake.ui.Button(
            emoji=e_ver,
            label=str(qtd_com) if qtd_com else None,
            style=disnake.ButtonStyle.secondary,
            custom_id=f"IG_comentarios_{sid}",
            disabled=disabled,
        ),
        disnake.ui.Button(
            emoji=e_add,
            style=disnake.ButtonStyle.primary,
            custom_id=f"IG_comentar_{sid}",
            disabled=disabled,
        ),
        disnake.ui.Button(
            emoji=e_del,
            style=disnake.ButtonStyle.danger,
            custom_id=f"IG_apagar_{sid}",
            disabled=disabled,
        ),
    )


def build_post_container(
    autor_mencao: str,
    imagem_url: str,
    conteudo: str | None,
    post_id: int | str,
    emojis: dict,
    primary_hex: str | None,
) -> list:
    """Monta o post no modo Container (components v2)."""
    parts: list = [
        disnake.ui.TextDisplay(f"## {autor_mencao}"),
        disnake.ui.Separator(divider=True, spacing=disnake.SeparatorSpacing.small),
        disnake.ui.MediaGallery(
            disnake.MediaGalleryItem(media=imagem_url, description="Imagem compartilhada")
        ),
    ]

    if conteudo:
        parts.append(disnake.ui.Separator(divider=False, spacing=disnake.SeparatorSpacing.small))
        parts.append(disnake.ui.TextDisplay(conteudo))

    parts.append(disnake.ui.Separator(divider=True, spacing=disnake.SeparatorSpacing.small))
    parts.append(build_post_buttons(post_id, emojis))

    return [disnake.ui.Container(*parts, **accent(primary_hex))]


def build_post_embed(
    autor_nome: str,
    autor_avatar: str,
    autor_mencao: str,
    imagem_url: str,
    conteudo: str | None,
    post_id: int | str,
    emojis: dict,
    primary_hex: str | None,
) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
    """Monta o post no modo Embed."""
    embed = disnake.Embed(title=f"{autor_mencao}:")
    embed.set_author(name=autor_nome, icon_url=autor_avatar)
    embed.set_image(url=imagem_url)

    if conteudo:
        embed.add_field(name="Mensagem:", value=conteudo, inline=False)

    if primary_hex:
        embed.color = color(primary_hex)

    return embed, [build_post_buttons(post_id, emojis)]


# ─── Log helpers ──────────────────────────────────────────────────────────────

async def obter_canal_logs(bot: disnake.ext.commands.Bot) -> disnake.TextChannel | None:
    try:
        canais_config = db.get_document("canais") or {}
        canal_logs_id = canais_config.get("canal_de_logs_do_sistema")
        if canal_logs_id:
            canal = bot.get_channel(int(canal_logs_id))
            if isinstance(canal, disnake.TextChannel):
                return canal
    except (ValueError, AttributeError):
        pass
    return None


async def enviar_log(bot: disnake.ext.commands.Bot, titulo: str, descricao: str, erro: bool = False):
    try:
        config = carregar_config()
        if not config.get("logs_ativados", False):
            return

        canal_logs = await obter_canal_logs(bot)
        if not canal_logs:
            return

        mode        = db.get_document("custom_mode").get("mode")
        colors      = db.get_document("custom_colors") or {}
        primary_hex = colors.get("primary")
        danger_hex  = colors.get("danger", "#dc3545")
        cor_hex     = danger_hex if erro else (primary_hex or "#5865F2")
        cor         = disnake.Colour(int(cor_hex.replace("#", ""), 16))

        if mode == "embed":
            embed = disnake.Embed(
                title=f"{f'{emoji.wrong}' if erro else '📸'} {titulo}",
                description=descricao,
                color=cor,
            )
            await canal_logs.send(embed=embed)
        else:
            container_kwargs = {}
            if primary_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_hex.replace("#", ""), 16))
            await canal_logs.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {f'{emoji.wrong}' if erro else '📸'} {titulo}\n{descricao}"),
                        **container_kwargs,
                    )
                ]
            )
    except Exception:
        pass
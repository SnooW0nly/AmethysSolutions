"""
modules/utilitarios/comunidade/twitter/helpers.py

Config, JSON helpers, log helpers e gerador de imagem (Pillow) do sistema de Twitter/X.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import time
from datetime import datetime
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY       = "automations_twitter"
_DB_PATH     = "database/automations/twitter"
REACTIONS_JSON   = f"{_DB_PATH}/reacoes.json"
COMMENTS_JSON    = f"{_DB_PATH}/comentarios.json"
RETWEETS_JSON    = f"{_DB_PATH}/retweets.json"
POSTS_JSON       = f"{_DB_PATH}/posts.json"

# ── Ícone do X em base64 (logo X branco) ──────────────────────────────────────
# Será desenhado via Pillow diretamente
X_LOGO_SVG = None  # usamos desenho vetorial no Pillow


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


def gerar_post_id() -> str:
    return str(int(time.time() * 1000))


# ─── Config ──────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("ativado", False)
    dados.setdefault("canal_id", None)
    dados.setdefault("cargo_id", None)
    dados.setdefault("admin_cargo_id", None)
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


# ─── Builders de botões ───────────────────────────────────────────────────────

def build_post_buttons(post_id: int | str) -> disnake.ui.ActionRow:
    """Monta a ActionRow com os botões de interação do tweet."""
    reactions = load_json(REACTIONS_JSON)
    comments  = load_json(COMMENTS_JSON)
    retweets  = load_json(RETWEETS_JSON)
    sid       = str(post_id)

    qtd_likes    = len(reactions.get(sid, []))
    qtd_com      = len(comments.get(sid, []))
    qtd_retweets = len(retweets.get(sid, []))

    disabled = not bool(post_id)

    return disnake.ui.ActionRow(
        # Curtir
        disnake.ui.Button(
            emoji="🤍",
            label=str(qtd_likes) if qtd_likes else None,
            style=disnake.ButtonStyle.secondary,
            custom_id=f"TW_curtir_{sid}",
            disabled=disabled,
        ),
        # Retwitar
        disnake.ui.Button(
            emoji="🔁",
            label=str(qtd_retweets) if qtd_retweets else None,
            style=disnake.ButtonStyle.secondary,
            custom_id=f"TW_retweet_{sid}",
            disabled=disabled,
        ),
        # Comentar
        disnake.ui.Button(
            emoji="💬",
            label=str(qtd_com) if qtd_com else None,
            style=disnake.ButtonStyle.secondary,
            custom_id=f"TW_comentar_{sid}",
            disabled=disabled,
        ),
        # Ver stats
        disnake.ui.Button(
            emoji="📊",
            style=disnake.ButtonStyle.secondary,
            custom_id=f"TW_stats_{sid}",
            disabled=disabled,
        ),
        # Apagar
        disnake.ui.Button(
            emoji="🗑️",
            style=disnake.ButtonStyle.danger,
            custom_id=f"TW_apagar_{sid}",
            disabled=disabled,
        ),
    )


# ─── Gerador de imagem estilo X/Twitter (dark) ────────────────────────────────

class TwitterImageGenerator:
    """Gera a imagem estilo X (Twitter) dark de um tweet."""

    # Paleta dark do X
    BG          = (0,   0,   0)        # fundo preto
    CARD_BG     = (0,   0,   0)        # card preto
    BORDER      = (47,  51,  54)       # borda cinza escura
    TEXT_MAIN   = (231, 233, 234)      # texto principal (quase branco)
    TEXT_SUB    = (113, 118, 123)      # texto secundário (cinza)
    TEXT_HANDLE = (113, 118, 123)      # @handle
    SEPARATOR   = (47,  51,  54)       # linha separadora
    ICON_BG     = (0,   0,   0)        # fundo do X

    def __init__(self):
        base_dir   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fonts_path = os.path.join(base_dir, "database", "fonts", "assets", "fonts")
        self.fonts = {
            "regular":  os.path.join(fonts_path, "gg_sans_Regular.ttf"),
            "medium":   os.path.join(fonts_path, "gg_sans_Medium.ttf"),
            "semibold": os.path.join(fonts_path, "gg_sans_Semibold.ttf"),
            "bold":     os.path.join(fonts_path, "gg_sans_Bold.ttf"),
        }

    def _load_font(self, style: str, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(self.fonts[style], size)
        except Exception:
            return ImageFont.load_default()

    def _draw_avatar(
        self,
        img: Image.Image,
        avatar_bytes: bytes | None,
        x: int, y: int,
        size: int,
    ):
        if avatar_bytes:
            try:
                av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                av = av.resize((size, size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (size, size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
                img.paste(av, (x, y), mask)
                return
            except Exception:
                pass
        # Fallback: círculo cinza com inicial
        draw = ImageDraw.Draw(img)
        draw.ellipse([x, y, x + size, y + size], fill=(47, 51, 54))

    def _draw_x_logo(self, draw: ImageDraw.Draw, x: int, y: int, size: int):
        """Desenha o logo X branco em uma área quadrada."""
        pad   = int(size * 0.18)
        x1, y1 = x + pad, y + pad
        x2, y2 = x + size - pad, y + size - pad
        lw = max(3, int(size * 0.12))
        draw.line([(x1, y1), (x2, y2)], fill=(231, 233, 234), width=lw)
        draw.line([(x2, y1), (x1, y2)], fill=(231, 233, 234), width=lw)

    def _wrap_text(self, draw: ImageDraw.Draw, text: str, font, max_width: int) -> list[str]:
        words  = text.split()
        lines, current = [], ""
        for word in words:
            test = f"{current} {word}".strip()
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def generate(
        self,
        mensagem: str,
        autor_nome: str,
        autor_handle: str,
        autor_avatar_bytes: bytes | None,
        timestamp: str,
        qtd_curtidas: int = 0,
        qtd_retweets: int = 0,
        qtd_comentarios: int = 0,
        is_retweet_of: str | None = None,   # nome de quem foi retweetado
    ) -> io.BytesIO:

        WIDTH  = 900
        INNER  = 28
        av_size = 56

        # Fontes
        f_nome    = self._load_font("bold",     24)
        f_handle  = self._load_font("regular",  20)
        f_msg     = self._load_font("regular",  23)
        f_footer  = self._load_font("regular",  18)
        f_rt_label = self._load_font("semibold", 18)
        f_stats   = self._load_font("regular",  19)

        # Calcular altura
        probe  = Image.new("RGB", (WIDTH, 200), self.BG)
        pdraw  = ImageDraw.Draw(probe)
        text_w = WIDTH - INNER * 2
        wrapped = self._wrap_text(pdraw, mensagem, f_msg, text_w)
        line_h  = pdraw.textbbox((0, 0), "Ag", font=f_msg)[3] + 10

        rt_h     = 28 if is_retweet_of else 0
        msg_h    = len(wrapped) * line_h
        stats_h  = 44   # linha de curtidas/retweets
        footer_h = 48   # linha dos botões/timestamp

        card_h = (
            INNER           # topo
            + (rt_h + 6 if rt_h else 0)
            + av_size + 12  # header (avatar + nome)
            + 16            # gap
            + msg_h         # texto
            + 20            # gap
            + 1             # separador
            + stats_h       # stats
            + 1             # separador
            + footer_h      # footer
            + INNER         # base
        )
        card_h = max(card_h, 180)

        img  = Image.new("RGB", (WIDTH, card_h), self.BG)
        draw = ImageDraw.Draw(img)

        # Borda externa
        draw.rectangle([0, 0, WIDTH - 1, card_h - 1], outline=self.BORDER, width=1)

        iy = INNER

        # ── "X retweetou" label ───────────────────────────────────────────────
        if is_retweet_of:
            rt_txt = f"🔁  {is_retweet_of} retweetou"
            draw.text((INNER + av_size // 2, iy), rt_txt, font=f_rt_label, fill=self.TEXT_SUB, anchor="lm")
            iy += rt_h + 6

        # ── Avatar ────────────────────────────────────────────────────────────
        self._draw_avatar(img, autor_avatar_bytes, INNER, iy, av_size)

        # ── Nome + handle + X logo ────────────────────────────────────────────
        name_x = INNER + av_size + 14
        name_y = iy + 2
        draw.text((name_x, name_y), autor_nome, font=f_nome, fill=self.TEXT_MAIN)

        handle_y = name_y + f_nome.size + 4
        draw.text((name_x, handle_y), f"@{autor_handle}", font=f_handle, fill=self.TEXT_HANDLE)

        # X no canto direito
        x_size = 30
        self._draw_x_logo(draw, WIDTH - INNER - x_size, iy + (av_size - x_size) // 2, x_size)

        iy += av_size + 16

        # ── Mensagem ──────────────────────────────────────────────────────────
        for line in wrapped:
            draw.text((INNER, iy), line, font=f_msg, fill=self.TEXT_MAIN)
            iy += line_h

        iy += 20

        # ── Separador ────────────────────────────────────────────────────────
        draw.line([(INNER, iy), (WIDTH - INNER, iy)], fill=self.SEPARATOR, width=1)
        iy += 1

        # ── Stats (curtidas · retweets · comentários) ─────────────────────────
        stats_y = iy + (stats_h - f_stats.size) // 2
        parts = []
        if qtd_curtidas > 0:
            parts.append(f"🤍 {qtd_curtidas} Curtida{'s' if qtd_curtidas != 1 else ''}")
        if qtd_retweets > 0:
            parts.append(f"🔁 {qtd_retweets} Retweet{'s' if qtd_retweets != 1 else ''}")
        if qtd_comentarios > 0:
            parts.append(f"💬 {qtd_comentarios} Comentário{'s' if qtd_comentarios != 1 else ''}")
        stats_txt = "   ·   ".join(parts) if parts else ""
        if stats_txt:
            draw.text((INNER, stats_y), stats_txt, font=f_stats, fill=self.TEXT_SUB)
        iy += stats_h

        # ── Separador 2 ───────────────────────────────────────────────────────
        draw.line([(INNER, iy), (WIDTH - INNER, iy)], fill=self.SEPARATOR, width=1)
        iy += 1

        # ── Footer (timestamp) ────────────────────────────────────────────────
        foot_y = iy + (footer_h - f_footer.size) // 2
        draw.text((INNER, foot_y), timestamp, font=f_footer, fill=self.TEXT_SUB)

        # ── Export ────────────────────────────────────────────────────────────
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf


_gen = TwitterImageGenerator()


def gerar_imagem_tweet(
    mensagem: str,
    autor_nome: str,
    autor_handle: str,
    autor_avatar_bytes: bytes | None,
    timestamp: str,
    post_id: str | None = None,
    is_retweet_of: str | None = None,
) -> io.BytesIO:
    """Wrapper síncrono para gerar a imagem do tweet."""
    reactions = load_json(REACTIONS_JSON) if post_id else {}
    comments  = load_json(COMMENTS_JSON)  if post_id else {}
    retweets  = load_json(RETWEETS_JSON)  if post_id else {}
    sid = str(post_id) if post_id else ""

    return _gen.generate(
        mensagem        = mensagem,
        autor_nome      = autor_nome,
        autor_handle    = autor_handle,
        autor_avatar_bytes = autor_avatar_bytes,
        timestamp       = timestamp,
        qtd_curtidas    = len(reactions.get(sid, [])),
        qtd_retweets    = len(retweets.get(sid, [])),
        qtd_comentarios = len(comments.get(sid, [])),
        is_retweet_of   = is_retweet_of,
    )
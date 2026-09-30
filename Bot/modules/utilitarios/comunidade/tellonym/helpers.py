"""
modules/automations/cartas/helpers.py

Config, JSON helpers, log helpers e gerador de imagem (Pillow) do sistema de cartas.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import textwrap
import time
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY      = "automations_cartas"
_DB_PATH    = "database/automations/cartas"
PENDENTES_JSON   = f"{_DB_PATH}/pendentes.json"
APROVADAS_JSON   = f"{_DB_PATH}/aprovadas.json"
COMENTARIOS_JSON = f"{_DB_PATH}/comentarios.json"


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


def gerar_carta_id() -> str:
    return str(int(time.time() * 1000))


# ─── Config ──────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("ativado", False)
    dados.setdefault("canal_id", None)
    dados.setdefault("cargo_id", None)       # cargo para enviar
    dados.setdefault("staff_cargo_id", None) # cargo para aprovar/recusar
    dados.setdefault("cor", "#7289DA")
    dados.setdefault("logs_ativados", False)
    dados.setdefault("mensagem_id", None)    # ID da mensagem "Enviar Tellonym"
    dados.setdefault("canal_logs_id", None)  # canal de logs das cartas
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

def build_carta_buttons(carta_id: str) -> disnake.ui.ActionRow:
    """Botões exibidos na carta aprovada no canal."""
    comentarios = load_json(COMENTARIOS_JSON)
    qtd = len(comentarios.get(carta_id, []))
    return disnake.ui.ActionRow(
        disnake.ui.Button(
            emoji=emoji.mail2,
            label=str(qtd) if qtd else None,
            style=disnake.ButtonStyle.secondary,
            custom_id=f"Cartas_vercomentarios_{carta_id}",
        ),
        disnake.ui.Button(
            emoji=emoji.edit,
            style=disnake.ButtonStyle.primary,
            custom_id=f"Cartas_comentar_{carta_id}",
        ),
    )


def build_moderacao_buttons(carta_id: str) -> list[disnake.ui.ActionRow]:
    """Botões de aprovação/recusa exibidos nos logs."""
    return [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Aprovar",
                emoji=emoji.correct,
                style=disnake.ButtonStyle.green,
                custom_id=f"Cartas_aprovar_{carta_id}",
            ),
            disnake.ui.Button(
                label="Recusar",
                emoji=emoji.wrong,
                style=disnake.ButtonStyle.red,
                custom_id=f"Cartas_recusar_{carta_id}",
            ),
        )
    ]


# ─── Gerador de imagem ────────────────────────────────────────────────────────

class CartaImageGenerator:
    """Gera a imagem estilo Tellonym de uma carta."""

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

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _draw_anon_avatar(self, img: Image.Image, x: int, y: int, size: int):
        """Avatar anônimo estilo Tellonym: círculo cinza + silhueta branca."""
        draw = ImageDraw.Draw(img)
        draw.ellipse([x, y, x + size, y + size], fill=(200, 200, 200))
        cx = x + size // 2
        # Cabeça
        head_r = int(size * 0.22)
        head_y = y + int(size * 0.20)
        draw.ellipse([cx - head_r, head_y, cx + head_r, head_y + head_r * 2], fill=(255, 255, 255))
        # Corpo
        body_w = int(size * 0.52)
        body_h = int(size * 0.32)
        body_y = y + int(size * 0.54)
        draw.ellipse([cx - body_w // 2, body_y, cx + body_w // 2, body_y + body_h * 2], fill=(255, 255, 255))

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
        self._draw_anon_avatar(img, x, y, size)

    def _wrap_text(self, draw: ImageDraw.Draw, text: str, font, max_width: int) -> list[str]:
        words = text.split()
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
        cor_hex: str,
        para_nome: str | None,
        autor_nome: str,
        autor_avatar_bytes: bytes | None,
        servidor_nome: str,
        servidor_icon_bytes: bytes | None,
        qtd_comentarios: int = 0,
    ) -> io.BytesIO:

        # ── Paleta Tellonym (light) ───────────────────────────────────────────
        CARD      = (255, 255, 255)
        BORDER    = (218, 218, 223)
        TEXT_MAIN = (28,  28,  30)
        TEXT_BODY = (44,  44,  46)
        TEXT_SUB  = (142, 142, 147)
        SEPARATOR = (229, 229, 234)
        accent_rgb = self._hex_to_rgb(cor_hex)

        # ── Layout ────────────────────────────────────────────────────────────
        WIDTH   = 900
        INNER   = 36
        RADIUS  = 22
        av_size = 64

        # ── Fontes (maiores para melhor leitura) ──────────────────────────────
        f_nome   = self._load_font("bold",     28)
        f_label  = self._load_font("regular",  19)
        f_para   = self._load_font("semibold", 22)
        f_msg    = self._load_font("regular",  24)
        f_footer = self._load_font("regular",  18)

        # ── Medir texto ───────────────────────────────────────────────────────
        probe   = Image.new("RGB", (WIDTH, 200))
        pdraw   = ImageDraw.Draw(probe)
        text_w  = WIDTH - INNER * 2
        wrapped = self._wrap_text(pdraw, mensagem, f_msg, text_w)
        line_h  = pdraw.textbbox((0, 0), "Ag", font=f_msg)[3] + 10

        para_h   = 36 if para_nome else 0
        msg_h    = len(wrapped) * line_h
        footer_h = 52

        card_h = INNER + av_size + INNER + para_h + msg_h + 20 + footer_h + INNER
        card_h = max(card_h, 200)

        # ── Imagem = somente o card (sem fundo extra) ─────────────────────────
        img  = Image.new("RGB", (WIDTH, card_h), CARD)
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [0, 0, WIDTH - 1, card_h - 1],
            radius=RADIUS, fill=CARD, outline=BORDER, width=2,
        )

        ix = INNER
        iy = INNER
        iw = WIDTH - INNER

        # ── Avatar ────────────────────────────────────────────────────────────
        self._draw_avatar(img, autor_avatar_bytes, ix, iy, av_size)

        # ── Nome ──────────────────────────────────────────────────────────────
        name_x = ix + av_size + 16
        name_y = iy + (av_size - 28) // 2
        draw.text((name_x, name_y), autor_nome, font=f_nome, fill=TEXT_MAIN)

        # ── "Marcados" (canto direito) ────────────────────────────────────────
        lbl_w = draw.textbbox((0, 0), "Marcados", font=f_label)[2]
        lbl_y = iy + (av_size - 19) // 2
        draw.text((iw - lbl_w, lbl_y), "Marcados", font=f_label, fill=TEXT_SUB)

        cur_y = iy + av_size + INNER

        # ── Para: @menção ─────────────────────────────────────────────────────
        if para_nome:
            draw.text((ix, cur_y), f"Para: {para_nome}", font=f_para, fill=accent_rgb)
            cur_y += para_h

        # ── Mensagem ──────────────────────────────────────────────────────────
        for line in wrapped:
            draw.text((ix, cur_y), line, font=f_msg, fill=TEXT_BODY)
            cur_y += line_h

        # ── Separador footer ──────────────────────────────────────────────────
        sep_y = card_h - footer_h
        draw.line([(ix, sep_y), (iw, sep_y)], fill=SEPARATOR, width=1)

        # ── Footer ────────────────────────────────────────────────────────────
        foot_y = sep_y + 15

        # Footer esquerdo: contador de comentários (sem emoji — Pillow não renderiza cor emoji)
        if qtd_comentarios > 0:
            com_txt = f"{qtd_comentarios} comentário{'s' if qtd_comentarios > 1 else ''}"
            draw.text((ix, foot_y), com_txt, font=f_footer, fill=TEXT_SUB)

        # Footer direito: nome do servidor
        ts_w = draw.textbbox((0, 0), servidor_nome, font=f_footer)[2]
        draw.text((iw - ts_w, foot_y), servidor_nome, font=f_footer, fill=TEXT_SUB)

        # ── Export ────────────────────────────────────────────────────────────
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf


# ─── Log helpers ──────────────────────────────────────────────────────────────

async def obter_canal_logs(bot) -> disnake.TextChannel | None:
    try:
        config        = carregar_config()
        canal_logs_id = config.get("canal_logs_id")
        if canal_logs_id:
            canal = bot.get_channel(int(canal_logs_id))
            if isinstance(canal, disnake.TextChannel):
                return canal
    except (ValueError, AttributeError):
        pass
    return None


async def enviar_log(bot, titulo: str, descricao: str, erro: bool = False):
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
                title=f"{f'{emoji.wrong}' if erro else f'{emoji.mail2}'} {titulo}",
                description=descricao,
                color=cor,
            )
            await canal_logs.send(embed=embed)
        else:
            kw = {}
            if primary_hex:
                kw["accent_colour"] = disnake.Colour(int(primary_hex.replace("#", ""), 16))
            await canal_logs.send(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {f'{emoji.wrong}' if erro else f'{emoji.mail2}'} {titulo}\n{descricao}"),
                    **kw,
                )
            ])
    except Exception:
        pass
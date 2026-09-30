"""
modules/utilitarios/comunidade/verificacao/helpers.py

Config, JSON helpers, gerador de CAPTCHA (Pillow) e utilitários do sistema de verificação.
"""
from __future__ import annotations

import io
import json
import os
import random
import string
import tempfile
import time
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY           = "comunidade_verificacao"
_DB_PATH         = "database/utilitarios/comunidade/verificacao"
CODIGOS_JSON     = f"{_DB_PATH}/codigos.json"
PENDENTES_JSON   = f"{_DB_PATH}/pendentes.json"


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


# ─── Config ───────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("codigo_ativo", False)       # Toggle: modo código
    dados.setdefault("captcha_ativo", False)      # Toggle: modo captcha
    dados.setdefault("captcha_modo", "modal")     # "modal" | "botao"
    dados.setdefault("logs_canal", None)          # canal de logs
    dados.setdefault("cargo_verificado", [])      # lista de IDs de cargo verificado
    dados.setdefault("cargo_responsavel", [])     # lista de IDs de cargo responsável
    dados.setdefault("expulsar_recusado", False)  # Toggle: expulsar se recusado
    dados.setdefault("mensagem_id", None)         # ID da msg do painel público
    dados.setdefault("canal_painel", None)        # canal onde o painel foi enviado
    return dados


def salvar_config(data: dict) -> None:
    db.save_document(DB_KEY, {}, data)


# ─── UI helpers ───────────────────────────────────────────────────────────────

def accent(primary_hex: str | None) -> dict:
    if primary_hex:
        return {"accent_colour": disnake.Colour(int(primary_hex.replace("#", ""), 16))}
    return {}


def color(hex_: str | None) -> disnake.Colour:
    if hex_:
        return disnake.Colour(int(hex_.replace("#", ""), 16))
    return disnake.Colour.blurple()


def _mode() -> str:
    return db.get_document("custom_mode").get("mode", "components")


# ─── Gerenciamento de Códigos ─────────────────────────────────────────────────

MAX_CODIGOS_POR_USER = 5


def get_codigos_usuario(user_id: int) -> list[dict]:
    dados = load_json(CODIGOS_JSON)
    return dados.get(str(user_id), [])


def salvar_codigos_usuario(user_id: int, codigos: list[dict]):
    dados = load_json(CODIGOS_JSON)
    dados[str(user_id)] = codigos
    save_json(CODIGOS_JSON, dados)


def validar_codigo(codigo: str) -> tuple[bool, int | None, dict | None]:
    """
    Retorna (valido, user_id_dono, entrada_codigo).
    Decrementa o uso se tiver limite.
    """
    dados = load_json(CODIGOS_JSON)
    codigo = codigo.strip().upper()
    for uid_str, lista in dados.items():
        for entry in lista:
            if entry.get("codigo", "").upper() == codigo:
                # Verificar usos
                max_usos = entry.get("max_usos")  # None = ilimitado
                usos     = entry.get("usos", 0)
                if max_usos is not None and usos >= max_usos:
                    return False, None, None  # esgotado
                # Incrementar usos
                entry["usos"] = usos + 1
                save_json(CODIGOS_JSON, dados)
                return True, int(uid_str), entry
    return False, None, None


def gerar_codigo_aleatorio(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ─── CAPTCHA ──────────────────────────────────────────────────────────────────

CAPTCHA_CHARS = string.ascii_uppercase + string.digits
CAPTCHA_LEN   = 6


def gerar_texto_captcha() -> str:
    return "".join(random.choices(CAPTCHA_CHARS, k=CAPTCHA_LEN))


def gerar_opcoes_captcha(correto: str, total: int = 25) -> list[str]:
    """Gera lista com `total` opções únicas, uma delas sendo o correto."""
    opcoes = {correto}
    while len(opcoes) < total:
        opcoes.add(gerar_texto_captcha())
    lista = list(opcoes)
    random.shuffle(lista)
    return lista


class CaptchaGenerator:
    def __init__(self):
        base_dir   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fonts_path = os.path.join(base_dir, "database", "fonts", "assets", "fonts")
        self.fonts = {
            "regular":  os.path.join(fonts_path, "gg_sans_Regular.ttf"),
            "bold":     os.path.join(fonts_path, "gg_sans_Bold.ttf"),
            "semibold": os.path.join(fonts_path, "gg_sans_Semibold.ttf"),
        }

    def _load_font(self, style: str, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(self.fonts[style], size)
        except Exception:
            return ImageFont.load_default()

    def generate(self, texto: str, primary_hex: str | None = None) -> io.BytesIO:
        """
        Gera imagem CAPTCHA estilo limpo com:
        - Fundo branco com borda arredondada
        - Texto embaralhado com rotações leves
        - Linhas de ruído
        - Pontos aleatórios
        """
        WIDTH, HEIGHT = 520, 160
        PADDING = 24
        BG     = (255, 255, 255)
        BORDER = (210, 210, 215)

        # Cor de destaque (accent) para algumas letras
        accent_rgb = (88, 101, 242)  # blurple padrão
        if primary_hex:
            h = primary_hex.lstrip("#")
            accent_rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        img  = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)

        # Borda arredondada
        draw.rounded_rectangle([0, 0, WIDTH - 1, HEIGHT - 1], radius=18, outline=BORDER, width=2)

        # Linhas de ruído
        for _ in range(8):
            x1 = random.randint(0, WIDTH)
            y1 = random.randint(0, HEIGHT)
            x2 = random.randint(0, WIDTH)
            y2 = random.randint(0, HEIGHT)
            r, g, b = [random.randint(180, 220) for _ in range(3)]
            draw.line([(x1, y1), (x2, y2)], fill=(r, g, b), width=1)

        # Pontos
        for _ in range(120):
            x = random.randint(PADDING, WIDTH - PADDING)
            y = random.randint(PADDING, HEIGHT - PADDING)
            r, g, b = [random.randint(170, 210) for _ in range(3)]
            draw.ellipse([x, y, x + 2, y + 2], fill=(r, g, b))

        # Letras individuais com rotação e offset vertical
        char_w  = (WIDTH - PADDING * 2) // len(texto)
        font_sz = random.randint(54, 64)
        font    = self._load_font("bold", font_sz)

        for i, ch in enumerate(texto):
            # Renderizar em imagem separada para rotacionar
            ch_img  = Image.new("RGBA", (char_w, HEIGHT), (0, 0, 0, 0))
            ch_draw = ImageDraw.Draw(ch_img)

            # Cor: alterna accent e cinza escuro
            if i % 2 == 0:
                fill = accent_rgb
            else:
                fill = (30, 30, 35)

            bbox  = ch_draw.textbbox((0, 0), ch, font=font)
            cw    = bbox[2] - bbox[0]
            ch_h  = bbox[3] - bbox[1]
            cx    = (char_w - cw) // 2
            cy    = (HEIGHT - ch_h) // 2 + random.randint(-12, 12)
            ch_draw.text((cx, cy), ch, font=font, fill=fill)

            angle = random.randint(-18, 18)
            ch_img = ch_img.rotate(angle, expand=False, resample=Image.Resampling.BICUBIC)

            x_pos = PADDING + i * char_w
            img.paste(ch_img, (x_pos, 0), ch_img)

        # Leve blur para suavizar
        img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf


_captcha_gen = CaptchaGenerator()


# ─── Sessões de CAPTCHA ───────────────────────────────────────────────────────
# user_id → {"texto": str, "expires": float}
_captcha_sessions: dict[int, dict] = {}
CAPTCHA_TTL = 300  # 5 minutos


def criar_sessao_captcha(user_id: int, texto: str):
    _captcha_sessions[user_id] = {
        "texto":   texto,
        "expires": time.time() + CAPTCHA_TTL,
    }


def validar_sessao_captcha(user_id: int, resposta: str) -> bool:
    sess = _captcha_sessions.get(user_id)
    if not sess:
        return False
    if time.time() > sess["expires"]:
        _captcha_sessions.pop(user_id, None)
        return False
    ok = sess["texto"].upper() == resposta.strip().upper()
    if ok:
        _captcha_sessions.pop(user_id, None)
    return ok


def limpar_sessao_captcha(user_id: int):
    _captcha_sessions.pop(user_id, None)


# ─── Log helpers ──────────────────────────────────────────────────────────────

async def enviar_log(bot, titulo: str, descricao: str, erro: bool = False):
    try:
        config     = carregar_config()
        canal_id   = config.get("logs_canal")
        if not canal_id:
            return
        canal = bot.get_channel(int(canal_id))
        if not canal:
            return

        mode        = _mode()
        colors      = db.get_document("custom_colors") or {}
        primary_hex = colors.get("primary")
        danger_hex  = colors.get("danger", "#dc3545")
        cor_hex     = danger_hex if erro else (primary_hex or "#5865F2")

        icone = emoji.wrong if erro else emoji.correct

        if mode == "embed":
            emb = disnake.Embed(
                title=f"{icone} {titulo}",
                description=descricao,
                color=color(cor_hex),
            )
            await canal.send(embed=emb)
        else:
            kw = accent(primary_hex)
            await canal.send(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {icone} {titulo}\n{descricao}"),
                    **kw,
                ),
            ], flags=disnake.MessageFlags(is_components_v2=True))
    except Exception:
        pass
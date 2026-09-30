import re
import io
import os
import time
import asyncio
import aiohttp
import disnake
from disnake.ext import commands
from PIL import Image, ImageDraw, ImageFont
from functions.emoji import emoji
from functions.database import database as db

_RE_ROBUX = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*(?:robux|rbx)\s*$",
    re.IGNORECASE,
)
_RE_REAIS = re.compile(
    r"^\s*(?:r\$\s*)?(\d+(?:[.,]\d+)?)\s*(?:reais|real|brl|r\$)\s*$",
    re.IGNORECASE,
)

ROBUX_TAXA = 0.30

_URL_ROBUX = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Robux_2019_Logo_gold.svg/960px-Robux_2019_Logo_gold.svg.png"
_URL_MONEY = "https://i.pinimg.com/originals/b0/f2/69/b0f26925ac0e76d62fbcb0ac6a5460c0.png"

_icon_cache: dict[str, bytes] = {}

def _parse_number(s: str) -> float:
    return float(s.replace(",", "."))

def _calcular(valor: float, tipo: str, preco_por_mil: float):
    tag = "Achievement Get!"
    if tipo == "robux":
        robux = int(valor)
        preco_sem_taxa = round((robux / 1000) * preco_por_mil, 2)
        preco_com_taxa = round(preco_sem_taxa * (1 - ROBUX_TAXA), 2)
        entrada_fmt          = f"{robux:,} Robux".replace(",", ".")
        resultado_sem_taxa_fmt = "R$ " + f"{preco_sem_taxa:.2f}".replace(".", ",")
        resultado_com_taxa_fmt = "R$ " + f"{preco_com_taxa:.2f}".replace(".", ",")
        main = f"{entrada_fmt}  ->  {resultado_sem_taxa_fmt}  |  {resultado_com_taxa_fmt} (c/ taxa)"
    else:
        robux_bruto = int(valor / (preco_por_mil / 1000))
        robux_liquido = int(valor / (preco_por_mil / 1000) / (1 - ROBUX_TAXA))
        entrada_fmt            = "R$ " + f"{valor:.2f}".replace(".", ",")
        resultado_sem_taxa_fmt = f"{robux_bruto:,} Robux".replace(",", ".")
        resultado_com_taxa_fmt = f"{robux_liquido:,} Robux".replace(",", ".")
        main = f"{entrada_fmt}  ->  {resultado_sem_taxa_fmt}  |  {resultado_com_taxa_fmt} (c/ taxa)"
    return tag, main, entrada_fmt, resultado_sem_taxa_fmt, resultado_com_taxa_fmt

_ICON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "image/png,image/jpeg,image/*;q=0.8,*/*;q=0.5",
}

async def _fetch_icon(url: str) -> bytes | None:
    if url in _icon_cache:
        return _icon_cache[url]
    try:
        async with aiohttp.ClientSession(headers=_ICON_HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    _icon_cache[url] = data
                    return data
                else:
                    print(f"[CalculadoraRoblox] Icone {url} retornou status {resp.status}")
    except Exception as e:
        print(f"[CalculadoraRoblox] Falha ao baixar icone {url}: {e}")
    return None

def _bytes_to_pil(data: bytes) -> Image.Image | None:
    try:
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        print(f"[CalculadoraRoblox] Falha ao decodificar imagem do icone ({len(data)} bytes): {e}")
        return None

def _fallback_robux_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gold = (255, 204, 0, 255)
    d.ellipse([0, 0, size - 1, size - 1], fill=gold)
    r = int(size * 0.32)
    cx, cy = size // 2, size // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 0))
    return img

def _fallback_money_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        [int(size * 0.04), int(size * 0.24), int(size * 0.96), int(size * 0.76)],
        radius=int(size * 0.10),
        fill=(0, 168, 50, 255),
    )
    r = int(size * 0.18)
    cx, cy = size // 2, size // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 130, 40, 255))
    return img

_FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database", "fonts", "assets",
)
_FONT_PATH = os.path.join(_FONT_DIR, "Minecraft.ttf")

_BLACK       = (0,   0,   0,   255)
_BORDER_GRAY = (85,  85,  85,  255)
_BG          = (33,  33,  33,  255)
_YELLOW      = (252, 252, 0,   255)
_WHITE       = (255, 255, 255, 255)

_W, _H       = 1600, 320
_BORDER_B    = 10
_BORDER_G    = 20
_CONTENT     = _BORDER_B + _BORDER_G

_TEXT_X      = 300
_TEXT_RIGHT_MARGIN = _CONTENT + 20
_TEXT_MAX_W  = _W - _TEXT_X - _TEXT_RIGHT_MARGIN

_TEXT_TOP    = _CONTENT + 15
_TEXT_BOTTOM = _H - _CONTENT - 15
_TEXT_GAP    = 10

_ICON_SIZE   = 220
_ICON_X      = _CONTENT + 10
_ICON_Y      = (_H - _ICON_SIZE) // 2

_FONT_MAX_SIZE = 96
_FONT_MIN_SIZE = 14

def _resolve_font_path() -> str | None:
    candidates = [
        _FONT_PATH,
        os.path.join(os.getcwd(), "database", "fonts", "assets", "Minecraft.ttf"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    print(
        f"[CalculadoraRoblox] Fonte não encontrada em nenhum dos caminhos testados "
        f"{candidates}, usando fallback."
    )
    return None

def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return r - l, b - t

def _fit_font(
    draw: ImageDraw.ImageDraw,
    font_path: str | None,
    text: str,
    max_width: int,
    max_height: int,
    max_size: int = _FONT_MAX_SIZE,
    min_size: int = _FONT_MIN_SIZE,
):
    """Acha o maior tamanho de fonte que cabe em max_width x max_height."""
    if not font_path:
        return ImageFont.load_default()

    size = max_size
    while size >= min_size:
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception as e:
            print(f"[CalculadoraRoblox] Falha ao carregar fonte em {font_path}: {e}")
            return ImageFont.load_default()
        w, h = _text_size(draw, text, font)
        if w <= max_width and h <= max_height:
            return font
        size -= 2
    return ImageFont.truetype(font_path, min_size)

def _draw_border_and_corners(img: Image.Image) -> None:
    px  = img.load()
    W, H = img.size
    T=(0,0,0,0); K=(0,0,0,255); G=(85,85,85,255); B=(33,33,33,255)

    def paint_row(y, dy_top, dy_bot):
        for x in range(W):
            dx_l = x
            dx_r = W - 1 - x

            if dy_top < 10:
                if dx_l < 20:              px[x,y]=T; continue
            elif dy_top < 20:
                if dx_l < 10:               px[x,y]=T; continue
                if dx_l < 20:              px[x,y]=K; continue

            if dy_top < 10:
                if dx_r < 30:              px[x,y]=T; continue
                if dx_r < 40:              px[x,y]=K; continue
            elif dy_top < 20:
                if dx_r < 20:              px[x,y]=T; continue
                if dx_r < 30:             px[x,y]=K; continue
            elif dy_top < 30:
                if dx_r < 10:               px[x,y]=T; continue
                if dx_r < 20:             px[x,y]=K; continue

            if dy_bot < 10:
                if dx_l < 30:              px[x,y]=T; continue
                if dx_l < 40:             px[x,y]=K; continue
            elif dy_bot < 20:
                if dx_l < 20:              px[x,y]=T; continue
                if dx_l < 30:             px[x,y]=K; continue
            elif dy_bot < 30:
                if dx_l < 10:               px[x,y]=T; continue
                if dx_l < 20:             px[x,y]=K; continue

            if dy_bot < 10:
                if dx_r < 20:              px[x,y]=T; continue
            elif dy_bot < 20:
                if dx_r < 10:               px[x,y]=T; continue
                if dx_r < 20:             px[x,y]=K; continue

            if dx_l < 10:                   px[x,y]=K; continue
            if dx_r < 10:                   px[x,y]=K; continue
            if dy_top < 10:                 px[x,y]=K; continue
            if dy_bot < 10:                 px[x,y]=K; continue

            gray_w_l = 30 if (dy_top < 40 or dy_bot < 40) else 20
            gray_w_r = 20

            if dx_l < 10 + gray_w_l:       px[x,y]=G; continue
            if dx_r < 10 + gray_w_r:       px[x,y]=G; continue

            gray_h_top = 30 if (10 <= dy_top < 40) else 20
            gray_h_bot = 30 if (10 <= dy_bot < 40) else 20
            if dy_top < 10 + gray_h_top:   px[x,y]=G; continue
            if dy_bot < 10 + gray_h_bot:   px[x,y]=G; continue

            px[x,y]=B

    for y in range(H):
        paint_row(y, y, H - 1 - y)

def _paste_icon(base: Image.Image, icon_pil: Image.Image) -> None:
    icon = icon_pil.convert("RGBA").resize((_ICON_SIZE, _ICON_SIZE), Image.LANCZOS)
    alpha = icon.split()[3]
    base.paste(icon, (_ICON_X, _ICON_Y), alpha)

def generate_minecraft_achievement(
    tag_line: str,
    main_line: str,
    icon_pil: Image.Image,
) -> io.BytesIO:
    img  = Image.new("RGBA", (_W, _H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_border_and_corners(img)
    _paste_icon(img, icon_pil)

    font_path = _resolve_font_path()

    avail_h_total = _TEXT_BOTTOM - _TEXT_TOP - _TEXT_GAP
    # tag_line um pouco menor proporcionalmente que main_line
    max_h_tag  = max(int(avail_h_total * 0.42), _FONT_MIN_SIZE)
    max_h_main = max(avail_h_total - max_h_tag, _FONT_MIN_SIZE)

    font_tag  = _fit_font(draw, font_path, tag_line,  _TEXT_MAX_W, max_h_tag,  max_size=70)
    font_main = _fit_font(draw, font_path, main_line, _TEXT_MAX_W, max_h_main, max_size=_FONT_MAX_SIZE)

    _, h_tag  = _text_size(draw, tag_line,  font_tag)
    _, h_main = _text_size(draw, main_line, font_main)

    block_h = h_tag + _TEXT_GAP + h_main
    avail_h = _TEXT_BOTTOM - _TEXT_TOP
    y_tag  = _TEXT_TOP + max((avail_h - block_h) // 2, 0)
    y_main = y_tag + h_tag + _TEXT_GAP

    # se ainda assim passar do limite inferior (margem de segurança), reposiciona colado no topo
    if y_main + h_main > _TEXT_BOTTOM:
        y_main = max(_TEXT_BOTTOM - h_main, y_tag + h_tag + 2)

    draw.text((_TEXT_X, y_tag),  tag_line,  font=font_tag,  fill=_YELLOW)
    draw.text((_TEXT_X, y_main), main_line, font=font_main, fill=_WHITE)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

_COOLDOWN_SECONDS = 5
_user_cooldowns: dict[int, float] = {}

def _check_cooldown(user_id: int) -> bool:
    now = time.monotonic()
    last = _user_cooldowns.get(user_id, 0.0)
    if now - last < _COOLDOWN_SECONDS:
        return False
    _user_cooldowns[user_id] = now
    if len(_user_cooldowns) > 1000:
        cutoff = now - _COOLDOWN_SECONDS * 10
        for uid in [k for k, v in list(_user_cooldowns.items()) if v < cutoff]:
            _user_cooldowns.pop(uid, None)
    return True

class CalculadoraRobloxTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _icon_cache.clear()

    @commands.Cog.listener("on_message")
    async def on_message(self, message: disnake.Message):
        if message.author.bot or not message.guild:
            return

        config = db.get_document("roblox_config") or {}

        if not config.get("calculadora_enabled", True):
            return

        canal_id = (config.get("canais") or {}).get("canal_calculadora")
        if not canal_id:
            return
        if message.channel.id != int(canal_id):
            return

        content = message.content.strip()
        tipo = None
        valor = None

        m = _RE_ROBUX.match(content)
        if m:
            tipo  = "robux"
            valor = _parse_number(m.group(1))

        if tipo is None:
            m = _RE_REAIS.match(content)
            if m:
                tipo  = "reais"
                valor = _parse_number(m.group(1))

        if tipo is None or valor is None or valor <= 0:
            return

        if not _check_cooldown(message.author.id):
            return

        preco_por_mil = float(config.get("preco_por_mil", 32.70))
        tag_line, main_line, entrada_fmt, resultado_sem_taxa_fmt, resultado_com_taxa_fmt = _calcular(valor, tipo, preco_por_mil)

        icon_url  = _URL_ROBUX if tipo == "robux" else _URL_MONEY
        icon_data = await _fetch_icon(icon_url)

        if icon_data:
            icon_pil = _bytes_to_pil(icon_data)
        else:
            icon_pil = None

        if icon_pil is None:
            icon_pil = _fallback_robux_icon(_ICON_SIZE) if tipo == "robux" else _fallback_money_icon(_ICON_SIZE)

        buf  = generate_minecraft_achievement(tag_line, main_line, icon_pil)
        file = disnake.File(buf, filename="calculadora_robux.png")

        mode   = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        color  = None
        if hex_val := colors.get("primary"):
            try:
                color = int(hex_val.replace("#", ""), 16)
            except Exception:
                pass

        preco_str = f"{preco_por_mil:.2f}".replace('.', ',')
        
        conteudo_texto = (
            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
            f"-# **Calculadora de Robux**\n\n"
            f"> O Roblox retém **30%** de taxa nas transferências feitas via Gamepass.\n"
            f"> Veja abaixo como fica o detalhamento da sua conversão:\n\n"
            f"- **Valor Inserido:** `{entrada_fmt}`\n"
            f"- **Bruto (Sem Taxa):** `{resultado_sem_taxa_fmt}`\n"
            f"- **Líquido (Com Taxa):** `{resultado_com_taxa_fmt}`\n\n"
            f"-# *A cotação atual é de R$ {preco_str} a cada 1.000 Robux.*"
        )

        try:
            if mode == "embed":
                embed = disnake.Embed(
                    description=conteudo_texto,
                    color=color or 0xFF8C00,
                )
                embed.set_image(url="attachment://calculadora_robux.png")
                await message.reply(embed=embed, file=file, mention_author=False)
            else:
                kw = {}
                if color:
                    kw["accent_colour"] = disnake.Colour(color)
                await message.reply(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(conteudo_texto),
                            disnake.ui.MediaGallery(
                                disnake.MediaGalleryItem(
                                    media=disnake.UnfurledMediaItem(
                                        url="attachment://calculadora_robux.png"
                                    )
                                )
                            ),
                            **kw,
                        )
                    ],
                    file=file,
                    flags=disnake.MessageFlags(is_components_v2=True),
                    mention_author=False,
                )
        except Exception as e:
            print(f"[CalculadoraRoblox] Erro ao responder: {e}")

def setup(bot: commands.Bot):
    bot.add_cog(CalculadoraRobloxTask(bot))
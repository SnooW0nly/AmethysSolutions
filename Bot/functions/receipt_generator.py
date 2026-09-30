import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io
from typing import List, Dict, Optional


def _hex_to_rgb(hex_color: str, fallback: tuple) -> tuple:
    """Converte cor hex (#RRGGBB) para tuple RGB, retornando fallback em caso de erro."""
    try:
        h = hex_color.strip().lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return fallback


class ReceiptGenerator:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.fonts_path = os.path.join(self.base_dir, "database", "fonts", "assets", "fonts")

        self.fonts = {
            "regular":  os.path.join(self.fonts_path, "gg sans Regular.ttf"),
            "medium":   os.path.join(self.fonts_path, "gg sans Medium.ttf"),
            "semibold": os.path.join(self.fonts_path, "gg sans Semibold.ttf"),
            "bold":     os.path.join(self.fonts_path, "gg sans Bold.ttf"),
        }

        # Cores padrão
        self._default_bg_color      = (13, 13, 13)
        self._default_card_color    = (22, 22, 24)
        self._default_accent_color  = (87, 242, 135)
        self._default_subtext_color = (160, 160, 168)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_font(self, key: str, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(self.fonts[key], size)
        except Exception:
            return ImageFont.load_default()

    def _circle_image(self, img: Image.Image, size: int) -> Image.Image:
        """Recorta imagem em círculo."""
        img = img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        result.paste(img, (0, 0), mask)
        return result

    def _rounded_image(self, img: Image.Image, size: int, radius: int = 8) -> Image.Image:
        """Recorta imagem com cantos arredondados."""
        img = img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
        result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        result.paste(img, (0, 0), mask)
        return result

    def _draw_checkmark(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int):
        """Desenha checkmark dentro de um círculo verde já desenhado."""
        # traço esquerdo
        draw.line(
            [cx - r // 3, cy, cx - r // 10, cy + r // 3],
            fill=(10, 10, 10), width=max(3, r // 6)
        )
        # traço direito
        draw.line(
            [cx - r // 10, cy + r // 3, cx + r // 2.2, cy - r // 2.8],
            fill=(10, 10, 10), width=max(3, r // 6)
        )

    def _paste_rgba(self, base: Image.Image, overlay: Image.Image, pos: tuple):
        """Cola imagem RGBA sobre base RGB."""
        base.paste(overlay, pos, overlay.split()[3])

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------

    def generate_receipt(
        self,
        user_name: str,
        user_handle: str,
        user_avatar_path: str,
        items: List[Dict],
        total_price: float,
        guild_name: str,
        guild_icon_path: str = None,
        footer_text: str = "amethys.solutions",
        subtotal: float = None,
        discount_amount: float = None,
        coupon_code: str = None,
        # Cores customizáveis (hex strings ou None para usar padrão)
        custom_bg_color: str = None,
        custom_card_color: str = None,
        custom_accent_color: str = None,
    ) -> io.BytesIO:

        # ---------- Cores (padrão ou override via hex) ----------
        bg_color     = _hex_to_rgb(custom_bg_color,    self._default_bg_color)    if custom_bg_color    else self._default_bg_color
        card_color   = _hex_to_rgb(custom_card_color,  self._default_card_color)  if custom_card_color  else self._default_card_color
        green_color  = _hex_to_rgb(custom_accent_color, self._default_accent_color) if custom_accent_color else self._default_accent_color

        # Cores derivadas / fixas
        border_color  = (40, 40, 44)
        text_color    = (255, 255, 255)
        subtext_color = self._default_subtext_color
        divider_color = (38, 38, 42)
        footer_color  = (90, 90, 98)
        price_color   = (255, 255, 255)

        # ---------- tamanhos base ----------
        W = 920
        PAD = 48           # padding externo (card)
        INNER = 44         # padding interno do card
        AVATAR_SIZE = 96
        ICON_SIZE = 38

        # Fontes
        f_name        = self._load_font("bold",     34)
        f_handle      = self._load_font("regular",  22)
        f_date        = self._load_font("regular",  20)
        f_status      = self._load_font("bold",     40)
        f_section     = self._load_font("semibold", 22)
        f_item        = self._load_font("regular",  24)
        f_item_price  = self._load_font("semibold", 24)
        f_sub_label   = self._load_font("regular",  24)
        f_sub_value   = self._load_font("semibold", 24)
        f_total_label = self._load_font("regular",  32)
        f_total_value = self._load_font("bold",     46)
        f_footer      = self._load_font("medium",   18)
        f_coupon      = self._load_font("regular",  20)

        # Calcular altura dinâmica
        ITEM_H      = 44
        items_h     = len(items) * ITEM_H + 16
        discount_h  = 0
        if discount_amount and discount_amount > 0:
            discount_h += 44
            if coupon_code:
                discount_h += 36
        subtotal_h  = 44 if subtotal else 0

        # Seções fixas: header(160) + status(70) + section_label(50) +
        #               items + sub + discount + divider(32) + total(90) + footer(70)
        card_h = 160 + 70 + 50 + items_h + subtotal_h + discount_h + 32 + 90 + 70
        H = card_h + PAD * 2

        # ---------- canvas ----------
        img  = Image.new("RGB", (W, H), bg_color)
        draw = ImageDraw.Draw(img)

        # Card
        card_x0, card_y0 = PAD, PAD
        card_x1, card_y1 = W - PAD, H - PAD
        draw.rounded_rectangle(
            [card_x0, card_y0, card_x1, card_y1],
            radius=28, fill=card_color
        )
        # Borda sutil
        draw.rounded_rectangle(
            [card_x0, card_y0, card_x1, card_y1],
            radius=28, outline=border_color, width=1
        )

        LEFT  = card_x0 + INNER
        RIGHT = card_x1 - INNER
        y     = card_y0 + INNER

        # ---------- Avatar ----------
        if user_avatar_path and os.path.exists(user_avatar_path):
            try:
                av = self._circle_image(Image.open(user_avatar_path), AVATAR_SIZE)
                self._paste_rgba(img, av, (LEFT, y))
            except Exception:
                draw.ellipse([LEFT, y, LEFT + AVATAR_SIZE, y + AVATAR_SIZE], fill=(50, 50, 54))
        else:
            draw.ellipse([LEFT, y, LEFT + AVATAR_SIZE, y + AVATAR_SIZE], fill=(50, 50, 54))

        # Nome e handle
        txt_x = LEFT + AVATAR_SIZE + 22
        draw.text((txt_x, y + 10), user_name, font=f_name, fill=text_color)
        draw.text((txt_x, y + 52), f"@{user_handle}", font=f_handle, fill=subtext_color)

        # Data (canto direito)
        now      = datetime.now()
        date_str = now.strftime("%d/%m • %H:%M")
        dw       = draw.textbbox((0, 0), date_str, font=f_date)[2]
        draw.text((RIGHT - dw, y + 16), date_str, font=f_date, fill=subtext_color)

        y += AVATAR_SIZE + 28

        # ---------- Status: Compra Realizada ----------
        CHECK_R = 20
        cx, cy = LEFT + CHECK_R, y + CHECK_R
        draw.ellipse([cx - CHECK_R, cy - CHECK_R, cx + CHECK_R, cy + CHECK_R], fill=green_color)
        self._draw_checkmark(draw, cx, cy, CHECK_R)

        draw.text((LEFT + CHECK_R * 2 + 16, y - 2), "Compra Realizada", font=f_status, fill=text_color)
        y += CHECK_R * 2 + 36

        # ---------- Seção Carrinho ----------
        draw.text((LEFT, y), "Carrinho", font=f_section, fill=subtext_color)
        y += 38

        for item in items:
            product_name = item.get("product_name", "Produto")
            campo_name   = item.get("campo_name", "")
            quantity     = item.get("quantity", 1)
            price        = item.get("price", 0)

            item_text  = f"{quantity}x {product_name}"
            if campo_name:
                item_text += f"  |  {campo_name}"
            price_text = f"R$ {price:.2f}".replace(".", ",")

            draw.text((LEFT, y), item_text, font=f_item, fill=text_color)
            pw = draw.textbbox((0, 0), price_text, font=f_item_price)[2]
            draw.text((RIGHT - pw, y), price_text, font=f_item_price, fill=price_color)
            y += ITEM_H

        y += 16

        # ---------- Subtotal ----------
        if subtotal:
            st_text = f"R$ {subtotal:.2f}".replace(".", ",")
            draw.text((LEFT, y), "Subtotal", font=f_sub_label, fill=subtext_color)
            sw = draw.textbbox((0, 0), st_text, font=f_sub_value)[2]
            draw.text((RIGHT - sw, y), st_text, font=f_sub_value, fill=subtext_color)
            y += 44

        # ---------- Desconto e Cupom ----------
        if discount_amount and discount_amount > 0:
            disc_text = f"Desconto  -R$ {discount_amount:.2f}".replace(".", ",")
            draw.text((LEFT, y), disc_text, font=f_sub_label, fill=green_color)
            y += 44
            if coupon_code:
                draw.text((LEFT, y), f"Cupom aplicado: {coupon_code}", font=f_coupon, fill=subtext_color)
                y += 36

        # ---------- Divisor ----------
        draw.line([(LEFT, y), (RIGHT, y)], fill=divider_color, width=2)
        y += 32

        # ---------- Total ----------
        draw.text((LEFT, y), "Valor pago", font=f_total_label, fill=subtext_color)
        total_text = f"R$ {total_price:.2f}".replace(".", ",")
        tw = draw.textbbox((0, 0), total_text, font=f_total_value)[2]
        # alinhar verticalmente ao label
        th_label = draw.textbbox((0, 0), "Valor pago", font=f_total_label)[3]
        th_total = draw.textbbox((0, 0), total_text, font=f_total_value)[3]
        draw.text((RIGHT - tw, y - (th_total - th_label) // 2), total_text, font=f_total_value, fill=green_color)
        y += 90

        # ---------- Footer ----------
        # Ícone do servidor
        if guild_icon_path and os.path.exists(guild_icon_path):
            try:
                gi = self._rounded_image(Image.open(guild_icon_path), ICON_SIZE, radius=10)
                self._paste_rgba(img, gi, (LEFT, y))
            except Exception:
                draw.rounded_rectangle([LEFT, y, LEFT + ICON_SIZE, y + ICON_SIZE], radius=8, fill=(50, 50, 54))
        else:
            draw.rounded_rectangle([LEFT, y, LEFT + ICON_SIZE, y + ICON_SIZE], radius=8, fill=(50, 50, 54))

        draw.text((LEFT + ICON_SIZE + 12, y + (ICON_SIZE - 18) // 2), guild_name.upper(), font=f_footer, fill=text_color)

        site_w = draw.textbbox((0, 0), footer_text, font=f_footer)[2]
        draw.text((RIGHT - site_w, y + (ICON_SIZE - 18) // 2), footer_text, font=f_footer, fill=footer_color)

        # ---------- Exportar ----------
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

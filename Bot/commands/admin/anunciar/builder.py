import asyncio
import aiohttp
import io
import json
import os
import re
from urllib.parse import urlparse, unquote
from typing import Any, Dict, List, Optional, Tuple

import disnake

from functions.database import database
from functions.emoji import emoji
from ..anunciar import Anunciar
from .components.buttons import Buttons

# Precompiled token regex for container parsing
TOKEN_RE = re.compile(r"\{\{(.*?)\}\}")

# Ordem padrão dos componentes
DEFAULT_ORDER = ["buttons", "selects"]

# Tipos de componente da API do Discord
_DAPI_TEXT_DISPLAY  = 10
_DAPI_MEDIA_GALLERY = 12
_DAPI_SEPARATOR     = 14
_DAPI_CONTAINER     = 17
_DAPI_ACTION_ROW    = 1
_DAPI_BUTTON        = 2
_DAPI_STRING_SELECT = 3


class Builder:
    @staticmethod
    async def _download_external_image(url: str) -> Optional[disnake.File]:
        """Download de imagem assíncrono, sem bloquear o event loop."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    resp.raise_for_status()

                    parsed = urlparse(url)
                    name   = unquote(os.path.basename(parsed.path)) or "image"

                    content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    default_ext  = None
                    if content_type in ("image/jpeg", "image/jpg"):
                        default_ext = ".jpg"
                    elif content_type == "image/png":
                        default_ext = ".png"
                    elif content_type == "image/gif":
                        default_ext = ".gif"
                    elif content_type == "image/webp":
                        default_ext = ".webp"

                    if "." not in name and default_ext:
                        name = f"{name}{default_ext}"
                    elif "." not in name:
                        name = f"{name}.png"

                    data = await resp.read()
                    return disnake.File(fp=io.BytesIO(data), filename=name)
        except Exception:
            return None

    @staticmethod
    def _parse_color_to_int(color_text: str) -> Optional[int]:
        try:
            color_text = color_text.strip()
            if color_text.startswith("#"):
                return int(color_text[1:], 16)
            if color_text.lower().startswith("0x"):
                return int(color_text, 16)
            return int(color_text, 16)
        except Exception:
            return None

    @staticmethod
    def _parse_image_token(params: str) -> Optional[disnake.ui.MediaGallery]:
        url     = None
        desc    = None
        spoiler = False
        url_m   = re.search(r"url='([^']+)'", params)
        if url_m:
            url = url_m.group(1)
        desc_m = re.search(r"desc='([^']*)'", params)
        if desc_m:
            desc = desc_m.group(1)
        if re.search(r"\bspoiler\b", params):
            spoiler = True
        if not url:
            return None
        return disnake.ui.MediaGallery(
            disnake.MediaGalleryItem(media=url, description=desc or None, spoiler=spoiler)
        )

    @staticmethod
    def _load_cfg() -> Dict[str, Any]:
        return database.get_document("messages_anunciar") or {}

    @staticmethod
    def _build_embed(msg_cfg: Dict[str, Any]) -> Optional[disnake.Embed]:
        embed_cfg: Dict[str, Any] = msg_cfg.get("embed") or {}
        has_any = any([
            embed_cfg.get("title"),
            embed_cfg.get("description"),
            embed_cfg.get("color"),
            embed_cfg.get("footer"),
        ])
        if not has_any:
            return None

        e = disnake.Embed()
        if embed_cfg.get("title"):
            e.title = embed_cfg["title"]
        if embed_cfg.get("description"):
            e.description = embed_cfg["description"]
        if embed_cfg.get("color"):
            try:
                e.color = int(embed_cfg["color"].lstrip("#"), 16)
            except Exception:
                pass
        if embed_cfg.get("footer"):
            e.set_footer(text=embed_cfg["footer"])

        if Anunciar._safe_get(msg_cfg, "embed.banner"):
            e.set_image(url=Anunciar._safe_get(msg_cfg, "embed.banner"))
        if Anunciar._safe_get(msg_cfg, "embed.thumbnail"):
            e.set_thumbnail(url=Anunciar._safe_get(msg_cfg, "embed.thumbnail"))
        return e

    @staticmethod
    def _build_buttons(msg_cfg: Dict[str, Any]) -> List[disnake.ui.ActionRow]:
        rows: List[disnake.ui.ActionRow] = []
        btns: List[Dict[str, Any]]       = msg_cfg.get("buttons") or []
        current_row: List[disnake.ui.Button] = []

        for b in btns:
            label        = b.get("label") or None
            data         = b.get("button", {})
            btn_type     = data.get("type", "disabled")
            style        = Buttons._style_from_str(data.get("style"))
            emoji_raw    = data.get("emoji")
            parsed_emoji = Buttons.processar_emoji(emoji_raw) if emoji_raw else None

            if btn_type == "url":
                button = disnake.ui.Button(
                    label=label,
                    style=disnake.ButtonStyle.url,
                    url=data.get("url"),
                    emoji=parsed_emoji,
                )
            else:
                button = disnake.ui.Button(
                    label=label,
                    style=style,
                    emoji=parsed_emoji,
                    custom_id=f"Anunciar_RuntimeAction_Botao_{b.get('id')}",
                    disabled=(btn_type == "disabled" or data.get("disabled", False)),
                )

            current_row.append(button)
            if len(current_row) == 5:
                rows.append(disnake.ui.ActionRow(*current_row))
                current_row = []

        if current_row:
            rows.append(disnake.ui.ActionRow(*current_row))

        return rows

    @staticmethod
    def _build_selects(msg_cfg: Dict[str, Any]) -> List[disnake.ui.ActionRow]:
        rows: List[disnake.ui.ActionRow] = []
        selects: List[Dict[str, Any]]    = msg_cfg.get("selects") or []

        for s in selects:
            options_data = s.get("options") or []
            if not options_data:
                continue

            options: List[disnake.SelectOption] = []
            for o in options_data:
                emoji_raw  = o.get("emoji")
                proc_emoji = Buttons.processar_emoji(emoji_raw) if emoji_raw else None
                options.append(
                    disnake.SelectOption(
                        label=o.get("label") or "Opção",
                        value=o.get("id"),
                        description=o.get("description") or None,
                        emoji=proc_emoji,
                    )
                )

            if not options:
                continue

            min_v = max(1, min(len(options), int(s.get("min_values") or 1)))
            max_v = max(min_v, min(len(options), int(s.get("max_values") or 1)))

            rows.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder=s.get("placeholder") or "Selecione uma opção",
                        custom_id=f"Anunciar_RuntimeAction_Select_{s.get('id')}",
                        options=options,
                        min_values=min_v,
                        max_values=max_v,
                    )
                )
            )

        return rows

    @staticmethod
    def _parse_container(text: str) -> Tuple[List[Any], Optional[int]]:
        if not text:
            return [], None

        components: List[Any]             = []
        accent_color_value: Optional[int] = None
        pos = 0
        for m in TOKEN_RE.finditer(text):
            if m.start() > pos:
                chunk = text[pos:m.start()].strip()
                if chunk:
                    components.append(disnake.ui.TextDisplay(chunk))

            inner = m.group(1).strip()
            if inner.lower() == "separator":
                components.append(disnake.ui.Separator())
            elif inner.lower().startswith("color:"):
                color_text         = inner[6:].strip()
                accent_color_value = Builder._parse_color_to_int(color_text)
            elif inner.lower().startswith("image"):
                params  = inner[5:].strip()
                gallery = Builder._parse_image_token(params)
                if gallery is not None:
                    components.append(gallery)
            pos = m.end()

        if pos < len(text):
            tail = text[pos:].strip()
            if tail:
                components.append(disnake.ui.TextDisplay(tail))

        return components, accent_color_value

    # ─── Converte JSON da API do Discord → componentes disnake ───────────────

    @staticmethod
    def _emoji_from_dapi(emoji_data: Optional[Dict]) -> Optional[str]:
        """Converte objeto emoji do Discord para string usável no disnake."""
        if not emoji_data:
            return None
        emoji_id   = emoji_data.get("id")
        emoji_name = emoji_data.get("name") or ""
        if emoji_id:
            return f"<:{emoji_name}:{emoji_id}>"
        return emoji_name or None

    @staticmethod
    def _button_style_from_dapi(style: int) -> disnake.ButtonStyle:
        return {
            1: disnake.ButtonStyle.primary,
            2: disnake.ButtonStyle.secondary,
            3: disnake.ButtonStyle.success,
            4: disnake.ButtonStyle.danger,
            5: disnake.ButtonStyle.url,
        }.get(style, disnake.ButtonStyle.secondary)

    @staticmethod
    def _build_discord_component(comp: Dict[str, Any]) -> Optional[Any]:
        """
        Converte um componente no formato JSON da API do Discord
        em um objeto disnake equivalente.
        Suporta: TextDisplay (10), MediaGallery (12), Separator (14),
                 Container (17), ActionRow (1) com Buttons (2) e StringSelect (3).
        """
        t = comp.get("type")

        if t == _DAPI_TEXT_DISPLAY:
            content = comp.get("content") or ""
            if not content:
                return None
            return disnake.ui.TextDisplay(content)

        if t == _DAPI_SEPARATOR:
            spacing_map = {1: disnake.SeparatorSpacing.small, 2: disnake.SeparatorSpacing.large}
            spacing = spacing_map.get(comp.get("spacing", 1), disnake.SeparatorSpacing.small)
            divider = comp.get("divider", True)
            return disnake.ui.Separator(spacing=spacing, divider=divider)

        if t == _DAPI_MEDIA_GALLERY:
            items_data = comp.get("items") or []
            if not items_data:
                return None
            items = []
            for item in items_data:
                media = item.get("media") or {}
                url   = media.get("url") or ""
                if not url:
                    continue
                items.append(
                    disnake.MediaGalleryItem(
                        media=url,
                        description=item.get("description") or None,
                        spoiler=bool(item.get("spoiler", False)),
                    )
                )
            if not items:
                return None
            return disnake.ui.MediaGallery(*items)

        if t == _DAPI_ACTION_ROW:
            inner_comps = comp.get("components") or []
            built: List[Any] = []
            for ic in inner_comps:
                obj = Builder._build_discord_component(ic)
                if obj is not None:
                    built.append(obj)
            if not built:
                return None
            return disnake.ui.ActionRow(*built)

        if t == _DAPI_BUTTON:
            style     = Builder._button_style_from_dapi(comp.get("style", 2))
            label     = comp.get("label") or None
            btn_emoji = Builder._emoji_from_dapi(comp.get("emoji"))
            disabled  = bool(comp.get("disabled", False))
            url       = comp.get("url")
            custom_id = comp.get("custom_id")

            if style == disnake.ButtonStyle.url and url:
                return disnake.ui.Button(
                    label=label, style=style, url=url,
                    emoji=btn_emoji, disabled=disabled,
                )
            if custom_id:
                return disnake.ui.Button(
                    label=label, style=style,
                    custom_id=custom_id,
                    emoji=btn_emoji, disabled=disabled,
                )
            # Botão sem custom_id e sem url — desativado por segurança
            return disnake.ui.Button(
                label=label or "?", style=style,
                custom_id=f"imported_btn_{id(comp)}",
                emoji=btn_emoji, disabled=True,
            )

        if t == _DAPI_STRING_SELECT:
            options_data = comp.get("options") or []
            options = []
            for o in options_data:
                opt_emoji = Builder._emoji_from_dapi(o.get("emoji"))
                options.append(
                    disnake.SelectOption(
                        label=o.get("label") or "Opção",
                        value=o.get("value") or o.get("label") or "opt",
                        description=o.get("description") or None,
                        emoji=opt_emoji,
                        default=bool(o.get("default", False)),
                    )
                )
            if not options:
                return None
            min_v = max(1, min(len(options), int(comp.get("min_values") or 1)))
            max_v = max(min_v, min(len(options), int(comp.get("max_values") or 1)))
            return disnake.ui.StringSelect(
                placeholder=comp.get("placeholder") or "Selecione uma opção",
                custom_id=comp.get("custom_id") or f"imported_select_{id(comp)}",
                options=options,
                min_values=min_v,
                max_values=max_v,
                disabled=bool(comp.get("disabled", False)),
            )

        if t == _DAPI_CONTAINER:
            inner_comps = comp.get("components") or []
            built_inner: List[Any] = []
            for ic in inner_comps:
                obj = Builder._build_discord_component(ic)
                if obj is not None:
                    built_inner.append(obj)

            accent_color_raw = comp.get("accent_color")
            kwargs: Dict[str, Any] = {}
            if accent_color_raw is not None:
                kwargs["accent_colour"] = disnake.Colour(int(accent_color_raw))
            if comp.get("spoiler"):
                kwargs["spoiler"] = True

            if not built_inner:
                return None
            return disnake.ui.Container(*built_inner, **kwargs)

        # Tipo desconhecido — ignora silenciosamente
        return None

    @staticmethod
    def _is_discord_json(text: str) -> bool:
        """Verifica se o texto é um JSON da API do Discord (lista de componentes)."""
        try:
            data = json.loads(text)
            return isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "type" in data[0]
        except Exception:
            return False

    @staticmethod
    def _build_from_discord_json(raw_json: str) -> List[Any]:
        """
        Converte uma lista de componentes no formato JSON da API do Discord
        em objetos disnake prontos para envio.
        """
        try:
            components_data: List[Dict] = json.loads(raw_json)
        except Exception:
            return []

        result: List[Any] = []
        for comp in components_data:
            obj = Builder._build_discord_component(comp)
            if obj is not None:
                result.append(obj)
        return result

    @staticmethod
    def _order_component_rows(
        button_rows: List[disnake.ui.ActionRow],
        select_rows: List[disnake.ui.ActionRow],
        comp_order: List[str],
    ) -> List[disnake.ui.ActionRow]:
        ordered: List[disnake.ui.ActionRow] = []
        for comp_type in comp_order:
            if comp_type == "buttons":
                ordered.extend(button_rows)
            elif comp_type == "selects":
                ordered.extend(select_rows)
        for row in button_rows:
            if row not in ordered:
                ordered.append(row)
        for row in select_rows:
            if row not in ordered:
                ordered.append(row)
        return ordered

    # ─── Método principal (async) ─────────────────────────────────────────────

    @staticmethod
    async def build_from_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
        msg_cfg: Dict[str, Any] = cfg.get("message", {}) or {}

        send_mode         = msg_cfg.get("send_mode", "auto")
        comp_order        = msg_cfg.get("component_order", DEFAULT_ORDER)
        is_v2             = bool(cfg.get("is_v2_component"))
        container_raw     = Anunciar._safe_get(msg_cfg, "container")
        has_container     = container_raw is not None
        embed_obj         = Builder._build_embed(msg_cfg)
        has_embed         = embed_obj is not None
        content_text: Optional[str] = msg_cfg.get("content") or None
        button_rows       = Builder._build_buttons(msg_cfg)
        select_rows       = Builder._build_selects(msg_cfg)
        all_component_rows = Builder._order_component_rows(button_rows, select_rows, comp_order)
        external_url: Optional[str] = msg_cfg.get("externalImage") or None
        has_external_image = bool(external_url)
        audio_url: Optional[str]   = msg_cfg.get("audio") or None

        # ── Modo forçado: só texto ────────────────────────────────────────────
        if send_mode == "content":
            result: Dict[str, Any] = {
                "mode":       "embed",
                "content":    content_text,
                "embed":      None,
                "components": all_component_rows or None,
            }
            if external_url:
                file = await Builder._download_external_image(external_url)
                if file:
                    result["files"] = [file]
            return result

        # ── Modo forçado: embed ───────────────────────────────────────────────
        if send_mode == "embed":
            result = {
                "mode":       "embed",
                "content":    content_text,
                "embed":      embed_obj,
                "components": all_component_rows or None,
            }
            if external_url:
                file = await Builder._download_external_image(external_url)
                if file:
                    result["files"] = [file]
            return result

        # ── Modo forçado: container ───────────────────────────────────────────
        if send_mode == "container":
            is_v2 = True

        # ── Lógica automática ─────────────────────────────────────────────────
        if not is_v2 and not has_container and not content_text and not has_embed and has_external_image:
            is_v2 = True

        if is_v2 or has_container:
            components: List[Any] = []

            if external_url:
                components.append(
                    disnake.ui.MediaGallery(disnake.MediaGalleryItem(media=external_url))
                )
            if content_text:
                components.append(disnake.ui.TextDisplay(content_text))

            if has_container:
                # ── JSON do Discord (importado do site) ──────────────────────
                if Builder._is_discord_json(container_raw):
                    discord_comps = Builder._build_from_discord_json(container_raw)
                    components.extend(discord_comps)
                else:
                    # ── Formato de tokens legado ({{separator}}, {{color:...}}) ──
                    parsed_components, accent_color_value = Builder._parse_container(container_raw)
                    inner = parsed_components or [disnake.ui.TextDisplay(container_raw)]
                    container_kwargs: Dict[str, Any] = {}
                    if accent_color_value is not None:
                        container_kwargs["accent_colour"] = disnake.Colour(accent_color_value)
                    components.append(disnake.ui.Container(*inner, **container_kwargs))

            components.extend(all_component_rows)
            v2_result: Dict[str, Any] = {
                "mode":       "v2",
                "components": components,
                "flags":      disnake.MessageFlags(is_components_v2=True),
            }
            if audio_url:
                from .components.audio import download_audio
                audio_file = await download_audio(audio_url)
                if audio_file:
                    v2_result["files"] = [audio_file]
            return v2_result

        # ── Modo embed/padrão ─────────────────────────────────────────────────
        result = {
            "mode":       "embed",
            "content":    content_text,
            "embed":      embed_obj,
            "components": all_component_rows if all_component_rows else None,
        }

        if external_url:
            file = await Builder._download_external_image(external_url)
            if file is not None:
                result["files"] = [file]

        if audio_url:
            from .components.audio import download_audio
            audio_file = await download_audio(audio_url)
            if audio_file:
                result.setdefault("files", [])
                result["files"].append(audio_file)

        return result

    @staticmethod
    async def build() -> Dict[str, Any]:
        cfg = Builder._load_cfg()
        return await Builder.build_from_cfg(cfg)
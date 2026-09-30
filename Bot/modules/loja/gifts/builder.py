"""
Builder do painel de Gifts.

Reutiliza inteiramente o Builder do sistema de Anunciar
(commands/admin/anunciar/builder.py), pois a estrutura de dados
armazenada em `gifts_panel_message` é idêntica à de `messages_anunciar`.

Também expõe `build_redeem_button()` para adicionar o botão de resgate
configurado no final da mensagem.
"""
import re
from typing import Any, Dict, Optional

import disnake

from functions.database import database as db
from commands.admin.anunciar.builder import Builder  # reutiliza tudo daqui


def _build_redeem_button() -> disnake.ui.ActionRow:
    """Retorna a ActionRow com o botão de resgate do gift."""
    cfg = db.get_document("gifts_config") or {}
    btn_cfg = cfg.get("redeem_button") or {}
    label = btn_cfg.get("label") or "Resgatar Gift"
    emoji_raw = btn_cfg.get("emoji") or None

    parsed_emoji = None
    if emoji_raw:
        DISCORD_RE = re.compile(r"<a?:[a-zA-Z0-9_]{2,32}:\d{17,22}>")
        if DISCORD_RE.fullmatch(emoji_raw):
            try:
                parsed_emoji = disnake.PartialEmoji.from_str(emoji_raw)
            except Exception:
                parsed_emoji = None
        else:
            parsed_emoji = emoji_raw  # unicode

    btn_kwargs: Dict[str, Any] = {
        "label": label,
        "style": disnake.ButtonStyle.green,
        "custom_id": "Gift_Resgatar",
    }
    if parsed_emoji:
        btn_kwargs["emoji"] = parsed_emoji

    return disnake.ui.ActionRow(disnake.ui.Button(**btn_kwargs))


async def build_gift_panel_message(include_button: bool = True) -> Dict[str, Any]:
    """
    Monta a mensagem do painel de resgate de gifts.

    Lê a configuração de `gifts_panel_message` (mesmo schema que
    `messages_anunciar`) e delega a construção ao Builder do Anunciar.
    Opcionalmente injeta o botão de resgate no final.
    """
    cfg = db.get_document("gifts_panel_message") or {}

    # O Builder espera um dict com a chave "message"
    built = await Builder.build_from_cfg(cfg)

    if not include_button:
        return built

    redeem_row = _build_redeem_button()

    # Injetar o botão de resgate
    if built["mode"] == "v2":
        # Em V2 os componentes são uma lista livre — adiciona ao final
        built["components"] = list(built.get("components") or []) + [redeem_row]
    else:
        # Em embed/content o botão vai junto aos components normais
        existing = list(built.get("components") or [])
        existing.append(redeem_row)
        built["components"] = existing

    return built
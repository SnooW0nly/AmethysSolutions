"""
cog_keys.py — Gerenciamento completo de keys do sistema Joiner
"""
from __future__ import annotations

import io
import datetime
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message

from .helpers import (
    load_config, get_key_stats,
    create_keys, list_keys,
    revoke_key, delete_key, get_key,
)


def _accent() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


def _format_key_row(k: dict) -> str:
    active = k.get("active", True)
    icon = "✅" if active else "❌"
    uses = k.get("uses", 0)
    max_uses = k.get("max_uses", 1)
    exp = k.get("expires_at")
    exp_str = f" · exp <t:{exp}:R>" if exp else ""
    note = f" · `{k['note'][:20]}`" if k.get("note") else ""
    return f"{icon} `{k['key']}` — {uses}/{max_uses} usos{exp_str}{note}"


def build_keys_panel() -> dict:
    stats = get_key_stats()
    keys = list_keys()

    preview = keys[:10]
    if preview:
        lines = [_format_key_row(k) for k in preview]
        if len(keys) > 10:
            lines.append(f"-# ... e mais {len(keys) - 10} keys")
        body_keys = "\n".join(lines)
    else:
        body_keys = "-# Nenhuma key criada ainda."

    body = (
        f"{emoji.cardbox} **Total:** `{stats['total']}` · Ativas: `{stats['active']}` · Inativas: `{stats['inactive']}`\n"
        f"{emoji.double_check} **Total de entradas via key:** `{stats['total_joins']}`\n\n"
        f"**Últimas keys:**\n{body_keys}"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Keys", emoji=emoji.plus, style=disnake.ButtonStyle.green,
                              custom_id="JoinerKeys_Criar"),
            disnake.ui.Button(label="Exportar (.txt)", emoji=emoji.folder, style=disnake.ButtonStyle.blurple,
                              custom_id="JoinerKeys_Exportar"),
            disnake.ui.Button(label="Ver Todas", emoji=emoji.search, style=disnake.ButtonStyle.grey,
                              custom_id="JoinerKeys_VerTodas"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Revogar Key", emoji=emoji.wrong, style=disnake.ButtonStyle.grey,
                              custom_id="JoinerKeys_Revogar"),
            disnake.ui.Button(label="Deletar Key", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                              custom_id="JoinerKeys_Deletar"),
            disnake.ui.Button(label="Limpar Inativas", emoji=emoji.reload, style=disnake.ButtonStyle.grey,
                              custom_id="JoinerKeys_LimparInativas"),
        ),
    ]

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                                       f"-# Painel > Entrar em Servidor > **Gerenciar Keys**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id="Joiner_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


# ──────────────────────────────────────────────────────────
#  Modais
# ──────────────────────────────────────────────────────────

class ModalCriarKeys(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Keys",
            custom_id="JoinerKeys_CriarModal",
            components=[
                disnake.ui.TextInput(label="Quantidade de keys", custom_id="quantidade",
                                     placeholder="Ex: 10", required=True, max_length=4),
                disnake.ui.TextInput(label="Usos por key (padrão: 1)", custom_id="usos",
                                     placeholder="Ex: 1 (1 uso por key)", required=False, max_length=5),
                disnake.ui.TextInput(label="Validade em horas (0 = sem validade)", custom_id="validade",
                                     placeholder="Ex: 24 (expira em 24h)", required=False, max_length=6),
                disnake.ui.TextInput(label="Nota (opcional)", custom_id="nota",
                                     placeholder="Ex: Lote VIP Maio/25", required=False, max_length=100),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        try:
            qty = max(1, min(500, int(inter.text_values.get("quantidade", "1").strip())))
        except Exception:
            qty = 1
        try:
            uses = max(1, int(inter.text_values.get("usos", "1").strip() or "1"))
        except Exception:
            uses = 1
        try:
            hours = float(inter.text_values.get("validade", "0").strip() or "0")
            expires_at = int(datetime.datetime.now().timestamp() + hours * 3600) if hours > 0 else None
        except Exception:
            expires_at = None
        note = inter.text_values.get("nota", "").strip()

        keys = create_keys(
            quantity=qty,
            uses_per_key=uses,
            expires_at=expires_at,
            note=note,
            created_by_id=inter.user.id,
            created_by_name=inter.user.display_name,
        )

        panel = build_keys_panel()
        flags = panel.pop("flags", None)
        await inter.edit_original_message(**panel, flags=flags)

        keys_text = "\n".join(keys)
        buf = io.BytesIO(keys_text.encode("utf-8"))
        exp_str = f"Expiram em {hours}h" if expires_at else "Sem validade"
        await inter.followup.send(
            f"{emoji.correct} **{len(keys)} keys criadas!**\n"
            f"-# Usos: `{uses}` · {exp_str}{' · ' + note if note else ''}\n\n"
            f"Keys enviadas no arquivo abaixo:",
            file=disnake.File(buf, filename=f"keys_{len(keys)}.txt"),
            ephemeral=True,
        )


class ModalRevogarKey(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Revogar Key",
            custom_id="JoinerKeys_RevogarModal",
            components=[
                disnake.ui.TextInput(label="Key a revogar", custom_id="key",
                                     placeholder="Cole a key completa aqui", required=True, max_length=50),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        key = inter.text_values.get("key", "").strip().upper()
        ok = revoke_key(key)
        panel = build_keys_panel()
        flags = panel.pop("flags", None)
        await message.wait(inter, send=False)
        await inter.edit_original_message(**panel, flags=flags)
        result = f"{emoji.correct} Key `{key}` revogada!" if ok else f"{emoji.wrong} Key não encontrada."
        await inter.followup.send(result, ephemeral=True)


class ModalDeletarKey(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Deletar Key",
            custom_id="JoinerKeys_DeletarModal",
            components=[
                disnake.ui.TextInput(label="Key a deletar", custom_id="key",
                                     placeholder="Cole a key completa aqui", required=True, max_length=50),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        key = inter.text_values.get("key", "").strip().upper()
        ok = delete_key(key)
        panel = build_keys_panel()
        flags = panel.pop("flags", None)
        await message.wait(inter, send=False)
        await inter.edit_original_message(**panel, flags=flags)
        result = f"{emoji.correct} Key `{key}` deletada!" if ok else f"{emoji.wrong} Key não encontrada."
        await inter.followup.send(result, ephemeral=True)


# ──────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────

class JoinerKeysCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _reply(self, inter: disnake.MessageInteraction, panel: dict):
        flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
        if inter.response.is_done():
            await inter.edit_original_message(**panel, flags=flags)
        else:
            await message.wait(inter, send=False)
            await inter.edit_original_message(**panel, flags=flags)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        if cid == "Joiner_PainelKeys":
            await self._reply(inter, build_keys_panel())

        elif cid == "JoinerKeys_Criar":
            await inter.response.send_modal(ModalCriarKeys())

        elif cid == "JoinerKeys_Revogar":
            await inter.response.send_modal(ModalRevogarKey())

        elif cid == "JoinerKeys_Deletar":
            await inter.response.send_modal(ModalDeletarKey())

        elif cid == "JoinerKeys_LimparInativas":
            from .helpers import DB_KEYS_KEY, _load_keys, _save_keys
            data = _load_keys()
            before = len(data["keys"])
            data["keys"] = {k: v for k, v in data["keys"].items() if v.get("active", True)}
            after = len(data["keys"])
            _save_keys(data)
            removed = before - after
            await self._reply(inter, build_keys_panel())
            await inter.followup.send(
                f"{emoji.correct} `{removed}` keys inativas removidas.", ephemeral=True)

        elif cid == "JoinerKeys_Exportar":
            keys = list_keys()
            if not keys:
                await inter.response.send_message(f"{emoji.wrong} Nenhuma key criada.", ephemeral=True)
                return
            lines = []
            for k in keys:
                active = "ATIVA" if k.get("active", True) else "INATIVA"
                exp = datetime.datetime.fromtimestamp(k["expires_at"]).strftime("%d/%m/%Y %H:%M") if k.get("expires_at") else "Sem validade"
                lines.append(f"{k['key']} | {active} | {k['uses']}/{k['max_uses']} usos | Expira: {exp} | {k.get('note', '')}")
            content = "\n".join(lines)
            buf = io.BytesIO(content.encode("utf-8"))
            await inter.response.send_message(
                f"{emoji.correct} **{len(keys)} keys exportadas:**",
                file=disnake.File(buf, filename=f"joiner_keys_{len(keys)}.txt"),
                ephemeral=True,
            )

        elif cid == "JoinerKeys_VerTodas":
            keys = list_keys()
            if not keys:
                await inter.response.send_message(f"{emoji.wrong} Nenhuma key criada.", ephemeral=True)
                return
            lines = [_format_key_row(k) for k in keys]
            chunk_size = 20
            chunks = [lines[i:i+chunk_size] for i in range(0, len(lines), chunk_size)]
            first = True
            for chunk in chunks[:3]:
                text = "\n".join(chunk)
                if first:
                    await inter.response.send_message(
                        f"**Keys ({len(keys)} total):**\n{text}", ephemeral=True)
                    first = False
                else:
                    await inter.followup.send(text, ephemeral=True)

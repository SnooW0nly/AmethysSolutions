"""
modules/customization/edit_emojis.py
─────────────────────────────────────────────────────────────────────────────
Editor de Emojis do painel de personalização.

Fluxo:
  Painel  →  [Editar Emojis]  →  EmojiListPanel (paginado, SelectMenu)
         →  EmojiEditModal  (emoji string OU upload de imagem)
         →  aplica no Discord + atualiza emojis.json
         →  [Resetar Padrão]  →  relê assets/ e recria todos no Discord
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import aiohttp

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji, reload_emoji_class

# ── caminhos ──────────────────────────────────────────────────────────────
EMOJIS_JSON   = "database/emojis/emojis.json"
ASSETS_PATH   = "database/emojis/assets"

# quantos emojis por página do SelectMenu (máx 25 opções)
PAGE_SIZE = 23   # 23 emojis + "◀ Anterior" + "▶ Próxima" quando necessário

# emojis protegidos: não aparecem na lista e não podem ser editados/resetados
LOCKED_EMOJIS: frozenset[str] = frozenset({
    "amethys",
    "entrega0", "entrega1", "entrega2", "entrega3",
    "entrega4", "entrega5", "entrega6",
    "a1", "b2", "c3", "d4", "e5",
})

# ── helpers ────────────────────────────────────────────────────────────────

def _load_emojis_json() -> dict:
    with open(EMOJIS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_emojis_json(data: dict) -> None:
    with open(EMOJIS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def _get_token_and_app() -> tuple[str, str]:
    cfg = db.obter("config.json")
    return cfg["bot"]["token"], cfg["bot"]["id"]

def _parse_emoji_tag(tag: str) -> tuple[str | None, str | None, bool]:
    """Retorna (name, id, animated) de uma tag <:name:id> ou <a:name:id>."""
    m = re.fullmatch(r"<(a?):(\w+):(\d+)>", tag.strip())
    if not m:
        return None, None, False
    return m.group(2), m.group(3), m.group(1) == "a"

async def _delete_emoji_from_discord(emoji_id: str) -> None:
    token, app_id = _get_token_and_app()
    url = f"https://discord.com/api/v10/applications/{app_id}/emojis/{emoji_id}"
    headers = {"Authorization": f"Bot {token}"}
    async with aiohttp.ClientSession() as s:
        async with s.delete(url, headers=headers) as r:
            if r.status not in (204, 404):
                text = await r.text()
                print(f"[EditEmojis] Erro ao deletar emoji {emoji_id}: {r.status} – {text}")

async def _upload_emoji_bytes(name: str, image_bytes: bytes, ext: str) -> str:
    """Faz upload de bytes de imagem como emoji de aplicação. Retorna o ID."""
    token, app_id = _get_token_and_app()
    tipo = "gif" if ext == "gif" else "png"
    b64   = base64.b64encode(image_bytes).decode()
    payload = {"name": name, "image": f"data:image/{tipo};base64,{b64}"}
    url     = f"https://discord.com/api/v10/applications/{app_id}/emojis"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, headers=headers, json=payload) as r:
            if r.status == 201:
                data = await r.json()
                return data["id"]
            text = await r.text()
            raise RuntimeError(f"Upload falhou ({r.status}): {text}")

async def _replace_emoji(name: str, new_tag: str | None,
                         image_bytes: bytes | None, ext: str = "png") -> str:
    """
    Substitui um emoji no Discord e no emojis.json.
    - new_tag: tag completa  <:name:id>  (tem prioridade)
    - image_bytes: bytes da nova imagem (se new_tag for None)
    Retorna a nova tag gravada.
    """
    db_data = _load_emojis_json()
    old_tag = db_data.get(name, "")

    # remove o emoji antigo do Discord
    _, old_id, _ = _parse_emoji_tag(old_tag)
    if old_id:
        await _delete_emoji_from_discord(old_id)

    if new_tag:
        final_tag = new_tag.strip()
    else:
        # faz upload da imagem e monta a tag
        new_id  = await _upload_emoji_bytes(name, image_bytes, ext)
        prefix  = "a" if ext == "gif" else ""
        sep     = "a:" if ext == "gif" else ":"
        final_tag = f"<{sep}{name}:{new_id}>" if ext == "gif" else f"<:{name}:{new_id}>"

    db_data[name] = final_tag
    _save_emojis_json(db_data)
    reload_emoji_class()
    return final_tag


async def _reset_single_from_asset(name: str) -> str | None:
    """
    Recria um emoji a partir do arquivo em assets/.
    Retorna a nova tag ou None se o asset não existir.
    """
    gif_path = os.path.join(ASSETS_PATH, f"{name}.gif")
    png_path = os.path.join(ASSETS_PATH, f"{name}.png")
    path = gif_path if os.path.isfile(gif_path) else (png_path if os.path.isfile(png_path) else None)
    if not path:
        return None

    ext = "gif" if path.endswith(".gif") else "png"
    with open(path, "rb") as f:
        image_bytes = f.read()

    db_data = _load_emojis_json()
    old_tag = db_data.get(name, "")
    _, old_id, _ = _parse_emoji_tag(old_tag)
    if old_id:
        await _delete_emoji_from_discord(old_id)

    new_id  = await _upload_emoji_bytes(name, image_bytes, ext)
    new_tag = f"<a:{name}:{new_id}>" if ext == "gif" else f"<:{name}:{new_id}>"
    db_data[name] = new_tag
    _save_emojis_json(db_data)
    return new_tag


# ══════════════════════════════════════════════════════════════════════════
#  Modal de edição de um emoji
# ══════════════════════════════════════════════════════════════════════════

class EmojiEditModal(disnake.ui.Modal):
    """
    Modal com dois campos:
      • Tag do emoji  →  <:nome:id>
      • Upload de Imagem PNG/GIF  →  campo de upload de arquivo
    """

    def __init__(self, emoji_name: str, current_tag: str, page: int):
        self.emoji_name  = emoji_name
        self.current_tag = current_tag
        self.page        = page

        components = [
            disnake.ui.Label(
                f"Emoji: {emoji_name}",
                component=disnake.ui.TextInput(
                    custom_id="emoji_tag",
                    placeholder='Cole a tag  <:nome:id>  ou  <a:nome:id>',
                    value=current_tag,
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=100,
                )
            ),
            disnake.ui.Label(
                "Upload de Imagem (PNG/GIF)",
                description="Envie uma imagem para substituir o emoji (deixe vazio se usar a tag acima)",
                component=disnake.ui.FileUpload(
                    custom_id="emoji_upload"
                )
            ),
        ]
        super().__init__(title=f"Editar Emoji  ·  {emoji_name}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        tag_input = inter.text_values.get("emoji_tag", "").strip()
        
        # Obtém os arquivos enviados
        uploaded_files = inter.data.get("attachments", [])

        # Validação: pelo menos um dos campos deve estar preenchido
        if not tag_input and not uploaded_files:
            await inter.edit_original_message(
                content=f"{emoji.wrong} Preencha a tag **ou** envie uma imagem."
            )
            return

        try:
            if tag_input and tag_input != self.current_tag:
                # Usuário colou uma tag
                n, eid, _ = _parse_emoji_tag(tag_input)
                if not eid:
                    await inter.edit_original_message(
                        content=f"{emoji.wrong} Tag inválida. Use o formato `<:nome:id>` ou `<a:nome:id>`."
                    )
                    return
                new_tag = await _replace_emoji(self.emoji_name, tag_input, None)

            elif uploaded_files:
                # Usuário enviou um arquivo
                file_data = uploaded_files[0]
                file_url = file_data.get("url")
                filename = file_data.get("filename", "").lower()
                
                # Valida extensão do arquivo
                if not (filename.endswith(".png") or filename.endswith(".gif")):
                    await inter.edit_original_message(
                        content=f"{emoji.wrong} Formato inválido. Envie apenas arquivos PNG ou GIF."
                    )
                    return
                
                # Baixa o arquivo
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_url) as resp:
                        if resp.status != 200:
                            await inter.edit_original_message(
                                content=f"{emoji.wrong} Não foi possível baixar a imagem (HTTP {resp.status})."
                            )
                            return
                        image_bytes = await resp.read()
                
                ext = "gif" if filename.endswith(".gif") else "png"
                new_tag = await _replace_emoji(self.emoji_name, None, image_bytes, ext)

            else:
                # Nada mudou
                await inter.edit_original_message(content=f"{emoji.correct} Nenhuma alteração detectada.")
                return

            await inter.edit_original_message(
                content=f"{emoji.correct} Emoji **{self.emoji_name}** atualizado para {new_tag} com sucesso!"
            )

        except Exception as e:
            await inter.edit_original_message(
                content=f"{emoji.wrong} Erro ao atualizar emoji: `{e}`"
            )


# ══════════════════════════════════════════════════════════════════════════
#  Painel de listagem de emojis (paginado)
# ══════════════════════════════════════════════════════════════════════════

class EditEmojisCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── builders estáticos ─────────────────────────────────────────────

    @staticmethod
    def _emoji_pages() -> list[list[tuple[str, str]]]:
        """Divide o dict de emojis em páginas de PAGE_SIZE itens."""
        data  = _load_emojis_json()
        items = [(n, t) for n, t in data.items() if n not in LOCKED_EMOJIS]
        pages = []
        for i in range(0, len(items), PAGE_SIZE):
            pages.append(items[i : i + PAGE_SIZE])
        return pages

    @staticmethod
    def _build_select(pages: list, page: int) -> disnake.ui.StringSelect:
        options = []
        for name, tag in pages[page]:
            # label e description
            label = name.replace("_", " ").title()
            desc  = tag if tag else "Sem tag definida"
            # tenta usar o próprio emoji como emoji da opção
            em_obj = None
            if tag:
                m = re.fullmatch(r"<(a?):(\w+):(\d+)>", tag.strip())
                if m:
                    try:
                        em_obj = disnake.PartialEmoji(
                            name=m.group(2),
                            id=int(m.group(3)),
                            animated=m.group(1) == "a",
                        )
                    except Exception:
                        em_obj = None
            options.append(
                disnake.SelectOption(
                    label=label[:100],
                    value=name,
                    description=desc[:100],
                    emoji=em_obj,
                )
            )
        return disnake.ui.StringSelect(
            custom_id="EditEmojis_Select",
            placeholder="Selecione um emoji para editar",
            options=options,
        )

    @staticmethod
    def _build_pagination_row(pages: list, page: int) -> disnake.ui.ActionRow:
        total = len(pages)
        prev_btn = disnake.ui.Button(
            label="◀ Anterior",
            style=disnake.ButtonStyle.grey,
            custom_id=f"EditEmojis_Page_{page - 1}",
            disabled=page == 0,
        )
        page_btn = disnake.ui.Button(
            label=f"Página {page + 1} / {total}",
            style=disnake.ButtonStyle.grey,
            custom_id="EditEmojis_PageInfo",
            disabled=True,
        )
        next_btn = disnake.ui.Button(
            label="Próxima ▶",
            style=disnake.ButtonStyle.grey,
            custom_id=f"EditEmojis_Page_{page + 1}",
            disabled=page >= total - 1,
        )
        return disnake.ui.ActionRow(prev_btn, page_btn, next_btn)

    # ── components V2 ─────────────────────────────────────────────────

    @staticmethod
    def get_panel_components(page: int = 0) -> list:
        pages = EditEmojisCog._emoji_pages()
        if not pages:
            return [disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Personalização > **Emojis**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Nenhum emoji encontrado no banco de dados."),
            )]

        page = max(0, min(page, len(pages) - 1))

        colors          = db.get_document("custom_colors")
        primary_hex     = colors.get("primary") or "#5c5ef0"
        primary_color   = int(primary_hex.replace("#", ""), 16)

        total_emojis    = sum(len(p) for p in pages)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Personalização > **Emojis**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"Gerencie os **{total_emojis} emojis** utilizados pelo bot.\n"
                    f"Selecione um emoji abaixo para substituí-lo por uma tag personalizada ou uma imagem."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(EditEmojisCog._build_select(pages, page)),
                EditEmojisCog._build_pagination_row(pages, page),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Resetar Padrão",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.reload,
                        custom_id="EditEmojis_Reset",
                    ),
                    disnake.ui.Button(
                        label="Colorido (Em breve)",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.wand,
                        custom_id="EditEmojis_Colorido",
                        disabled=True,
                    ),
                ),
                accent_colour=disnake.Colour(primary_color),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Painel_Personalizacao",
                ),
            ),
        ]

    # ── embed V1 ──────────────────────────────────────────────────────

    @staticmethod
    def get_panel_embed(page: int = 0):
        pages = EditEmojisCog._emoji_pages()
        page  = max(0, min(page, len(pages) - 1)) if pages else 0

        colors        = db.get_document("custom_colors")
        primary_hex   = colors.get("primary") or "#5c5ef0"
        primary_color = int(primary_hex.replace("#", ""), 16)
        total_emojis  = sum(len(p) for p in pages) if pages else 0

        embed = disnake.Embed(
            title="Editor de Emojis",
            description=(
                f"Gerencie os **{total_emojis} emojis** utilizados pelo bot.\n"
                "Selecione um emoji abaixo para substituí-lo por uma tag personalizada ou imagem."
            ),
            color=primary_color,
        )

        components: list = []
        if pages:
            components.append(disnake.ui.ActionRow(EditEmojisCog._build_select(pages, page)))
            components.append(EditEmojisCog._build_pagination_row(pages, page))

        components += [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Resetar Padrão",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.reload,
                    custom_id="EditEmojis_Reset",
                ),
                disnake.ui.Button(
                    label="Colorido (Em breve)",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.wand,
                    custom_id="EditEmojis_Colorido",
                    disabled=True,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Painel_Personalizacao",
                ),
            ),
        ]
        return embed, components

    # ── listeners ─────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── paginação ──────────────────────────────────────────────────
        if cid.startswith("EditEmojis_Page_"):
            await inter.response.defer()
            try:
                page = int(cid.split("_")[-1])
            except ValueError:
                return
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, comps = self.get_panel_embed(page)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=self.get_panel_components(page))

        # ── resetar padrão ─────────────────────────────────────────────
        elif cid == "EditEmojis_Reset":
            await inter.response.defer(ephemeral=True)
            await inter.edit_original_response(
                content=(
                    f"{emoji.loading} **Resetando emojis…**\n"
                    "-# Isso pode levar alguns segundos. Aguarde."
                )
            )
            db_data = _load_emojis_json()
            success = 0
            failed  = 0
            for name in list(db_data.keys()):
                if name in LOCKED_EMOJIS:
                    continue   # protegido: nunca sobrescrever
                try:
                    result = await _reset_single_from_asset(name)
                    if result:
                        success += 1
                    else:
                        failed += 1
                    await asyncio.sleep(0.4)   # respeitar rate limit
                except Exception as e:
                    print(f"[EditEmojis] Reset falhou para '{name}': {e}")
                    failed += 1

            reload_emoji_class()
            await inter.edit_original_response(
                content=(
                    f"{emoji.correct} **Reset concluído!**\n"
                    f"-# {success} emojis restaurados · {failed} falharam"
                )
            )

        # ── abre o painel de emojis (vindo de Personalização) ──────────
        elif cid == "Painel_EditarEmojis":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, comps = self.get_panel_embed(0)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=self.get_panel_components(0))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "EditEmojis_Select":
            return

        emoji_name = inter.values[0]

        # bloqueia emojis protegidos
        if emoji_name in LOCKED_EMOJIS:
            await inter.response.send_message(
                content=f"{emoji.forbidden} O emoji **{emoji_name}** é protegido e não pode ser editado.",
                ephemeral=True,
            )
            return

        db_data    = _load_emojis_json()
        current    = db_data.get(emoji_name, "")

        # detecta a página atual pelo botão de info (disabled) no ActionRow
        page = 0
        for row in inter.message.components:
            for comp in (row.children if hasattr(row, "children") else []):
                cid = getattr(comp, "custom_id", "") or ""
                if cid.startswith("EditEmojis_Page_"):
                    # o botão "Próxima" aponta para page+1
                    try:
                        candidate = int(cid.split("_")[-1]) - 1
                        if candidate >= 0:
                            page = candidate
                    except ValueError:
                        pass

        await inter.response.send_modal(EmojiEditModal(emoji_name, current, page))
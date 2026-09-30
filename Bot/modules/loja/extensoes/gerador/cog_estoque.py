"""
cog_estoque.py — Gerenciamento de estoque dos serviços do Gerador
"""
from __future__ import annotations

import io
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from .helpers import (
    get_service, get_stock_count, add_stock_items,
    clear_stock, get_all_stock_items,
)
from .cog_servicos import build_service_detail


def _accent() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


def _embed_color() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"color": int(hex_.replace("#", ""), 16)}
    return {}


def _mode() -> str:
    return db.get_document("custom_mode").get("mode")


def build_stock_panel(mode: str, service_id: str) -> dict:
    svc = get_service(service_id)
    if not svc:
        from .cog_servicos import build_services_panel
        return build_services_panel(mode)

    fake = svc.get("stock_fake", {})
    fake_enabled = fake.get("enabled", False)
    stock_count = get_stock_count(service_id)
    stock_label = "♾ FAKE (infinito)" if fake_enabled else str(stock_count)

    body = (
        f"{emoji.cardbox} **Itens em estoque:** `{stock_label}`\n"
        f"{emoji.infinity} **Stock Fake:** `{'ATIVO' if fake_enabled else 'Desativado'}`\n\n"
        f"-# Stock fake = bot entrega uma mensagem fictícia mesmo sem estoque real.\n"
        f"-# Útil para serviços que você entrega manualmente depois."
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar Itens", emoji=emoji.plus, style=disnake.ButtonStyle.green,
                              custom_id=f"Gerador_Stock_Adicionar:{service_id}"),
            disnake.ui.Button(label="Upload .txt", emoji=emoji.folder, style=disnake.ButtonStyle.blurple,
                              custom_id=f"Gerador_Stock_Upload:{service_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Ver Estoque", emoji=emoji.search, style=disnake.ButtonStyle.grey,
                              custom_id=f"Gerador_Stock_Ver:{service_id}"),
            disnake.ui.Button(label="Limpar Tudo", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                              custom_id=f"Gerador_Stock_Limpar:{service_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Stock Fake: ATIVO" if fake_enabled else "Stock Fake: OFF",
                emoji=emoji.infinity,
                style=disnake.ButtonStyle.green if fake_enabled else disnake.ButtonStyle.grey,
                custom_id=f"Gerador_Stock_ToggleFake:{service_id}",
            ),
            disnake.ui.Button(label="Editar msg fake", emoji=emoji.edit, style=disnake.ButtonStyle.grey,
                              custom_id=f"Gerador_Stock_EditFakeMsg:{service_id}"),
        ),
    ]

    if mode == "embed":
        embed = disnake.Embed(
            title=f"Estoque: {svc['nome']}",
            description=f"-# Painel > Gerador > {svc['nome']} > **Estoque**\n\n{body}",
            **_embed_color(),
        )
        return {"embed": embed, "components": rows + [disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                              custom_id=f"Gerador_Servico_Detalhe:{service_id}")
        )]}

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerador > {svc['nome']} > **Estoque**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id=f"Gerador_Servico_Detalhe:{service_id}")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


class AdicionarEstoqueModal(disnake.ui.Modal):
    def __init__(self, service_id: str):
        self.service_id = service_id
        super().__init__(
            title="Adicionar Estoque",
            custom_id=f"Gerador_Stock_AdicionarModal:{service_id}",
            components=[
                disnake.ui.TextInput(
                    label="Itens (um por linha, máx. 100 por vez)",
                    custom_id="items",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    max_length=4000,
                    placeholder="item1\nitem2\nitem3...",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        raw = inter.text_values["items"]
        items = [l.strip() for l in raw.split("\n") if l.strip()][:1000]
        if not items:
            await inter.response.send_message(f"{emoji.wrong} Nenhum item válido.", ephemeral=True)
            return
        total = add_stock_items(self.service_id, items)
        mode = _mode()
        panel = build_stock_panel(mode, self.service_id)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)
        await inter.followup.send(f"{emoji.correct} `{len(items)}` itens adicionados. Total: `{total}`", ephemeral=True)


class EditFakeMsgModal(disnake.ui.Modal):
    def __init__(self, service_id: str):
        self.service_id = service_id
        svc = get_service(service_id) or {}
        current = svc.get("stock_fake", {}).get("mensagem_fake") or ""
        super().__init__(
            title="Mensagem do Stock Fake",
            custom_id=f"Gerador_Stock_EditFakeMsgModal:{service_id}",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem (use {user}, {servico})",
                    custom_id="msg",
                    style=disnake.TextInputStyle.paragraph,
                    value=current,
                    required=True, max_length=1000,
                    placeholder="✅ {user}, aqui está o acesso ao {servico}!\n\n`login:senha`",
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        msg = inter.text_values["msg"]
        from .helpers import update_service
        svc = get_service(self.service_id) or {}
        fake = svc.get("stock_fake", {})
        fake["mensagem_fake"] = msg
        update_service(self.service_id, {"stock_fake": fake})
        mode = _mode()
        panel = build_stock_panel(mode, self.service_id)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            await inter.edit_original_message(content=None, **panel)
        else:
            await message.wait(inter, send=False)
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)


class GeradorEstoqueCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending_uploads: dict[int, str] = {}  # user_id -> service_id

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""
        mode = _mode()

        if cid.startswith("Gerador_Servico_Estoque:"):
            sid = cid.split(":", 1)[1]
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = build_stock_panel(mode, sid)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid.startswith("Gerador_Stock_Adicionar:"):
            sid = cid.split(":", 1)[1]
            await inter.response.send_modal(AdicionarEstoqueModal(sid))

        elif cid.startswith("Gerador_Stock_EditFakeMsg:"):
            sid = cid.split(":", 1)[1]
            await inter.response.send_modal(EditFakeMsgModal(sid))

        elif cid.startswith("Gerador_Stock_ToggleFake:"):
            sid = cid.split(":", 1)[1]
            svc = get_service(sid) or {}
            fake = svc.get("stock_fake", {})
            fake["enabled"] = not fake.get("enabled", False)
            from .helpers import update_service
            update_service(sid, {"stock_fake": fake})
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = build_stock_panel(mode, sid)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid.startswith("Gerador_Stock_Limpar:"):
            sid = cid.split(":", 1)[1]
            clear_stock(sid)
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = build_stock_panel(mode, sid)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", None)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid.startswith("Gerador_Stock_Ver:"):
            sid = cid.split(":", 1)[1]
            svc = get_service(sid)
            items = get_all_stock_items(sid)
            if not items:
                await inter.response.send_message(f"{emoji.warn} Nenhum item no estoque.", ephemeral=True)
                return
            content = f"=== ESTOQUE: {svc['nome']} ({len(items)} itens) ===\n\n"
            content += "\n".join(items)
            buf = io.BytesIO(content.encode("utf-8"))
            await inter.response.send_message(
                f"{emoji.correct} {len(items)} itens em estoque:",
                file=disnake.File(buf, filename=f"estoque_{svc['nome']}.txt"),
                ephemeral=True,
            )

        elif cid.startswith("Gerador_Stock_Upload:"):
            sid = cid.split(":", 1)[1]
            svc = get_service(sid)
            self._pending_uploads[inter.user.id] = sid
            try:
                dm = await inter.user.create_dm()
                colors = db.get_document("custom_colors") or {}
                hex_ = colors.get("primary")
                if mode == "embed":
                    e = disnake.Embed(
                        description=(
                            f"**Upload de Estoque — {svc['nome']}**\n\n"
                            "Envie um arquivo **.txt** com os itens, um por linha.\n"
                            f"{emoji.warn} Você tem 5 minutos para enviar."
                        ),
                    )
                    if hex_:
                        e.color = int(hex_.replace("#", ""), 16)
                    await dm.send(embed=e)
                else:
                    kw = {}
                    if hex_:
                        kw["accent_colour"] = disnake.Colour(int(hex_.replace("#", ""), 16))
                    await dm.send(
                        components=[
                            disnake.ui.Container(
                                disnake.ui.TextDisplay(
                                    f"## {emoji.folder} Upload de Estoque\n"
                                    f"-# Serviço: **{svc['nome']}**\n\n"
                                    f"Envie um arquivo **.txt** com os itens, um por linha.\n"
                                    f"{emoji.warn} Você tem 5 minutos para enviar."
                                ),
                                **kw,
                            )
                        ],
                        flags=disnake.MessageFlags(is_components_v2=True),
                    )
                await inter.response.send_message(f"{emoji.correct} Verifique sua DM!", ephemeral=True)
            except disnake.Forbidden:
                await inter.response.send_message(f"{emoji.wrong} Não foi possível abrir DM.", ephemeral=True)
                self._pending_uploads.pop(inter.user.id, None)

    @commands.Cog.listener("on_message")
    async def on_dm_upload(self, msg: disnake.Message):
        if msg.author.bot:
            return
        if not isinstance(msg.channel, disnake.DMChannel):
            return
        if msg.author.id not in self._pending_uploads:
            return

        service_id = self._pending_uploads.get(msg.author.id)
        if not msg.attachments:
            await msg.channel.send(f"{emoji.warn} Envie um arquivo **.txt**.")
            return

        txt = next((a for a in msg.attachments if a.filename.lower().endswith(".txt")), None)
        if not txt:
            await msg.channel.send(f"{emoji.wrong} Apenas arquivos **.txt** são aceitos.")
            return

        try:
            content = (await txt.read()).decode("utf-8")
            items = [l.strip() for l in content.split("\n") if l.strip()][:10000]
            if not items:
                await msg.channel.send(f"{emoji.wrong} Arquivo vazio.")
                return
            total = add_stock_items(service_id, items)
            svc = get_service(service_id)
            self._pending_uploads.pop(msg.author.id, None)
            await msg.channel.send(
                f"{emoji.correct} **{len(items)} itens** adicionados ao estoque de **{svc['nome'] if svc else service_id}**!\n"
                f"-# Total atual: `{total}`"
            )
        except Exception as e:
            await msg.channel.send(f"{emoji.wrong} Erro: {e}")

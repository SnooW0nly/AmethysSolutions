"""
modules/utilitarios/comunidade/verificacao/commands/codigos.py

Slash command /codigos — gerenciador de códigos de verificação.
Disponível apenas para quem tem cargo de responsável.
Máximo 5 códigos por usuário.
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji

from ..helpers import (
    carregar_config, color, accent, _mode,
    load_json, save_json, gerar_codigo_aleatorio,
    CODIGOS_JSON, MAX_CODIGOS_POR_USER,
    get_codigos_usuario, salvar_codigos_usuario,
)


def _verificar_responsavel(inter: disnake.ApplicationCommandInteraction) -> bool:
    config       = carregar_config()
    responsaveis = config.get("cargo_responsavel", [])
    if not responsaveis:
        return False
    roles = [str(r.id) for r in getattr(inter.author, "roles", [])]
    return any(r in roles for r in responsaveis)


def _painel_codigos(user_id: int, primary_hex: str | None, mode: str) -> list | tuple:
    codigos = get_codigos_usuario(user_id)
    total   = len(codigos)

    if codigos:
        linhas = []
        for i, c in enumerate(codigos, 1):
            usos    = c.get("usos", 0)
            max_u   = c.get("max_usos")
            uso_txt = f"{usos}/{max_u}" if max_u is not None else f"{usos}/∞"
            linhas.append(
                f"`{i}.` **{c.get('nome', '?')}** — Código: `{c.get('codigo', '?')}` — Usos: `{uso_txt}`"
            )
        lista_txt = "\n".join(linhas)
    else:
        lista_txt = "*Nenhum código criado ainda.*"

    row_acoes = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Criar código",
            emoji=emoji.plus,
            style=disnake.ButtonStyle.green,
            custom_id="Codigos_Criar",
            disabled=(total >= MAX_CODIGOS_POR_USER),
        ),
        disnake.ui.Button(
            label="Apagar código",
            emoji=emoji.minus,
            style=disnake.ButtonStyle.red,
            custom_id="Codigos_ApagarSelecionar",
            disabled=not bool(codigos),
        ),
        disnake.ui.Button(
            label="Resetar usos",
            emoji=emoji.edit,
            style=disnake.ButtonStyle.blurple,
            custom_id="Codigos_ResetarUsos",
            disabled=not bool(codigos),
        ),
    )

    slots_txt = f"`{total}/{MAX_CODIGOS_POR_USER}` slots usados"

    if mode == "embed":
        emb = disnake.Embed(
            title="Meus Códigos de Verificação",
            description=f"{lista_txt}\n\n{slots_txt}",
        )
        if primary_hex:
            emb.color = color(primary_hex)
        return emb, [row_acoes]
    else:
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.commands} Meus Códigos\n"
                    f"-# {slots_txt}\n\n"
                    f"{lista_txt}"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                row_acoes,
                **accent(primary_hex),
            )
        ]


class CodigosCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="codigos", description="Gerencie seus códigos de verificação.")
    async def codigos(self, inter: disnake.ApplicationCommandInteraction):
        if not _verificar_responsavel(inter):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem o cargo responsável para usar este comando.",
                ephemeral=True,
            )
            return

        mode        = _mode()
        primary_hex = db.get_document("custom_colors").get("primary")
        result      = _painel_codigos(inter.author.id, primary_hex, mode)

        if mode == "embed":
            emb, comps = result
            await inter.response.send_message(embed=emb, components=comps, ephemeral=True)
        else:
            await inter.response.send_message(
                components=result,
                ephemeral=True,
                flags=disnake.MessageFlags(is_components_v2=True),
            )

    # ── Listener de botões do painel de códigos ───────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _btn_codigos(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Codigos_"):
            return

        if not _verificar_responsavel(inter):
            await inter.response.send_message("Sem permissão.", ephemeral=True)
            return

        if cid == "Codigos_Criar":
            await inter.response.send_modal(CriarCodigoModal(self.bot))
            return

        mode        = _mode()
        primary_hex = db.get_document("custom_colors").get("primary")

        from functions.message import message, embed_message
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "Codigos_ApagarSelecionar":
            codigos = get_codigos_usuario(inter.author.id)
            if not codigos:
                await inter.edit_original_message(content="Nenhum código para apagar.", components=[])
                return
            options = [
                disnake.SelectOption(
                    label=f"{c.get('nome', '?')} ({c.get('codigo', '?')})",
                    value=str(i),
                    description=f"Usos: {c.get('usos', 0)}"
                )
                for i, c in enumerate(codigos)
            ]
            select_row = disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Selecione o código para apagar...",
                    custom_id="Codigos_ConfirmarApagar",
                    options=options,
                )
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Codigos_Voltar"),
            )
            if mode == "embed":
                emb = disnake.Embed(title="Apagar Código", description="Selecione qual código deseja apagar.")
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay("# Apagar Código\nSelecione qual código deseja remover."),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row,
                        **accent(primary_hex),
                    ),
                    voltar,
                ])
            return

        if cid == "Codigos_ResetarUsos":
            codigos = get_codigos_usuario(inter.author.id)
            options = [
                disnake.SelectOption(
                    label=f"{c.get('nome', '?')} ({c.get('codigo', '?')})",
                    value=str(i),
                    description=f"Usos atuais: {c.get('usos', 0)}"
                )
                for i, c in enumerate(codigos)
            ]
            select_row = disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Selecione o código para resetar usos...",
                    custom_id="Codigos_ConfirmarReset",
                    options=options,
                )
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Codigos_Voltar"),
            )
            if mode == "embed":
                emb = disnake.Embed(title="Resetar Usos", description="Selecione qual código terá os usos zerados.")
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay("# Resetar Usos\nSelecione qual código terá os usos zerados."),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row,
                        **accent(primary_hex),
                    ),
                    voltar,
                ])
            return

        if cid == "Codigos_Voltar":
            result = _painel_codigos(inter.author.id, primary_hex, mode)
            if mode == "embed":
                emb, comps = result
                await inter.edit_original_message(content=None, embed=emb, components=comps)
            else:
                await inter.edit_original_message(components=result)
            return

    # ── Listener de dropdowns ─────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _dropdown_codigos(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Codigos_"):
            return

        if not _verificar_responsavel(inter):
            await inter.response.send_message("Sem permissão.", ephemeral=True)
            return

        mode        = _mode()
        primary_hex = db.get_document("custom_colors").get("primary")

        from functions.message import message, embed_message
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "Codigos_ConfirmarApagar":
            idx     = int(inter.values[0])
            codigos = get_codigos_usuario(inter.author.id)
            if 0 <= idx < len(codigos):
                codigos.pop(idx)
                salvar_codigos_usuario(inter.author.id, codigos)

            result = _painel_codigos(inter.author.id, primary_hex, mode)
            if mode == "embed":
                emb, comps = result
                await inter.edit_original_message(content=None, embed=emb, components=comps)
            else:
                await inter.edit_original_message(components=result)
            return

        if cid == "Codigos_ConfirmarReset":
            idx     = int(inter.values[0])
            codigos = get_codigos_usuario(inter.author.id)
            if 0 <= idx < len(codigos):
                codigos[idx]["usos"] = 0
                salvar_codigos_usuario(inter.author.id, codigos)

            result = _painel_codigos(inter.author.id, primary_hex, mode)
            if mode == "embed":
                emb, comps = result
                await inter.edit_original_message(content=None, embed=emb, components=comps)
            else:
                await inter.edit_original_message(components=result)
            return


# ─── Modais ───────────────────────────────────────────────────────────────────

class CriarCodigoModal(disnake.ui.Modal):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        sugestao = gerar_codigo_aleatorio()
        super().__init__(
            title="Criar Código de Verificação",
            custom_id="Codigos_CriarModal",
            components=[
                disnake.ui.TextInput(
                    label="Nome do código (identificador)",
                    placeholder="Ex: Amigos da Discord...",
                    custom_id="nome",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    min_length=1,
                    max_length=32,
                ),
                disnake.ui.TextInput(
                    label="Código",
                    placeholder=f"Ex: {sugestao} (deixe em branco para gerar automaticamente)",
                    custom_id="codigo",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    min_length=0,
                    max_length=32,
                ),
                disnake.ui.TextInput(
                    label="Máximo de usos (deixe vazio = ilimitado)",
                    placeholder="Ex: 10",
                    custom_id="max_usos",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    min_length=0,
                    max_length=5,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        nome     = inter.text_values.get("nome", "").strip()
        codigo   = inter.text_values.get("codigo", "").strip().upper() or gerar_codigo_aleatorio()
        max_raw  = inter.text_values.get("max_usos", "").strip()
        mode     = _mode()
        primary_hex = db.get_document("custom_colors").get("primary")

        max_usos: int | None = None
        if max_raw:
            try:
                max_usos = max(1, int(max_raw))
            except ValueError:
                from functions.message import message, embed_message
                if mode == "embed":
                    await embed_message.wait(inter)
                else:
                    await message.wait(inter)
                await inter.followup.send(
                    f"{emoji.wrong} Valor inválido para máximo de usos.", ephemeral=True
                )
                return

        from functions.message import message, embed_message
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        codigos = get_codigos_usuario(inter.author.id)

        if len(codigos) >= MAX_CODIGOS_POR_USER:
            await inter.followup.send(
                f"{emoji.wrong} Você já atingiu o limite de {MAX_CODIGOS_POR_USER} códigos.",
                ephemeral=True,
            )
            return

        # Verificar se código já existe globalmente
        todos = load_json(CODIGOS_JSON)
        for uid_str, lista in todos.items():
            for entry in lista:
                if entry.get("codigo", "").upper() == codigo.upper():
                    await inter.followup.send(
                        f"{emoji.wrong} O código `{codigo}` já está em uso.", ephemeral=True
                    )
                    return

        codigos.append({
            "nome":     nome,
            "codigo":   codigo,
            "max_usos": max_usos,
            "usos":     0,
        })
        salvar_codigos_usuario(inter.author.id, codigos)

        result = _painel_codigos(inter.author.id, primary_hex, mode)
        if mode == "embed":
            emb, comps = result
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(components=result)


def setup(bot: commands.Bot):
    bot.add_cog(CodigosCommand(bot))
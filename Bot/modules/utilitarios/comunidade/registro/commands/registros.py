"""
modules/utilitarios/comunidade/registro/commands/registros.py

Prefixo: registros
Somente cargo líder pode usar.
Exibe o ranking de registradores com paginação.
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ..helpers import carregar_config, accent, get_color, _mode, load_json, REGISTRADORES_JSON

POR_PAG = 10


def _build_rank_components(ranking: list, pagina: int, total_pags: int) -> tuple:
    """Retorna (texto_linhas, nav_buttons)."""
    fatia = ranking[(pagina - 1) * POR_PAG: pagina * POR_PAG]
    linhas = []
    for pos, (uid, info) in enumerate(fatia, start=(pagina - 1) * POR_PAG + 1):
        nome  = info.get("nome", f"<@{uid}>")
        total = info.get("total", 0)
        linhas.append(f"`#{pos:02}` **{nome}** — `{total}` registro(s)")

    txt = "\n".join(linhas) if linhas else "_Nenhum registro encontrado._"
    rodape = f"-# Página {pagina}/{total_pags} • {len(ranking)} registrador(es)"

    nav = []
    if pagina > 1:
        nav.append(disnake.ui.Button(label="◀ Anterior", custom_id=f"RegistrosRank_Pag:{pagina - 1}", style=disnake.ButtonStyle.gray))
    if pagina < total_pags:
        nav.append(disnake.ui.Button(label="Próxima ▶", custom_id=f"RegistrosRank_Pag:{pagina + 1}", style=disnake.ButtonStyle.gray))

    return txt, rodape, nav


class RegistrosCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _check_lider(self, ctx_or_inter) -> bool:
        cfg = carregar_config()
        cargo_lider_id = cfg.get("cargo_lider")
        if not cargo_lider_id:
            return True  # sem restrição configurada
        guild = ctx_or_inter.guild
        member = ctx_or_inter.author if hasattr(ctx_or_inter, "author") else ctx_or_inter.author
        role = guild.get_role(int(cargo_lider_id))
        return role is None or role in member.roles

    @commands.command(name="registros")
    async def cmd_registros(self, ctx: commands.Context, pagina: int = 1):
        if not self._check_lider(ctx):
            await ctx.reply(f"{emoji.wrong} Apenas líderes podem usar este comando.", delete_after=8)
            return

        dados = load_json(REGISTRADORES_JSON)
        if not dados:
            await ctx.reply(f"{emoji.warn} Nenhum registro encontrado ainda.")
            return

        ranking = sorted(dados.items(), key=lambda x: x[1].get("total", 0), reverse=True)
        total_pags = max(1, (len(ranking) + POR_PAG - 1) // POR_PAG)
        pagina = max(1, min(pagina, total_pags))

        txt, rodape, nav = _build_rank_components(ranking, pagina, total_pags)
        mode = _mode()

        if mode == "embed":
            embed = disnake.Embed(
                title="📋 Ranking de Registros",
                description=f"{txt}\n\n{rodape}",
                color=get_color() or disnake.Colour.blurple(),
            )
            components = [disnake.ui.ActionRow(*nav)] if nav else []
            await ctx.send(embed=embed, components=components)
        else:
            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# 📋 Ranking de Registros\n{txt}\n\n{rodape}"),
                    *([disnake.ui.ActionRow(*nav)] if nav else []),
                    **accent(),
                )
            ]
            await ctx.send(components=components, flags=disnake.MessageFlags(is_components_v2=True))

    # ── Paginação via botão ────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _rank_paginate(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RegistrosRank_Pag:"):
            return

        if not self._check_lider(inter):
            await inter.response.send_message(f"{emoji.wrong} Acesso negado.", ephemeral=True)
            return

        await inter.response.defer()
        pagina = int(cid.split(":")[1])

        dados = load_json(REGISTRADORES_JSON)
        ranking = sorted(dados.items(), key=lambda x: x[1].get("total", 0), reverse=True)
        total_pags = max(1, (len(ranking) + POR_PAG - 1) // POR_PAG)
        pagina = max(1, min(pagina, total_pags))

        txt, rodape, nav = _build_rank_components(ranking, pagina, total_pags)
        mode = _mode()

        if mode == "embed":
            embed = disnake.Embed(
                title="📋 Ranking de Registros",
                description=f"{txt}\n\n{rodape}",
                color=get_color() or disnake.Colour.blurple(),
            )
            await inter.edit_original_message(
                embed=embed,
                components=[disnake.ui.ActionRow(*nav)] if nav else [],
            )
        else:
            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# 📋 Ranking de Registros\n{txt}\n\n{rodape}"),
                    *([disnake.ui.ActionRow(*nav)] if nav else []),
                    **accent(),
                )
            ]
            await inter.edit_original_message(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True),
            )


def setup(bot: commands.Bot):
    bot.add_cog(RegistrosCommand(bot))
"""
modules/utilitarios/comunidade/registro/commands/registrar.py

Prefixo: registrar / re
Só ativo no modo manual.
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ..helpers import carregar_config, accent, build_registro_components

# Sessões importadas do cog principal
from ..cog import _sessoes


class RegistrarCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="registrar", aliases=["re"])
    async def cmd_registrar(self, ctx: commands.Context, membro: disnake.Member = None):
        cfg = carregar_config()

        if cfg.get("modo") != "manual":
            await ctx.reply(
                f"{emoji.wrong} O sistema está no modo **automático**. Use o botão de registro no painel.",
                delete_after=8,
            )
            return

        # Verificar cargo registrador
        cargo_reg_id = cfg.get("cargo_registrador")
        if cargo_reg_id:
            role = ctx.guild.get_role(int(cargo_reg_id))
            if role and role not in ctx.author.roles:
                await ctx.reply(
                    f"{emoji.wrong} Você não tem o cargo necessário para registrar.",
                    delete_after=8,
                )
                return

        # Resolver membro via menção ou reply
        if membro is None:
            ref = ctx.message.reference
            if ref and ref.resolved and isinstance(ref.resolved, disnake.Message):
                author = ref.resolved.author
                membro = author if isinstance(author, disnake.Member) else None
            if membro is None:
                await ctx.reply(
                    f"{emoji.wrong} Mencione um membro ou responda à mensagem dele.\n"
                    f"-# Uso: `registrar @membro` ou responda à mensagem do membro.",
                    delete_after=10,
                )
                return

        if membro.bot:
            await ctx.reply(f"{emoji.wrong} Não é possível registrar um bot.", delete_after=8)
            return

        if membro.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode registrar a si mesmo.", delete_after=8)
            return

        paginas = cfg.get("paginas", {})
        primeira = next((int(k) for k in sorted(paginas.keys()) if paginas[k].get("cargos")), 1)

        sessao = {
            "pagina": primeira,
            "cargos_selecionados": {},
            "registrado_id": membro.id,
            "registrador_id": ctx.author.id,
        }

        comps = build_registro_components(
            cfg, primeira, {},
            ctx.guild,
            registrado_id=membro.id,
            registrador_id=ctx.author.id,
        )

        sent = await ctx.send(
            components=comps,
            flags=disnake.MessageFlags(is_components_v2=True),
        )
        _sessoes[sent.id] = sessao


def setup(bot: commands.Bot):
    bot.add_cog(RegistrarCommand(bot))
"""
modules/utilitarios/comunidade/cog.py  — com Conversor adicionado
"""
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji


def _mode() -> str:
    return (db.get_document("custom_mode") or {}).get("mode", "components")


def _color() -> int:
    h = (db.get_document("custom_colors") or {}).get("primary")
    return int(h.replace("#", ""), 16) if h else 0x5865F2


def _ck() -> dict:
    c = _color()
    return {"accent_colour": disnake.Colour(c)} if c else {}


class ComunidadeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_community_select(self) -> disnake.ui.StringSelect:
        select = disnake.ui.StringSelect(
            custom_id="Comunidade_Select",
            placeholder="Navegar",
        )

        select.add_option(label="Verificação",        value="Comunidade_Verificacao",  emoji=emoji.correct)
        select.add_option(label="Sistema de Registro", value="Comunidade_Registro",    emoji=emoji.telegram)
        select.add_option(label="Cargo por tag/bio",   value="Comunidade_TagBio",      emoji=emoji.coupon)
        select.add_option(label="Família",             value="Comunidade_Familia",     emoji=emoji.group)
        select.add_option(label="Reputação",           value="Comunidade_Reputacao",   emoji=emoji.member)
        select.add_option(label="Conversor de Mídia",  value="Comunidade_Conversor",   emoji=emoji.reload)
        select.add_option(label="Panela (em breve) ",  value="Comunidade_Panela",      emoji=emoji.group)
        select.add_option(label="FiveM (em breve) ",   value="Comunidade_FiveM",       emoji=emoji.gun)
        select.add_option(label="Instagram",           value="Comunidade_Instagram",   emoji=emoji.sparkles)
        select.add_option(label="Tellonym",            value="Comunidade_Tellonym",    emoji=emoji.ghost)
        select.add_option(label="Twitter/X",           value="Comunidade_Twitter",     emoji=emoji.sparkles)

        return select

    def community_components(self, inter=None) -> list:
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > **Comunidade**\n"
                    f"Gerencie os recursos de comunidade do seu servidor."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(self._get_community_select()),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Comunidade_VoltarPainel"),
                ),
            )
        ]

    def community_embed(self, inter=None) -> tuple:
        embed = disnake.Embed(
            title="Comunidade",
            description="Bem-vindo ao painel de comunidade.\nSelecione um módulo abaixo para começar.",
            color=_color(),
        )
        components = [disnake.ui.ActionRow(self._get_community_select())]
        return embed, components

    @commands.Cog.listener("on_dropdown")
    async def on_comunidade_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "Comunidade_Select":
            return

        value = inter.values[0]

        # ── Instagram ────────────────────────────────────────────────────────
        if value == "Comunidade_Instagram":
            cog = self.bot.get_cog("InstagramCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Instagram não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # ── Tellonym ─────────────────────────────────────────────────────────
        if value == "Comunidade_Tellonym":
            cog = self.bot.get_cog("CartasCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Tellonym não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # ── Twitter/X ────────────────────────────────────────────────────────
        if value == "Comunidade_Twitter":
            cog = self.bot.get_cog("TwitterCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Twitter/X não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # ── Cargo por Tag/Bio ────────────────────────────────────────────────
        if value == "Comunidade_TagBio":
            cog = self.bot.get_cog("TagBioCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Tag/Bio não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # ── Registro ─────────────────────────────────────────────────────────
        if value == "Comunidade_Registro":
            cog = self.bot.get_cog("RegistroCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Registro não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # ── Verificação ──────────────────────────────────────────────────────
        if value == "Comunidade_Verificacao":
            cog = self.bot.get_cog("VerificacaoCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Verificação não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # ── Família ──────────────────────────────────────────────────────────
        if value == "Comunidade_Familia":
            cog = self.bot.get_cog("FamiliaCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Família não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # ── Reputação ─────────────────────────────────────────────────────────
        if value == "Comunidade_Reputacao":
            cog = self.bot.get_cog("ReputacaoCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Reputação não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # ── Conversor de Mídia ───────────────────────────────────────────────
        if value == "Comunidade_Conversor":
            cog = self.bot.get_cog("ConversorCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Conversor não encontrado.", ephemeral=True)
                return
            await self._open_subpanel(inter, cog, "embed" if _mode() == "embed" else "components")
            return

        # Qualquer outro → em breve
        if value.startswith("Comunidade_"):
            await inter.response.send_message(
                f"{emoji.warn} **Em breve!** Esta funcionalidade ainda está sendo desenvolvida.",
                ephemeral=True,
            )

    async def _open_subpanel(self, inter: disnake.MessageInteraction, cog, mode: str):
        if not inter.response.is_done():
            await inter.response.defer(with_message=False)

        if mode == "embed":
            if hasattr(cog, "PainelEmbed"):
                embed, comps = cog.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            if hasattr(cog, "Painel"):
                await inter.edit_original_message(components=cog.Painel())

    @commands.Cog.listener("on_button_click")
    async def on_comunidade_button(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Comunidade_Reputacao":
            cog = self.bot.get_cog("ReputacaoCog")
            if not cog:
                await inter.response.send_message("⚠️ Módulo de Reputação não encontrado.", ephemeral=True)
                return
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=cog.Painel())
            return

        if inter.component.custom_id == "Comunidade_VoltarPainel":
            painel = self.bot.get_cog("PainelCommand")
            if not painel:
                await inter.response.send_message("⚠️ Painel não encontrado.", ephemeral=True)
                return

            mode = _mode()
            if not inter.response.is_done():
                await inter.response.defer(with_message=False)

            if mode == "embed":
                embed, comps = painel.PainelEmbed(inter, None)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=painel.PainelComponents(inter, None))


def setup(bot: commands.Bot):
    bot.add_cog(ComunidadeCog(bot))
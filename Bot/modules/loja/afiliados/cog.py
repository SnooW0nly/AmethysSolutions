"""
Painel administrativo do sistema de afiliados.
Acessível via Painel > Loja > Afiliados.
"""
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from . import helpers


# ──────────────────────────────────────────────────────────
# Modal de configuração de comissão
# ──────────────────────────────────────────────────────────

class ComissaoModal(disnake.ui.Modal):
    def __init__(self):
        config = helpers.carregar_config()
        components = [
            disnake.ui.TextInput(
                label="Percentual de Comissão (%)",
                custom_id="percentual",
                value=str(config.get("comissao_percentual", 5.0)),
                placeholder="Ex: 5.0 (para 5% por venda)",
                max_length=6,
                required=True,
            )
        ]
        super().__init__(title="Configurar Comissão de Afiliados", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer()
        try:
            percentual = float(inter.text_values["percentual"].replace(",", "."))
            if not (0 < percentual <= 100):
                raise ValueError
        except ValueError:
            await inter.followup.send(
                f"{emoji.wrong} Percentual inválido! Use um número entre 0.1 e 100.",
                ephemeral=True
            )
            return

        config = helpers.carregar_config()
        config["comissao_percentual"] = round(percentual, 2)
        helpers.salvar_config(config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed, comps = AfiliadosCog.painel_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(components=AfiliadosCog.painel(inter))


# ──────────────────────────────────────────────────────────
# Cog principal do painel admin
# ──────────────────────────────────────────────────────────

class AfiliadosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Construtores de painel ────────────────────────────

    @staticmethod
    def _get_status_text(inter) -> str:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        percentual = config.get("comissao_percentual", 5.0)
        canal_saque_id = config.get("canal_saque_id")

        canal_texto = "`Não configurado`"
        if canal_saque_id:
            guild = getattr(inter, "guild", None)
            if guild:
                canal = guild.get_channel(int(canal_saque_id))
                canal_texto = canal.mention if canal else "`Canal não encontrado`"

        return (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"💰 **Comissão por venda:** `{percentual}%`\n"
            f"💸 **Canal de Saque:** {canal_texto}\n"
        ), ativado

    @staticmethod
    def painel(inter) -> list:
        resumo_tuple = AfiliadosCog._get_status_text(inter)
        resumo, ativado = resumo_tuple

        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Loja > **Afiliados**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Gerencie o sistema de afiliados da sua loja.\n"
                    "Afiliados ganham comissão quando convidados realizam compras."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.power,
                        custom_id="Afiliados_Toggle"
                    ),
                    disnake.ui.Button(
                        label="Configurar Comissão",
                        style=disnake.ButtonStyle.blurple,
                        emoji="💰",
                        custom_id="Afiliados_ConfigComissao",
                        disabled=not ativado
                    ),
                    disnake.ui.Button(
                        label="Canal de Saque",
                        style=disnake.ButtonStyle.grey,
                        emoji="💸",
                        custom_id="Afiliados_ConfigCanal",
                        disabled=not ativado
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Panel"
                )
            )
        ]

    @staticmethod
    def painel_embed(inter) -> tuple:
        resumo_tuple = AfiliadosCog._get_status_text(inter)
        resumo, ativado = resumo_tuple

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title="🔗 Sistema de Afiliados",
            description=(
                "-# Painel > Loja > **Afiliados**\n\n"
                "Gerencie o sistema de afiliados da sua loja.\n"
                "Afiliados ganham comissão quando convidados realizam compras."
            )
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        embed.add_field(name="Configurações Atuais", value=resumo, inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.power,
                    custom_id="Afiliados_Toggle"
                ),
                disnake.ui.Button(
                    label="Configurar Comissão",
                    style=disnake.ButtonStyle.blurple,
                    emoji="💰",
                    custom_id="Afiliados_ConfigComissao",
                    disabled=not ativado
                ),
                disnake.ui.Button(
                    label="Canal de Saque",
                    style=disnake.ButtonStyle.grey,
                    emoji="💸",
                    custom_id="Afiliados_ConfigCanal",
                    disabled=not ativado
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Panel"
                )
            )
        ]
        return embed, components

    @staticmethod
    def painel_canal() -> list:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Loja > Afiliados > **Canal de Saque**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Selecione o canal onde as **solicitações de saque** dos afiliados serão enviadas.\n"
                    "-# Os administradores deverão processar manualmente os saques neste canal."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="Afiliados_SelectCanal",
                        placeholder="Selecione um canal de texto",
                        channel_types=[disnake.ChannelType.text],
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Afiliados_Voltar"
                )
            )
        ]

    @staticmethod
    def painel_canal_embed() -> tuple:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title="🔗 Afiliados › Canal de Saque",
            description=(
                "Selecione o canal onde as **solicitações de saque** dos afiliados serão enviadas.\n"
                "Os administradores deverão processar manualmente os saques neste canal."
            )
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Afiliados_SelectCanal",
                    placeholder="Selecione um canal de texto",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Afiliados_Voltar"
                )
            )
        ]
        return embed, components

    # ── Listeners ────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Afiliados_"):
            return

        if cid == "Afiliados_ConfigComissao":
            await inter.response.send_modal(ComissaoModal())
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await inter.response.defer(with_message=False)
            await message.wait(inter, send=False)

        if cid == "Afiliados_Toggle":
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            if mode == "embed":
                embed, comps = self.painel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=self.painel(inter))

        elif cid == "Afiliados_ConfigCanal":
            if mode == "embed":
                embed, comps = self.painel_canal_embed()
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=self.painel_canal())

        elif cid == "Afiliados_Voltar":
            if mode == "embed":
                embed, comps = self.painel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=self.painel(inter))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.data.custom_id != "Afiliados_SelectCanal":
            return

        canal_id = int(inter.values[0])
        config = helpers.carregar_config()
        config["canal_saque_id"] = canal_id
        helpers.salvar_config(config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
            embed, comps = self.painel_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.response.defer(with_message=False)
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=self.painel(inter))


def setup(bot: commands.Bot):
    bot.add_cog(AfiliadosCog(bot))
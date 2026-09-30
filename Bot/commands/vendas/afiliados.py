"""
Comando /afiliados — painel pessoal do afiliado.
Permite ver saldo, configurar Pix, togglear notificações e solicitar saque.
"""
import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.utils import utils
from modules.loja.afiliados import helpers


# ──────────────────────────────────────────────────────────
# Modal: configurar chave Pix
# ──────────────────────────────────────────────────────────

class PixModal(disnake.ui.Modal):
    def __init__(self, current_pix: str = ""):
        components = [
            disnake.ui.TextInput(
                label="Chave Pix",
                custom_id="pix_key",
                value=current_pix,
                placeholder="CPF, CNPJ, e-mail, telefone ou chave aleatória",
                max_length=150,
                required=True,
            )
        ]
        super().__init__(title="Configurar Chave Pix", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(with_message=False)

        pix = inter.text_values["pix_key"].strip()
        if not pix:
            await inter.followup.send(
                f"{emoji.wrong} Chave Pix inválida!", ephemeral=True
            )
            return

        membro = helpers.get_membro(str(inter.user.id))
        membro["pix"] = pix
        helpers.salvar_membro(str(inter.user.id), membro)

        mode = db.get_document("custom_mode").get("mode")
        painel = AfiliadorComando._build_painel(inter.user, mode)
        if mode == "embed":
            embed, comps = painel
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(components=painel)


# ──────────────────────────────────────────────────────────
# Modal: solicitar saque
# ──────────────────────────────────────────────────────────

class SacarModal(disnake.ui.Modal):
    def __init__(self, saldo_disponivel: float, pix: str, guild: disnake.Guild | None):
        self._saldo = saldo_disponivel
        self._guild = guild
        components = [
            disnake.ui.TextInput(
                label=f"Valor (Disponível: R$ {saldo_disponivel:.2f})",
                custom_id="valor_saque",
                value=f"{saldo_disponivel:.2f}",
                placeholder="Ex: 50.00",
                max_length=10,
                required=True,
            )
        ]
        super().__init__(title="Solicitar Saque — Afiliados", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(with_message=False)

        # Validar valor
        try:
            valor = float(inter.text_values["valor_saque"].replace(",", "."))
            if valor <= 0:
                raise ValueError
        except ValueError:
            await inter.followup.send(
                f"{emoji.wrong} Valor inválido! Digite um número positivo.",
                ephemeral=True
            )
            return

        membro = helpers.get_membro(str(inter.user.id))
        saldo = membro.get("saldo", 0.0)

        if round(valor, 2) > round(saldo, 2):
            await inter.followup.send(
                f"{emoji.wrong} Saldo insuficiente! Seu saldo atual é `R$ {saldo:.2f}`.",
                ephemeral=True
            )
            return

        pix = membro.get("pix")
        if not pix:
            await inter.followup.send(
                f"{emoji.wrong} Configure sua chave Pix antes de solicitar um saque!",
                ephemeral=True
            )
            return

        config = helpers.carregar_config()
        canal_saque_id = config.get("canal_saque_id")
        if not canal_saque_id:
            await inter.followup.send(
                f"{emoji.wrong} O canal de saque não está configurado. Contate um administrador.",
                ephemeral=True
            )
            return

        guild = self._guild or inter.guild
        canal = guild.get_channel(int(canal_saque_id)) if guild else None
        if not canal:
            await inter.followup.send(
                f"{emoji.wrong} Canal de saque não encontrado. Contate um administrador.",
                ephemeral=True
            )
            return

        # Debitar saldo
        sucesso = helpers.solicitar_saque(str(inter.user.id), valor)
        if not sucesso:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao processar o saque. Tente novamente.",
                ephemeral=True
            )
            return

        # Enviar solicitação no canal de saques
        mode = db.get_document("custom_mode").get("mode")
        colors = db.get_document("custom_colors") or {}
        primary_hex = colors.get("primary")
        color = None
        if primary_hex:
            try:
                color = int(primary_hex.replace("#", ""), 16)
            except Exception:
                pass

        novo_saldo = round(saldo - valor, 2)
        saque_texto = (
            f"**Usuário:** {inter.user.mention} (`{inter.user.id}`)\n"
            f"**Valor solicitado:** `R$ {valor:.2f}`\n"
            f"**Chave Pix:** `{pix}`\n"
            f"**Saldo restante:** `R$ {novo_saldo:.2f}`"
        )

        try:
            if mode == "embed":
                embed_s = disnake.Embed(
                    title="💸 Solicitação de Saque — Afiliados",
                    description=saque_texto,
                    color=color or disnake.Color.orange()
                )
                embed_s.set_thumbnail(url=inter.user.display_avatar.url)
                await canal.send(embed=embed_s)
            else:
                container_kwargs = {}
                if color:
                    container_kwargs["accent_colour"] = disnake.Colour(color)
                await canal.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"# 💸 Solicitação de Saque\n"
                                f"-# Sistema de Afiliados"
                            ),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay(saque_texto),
                            **container_kwargs
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
        except Exception as e:
            print(f"[Afiliados] Erro ao enviar saque no canal: {e}")

        # Atualizar painel do usuário
        painel = AfiliadorComando._build_painel(inter.user, mode)
        if mode == "embed":
            embed_p, comps = painel
            await inter.edit_original_message(content=None, embed=embed_p, components=comps)
        else:
            await inter.edit_original_message(components=painel)

        await inter.followup.send(
            f"{emoji.correct} Saque de **R$ {valor:.2f}** solicitado com sucesso!\n"
            f"-# Aguarde o processamento no canal de saques.",
            ephemeral=True
        )


# ──────────────────────────────────────────────────────────
# Cog do comando /afiliados
# ──────────────────────────────────────────────────────────

class AfiliadorComando(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _build_painel(user: disnake.User | disnake.Member, mode: str):
        """Constrói o painel pessoal do afiliado."""
        membro = helpers.get_membro(str(user.id))

        saldo = membro.get("saldo", 0.0)
        pix = membro.get("pix")
        notificar = membro.get("notificar_dm", True)
        num_convidados = len(membro.get("convidados", []))
        tem_pix = bool(pix)

        pix_display = f"`{pix}`" if tem_pix else "`Não configurada`"

        resumo = (
            f"💰 **Saldo disponível:** `R$ {saldo:.2f}`\n"
            f"🔑 **Chave Pix:** {pix_display}\n"
            f"🔔 **Notificações DM:** `{'Ativado' if notificar else 'Desativado'}`\n"
            f"👥 **Membros convidados:** `{num_convidados}`\n"
        )

        primary_hex = db.get_document("custom_colors").get("primary")
        color = None
        if primary_hex:
            try:
                color = int(primary_hex.replace("#", ""), 16)
            except Exception:
                pass

        botoes = [
            disnake.ui.Button(
                label="Configurar Pix",
                style=disnake.ButtonStyle.blurple,
                emoji="🔑",
                custom_id="MeusAfiliados_ConfigPix"
            ),
            disnake.ui.Button(
                label="Notificações",
                style=disnake.ButtonStyle.green if notificar else disnake.ButtonStyle.grey,
                emoji="🔔" if notificar else "🔕",
                custom_id="MeusAfiliados_ToggleDM"
            ),
            disnake.ui.Button(
                label="Sacar",
                style=disnake.ButtonStyle.green if saldo > 0 else disnake.ButtonStyle.grey,
                emoji="💸",
                custom_id="MeusAfiliados_Sacar",
                disabled=saldo <= 0
            ),
        ]

        if mode == "embed":
            embed = disnake.Embed(
                title="🔗 Meu Painel de Afiliados",
                description="-# Gerencie suas comissões e solicite saques.",
                color=color or disnake.Color.blurple()
            )
            embed.add_field(name="Informações da Conta", value=resumo, inline=False)
            embed.set_thumbnail(url=user.display_avatar.url)

            if not tem_pix:
                embed.set_footer(text="⚠️ Configure sua chave Pix para poder sacar.")

            components = [disnake.ui.ActionRow(*botoes)]
            return embed, components

        else:
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)

            aviso = ""
            if not tem_pix:
                aviso = "\n-# ⚠️ Configure sua chave Pix para poder sacar."

            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# 🔗 Meu Painel de Afiliados\n"
                        f"-# Gerencie suas comissões e solicite saques."
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.TextDisplay(resumo + aviso),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    disnake.ui.ActionRow(*botoes),
                    **container_kwargs
                )
            ]

    # ── Slash command ────────────────────────────────────

    @commands.slash_command(
        name="afiliados",
        description="Veja seu painel de afiliado, saldo de comissões e solicite saques",
        guild_ids=[utils.obter_server_principal()],
    )
    async def cmd_afiliados(self, inter: disnake.CommandInteraction):
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            await inter.response.send_message(
                f"{emoji.wrong} O sistema de afiliados não está ativo no momento.",
                ephemeral=True
            )
            return

        mode = db.get_document("custom_mode").get("mode")
        painel = self._build_painel(inter.user, mode)

        if mode == "embed":
            embed, comps = painel
            await inter.response.send_message(embed=embed, components=comps, ephemeral=True)
        else:
            await inter.response.send_message(
                components=painel,
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True
            )

    # ── Botões do painel pessoal ─────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("MeusAfiliados_"):
            return

        # Verificar se sistema está ativo
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"{emoji.wrong} O sistema de afiliados não está ativo.",
                    ephemeral=True
                )
            return

        if cid == "MeusAfiliados_ConfigPix":
            membro = helpers.get_membro(str(inter.user.id))
            await inter.response.send_modal(PixModal(current_pix=membro.get("pix") or ""))
            return

        if cid == "MeusAfiliados_Sacar":
            membro = helpers.get_membro(str(inter.user.id))
            saldo = membro.get("saldo", 0.0)

            if saldo <= 0:
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem saldo disponível para saque.",
                    ephemeral=True
                )
                return

            if not config.get("canal_saque_id"):
                await inter.response.send_message(
                    f"{emoji.wrong} O canal de saque não está configurado. Contate um administrador.",
                    ephemeral=True
                )
                return

            if not membro.get("pix"):
                await inter.response.send_message(
                    f"{emoji.wrong} Configure sua chave Pix antes de solicitar um saque!",
                    ephemeral=True
                )
                return

            await inter.response.send_modal(
                SacarModal(
                    saldo_disponivel=saldo,
                    pix=membro.get("pix", ""),
                    guild=inter.guild
                )
            )
            return

        # Para toggle DM, defer sem mensagem
        if not inter.response.is_done():
            try:
                await inter.response.defer_update()
            except Exception:
                pass

        if cid == "MeusAfiliados_ToggleDM":
            membro = helpers.get_membro(str(inter.user.id))
            membro["notificar_dm"] = not membro.get("notificar_dm", True)
            helpers.salvar_membro(str(inter.user.id), membro)

            mode = db.get_document("custom_mode").get("mode")
            painel = self._build_painel(inter.user, mode)
            if mode == "embed":
                embed, comps = painel
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=painel)


def setup(bot: commands.Bot):
    bot.add_cog(AfiliadorComando(bot))
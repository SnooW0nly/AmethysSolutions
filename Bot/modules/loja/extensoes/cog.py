from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from .subscription_manager import is_extension_active, PURCHASABLE_EXTENSIONS

def build_extensoes_panel(mode: str) -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")

    options = [
        disnake.SelectOption(
            label="Roblox",
            value="roblox",
            emoji=emoji.roblox,
            description="Sistema de venda de Robux e Gamepass",
        ),
        disnake.SelectOption(
            label="Gerador",
            value="gerador",
            emoji=emoji.commands,
            description="Sistema de geração de contas e serviços",
        ),
        disnake.SelectOption(
            label="Impulso Automático",
            value="joiner",
            emoji=emoji.boost,
            description="Entrega/Venda de impulso automático com OAuth2",
        ),
        disnake.SelectOption(
            label="Nitrada Automática",
            value="nitrada",
            emoji=emoji.rocket,
            description="Sistema automatizado de ativação de Nitro",
        ),
    ]

    if mode == "embed":
        embed_kw = {}
        if hex_:
            embed_kw["color"] = int(hex_.replace("#", ""), 16)
        embed = disnake.Embed(
            description=(
                f"-# Painel > Loja > **Extensões**\n\n"
                f"Gerencie as extensões disponíveis da sua loja.\n"
                f"Selecione uma extensão abaixo para acessar suas configurações."
            ),
            **embed_kw,
        )
        return {
            "embed": embed,
            "components": [
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="LojaExtensoes_Select",
                        placeholder="Selecione uma extensão",
                        options=options,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Loja_Panel",
                    )
                ),
            ],
        }

    container_kw = {}
    if hex_:
        container_kw["accent_colour"] = disnake.Colour(int(hex_.replace("#", ""), 16))

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Loja > **Extensões**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"Gerencie as extensões disponíveis da sua loja.\n"
                    f"Selecione uma extensão abaixo para acessar suas configurações."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"{emoji.roblox} **Roblox**\n"
                    f"-# Sistema de venda de Robux e Gamepass com entrega manual via ticket"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"{emoji.commands} **Gerador**\n"
                    f"-# Venda assinaturas do sistema de Gerador ou apenas o utilize em seu servidor para interação."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"{emoji.boost} **Impulso Automático**\n"
                    f"-# Entrega/Venda de impulso automático com OAuth2."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"{emoji.rocket} **Nitrada Automática**\n"
                    f"-# Sistema automatizado de ativação de Nitro via contas, links e cartões."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="LojaExtensoes_Select",
                        placeholder="Selecione uma extensão",
                        options=options,
                    )
                ),
                **container_kw,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Panel",
                )
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_nitrada_bloqueada_panel(mode: str) -> dict:
    """Painel exibido quando a extensão Nitrada não está ativa (necessita compra)."""
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    info = PURCHASABLE_EXTENSIONS.get("nitrada", {})
    preco = info.get("price", 30.0)
  #  duracao = info.get("duration_days", 30)

    body = (
        f"## {emoji.rocket} Nitrada Automática\n\n"
        f"Esta extensão **não está ativa** no momento.\n\n"
        f"**O que ela faz:**\n"
        f"├Processa contas Discord e tenta ativar Nitro promocional\n"
        f"Workers assíncronos com fila inteligente\n"
        f"Painel completo de logs, estatísticas e diagnóstico\n\n"
        f"**Valor:** R$ {preco:.2f}"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label=f"Assinar por R$ {preco:.2f}",
                style=disnake.ButtonStyle.green,
                emoji=emoji.cart,
                custom_id="Nitrada_Comprar",
            )
        )
    ]
    back = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id="LojaExtensoes_Panel",
        )
    )

    if mode == "embed":
        embed_kw = {}
        if hex_:
            embed_kw["color"] = int(hex_.replace("#", ""), 16)
        embed = disnake.Embed(
            title="{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}",
            description=f"-# Painel > Loja > Extensões > **Nitrada**\n\n{body}",
            **embed_kw,
        )
        return {"embed": embed, "components": rows + [back]}

    container_kw = {}
    if hex_:
        container_kw["accent_colour"] = disnake.Colour(int(hex_.replace("#", ""), 16))

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Loja > Extensões > **Nitrada**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **container_kw,
            ),
            back,
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


class ExtensoesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _mode(self) -> str:
        return db.get_document("custom_mode").get("mode")

    async def _show_extensoes(self, inter: disnake.MessageInteraction):
        mode = self._mode()
        await (embed_message if mode == "embed" else message).wait(inter, send=False)
        panel = build_extensoes_panel(mode)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
            await inter.edit_original_message(**panel, flags=flags)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "LojaExtensoes_Panel":
            await self._show_extensoes(inter)

        elif cid == "Nitrada_Comprar":
            from .subscription_manager import create_payment
            await inter.response.defer(ephemeral=True)
            payer_name = inter.user.display_name or inter.user.name
            payer_doc_map = db.get_document("user_documents") or {}
            payer_document = payer_doc_map.get(str(inter.user.id), "00000000000")
            result = await create_payment("nitrada", str(inter.user.id), payer_name, payer_document)
            if result.get("success"):
                await inter.followup.send(
                    f"# **Pagamento gerado!**\n\n"
                    f"- Valor: `R$ {result['value']:.2f}`\n"
                    f"> Código PIX:\n```\n{result.get('copy_paste', 'N/A')}\n```\n"
                    f"-# ID do pagamento: `{result['payment_id']}`\n"
                    f"-# A extensão será ativada automaticamente após confirmação.",
                    ephemeral=True,
                )
            else:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao gerar pagamento: {result.get('error', 'desconhecido')}",
                    ephemeral=True,
                )

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "LojaExtensoes_Select":
            return

        choice = inter.values[0]
        mode = self._mode()
        await (embed_message if mode == "embed" else message).wait(inter, send=False)

        if choice == "roblox":
            from .roblox.paineis import get_roblox_main_panel
            config = db.get_document("roblox_config") or {}
            components, flags = get_roblox_main_panel(config, mode)
            if mode == "embed":
                embed, comps = components
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await inter.edit_original_message(components=components, flags=flags)

        elif choice == "gerador":
            from .gerador.cog_painel import build_main_panel
            panel = build_main_panel(mode)
            if "embed" in panel:
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
                await inter.edit_original_message(**panel, flags=flags)

        elif choice == "joiner":
            from .joiner.cog_painel import build_main_panel
            panel = build_main_panel(mode)
            if "embed" in panel:
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
                await inter.edit_original_message(**panel, flags=flags)

        elif choice == "nitrada":
            if is_extension_active("nitrada"):
                from .auto_nitrada.cog import build_main_panel_async
                # Tenta obter o api_client do cog principal, se disponível
                nitro_cog = inter.bot.get_cog("NitroAutomaticoCog")
                api_client = nitro_cog.api_client if nitro_cog else None
                panel = await build_main_panel_async(mode, api_client)
                if "embed" in panel:
                    await inter.edit_original_message(content=None, **panel)
                else:
                    flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
                    await inter.edit_original_message(**panel, flags=flags)
            else:
                # Extensão inativa — exibe painel de compra
                panel = build_nitrada_bloqueada_panel(mode)
                if "embed" in panel:
                    await inter.edit_original_message(content=None, **panel)
                else:
                    flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
                    await inter.edit_original_message(**panel, flags=flags)

        else:
            await self._show_extensoes(inter)


def setup(bot: commands.Bot):
    bot.add_cog(ExtensoesCog(bot))
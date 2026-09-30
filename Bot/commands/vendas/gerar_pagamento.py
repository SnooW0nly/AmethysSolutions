import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms
from functions.utils import utils


class GerarPagamentoCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="gerar_pagamento",
        description="Gera um pagamento Pix avulso",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(administrator=True),
    )
    async def gerar_pagamento(
        self,
        inter: disnake.ApplicationCommandInteraction,
        valor: float = commands.Param(
            description="Valor do pagamento (ex: 29.90)",
            min_value=0.01,
        ),
        descricao: str = commands.Param(
            description="Descrição do pagamento (opcional)",
            default=None,
        ),
        cliente_paga_taxa: str = commands.Param(
            description="O cliente vai pagar a taxa de serviço?",
            default="nao",
            choices=["sim", "nao"],
        ),
    ):
        if not await perms.check(inter.author.id):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando!",
                ephemeral=True,
            )
            return

        await inter.response.defer(ephemeral=True)

        # Verificar se há algum provedor Pix configurado
        pagamentos = db.get_document("pagamentos") or {}
        payment_configs = db.get_document("payment_configs") or {}

        pix_providers = [
            "amethys_wallet", "mercado_pago", "efibank", "pushinpay",
            "misticpay", "livepix", "nubank_imap", "asaas", "pix_manual",
        ]
        tem_pix = any(pagamentos.get(p) for p in pix_providers)

        if not tem_pix:
            await inter.followup.send(
                f"{emoji.wrong} Nenhum provedor Pix está ativado! Configure um em **Configurações > Pagamentos**.",
                ephemeral=True,
            )
            return

        # Calcular taxa se amethys_wallet estiver ativo e cliente pagar
        valor_final = round(valor, 2)
        taxa = 0.0

        aw_cfg = payment_configs.get("amethys_wallet") or {}
        aw_ativo = bool(pagamentos.get("amethys_wallet")) and bool(aw_cfg.get("api_key"))

        if aw_ativo and cliente_paga_taxa == "sim" and valor_final > 0:
            try:
                from functions.payments.amethys_wallet import _request as _aw_request, _get_api_key as _aw_get_key
                aw_key = _aw_get_key()
                plan_r = await _aw_request("GET", "api/v1/user/my-plan", api_key=aw_key)
                plan_d = plan_r.get("data", {}).get("currentPlan", {})
                fp = float(plan_d.get("transactionFeePercent", 0))
                ff = float(plan_d.get("transactionFeeFixed", 0)) / 100
                taxa = round((valor_final * fp / 100) + ff, 2)
                valor_final = round(valor_final + taxa, 2)
            except Exception:
                pass

        desc_final = descricao or f"Pagamento avulso — R$ {utils.format_price_brl(valor_final)}"

        # Gerar o pagamento
        try:
            from modules.loja.cart.checkout import _create_payment
            result = await _create_payment(
                payment_method="pix",
                amount=valor_final,
                user=inter.author,
                description=desc_final,
            )
        except Exception as e:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao gerar pagamento: `{e}`",
                ephemeral=True,
            )
            return

        if not result:
            await inter.followup.send(
                f"{emoji.wrong} Não foi possível gerar o pagamento. Verifique se o provedor está configurado corretamente.",
                ephemeral=True,
            )
            return

        # Extrair dados do resultado
        from modules.loja.cart.checkout import _extract_urls, _extract_qr_image, _http_get_bytes
        checkout_url, copy_code = _extract_urls(result)
        qr_bytes, qr_url = _extract_qr_image(result)

        if qr_url and not qr_bytes:
            qr_bytes = await _http_get_bytes(qr_url)

        # Montar resposta
        mode = db.get_document("custom_mode").get("mode")
        colors = db.get_document("custom_colors") or {}
        primary_hex = colors.get("primary")

        valor_str = utils.format_price_brl(valor_final)
        taxa_str = utils.format_price_brl(taxa) if taxa > 0 else None

        info_lines = (
            f"-# Valor: `{valor_str}`\n"
            + (f"-# Taxa incluída: `{taxa_str}`\n" if taxa_str else "")
            + (f"-# Descrição: `{desc_final}`\n" if descricao else "")
        )

        files = []
        if qr_bytes:
            files.append(disnake.File(
                __import__("io").BytesIO(qr_bytes),
                filename="qrcode.png",
            ))

        buttons = []
        if copy_code:
            buttons.append(disnake.ui.Button(
                label="Copiar código Pix",
                emoji=emoji.pix,
                style=disnake.ButtonStyle.blurple,
                custom_id=f"copy_pix_code:{copy_code[:80]}",
            ))
        if checkout_url:
            buttons.append(disnake.ui.Button(
                label="Abrir link",
                emoji=emoji.link,
                style=disnake.ButtonStyle.url,
                url=checkout_url,
            ))

        if mode == "embed":
            embed_kwargs = {}
            if primary_hex:
                try:
                    embed_kwargs["color"] = int(primary_hex.replace("#", ""), 16)
                except (ValueError, AttributeError):
                    pass

            embed = disnake.Embed(
                description=(
                    f"-# Painel > **Gerar Pagamento**\n\n"
                    f"**Pagamento Pix gerado com sucesso!**\n"
                    f"{info_lines}"
                    + (f"\n```{copy_code}```" if copy_code else "")
                ),
                **embed_kwargs,
            )
            if qr_bytes:
                embed.set_image(url="attachment://qrcode.png")

            components = []
            if buttons:
                components.append(disnake.ui.ActionRow(*buttons))

            await inter.followup.send(
                embed=embed,
                components=components or None,
                files=files or None,
                ephemeral=True,
            )

        else:
            container_kwargs = {}
            if primary_hex:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(
                        int(primary_hex.replace("#", ""), 16)
                    )
                except (ValueError, AttributeError):
                    pass

            container_children = [
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > **Gerar Pagamento**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"**Pagamento Pix gerado!**\n{info_lines}"
                    + (f"\n```{copy_code}```" if copy_code else "")
                ),
            ]

            if qr_bytes:
                container_children.append(
                    disnake.ui.MediaGallery(
                        disnake.ui.MediaGalleryItem(media="attachment://qrcode.png")
                    )
                )

            if buttons:
                container_children.append(disnake.ui.ActionRow(*buttons))

            await inter.followup.send(
                components=[
                    disnake.ui.Container(*container_children, **container_kwargs),
                ],
                files=files or None,
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True,
            )


def setup(bot: commands.Bot):
    bot.add_cog(GerarPagamentoCommand(bot))
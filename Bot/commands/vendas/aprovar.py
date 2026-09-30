import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms


class AprovarPagamentoCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="aprovar",
        description="Aprova o pagamento do carrinho atual (somente dentro de um carrinho)",
        default_member_permissions=disnake.Permissions(administrator=True),
    )
    async def aprovar(self, inter: disnake.ApplicationCommandInteraction):
        if not await perms.check(inter.author.id):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando!",
                ephemeral=True,
            )
            return

        # Verificar se o comando foi usado dentro de uma thread
        if not isinstance(inter.channel, disnake.Thread):
            await inter.response.send_message(
                f"{emoji.wrong} Este comando só pode ser usado **dentro de um carrinho** (thread de compra)!",
                ephemeral=True,
            )
            return

        await inter.response.defer(ephemeral=True)

        thread_id = inter.channel.id
        cart_id = str(thread_id)

        # Buscar o carrinho correspondente a esta thread
        loja_data = db.get_document("loja_data") or {}
        cart = loja_data.get("carts", {}).get(cart_id)

        if not cart:
            await inter.followup.send(
                f"{emoji.wrong} Nenhum carrinho encontrado nesta thread!",
                ephemeral=True,
            )
            return

        status = cart.get("status")

        if status == "approved":
            await inter.followup.send(
                f"{emoji.wrong} Este carrinho já foi aprovado!",
                ephemeral=True,
            )
            return

        if status == "cancelled":
            await inter.followup.send(
                f"{emoji.wrong} Este carrinho foi cancelado e não pode ser aprovado!",
                ephemeral=True,
            )
            return

        if status not in ("pending", "cart"):
            await inter.followup.send(
                f"{emoji.wrong} Status inválido para aprovação: `{status}`",
                ephemeral=True,
            )
            return

        # ── APROVAÇÃO MANUAL ──────────────────────────────────────────────────
        # Marcar status como "cancelled" no banco para que nenhum monitor
        # de pagamento externo (Amethys Wallet, Pix, etc.) processe este
        # carrinho e mova dinheiro real. O bot considera aprovado internamente.
        # IMPORTANTE: NÃO chamar nenhuma API de pagamento aqui.
        loja_data["carts"][cart_id]["status"] = "cancelled"
        db.save_document("loja_data", loja_data)

        # Processar aprovação pelo fluxo padrão do checkout
        # _handle_payment_approved redefine status → "approved" internamente,
        # processa entrega, registra compra, atribui cargos e envia logs.
        from modules.loja.cart.checkout import _handle_payment_approved
        await _handle_payment_approved(cart_id, self.bot)

        await inter.followup.send(
            f"{emoji.correct} Pagamento aprovado manualmente! O carrinho foi processado.",
            ephemeral=True,
        )


def setup(bot: commands.Bot):
    bot.add_cog(AprovarPagamentoCommand(bot))
import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji
from .modals import CreateFieldModal, EditFieldModal, EditInstructionsModal
from .configurar import ConfigurarCampo
from ..cog import GerenciarCamposCategorias


class FieldActions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        if custom_id.startswith("Loja_CriarCampo:"):
            product_id = custom_id.split(":", 1)[1]
            modal = CreateFieldModal(product_id)
            await inter.response.send_modal(modal)
            return

        if custom_id.startswith("Loja_CriarCampoCategoria:"):
            _, rest = custom_id.split(":", 1)
            product_id, category_id = rest.split(":", 1)
            modal = CreateFieldModal(product_id, category_id=category_id)
            await inter.response.send_modal(modal)
            return

        if custom_id.startswith("Loja_EditarCampo:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)

            # Campos boost não permitem edição do nome
            products = db.get_document("loja_products") or {}
            campo = (products.get(product_id, {}).get("campos") or {}).get(field_id, {})
            if campo.get("boost_field"):
                await inter.response.send_message(
                    f" {emoji.alert} Campos de boost têm nome fixo e não podem ser renomeados.\n"
                    f"-# Para alterar o preço ou outras configurações, use as opções disponíveis no painel do campo.",
                    ephemeral=True,
                )
                return

            modal = EditFieldModal(product_id, field_id)
            await inter.response.send_modal(modal)
            return

        if custom_id.startswith("Loja_ApagarCampo:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            await message.wait(inter, send=False)

            products = db.get_document("loja_products")
            product = products.get(product_id) or {}
            campos = product.get("campos") or {}
            if field_id in campos:
                campos.pop(field_id, None)
                product["campos"] = campos
                products[product_id] = product
                db.save_document("loja_products", products)
                
                # Sincronizar silenciosamente todas as mensagens do produto
                from modules.loja.products.product.edit import sync_product_messages_silently
                await sync_product_messages_silently(inter.client, product_id)

            mode = db.get_document("custom_mode").get("mode")
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, product_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)

        if custom_id.startswith("Loja_EstoqueCampo:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            from .estoque.visualizar import panel as stock_panel
            mode = db.get_document("custom_mode").get("mode")
            panel_data = stock_panel(inter, product_id, field_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_CargosCampo:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            from .cargos.configurar import ConfigurarCargosCampo
            mode = db.get_document("custom_mode").get("mode")
            panel_data = ConfigurarCargosCampo.panel(inter, product_id, field_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_CondicoesCampo:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            from .condicoes.modals import CondicoesModal
            await inter.response.send_modal(CondicoesModal(product_id, field_id))
            return

        if custom_id.startswith("Loja_InstrucoesCampo:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            modal = EditInstructionsModal(product_id, field_id)
            await inter.response.send_modal(modal)
            return

        if custom_id.startswith("Loja_ToggleSubscription:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            await message.wait(inter, send=False)

            products = db.get_document("loja_products")
            product = products.get(product_id) or {}
            campos = product.get("campos") or {}
            field = campos.get(field_id)
            if field:
                is_sub = field.get("is_subscription", False)
                field["is_subscription"] = not is_sub
                field["updated_at"] = int(disnake.utils.utcnow().timestamp())
                campos[field_id] = field
                product["campos"] = campos
                products[product_id] = product
                db.save_document("loja_products", products)
                
                from modules.loja.products.product.edit import sync_product_messages_silently
                await sync_product_messages_silently(inter.client, product_id)

            mode = db.get_document("custom_mode").get("mode")
            panel_data = ConfigurarCampo.panel(inter, product_id, field_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)
            return


def setup(bot: commands.Bot):
    bot.add_cog(FieldActions(bot))


def _get_boost_linked_product_id() -> str | None:
    """Retorna o product_id que já tem boost vinculado (somente 1 permitido globalmente)."""
    products = db.get_document("loja_products") or {}
    for pid, prod in products.items():
        campos = prod.get("campos") or {}
        if any(c.get("boost_field") for c in campos.values()):
            return pid
    return None


class BoostFieldActions(commands.Cog):
    """Handlers para campos de boost vinculados ao sistema Joiner."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""

        # ── Vincular Boost ────────────────────────────────────────────────────
        if custom_id.startswith("Loja_VincularBoost:"):
            product_id = custom_id.split(":", 1)[1]
            await inter.response.defer(ephemeral=True)

            # Restrição: somente 1 produto pode ter boost vinculado
            already_linked = _get_boost_linked_product_id()
            if already_linked and already_linked != product_id:
                products = db.get_document("loja_products") or {}
                other_name = (products.get(already_linked) or {}).get("name", already_linked)
                await inter.followup.send(
                    f"{emoji.alert} Já existe um produto com Boost vinculado: **{other_name}**\n"
                    f"-# Desvincule-o antes de vincular em outro produto.",
                    ephemeral=True,
                )
                return

            from .configurar import BOOST_FIELD_VARIANTS
            import time, secrets

            products = db.get_document("loja_products") or {}
            product = products.get(product_id)
            if not product:
                await inter.followup.send("Produto não encontrado.", ephemeral=True)
                return

            campos = product.setdefault("campos", {})

            # Checar se já tem boost neste produto
            existing_boost = [c for c in campos.values() if c.get("boost_field")]
            if existing_boost:
                await inter.followup.send(
                    f"{emoji.alert} Este produto já possui `{len(existing_boost)}` campos de boost vinculados.",
                    ephemeral=True,
                )
                return

            now = int(time.time())
            created = 0
            for (nome, boosts, periodicidade) in BOOST_FIELD_VARIANTS:
                field_id = "boost_" + secrets.token_hex(4)
                while field_id in campos:
                    field_id = "boost_" + secrets.token_hex(4)
                campos[field_id] = {
                    "id": field_id,
                    "name": nome,
                    "price": 0.0,
                    "boost_field": True,
                    "boost_count": boosts,
                    "boost_period": periodicidade,
                    "boost_disabled": False,
                    "created_at": now,
                    "updated_at": now,
                }
                created += 1

            product["campos"] = campos
            products[product_id] = product
            db.save_document("loja_products", products)

            try:
                from modules.loja.products.product.edit import sync_product_messages_silently
                await sync_product_messages_silently(inter.client, product_id)
            except Exception:
                pass

            mode = db.get_document("custom_mode").get("mode")
            from ..cog import GerenciarCamposCategorias
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, product_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)

            await inter.followup.send(
                f"{emoji.boost} **{created} campos de boost criados!**\n"
                f"-# 6 variantes mensais + 6 variantes trimestrais.\n"
                f"-# Configure o preço de cada campo e use os toggles Mensal/Trimestral para ativar/desativar em massa.",
                ephemeral=True,
            )

        # ── Desvincular Boost: apagar todos os campos boost ───────────────────
        elif custom_id.startswith("Loja_DesvincularBoost:"):
            product_id = custom_id.split(":", 1)[1]
            await inter.response.defer(ephemeral=True)

            products = db.get_document("loja_products") or {}
            product = products.get(product_id)
            if not product:
                await inter.followup.send("Produto não encontrado.", ephemeral=True)
                return

            campos = product.get("campos") or {}
            boost_ids = [fid for fid, c in campos.items() if c.get("boost_field")]
            for fid in boost_ids:
                campos.pop(fid, None)

            product["campos"] = campos
            products[product_id] = product
            db.save_document("loja_products", products)

            try:
                from modules.loja.products.product.edit import sync_product_messages_silently
                await sync_product_messages_silently(inter.client, product_id)
            except Exception:
                pass

            mode = db.get_document("custom_mode").get("mode")
            from ..cog import GerenciarCamposCategorias
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, product_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)

            await inter.followup.send(
                f"{emoji.delete} **{len(boost_ids)} campos de boost removidos.** Produto desvinculado.",
                ephemeral=True,
            )

        # ── Toggle período em massa (Mensal / Trimestral) ─────────────────────
        elif custom_id.startswith("Loja_ToggleBoostPeriodo:"):
            _, rest = custom_id.split(":", 1)
            product_id, period = rest.split(":", 1)  # period = "mensal" | "trimestral"

            products = db.get_document("loja_products") or {}
            product = products.get(product_id, {})
            campos = product.get("campos") or {}

            # Verificar estado atual: se algum do período está ativo → desativar todos; senão ativar todos
            period_fields = {fid: c for fid, c in campos.items()
                             if c.get("boost_field") and c.get("boost_period") == period}
            any_active = any(not c.get("boost_disabled") for c in period_fields.values())
            new_disabled = any_active  # se algum ativo → vai desativar todos; senão ativa todos

            import time as _t
            now = int(_t.time())
            for fid in period_fields:
                campos[fid]["boost_disabled"] = new_disabled
                campos[fid]["updated_at"] = now

            product["campos"] = campos
            products[product_id] = product
            db.save_document("loja_products", products)

            try:
                from modules.loja.products.product.edit import sync_product_messages_silently
                await sync_product_messages_silently(inter.client, product_id)
            except Exception:
                pass

            mode = db.get_document("custom_mode").get("mode")
            from ..cog import GerenciarCamposCategorias
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, product_id)
            if mode == "embed":
                await (embed_message).wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await (message).wait(inter, send=False)
                await inter.edit_original_message(**panel_data)

            period_label = "Mensal" if period == "mensal" else "Trimestral"
            status_label = "desativados" if new_disabled else "ativados"
            await inter.followup.send(
                f"{'{emoji.wrong}' if new_disabled else '{emoji.correct}'} Todos os campos **{period_label}** ({len(period_fields)}) foram {status_label}.",
                ephemeral=True,
            )

        # ── Toggle campo boost individual ─────────────────────────────────────
        elif custom_id.startswith("Loja_ToggleBoostCampo:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)

            products = db.get_document("loja_products") or {}
            product = products.get(product_id, {})
            campo = (product.get("campos") or {}).get(field_id)
            if not campo:
                await inter.response.send_message("Campo não encontrado.", ephemeral=True)
                return

            campo["boost_disabled"] = not campo.get("boost_disabled", False)
            import time as _t2
            campo["updated_at"] = int(_t2.time())
            product["campos"][field_id] = campo
            products[product_id] = product
            db.save_document("loja_products", products)

            try:
                from modules.loja.products.product.edit import sync_product_messages_silently
                await sync_product_messages_silently(inter.client, product_id)
            except Exception:
                pass

            mode = db.get_document("custom_mode").get("mode")
            from .configurar import ConfigurarCampo
            panel_data = ConfigurarCampo.panel(inter, product_id, field_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)

            status = "desativado" if campo["boost_disabled"] else "ativado"
            await inter.followup.send(
                f"{'{emoji.wrong}' if campo['boost_disabled'] else '{emoji.correct}'} Campo **{campo.get('name')}** {status}.",
                ephemeral=True,
            )


def setup_boost(bot: commands.Bot):
    bot.add_cog(BoostFieldActions(bot))
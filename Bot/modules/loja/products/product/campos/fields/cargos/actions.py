import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from .configurar import ConfigurarCargosCampo, _ensure_field_roles_structure


class DuracaoCargoModal(disnake.ui.Modal):
    def __init__(self, product_id: str, field_id: str, duracao_atual: int):
        self.product_id = product_id
        self.field_id = field_id

        components = [
            disnake.ui.TextInput(
                label="Duração do cargo (em minutos)",
                placeholder="Deixe em branco ou 0 para permanente",
                custom_id="duracao_minutos",
                value=str(duracao_atual) if duracao_atual else "",
                required=False,
                max_length=10,
            )
        ]
        super().__init__(
            title="Duração do Cargo",
            custom_id=f"DuracaoCargoModal:{product_id}:{field_id}",
            components=components,
        )



class CargosCampoActions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        if custom_id.startswith("Loja_CargosCampo_Voltar:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            from ..configurar import ConfigurarCampo
            panel_data = ConfigurarCampo.panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)

        elif custom_id.startswith("Loja_CargosCampo_Duracao:"):
            _, product_id, field_id = custom_id.split(":", 2)
            products = db.get_document("loja_products")
            product = (products or {}).get(product_id) or {}
            field = (product.get("campos") or {}).get(field_id)
            if not field:
                return

            field = _ensure_field_roles_structure(field)
            cargos = field.get("cargos", {})
            duracao_atual = cargos.get("duracao_minutos")

            modal = DuracaoCargoModal(product_id, field_id, duracao_atual)
            await inter.response.send_modal(modal)

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id or ""
        if custom_id.startswith("DuracaoCargoModal:"):
            _, product_id, field_id = custom_id.split(":", 2)
            duracao_str = inter.text_values["duracao_minutos"]

            try:
                duracao_minutos = int(duracao_str) if duracao_str and duracao_str.isdigit() else 0
            except ValueError:
                duracao_minutos = 0

            products = db.get_document("loja_products")
            product = (products or {}).get(product_id) or {}
            field = (product.get("campos") or {}).get(field_id)
            if not field:
                return

            field = _ensure_field_roles_structure(field)
            cargos = field.get("cargos", {})

            if duracao_minutos > 0:
                cargos["duracao_minutos"] = duracao_minutos
            elif "duracao_minutos" in cargos:
                del cargos["duracao_minutos"]

            field["cargos"] = cargos
            product["campos"][field_id] = field
            products[product_id] = product
            db.save_document("loja_products", products)

            mode = db.get_document("custom_mode").get("mode")
            panel_data = ConfigurarCargosCampo.panel(inter, product_id, field_id)

            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        if custom_id.startswith("Loja_CargosCampo_Adicionar:") or custom_id.startswith("Loja_CargosCampo_Remover:") or custom_id.startswith("Loja_CargosCampo_Proibidos:"):
            # Defer IMEDIATAMENTE antes de qualquer operação
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            
            action, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)

            products = db.get_document("loja_products")
            product = (products or {}).get(product_id) or {}
            campos = product.get("campos") or {}
            field = campos.get(field_id)
            if not field:
                return

            cargos = field.get("cargos") or {}
            add_list = cargos.get("adicionar") or []
            rem_list = cargos.get("remover") or []
            forbidden_list = cargos.get("proibidos") or []

            # Convert selected values to int list
            selected = [int(v) for v in (inter.values or [])]

            if action.endswith("Adicionar"):
                add_list = selected
            elif action.endswith("Remover"):
                rem_list = selected
            elif action.endswith("Proibidos"):
                forbidden_list = selected

            cargos = {"adicionar": add_list, "remover": rem_list, "proibidos": forbidden_list}
            field["cargos"] = cargos
            field["updated_at"] = int(disnake.utils.utcnow().timestamp())
            campos[field_id] = field
            product["campos"] = campos
            info = product.get("info") or {}
            info["updated_at"] = int(disnake.utils.utcnow().timestamp())
            product["info"] = info
            products[product_id] = product
            db.save_document("loja_products", products)
            
            # Sincronizar silenciosamente todas as mensagens do produto
            from modules.loja.products.product.edit import sync_product_messages_silently
            await sync_product_messages_silently(inter.client, product_id)

            panel_data = ConfigurarCargosCampo.panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)


def setup(bot: commands.Bot):
    bot.add_cog(CargosCampoActions(bot))



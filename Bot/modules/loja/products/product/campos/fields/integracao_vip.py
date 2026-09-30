import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils
from functions.loja_products import container_kwargs_for_product, embed_kwargs_for_product

class IntegracaoVIPPanel:
    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return IntegracaoVIPPanel._panel_embed(inter, product_id, field_id)
        return IntegracaoVIPPanel._panel_components(inter, product_id, field_id)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id) or {}
        
        integracao = field.get("integracao_vip") or {}
        familia_ativa = integracao.get("familia", False)
        tempcall_ativa = integracao.get("tempcall", False)

        container_kwargs = container_kwargs_for_product(product)
        product_name = product.get("name") or product_id
        field_name = field.get("name") or field_id

        header_text = f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > {product_name} > {field_name} > **Integração VIP**"
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(header_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Vincule o sistema de VIP a outras funcionalidades do bot."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Sistema de Família",
                        emoji=emoji.group,
                        style=disnake.ButtonStyle.green if familia_ativa else disnake.ButtonStyle.grey,
                        custom_id=f"Loja_ToggleVIPIntegracao:{product_id}:{field_id}:familia"
                    ),
                    disnake.ui.Button(
                        label="Sistema de Temp Call",
                        emoji=emoji.voice,
                        style=disnake.ButtonStyle.green if tempcall_ativa else disnake.ButtonStyle.grey,
                        custom_id=f"Loja_ToggleVIPIntegracao:{product_id}:{field_id}:tempcall"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_IntegracaoVIP_Voltar:{product_id}:{field_id}")),
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id) or {}
        
        integracao = field.get("integracao_vip") or {}
        familia_ativa = integracao.get("familia", False)
        tempcall_ativa = integracao.get("tempcall", False)

        embed_kwargs = embed_kwargs_for_product(product)
        product_name = product.get("name") or product_id
        field_name = field.get("name") or field_id

        desc = (
            f"-# Painel > Loja > {product_name} > {field_name} > **Integração VIP**\n\n"
            f"Vincule o sistema de VIP a outras funcionalidades do bot.\n\n"
            f"-# Sistema de Família: {'`Ativo`' if familia_ativa else '`Desativado`'}\n"
            f"-# Sistema de Temp Call: {'`Ativo`' if tempcall_ativa else '`Desativado`'}\n"
        )

        embed = disnake.Embed(description=desc, **embed_kwargs)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Sistema de Família",
                    emoji=emoji.group,
                    style=disnake.ButtonStyle.green if familia_ativa else disnake.ButtonStyle.grey,
                    custom_id=f"Loja_ToggleVIPIntegracao:{product_id}:{field_id}:familia"
                ),
                disnake.ui.Button(
                    label="Sistema de Temp Call",
                    emoji=emoji.voice,
                    style=disnake.ButtonStyle.green if tempcall_ativa else disnake.ButtonStyle.grey,
                    custom_id=f"Loja_ToggleVIPIntegracao:{product_id}:{field_id}:tempcall"
                )
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_IntegracaoVIP_Voltar:{product_id}:{field_id}")),
        ]
        return {"embed": embed, "components": components}

class IntegracaoVIPActions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        
        if custom_id.startswith("Loja_IntegracaoVIP:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            
            panel_data = IntegracaoVIPPanel.panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_IntegracaoVIP_Voltar:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            
            from .configurar import ConfigurarCampo
            panel_data = ConfigurarCampo.panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_ToggleVIPIntegracao:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id, system = rest.split(":", 2)
            await message.wait(inter, send=False)

            products = db.get_document("loja_products")
            product = products.get(product_id) or {}
            campos = product.get("campos") or {}
            field = campos.get(field_id)
            if field:
                integracao = field.setdefault("integracao_vip", {})
                integracao[system] = not integracao.get(system, False)
                field["updated_at"] = int(disnake.utils.utcnow().timestamp())
                campos[field_id] = field
                product["campos"] = campos
                products[product_id] = product
                db.save_document("loja_products", products)

            mode = db.get_document("custom_mode").get("mode")
            panel_data = IntegracaoVIPPanel.panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

def setup(bot: commands.Bot):
    bot.add_cog(IntegracaoVIPActions(bot))

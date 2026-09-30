import disnake

from functions.database import database as db
from functions.message import message, embed_message


class CondicoesModal(disnake.ui.Modal):
    def __init__(self, product_id: str, field_id: str):
        self.product_id = product_id
        self.field_id = field_id

        products = db.get_document("loja_products")
        product = (products or {}).get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id) or {}
        cond = field.get("condicoes") or {}

        vmin = "" if cond.get("valorMin") in (None, "") else str(cond.get("valorMin"))
        vmax = "" if cond.get("valorMax") in (None, "") else str(cond.get("valorMax"))
        qmin = "" if cond.get("quantidadeMin") in (None, "") else str(cond.get("quantidadeMin"))
        qmax = "" if cond.get("quantidadeMax") in (None, "") else str(cond.get("quantidadeMax"))

        components = [
            disnake.ui.Label(
                text="Valor mínimo (BRL)",
                component=disnake.ui.TextInput(
                    custom_id="valuemin",
                    placeholder="Ex.: 10.00",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=15,
                    value=vmin,
                ),
                description="Valor mínimo em reais para comprar este campo.",
            ),
            disnake.ui.Label(
                text="Valor máximo (BRL)",
                component=disnake.ui.TextInput(
                    custom_id="valuemax",
                    placeholder="Ex.: 1000.00",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=15,
                    value=vmax,
                ),
                description="Valor máximo em reais para comprar este campo.",
            ),
            disnake.ui.Label(
                text="Quantidade mínima",
                component=disnake.ui.TextInput(
                    custom_id="quantidademin",
                    placeholder="Ex.: 1",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=10,
                    value=qmin,
                ),
                description="Quantidade mínima para comprar.",
            ),
            disnake.ui.Label(
                text="Quantidade máxima",
                component=disnake.ui.TextInput(
                    custom_id="quantidademax",
                    placeholder="Ex.: 100",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=10,
                    value=qmax,
                ),
                description="Quantidade máxima para comprar.",
            ),
        ]

        super().__init__(title="Gerenciar Condições", components=components, custom_id=f"condicoes_modal:{product_id}:{field_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        valores = inter.resolved_values
        
        # Limites máximos para evitar overflow do MongoDB (8 bytes = 2^63-1)
        MAX_FLOAT = 999999999.99  # Limite seguro para valores monetários
        MAX_INT = 2147483647      # Limite seguro para inteiros (2^31-1)
        
        # Parse values with graceful fallback and validation
        def _to_float(v):
            if v in (None, ""):
                return None
            try:
                # Substituir vírgula por ponto
                v_str = str(v).replace(",", ".").strip()
                value = float(v_str)
                # Validar limites
                if value < 0:
                    return 0.0
                if value > MAX_FLOAT:
                    return MAX_FLOAT
                return round(value, 2)  # Arredondar para 2 casas decimais
            except Exception:
                return None
                
        def _to_int(v):
            if v in (None, ""):
                return None
            try:
                value = int(float(str(v).replace(",", ".").strip()))
                # Validar limites
                if value < 0:
                    return 0
                if value > MAX_INT:
                    return MAX_INT
                return value
            except Exception:
                return None

        valuemin = _to_float(valores.get("valuemin"))
        valuemax = _to_float(valores.get("valuemax"))
        quantidademin = _to_int(valores.get("quantidademin"))
        quantidademax = _to_int(valores.get("quantidademax"))
        
        # Validar lógica: mínimo não pode ser maior que máximo
        if valuemin is not None and valuemax is not None and valuemin > valuemax:
            valuemin, valuemax = valuemax, valuemin  # Trocar valores
        if quantidademin is not None and quantidademax is not None and quantidademin > quantidademax:
            quantidademin, quantidademax = quantidademax, quantidademin  # Trocar valores

        products = db.get_document("loja_products")
        product = (products or {}).get(self.product_id) or {}
        campos = product.get("campos") or {}
        field = campos.get(self.field_id) or {}

        field["condicoes"] = {"valorMin": valuemin, "valorMax": valuemax, "quantidadeMin": quantidademin, "quantidadeMax": quantidademax}
        field["updated_at"] = int(disnake.utils.utcnow().timestamp())
        campos[self.field_id] = field
        product["campos"] = campos
        products[self.product_id] = product
        db.save_document("loja_products", products)
        
        # Sincronizar silenciosamente todas as mensagens do produto
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(inter.client, self.product_id)

        from ..configurar import ConfigurarCampo
        panel_data = ConfigurarCampo.panel(inter, self.product_id, self.field_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)



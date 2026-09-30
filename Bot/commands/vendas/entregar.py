import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms
from functions.utils import utils
from modules.loja.cart.stock_manager import StockManager
from modules.loja.cart.purchase_manager import PurchaseManager
from typing import Optional, List


class PaginatedFieldSelectView(disnake.ui.View):
    def __init__(self, all_options: List[disnake.SelectOption], callback_func, temp_data):
        super().__init__(timeout=300)
        self.all_options = all_options
        self.callback_func = callback_func
        self.temp_data = temp_data
        self.page = 0
        self.items_per_page = 25
        self.total_pages = (len(all_options) - 1) // self.items_per_page + 1
        
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        # Calcular fatia de opções para a página atual
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_options = self.all_options[start:end]
        
        # Select Menu
        select = disnake.ui.StringSelect(
            placeholder=f"Selecione o campo (Página {self.page + 1}/{self.total_pages})",
            options=current_options,
            custom_id=f"field_select_{self.page}",
            min_values=1,
            max_values=1
        )
        select.callback = self.select_field
        self.add_item(select)
        
        # Botões de navegação (apenas se houver mais de 1 página)
        if self.total_pages > 1:
            prev_button = disnake.ui.Button(
                label="Anterior",
                style=disnake.ButtonStyle.secondary,
                disabled=(self.page == 0),
                custom_id="prev_page"
            )
            prev_button.callback = self.prev_page
            self.add_item(prev_button)
            
            next_button = disnake.ui.Button(
                label="Próximo",
                style=disnake.ButtonStyle.secondary,
                disabled=(self.page == self.total_pages - 1),
                custom_id="next_page"
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

    async def prev_page(self, inter: disnake.MessageInteraction):
        if self.page > 0:
            self.page -= 1
            self.update_components()
            await inter.response.edit_message(view=self)

    async def next_page(self, inter: disnake.MessageInteraction):
        if self.page < self.total_pages - 1:
            self.page += 1
            self.update_components()
            await inter.response.edit_message(view=self)

    async def select_field(self, inter: disnake.MessageInteraction):
        # O callback é anexado dinamicamente, mas precisamos pegar o select correto
        select = [item for item in self.children if isinstance(item, disnake.ui.StringSelect)][0]
        
        await inter.response.defer(ephemeral=True)
        
        field_id = select.values[0]
        if field_id == "__none__":
            await inter.followup.send(
                f"{emoji.wrong} Este produto não possui campos selecionáveis.",
                ephemeral=True
            )
            return
            
        product_id = self.temp_data["product_id"]
        product_data = self.temp_data["product_data"]
        quantidade = self.temp_data["quantidade"]
        membro = self.temp_data["membro"]
        
        campos = product_data.get("campos", {})
        campo_data = campos.get(field_id)
        
        if not campo_data:
            await inter.followup.send(
                f"{emoji.wrong} Campo não encontrado!",
                ephemeral=True
            )
            return
        
        # Processar entrega
        delivered_by = self.temp_data.get("inter_author")
        await self.callback_func(
            inter,
            product_id,
            product_data,
            field_id,
            campo_data,
            quantidade,
            membro,
            delivered_by
        )


class EntregarCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def product_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str):
        """Autocomplete para produtos"""
        products = db.get_document("loja_products") or {}
        if not products:
            return []
            
        string = string.lower()
        choices = []
        
        for product_id, product_data in products.items():
            if not isinstance(product_data, dict):
                continue
                
            name = product_data.get("name", "Sem nome")
            if string in name.lower():
                # Limitar tamanho do nome para caber no autocomplete
                display_name = name[:100]
                choices.append(disnake.OptionChoice(name=display_name, value=str(product_id)))
                
            if len(choices) >= 25:
                break
                
        return choices

    async def _process_delivery(self, inter, product_id, product_data, campo_id, campo_data, quantidade, membro, delivered_by=None):
        """Processa a entrega do produto"""
        # Obter autor da entrega
        if delivered_by is None:
            delivered_by = inter.author if hasattr(inter, 'author') else None
        
        # Verificar estoque
        stock_items = StockManager.get_stock_items(product_id, campo_id, quantidade)
        
        if not stock_items:
            await inter.followup.send(
                f"{emoji.wrong} Não há estoque suficiente para entregar `{quantidade}` unidade(s)!",
                ephemeral=True
            )
            return
        
        # Enviar itens para o membro
        items_text = "\n".join(stock_items)
        
        delivered_by_mention = delivered_by.mention if delivered_by else "Sistema"
        
        campo_name = campo_data.get('name') if campo_data else "Padrão"
        
        # Obter modo (components = container, embed = embed)
        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        
        # Obter cor primária se disponível
        color_data = db.get_document("custom_colors") or {}
        primary_color_hex = color_data.get("primary")
        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except:
                color = disnake.Color.green().value
        
        # Tentar enviar DM
        dm_sent = False
        dm_closed = False
        
        try:
            if mode == "embed":
                # Modo Embed
                embed = disnake.Embed(
                    title=f"{emoji.cart} Entrega Manual",
                    description=(
                        f"{emoji.cardbox} **Produto:** `{product_data.get('name')}`\n"
                        f"{emoji.route} **Campo:** `{campo_name}`\n"
                        f"{emoji.coupon} **Quantidade:** `{quantidade}`\n"
                        f"{emoji.member} **Entregue por:** {delivered_by_mention}"
                    ),
                    color=color if color else disnake.Color.green()
                )
                embed.add_field(
                    name=f"{emoji.cardbox} Seus Itens",
                    value=f"```\n{items_text}\n```",
                    inline=False
                )
                
                await membro.send(embed=embed)
                dm_sent = True
            else:
                # Modo Container (components)
                container_kwargs = {}
                if color:
                    container_kwargs["accent_colour"] = disnake.Colour(color)
                
                container_items = [
                    disnake.ui.TextDisplay(
                        f"# {emoji.cart}\n-# **Entrega Manual**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"{emoji.cardbox} **Produto:** `{product_data.get('name')}`\n"
                        f"{emoji.route} **Campo:** `{campo_name}`\n"
                        f"{emoji.coupon} **Quantidade:** `{quantidade}`\n"
                        f"{emoji.member} **Entregue por:** {delivered_by_mention}"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"### {emoji.cardbox} Seus Itens\n```\n{items_text}\n```"
                    )
                ]
                
                container = disnake.ui.Container(
                    *container_items,
                    **container_kwargs
                )
                
                await membro.send(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
                dm_sent = True
                
        except disnake.Forbidden:
            # DM fechada ou bloqueada
            dm_closed = True
            dm_sent = False
        except Exception:
            # Outro erro
            dm_sent = False
        
        # Registrar compra manual (valor 0 pois foi entrega manual)
        PurchaseManager.register_purchase(
            user_id=membro.id,
            product_id=product_id,
            product_name=product_data.get("name"),
            field_id=campo_id,
            field_name=campo_name,
            quantity=quantidade,
            unit_price=0,
            total_price=0,
            discount_amount=0,
            final_price=0,
            payment_method="manual_delivery",
            items_received=stock_items,
            metadata={
                "delivered_by": delivered_by.id if delivered_by else None,
                "delivery_type": "manual_command"
            }
        )
        
        # Responder
        if dm_sent:
            await inter.followup.send(
                f"{emoji.correct} **`{quantidade}`** unidade(s) de **`{product_data.get('name')}`** "
                f"foram entregues para {membro.mention} com sucesso! {emoji.correct}",
                ephemeral=True
            )
        elif dm_closed:
            await inter.followup.send(
                f"{emoji.warn} **Atenção!** Os itens foram removidos do estoque, mas **não foi possível "
                f"enviar a DM** para {membro.mention} porque as **mensagens diretas estão fechadas**.\n\n"
                f"{emoji.information} **Itens entregues:**\n"
                f"```\n{items_text}\n```\n\n"
                f"{emoji.warn} **Aviso:** O usuário precisa abrir as DMs para receber entregas automáticas.",
                ephemeral=True
            )
        else:
            await inter.followup.send(
                f"{emoji.warn} Os itens foram removidos do estoque, mas não foi possível "
                f"enviar DM para {membro.mention}.\n\n"
                f"{emoji.information} **Itens entregues:**\n"
                f"```\n{items_text}\n```",
                ephemeral=True
            )

    @commands.slash_command(
        name="entregar",
        description="Entrega manual de produtos para um membro",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def entregar(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        produto: str = commands.Param(autocomplete=product_autocomplete),
        membro: disnake.Member = commands.Param(),
        quantidade: int = commands.Param(default=1, ge=1)
    ):
        # Verificar permissões
        if not await perms.check(inter.author.id):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando!",
                ephemeral=True
            )
            return
        
        await inter.response.defer(ephemeral=True)
        
        # Carregar produto
        products = db.get_document("loja_products")
        if not produto or produto not in products:
            await inter.followup.send(
                f"{emoji.wrong} Produto não encontrado!",
                ephemeral=True
            )
            return
            
        product_data = products[produto]
        
        # Verificar se tem campos
        campos = product_data.get("campos", {})
        
        # Se tiver campos, mostrar select
        if campos:
            # Criar opções do select de campos
            field_options = []
            for field_id, field_info in campos.items():
                # Validar field_id
                field_id_str = str(field_id).strip()
                if not field_id_str:
                    continue
                # Validar field_info
                if not isinstance(field_info, dict):
                    continue
                field_name = field_info.get("name", "Sem nome") or "Sem nome"
                display_name = field_name[:80] if len(field_name) > 80 else field_name
                try:
                    field_options.append(
                        disnake.SelectOption(
                            label=display_name,
                            value=field_id_str,
                            description=f"Campo do produto"
                        )
                    )
                except Exception:
                    continue
            
            # Validar e garantir que há pelo menos 1 opção válida
            valid_field_options = []
            for opt in field_options:
                if isinstance(opt, disnake.SelectOption):
                    # Validar que a opção tem label e value válidos
                    if opt.label and opt.value and len(str(opt.label).strip()) > 0 and len(str(opt.value).strip()) > 0:
                        valid_field_options.append(opt)
            
            # Se não houver opções válidas, usar placeholder
            if not valid_field_options:
                 valid_field_options = [
                    disnake.SelectOption(
                        label="Nenhum campo disponível",
                        value="__none__",
                        description="Este produto não possui campos selecionáveis"
                    )
                ]
            
             # Criar e mostrar view de seleção de campo (paginada)
            try:
                view = PaginatedFieldSelectView(valid_field_options, self._process_delivery, {
                    "product_id": produto,
                    "product_data": product_data,
                    "quantidade": quantidade,
                    "membro": membro,
                    "inter_author": inter.author
                })
                
                await inter.followup.send(
                    f"{emoji.information} Este produto possui campo(s). Selecione o campo desejado:",
                    ephemeral=True,
                    view=view
                )
                return
            except Exception as view_error:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao criar seletor de campos: {str(view_error)}",
                    ephemeral=True
                )
                return

        # Se não tiver campos, processar entrega direta (campo padrão/único)
        await self._process_delivery(
            inter,
            produto,
            product_data,
            None, # campo_id
            None, # campo_data
            quantidade,
            membro,
            inter.author
        )


def setup(bot: commands.Bot):
    bot.add_cog(EntregarCommand(bot))
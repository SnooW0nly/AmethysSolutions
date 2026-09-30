import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from modules.loja.cart.purchase_manager import PurchaseManager
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import io
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg


class FilterModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Data Inicial (DD/MM/AAAA)",
                custom_id="start_date",
                placeholder="Ex: 01/01/2024",
                required=False,
                max_length=10
            ),
            disnake.ui.TextInput(
                label="Data Final (DD/MM/AAAA)",
                custom_id="end_date",
                placeholder="Ex: 31/12/2024",
                required=False,
                max_length=10
            ),
            disnake.ui.TextInput(
                label="ID do Produto (opcional)",
                custom_id="product_id",
                placeholder="Deixe vazio para todos os produtos",
                required=False
            ),
            disnake.ui.TextInput(
                label="ID do Cliente (opcional)",
                custom_id="user_id",
                placeholder="Deixe vazio para todos os clientes",
                required=False
            )
        ]
        super().__init__(title="Filtrar Rendimentos", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        # Processar filtros
        filters = {}
        
        # Parse datas
        try:
            if inter.text_values.get("start_date"):
                start = datetime.strptime(inter.text_values["start_date"], "%d/%m/%Y")
                filters["start_date"] = start.timestamp()
            
            if inter.text_values.get("end_date"):
                end = datetime.strptime(inter.text_values["end_date"], "%d/%m/%Y")
                filters["end_date"] = end.timestamp()
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Formato de data inválido! Use DD/MM/AAAA",
                ephemeral=True
            )
            return
        
        if inter.text_values.get("product_id"):
            filters["product_id"] = inter.text_values["product_id"]
        
        if inter.text_values.get("user_id"):
            filters["user_id"] = inter.text_values["user_id"]
        
        # Salvar filtros temporariamente
        await inter.response.defer(ephemeral=True)
        
        # Gerar relatório com filtros
        cog = inter.bot.get_cog("RendimentosSystem")
        if cog:
            await cog.generate_filtered_report(inter, filters)


class GraphPeriodModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Período em Dias",
                custom_id="period_days",
                placeholder="Ex: 7 (últimos 7 dias), 30, 365, etc.",
                required=True,
                max_length=4,
                min_length=1
            )
        ]
        super().__init__(title="Selecionar Período do Gráfico", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        # Validar período
        try:
            days = int(inter.text_values.get("period_days", "30"))
            if days <= 0:
                await inter.response.send_message(
                    f"{emoji.wrong} O período deve ser um número positivo!",
                    ephemeral=True
                )
                return
            if days > 3650:  # Máximo de 10 anos
                await inter.response.send_message(
                    f"{emoji.wrong} O período máximo é de 3650 dias (10 anos)!",
                    ephemeral=True
                )
                return
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Por favor, insira um número válido de dias!",
                ephemeral=True
            )
            return
        
        # Gerar gráfico com o período especificado
        await inter.response.defer(ephemeral=True)
        
        cog = inter.bot.get_cog("RendimentosSystem")
        if cog:
            await cog.generate_graph(inter, days)


class RendimentosSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener("on_button_click")
    async def rendimentos_button_listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("Rendimentos_"):
            return
        
        if inter.component.custom_id == "Rendimentos_Filter":
            await inter.response.send_modal(FilterModal())
        
        elif inter.component.custom_id == "Rendimentos_Graph":
            await inter.response.send_modal(GraphPeriodModal())
        
        elif inter.component.custom_id == "Rendimentos_Export":
            await self.export_data(inter)
    
    def panel(self, inter: disnake.Interaction) -> dict:
        """Painel principal de rendimentos"""
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            return self._panel_components(inter)
        return self._panel_embed(inter)
    
    def _panel_components(self, inter: disnake.Interaction) -> dict:
        # Obter estatísticas gerais
        stats = PurchaseManager.get_statistics()
        
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        # Calcular rendimento do mês atual
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1).timestamp()
        
        month_revenue = 0
        month_sales = 0
        all_purchases = PurchaseManager.get_all_purchases()
        
        for purchase in all_purchases:
            if purchase.get("timestamp", 0) >= month_start:
                month_revenue += purchase.get("pricing", {}).get("final_price", 0)
                month_sales += 1
        
        # Top produtos
        top_products_text = ""
        products_sorted = sorted(
            stats.get("products_sold", {}).items(),
            key=lambda x: x[1]["revenue"],
            reverse=True
        )[:3]
        
        for product_id, data in products_sorted:
            top_products_text += f"-# {emoji.arrow} **{data['name']}**: `R$ {data['revenue']:.2f} ({data['count']} vendas)`\n"
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > **Rendimentos**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{emoji.chart} **Estatísticas Gerais**\n"
                    f"-# {emoji.cart} **Total de Vendas:** `{stats.get('total_purchases', 0)}`\n"
                    f"-# {emoji.dollar} **Receita Total:** `R$ {stats.get('total_revenue', 0):.2f}`\n"
                    f"-# {emoji.members} **Clientes Únicos:** `{stats.get('unique_customers', 0)}`\n"
                    f"-# {emoji.cardbox} **Itens Vendidos:** `{stats.get('total_items_sold', 0)}`"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{emoji.calendar} **Este Mês**\n"
                    f"-# {emoji.cart} **Vendas:** `{month_sales}`\n"
                    f"-# {emoji.dollar} **Receita:** `R$ {month_revenue:.2f}`\n"
                    f"-# {emoji.chart} **Média por Venda:** `R$ {(month_revenue/month_sales if month_sales > 0 else 0):.2f}`"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{emoji.star} **Top Produtos**\n{top_products_text if top_products_text else '-# Nenhum produto vendido ainda'}"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Aplicar Filtros",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.double_check,
                        custom_id="Rendimentos_Filter"
                    ),
                    disnake.ui.Button(
                        label="Gerar Gráfico",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.chart,
                        custom_id="Rendimentos_Graph"
                    ),
                    disnake.ui.Button(
                        label="Exportar Dados",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.save,
                        custom_id="Rendimentos_Export"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="PainelInicial"
                )
            )
        ]}
    
    def _panel_embed(self, inter: disnake.Interaction):
        stats = PurchaseManager.get_statistics()
        
        # Estatísticas do mês
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        all_purchases = PurchaseManager.get_all_purchases()
        
        month_purchases = [
            p for p in all_purchases 
            if p.get("timestamp", 0) >= month_start.timestamp()
        ]
        month_sales = len(month_purchases)
        month_revenue = sum(p.get("pricing", {}).get("final_price", 0) for p in month_purchases)
        
        # Top produtos
        top_products_text = ""
        products_sorted = sorted(
            stats.get("products_sold", {}).items(),
            key=lambda x: x[1]["revenue"],
            reverse=True
        )[:3]
        
        for product_id, data in products_sorted:
            top_products_text += f"• **{data['name']}**: R$ {data['revenue']:.2f} ({data['count']} vendas)\n"
        
        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Rendimentos",
            description="Painel > **Rendimentos**",
            color=disnake.Color.from_rgb(0, 202, 164)
        )
        
        # Estatísticas Gerais
        embed.add_field(
            name=f"{emoji.chart} Estatísticas Gerais",
            value=(
                f"{emoji.cart} **Total de Vendas:** `{stats.get('total_purchases', 0)}`\n"
                f"{emoji.dollar} **Receita Total:** `R$ {stats.get('total_revenue', 0):.2f}`\n"
                f"{emoji.members} **Clientes Únicos:** `{stats.get('unique_customers', 0)}`\n"
                f"{emoji.cardbox} **Itens Vendidos:** `{stats.get('total_items_sold', 0)}`"
            ),
            inline=False
        )
        
        # Este Mês
        embed.add_field(
            name=f"{emoji.calendar} Este Mês",
            value=(
                f"{emoji.cart} **Vendas:** `{month_sales}`\n"
                f"{emoji.dollar} **Receita:** `R$ {month_revenue:.2f}`\n"
                f"{emoji.chart} **Média por Venda:** `R$ {(month_revenue/month_sales if month_sales > 0 else 0):.2f}`"
            ),
            inline=False
        )
        
        # Top Produtos
        embed.add_field(
            name=f"{emoji.star} Top Produtos",
            value=top_products_text if top_products_text else "Nenhum produto vendido ainda",
            inline=False
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Aplicar Filtros",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.double_check,
                    custom_id="Rendimentos_Filter"
                ),
                disnake.ui.Button(
                    label="Gerar Gráfico",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.chart,
                    custom_id="Rendimentos_Graph"
                ),
                disnake.ui.Button(
                    label="Exportar Dados",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.save,
                    custom_id="Rendimentos_Export"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="PainelInicial"
                )
            )
        ]
        
        return embed, components
    
    async def generate_graph(self, inter: disnake.Interaction, days: int = 30):
        """Gera gráfico de vendas"""
        # Obter dados do período especificado
        now = datetime.now()
        period_start = now - timedelta(days=days)
        
        all_purchases = PurchaseManager.get_all_purchases()
        
        # Agrupar por dia
        daily_data = {}
        for purchase in all_purchases:
            timestamp = purchase.get("timestamp", 0)
            if timestamp >= period_start.timestamp():
                date = datetime.fromtimestamp(timestamp).date()
                if date not in daily_data:
                    daily_data[date] = {"revenue": 0, "sales": 0}
                daily_data[date]["revenue"] += purchase.get("pricing", {}).get("final_price", 0)
                daily_data[date]["sales"] += 1
        
        if not daily_data:
            await inter.followup.send(
                f"{emoji.wrong} Não há dados suficientes para gerar o gráfico!",
                ephemeral=True
            )
            return
        
        # Preparar dados para o gráfico
        dates = sorted(daily_data.keys())
        revenues = [daily_data[date]["revenue"] for date in dates]
        sales = [daily_data[date]["sales"] for date in dates]
        
        # Criar gráfico
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f'Análise de Vendas - Últimos {days} dias', fontsize=16)
        
        # Gráfico de receita
        ax1.plot(dates, revenues, 'b-', linewidth=2, marker='o')
        ax1.fill_between(dates, revenues, alpha=0.3)
        ax1.set_ylabel('Receita (R$)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        # Gráfico de vendas
        ax2.bar(dates, sales, color='green', alpha=0.7)
        ax2.set_ylabel('Número de Vendas', fontsize=12)
        ax2.set_xlabel('Data', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        plt.tight_layout()
        
        # Salvar em buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        plt.close()
        
        # Enviar arquivo - sempre apenas a imagem, sem embed ou container
        file = disnake.File(buffer, filename="rendimentos_grafico.png")
        
        await inter.followup.send(file=file, ephemeral=True)
    
    async def export_data(self, inter: disnake.Interaction):
        """Exporta dados de vendas"""
        await inter.response.defer(ephemeral=True)
        
        all_purchases = PurchaseManager.get_all_purchases()
        
        # Preparar dados para exportação
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "total_purchases": len(all_purchases),
            "statistics": PurchaseManager.get_statistics(),
            "purchases": []
        }
        
        for purchase in all_purchases:
            export_data["purchases"].append({
                "id": purchase.get("purchase_id"),
                "date": datetime.fromtimestamp(purchase.get("timestamp", 0)).isoformat(),
                "user_id": purchase.get("user_id"),
                "product": purchase.get("product", {}).get("name"),
                "field": purchase.get("field", {}).get("name"),
                "quantity": purchase.get("quantity"),
                "unit_price": purchase.get("pricing", {}).get("unit_price"),
                "discount": purchase.get("pricing", {}).get("discount_amount"),
                "final_price": purchase.get("pricing", {}).get("final_price"),
                "payment_method": purchase.get("payment", {}).get("method")
            })
        
        # Criar arquivo TXT formatado
        txt_content = self._format_export_txt(export_data, all_purchases)
        buffer = io.BytesIO(txt_content.encode('utf-8'))
        buffer.seek(0)
        
        file = disnake.File(
            buffer,
            filename=f"rendimentos_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        await inter.followup.send(
            f"{emoji.correct} Dados exportados com sucesso!",
            file=file,
            ephemeral=True
        )
    
    def _format_export_txt(self, export_data: dict, purchases: list) -> str:
        """Formata os dados de exportação em TXT organizado"""
        lines = []
        lines.append("=" * 80)
        lines.append("RELATORIO DE RENDIMENTOS".center(80))
        lines.append("=" * 80)
        lines.append("")
        
        # Obter estatísticas
        stats = export_data.get('statistics', {})
        
        # Informações gerais
        lines.append("RESUMO GERAL")
        lines.append("-" * 80)
        lines.append(f"Data de Exportacao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"Total de Vendas: {stats.get('total_purchases', 0)}")
        lines.append(f"Receita Total: R$ {stats.get('total_revenue', 0):.2f}")
        lines.append(f"Clientes Unicos: {stats.get('unique_customers', 0)}")
        lines.append(f"Itens Vendidos: {stats.get('total_items_sold', 0)}")
        lines.append(f"Ticket Medio: R$ {stats.get('average_ticket', 0):.2f}")
        lines.append("")
        
        # Detalhamento por produto
        products_sold = stats.get('products_sold', {})
        if products_sold:
            lines.append("VENDAS POR PRODUTO")
            lines.append("-" * 80)
            for product_id, data in sorted(
                products_sold.items(),
                key=lambda x: x[1]['revenue'],
                reverse=True
            ):
                lines.append(f"  Produto: {data['name']}")
                lines.append(f"    Quantidade Vendida: {data['count']}")
                lines.append(f"    Receita Gerada: R$ {data['revenue']:.2f}")
                lines.append("")
        
        # Lista de compras
        lines.append("DETALHAMENTO DE COMPRAS")
        lines.append("=" * 80)
        lines.append("")
        
        for i, purchase in enumerate(purchases, 1):
            lines.append(f"COMPRA #{i}")
            lines.append("-" * 80)
            lines.append(f"  ID: {purchase.get('purchase_id', 'N/A')}")
            lines.append(f"  Data: {datetime.fromtimestamp(purchase.get('timestamp', 0)).strftime('%d/%m/%Y %H:%M:%S')}")
            lines.append(f"  Cliente ID: {purchase.get('user_id', 'N/A')}")
            lines.append(f"  Produto: {purchase.get('product', {}).get('name', 'N/A')}")
            lines.append(f"  Campo: {purchase.get('field', {}).get('name', 'N/A')}")
            lines.append(f"  Quantidade: {purchase.get('quantity', 0)}")
            lines.append(f"  Preco Unitario: R$ {purchase.get('pricing', {}).get('unit_price', 0):.2f}")
            
            discount = purchase.get('pricing', {}).get('discount_amount', 0)
            if discount > 0:
                lines.append(f"  Desconto: R$ {discount:.2f}")
                coupon = purchase.get('pricing', {}).get('coupon_code')
                if coupon:
                    lines.append(f"  Cupom Usado: {coupon}")
            
            lines.append(f"  Valor Final: R$ {purchase.get('pricing', {}).get('final_price', 0):.2f}")
            lines.append(f"  Metodo de Pagamento: {purchase.get('payment', {}).get('method', 'N/A').upper()}")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("FIM DO RELATORIO".center(80))
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    async def generate_filtered_report(self, inter: disnake.Interaction, filters: dict):
        """Gera relatório com filtros aplicados"""
        all_purchases = PurchaseManager.get_all_purchases()
        
        # Aplicar filtros
        filtered = []
        for purchase in all_purchases:
            # Filtro de data
            if "start_date" in filters and purchase.get("timestamp", 0) < filters["start_date"]:
                continue
            if "end_date" in filters and purchase.get("timestamp", 0) > filters["end_date"]:
                continue
            
            # Filtro de produto
            if "product_id" in filters and purchase.get("product", {}).get("id") != filters["product_id"]:
                continue
            
            # Filtro de usuário
            if "user_id" in filters and purchase.get("user_id") != filters["user_id"]:
                continue
            
            filtered.append(purchase)
        
        if not filtered:
            await inter.followup.send(
                f"{emoji.wrong} Nenhuma venda encontrada com os filtros aplicados!",
                ephemeral=True
            )
            return
        
        # Calcular estatísticas filtradas
        total_revenue = sum(p.get("pricing", {}).get("final_price", 0) for p in filtered)
        total_items = sum(p.get("quantity", 0) for p in filtered)
        average_price = total_revenue / len(filtered) if filtered else 0
        
        # Verificar modo de exibição
        mode = db.get_document("custom_mode").get("mode", "embed")
        
        if mode == "components":
            # Modo Container
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            # Preparar texto de filtros aplicados
            filters_text = []
            if "start_date" in filters:
                filters_text.append(f"-# {emoji.calendar} **De:** `{datetime.fromtimestamp(filters['start_date']).strftime('%d/%m/%Y')}`")
            if "end_date" in filters:
                filters_text.append(f"-# {emoji.calendar} **Até:** `{datetime.fromtimestamp(filters['end_date']).strftime('%d/%m/%Y')}`")
            if "product_id" in filters:
                filters_text.append(f"-# {emoji.bag} **Produto:** `{filters['product_id']}`")
            if "user_id" in filters:
                filters_text.append(f"-# {emoji.member} **Cliente:** `{filters['user_id']}`")
            
            container_components = [
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Rendimentos\n-# **Relatório Filtrado**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{emoji.information} **Estatísticas**\n"
                    f"-# {emoji.cart} **Vendas Encontradas:** `{len(filtered)}`\n"
                    f"-# {emoji.dollar} **Receita Total:** `R$ {total_revenue:.2f}`\n"
                    f"-# {emoji.cardbox} **Itens Vendidos:** `{total_items}`\n"
                    f"-# {emoji.chart} **Média por Venda:** `R$ {average_price:.2f}`"
                ),
            ]
            
            if filters_text:
                container_components.append(disnake.ui.Separator())
                container_components.append(
                    disnake.ui.TextDisplay(
                        f"{emoji.double_check} **Filtros Aplicados**\n" + "\n".join(filters_text)
                    )
                )
            
            container = disnake.ui.Container(*container_components, **container_kwargs)
            
            await inter.followup.send(
                components=[container],
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True
            )
        else:
            # Modo Embed
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            embed_color = disnake.Color.blue()
            if primary_color_hex:
                try:
                    embed_color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except:
                    pass
            
            embed = disnake.Embed(
                title=f"Rendimentos",
                description=f"{emoji.information} Encontradas **{len(filtered)}** vendas",
                color=embed_color
            )
            
            embed.add_field(
                name=f"{emoji.dollar} Receita",
                value=f"`R$ {total_revenue:.2f}`",
                inline=True
            )
            
            embed.add_field(
                name=f"{emoji.cardbox} Itens",
                value=f"`{total_items}`",
                inline=True
            )
            
            embed.add_field(
                name=f"{emoji.chart} Média",
                value=f"`R$ {average_price:.2f}`",
                inline=True
            )
            
            # Adicionar filtros aplicados
            filters_text = []
            if "start_date" in filters:
                filters_text.append(f"{emoji.calendar} **De:** `{datetime.fromtimestamp(filters['start_date']).strftime('%d/%m/%Y')}`")
            if "end_date" in filters:
                filters_text.append(f"{emoji.calendar} **Até:** `{datetime.fromtimestamp(filters['end_date']).strftime('%d/%m/%Y')}`")
            if "product_id" in filters:
                filters_text.append(f"{emoji.bag} **Produto:** `{filters['product_id']}`")
            if "user_id" in filters:
                filters_text.append(f"{emoji.member} **Cliente:** `{filters['user_id']}`")
            
            if filters_text:
                embed.add_field(
                    name=f"{emoji.double_check} Filtros Aplicados",
                    value="\n".join(filters_text),
                    inline=False
                )
            
            embed.timestamp = datetime.now()
            
            await inter.followup.send(embed=embed, ephemeral=True)
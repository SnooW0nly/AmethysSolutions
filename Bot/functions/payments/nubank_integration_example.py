"""
Exemplo de integração do Nubank IMAP com sistema de vendas
"""
import asyncio
import sys
from pathlib import Path
import discord
from datetime import datetime
from typing import Optional

# Adicionar o diretório raiz ao path para imports funcionarem
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from functions.payments.imap_nubank import (
    create_nubank_imap_payment,
    check_nubank_imap_payment,
    monitor_nubank_imap_payments
)


class NubankPaymentHandler:
    """Handler para gerenciar pagamentos via Nubank IMAP no Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.monitoring_task = None
    
    def start_monitoring(self):
        """Inicia monitoramento em background"""
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitor_loop())
            print("✅ Monitoramento Nubank IMAP iniciado")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            print("⏹️  Monitoramento Nubank IMAP parado")
    
    async def _monitor_loop(self):
        """Loop de monitoramento contínuo"""
        while True:
            try:
                approved_payments = await monitor_nubank_imap_payments()
                
                for payment in approved_payments:
                    await self._handle_approved_payment(payment)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Erro no monitoramento Nubank: {e}")
            
            # Aguardar 30 segundos antes da próxima verificação
            await asyncio.sleep(30)
    
    async def _handle_approved_payment(self, payment: dict):
        """
        Processa um pagamento aprovado
        
        Args:
            payment: Dados do pagamento aprovado
        """
        cart_id = payment.get("cart_id")
        amount = payment.get("amount")
        payer_name = payment.get("payer_name")
        
        print(f"✅ Pagamento aprovado: {cart_id} - R$ {amount:.2f}")
        
        # Aqui você implementa a lógica de aprovação
        # Exemplo: liberar produto, dar cargo, etc.
        
        # Buscar informações do carrinho/pedido
        # user_id, product_id = get_order_info(cart_id)
        
        # Liberar produto/serviço
        # await deliver_product(user_id, product_id)
        
        # Notificar usuário
        # await notify_user(user_id, f"Pagamento aprovado! Valor: R$ {amount:.2f}")
    
    async def create_payment_embed(
        self,
        user: discord.User,
        product_name: str,
        amount: float,
        cart_id: str
    ) -> tuple[discord.Embed, Optional[discord.File]]:
        """
        Cria um pagamento e retorna embed + QR code
        
        Args:
            user: Usuário que está comprando
            product_name: Nome do produto
            amount: Valor
            cart_id: ID do carrinho
        
        Returns:
            Tupla com (embed, file do QR code)
        """
        try:
            # Criar pagamento
            payment = await create_nubank_imap_payment(
                amount=amount,
                cart_id=cart_id,
                description=f"Compra: {product_name}",
                merchant_name="Minha Loja"
            )
            
            # Criar embed
            embed = discord.Embed(
                title="💳 Pagamento via PIX - Nubank",
                description=f"**Produto:** {product_name}\n**Valor:** R$ {amount:.2f}",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="📱 Como pagar",
                value=(
                    "1️⃣ Abra o app do seu banco\n"
                    "2️⃣ Escaneie o QR Code ou copie o código\n"
                    "3️⃣ Confirme o pagamento\n"
                    "4️⃣ Aguarde a aprovação automática!"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🆔 ID do Pedido",
                value=f"`{cart_id}`",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Validade",
                value="30 minutos",
                inline=True
            )
            
            # Código PIX (Copia e Cola)
            pix_code = payment.get("pix_copia_cola", "")
            if len(pix_code) > 1024:
                embed.add_field(
                    name="📋 Código PIX",
                    value=f"```\n{pix_code[:500]}...\n```\n*(Código muito longo, use o QR Code)*",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📋 Código PIX (Copiar e Colar)",
                    value=f"```\n{pix_code}\n```",
                    inline=False
                )
            
            embed.set_footer(text="O pagamento será aprovado automaticamente em até 2 minutos")
            
            # QR Code como arquivo
            qr_bytes = payment.get("qr_code_bytes")
            if qr_bytes:
                file = discord.File(
                    fp=io.BytesIO(qr_bytes),
                    filename="qrcode.png"
                )
                embed.set_image(url="attachment://qrcode.png")
                return embed, file
            
            return embed, None
        
        except Exception as e:
            # Embed de erro
            embed = discord.Embed(
                title="❌ Erro ao Gerar Pagamento",
                description=f"Não foi possível gerar o pagamento: {str(e)}",
                color=discord.Color.red()
            )
            return embed, None
    
    async def wait_for_payment(
        self,
        payment_id: str,
        timeout: int = 1800  # 30 minutos
    ) -> dict:
        """
        Aguarda um pagamento ser aprovado
        
        Args:
            payment_id: ID do pagamento
            timeout: Timeout em segundos
        
        Returns:
            Status do pagamento
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Verificar se passou o timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                return {
                    "status": "timeout",
                    "payment_id": payment_id
                }
            
            # Verificar status
            status = await check_nubank_imap_payment(payment_id)
            
            if status.get("status") == "approved":
                return status
            
            # Aguardar 10 segundos antes de verificar novamente
            await asyncio.sleep(10)


# ============================================================================
# EXEMPLO DE USO EM COMANDO DO DISCORD
# ============================================================================

import io


class ShopCog(discord.Cog):
    """Exemplo de Cog para vendas com Nubank IMAP"""
    
    def __init__(self, bot):
        self.bot = bot
        self.payment_handler = NubankPaymentHandler(bot)
        self.payment_handler.start_monitoring()
    
    def cog_unload(self):
        """Cleanup ao descarregar o cog"""
        self.payment_handler.stop_monitoring()
    
    @discord.app_commands.command(name="comprar")
    async def buy_product(
        self,
        interaction: discord.Interaction,
        produto: str,
        valor: float
    ):
        """
        Compra um produto via PIX
        
        Args:
            produto: Nome do produto
            valor: Valor do produto
        """
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Gerar ID único do carrinho
            cart_id = f"CART{interaction.user.id}{int(asyncio.get_event_loop().time())}"
            
            # Criar pagamento
            embed, file = await self.payment_handler.create_payment_embed(
                user=interaction.user,
                product_name=produto,
                amount=valor,
                cart_id=cart_id
            )
            
            # Enviar para o usuário
            if file:
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Aguardar pagamento em background
            asyncio.create_task(
                self._wait_and_deliver(interaction, cart_id, produto)
            )
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro",
                description=f"Erro ao processar compra: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _wait_and_deliver(
        self,
        interaction: discord.Interaction,
        cart_id: str,
        product_name: str
    ):
        """Aguarda pagamento e entrega o produto"""
        # Aguardar até 30 minutos
        status = await self.payment_handler.wait_for_payment(cart_id, timeout=1800)
        
        if status.get("status") == "approved":
            # Pagamento aprovado!
            embed = discord.Embed(
                title="✅ Pagamento Aprovado!",
                description=f"Seu pagamento foi aprovado com sucesso!\n\n**Produto:** {product_name}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="💰 Valor Pago",
                value=f"R$ {status.get('amount', 0):.2f}",
                inline=True
            )
            
            if status.get("payer_name"):
                embed.add_field(
                    name="👤 Pagador",
                    value=status.get("payer_name"),
                    inline=True
                )
            
            # Aqui você entrega o produto
            # await deliver_product(interaction.user, product_name)
            
            try:
                await interaction.user.send(embed=embed)
            except discord.Forbidden:
                pass
        
        elif status.get("status") == "timeout":
            # Timeout
            embed = discord.Embed(
                title="⏱️ Pagamento Expirado",
                description=f"O tempo para pagamento expirou.\n\n**Pedido:** {cart_id}",
                color=discord.Color.orange()
            )
            
            try:
                await interaction.user.send(embed=embed)
            except discord.Forbidden:
                pass


# ============================================================================
# EXEMPLO DE SETUP NO BOT PRINCIPAL
# ============================================================================

async def setup(bot):
    """Adiciona o cog ao bot"""
    await bot.add_cog(ShopCog(bot))


# ============================================================================
# EXEMPLO DE USO STANDALONE
# ============================================================================

async def exemplo_simples():
    """Exemplo simples de uso sem Discord"""
    print("🛍️  Criando pagamento...")
    
    # Criar pagamento
    payment = await create_nubank_imap_payment(
        amount=29.90,
        cart_id="TESTE123",
        description="Produto Teste"
    )
    
    print(f"✅ Pagamento criado: {payment['payment_id']}")
    print(f"💳 Código PIX: {payment['pix_copia_cola'][:50]}...")
    print(f"\n⏳ Aguardando pagamento por 5 minutos...")
    
    # Aguardar pagamento
    for i in range(10):  # 10 x 30s = 5 minutos
        await asyncio.sleep(30)
        
        status = await check_nubank_imap_payment(payment['payment_id'])
        
        if status['status'] == 'approved':
            print(f"\n🎉 Pagamento aprovado!")
            print(f"💰 Valor: R$ {status['amount']:.2f}")
            if status.get('payer_name'):
                print(f"👤 Pagador: {status['payer_name']}")
            return True
        
        print(f"   [{i+1}/10] Ainda pendente...")
    
    print(f"\n⏱️  Timeout - Pagamento não foi detectado")
    return False


if __name__ == "__main__":
    # Executar exemplo standalone
    asyncio.run(exemplo_simples())


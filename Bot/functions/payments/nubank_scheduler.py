"""
Scheduler para monitoramento contínuo de pagamentos Nubank IMAP
Execute este script para iniciar o monitoramento em background
"""
import asyncio
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional

# Adicionar o diretório raiz ao path para imports funcionarem
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from functions.payments.imap_nubank import monitor_nubank_imap_payments


class NubankPaymentScheduler:
    """Scheduler para monitorar pagamentos do Nubank continuamente"""
    
    def __init__(
        self,
        interval: int = 30,
        callback: Optional[Callable] = None
    ):
        """
        Inicializa o scheduler
        
        Args:
            interval: Intervalo entre verificações em segundos (padrão: 30)
            callback: Função assíncrona a ser chamada quando um pagamento for aprovado
        """
        self.interval = interval
        self.callback = callback
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.stats = {
            "total_checks": 0,
            "total_approved": 0,
            "errors": 0,
            "started_at": None,
            "last_check": None
        }
    
    async def _monitor_loop(self):
        """Loop principal de monitoramento"""
        print(f"🔄 Monitoramento iniciado (intervalo: {self.interval}s)")
        
        while self.running:
            try:
                self.stats["last_check"] = datetime.utcnow().isoformat()
                self.stats["total_checks"] += 1
                
                # Verificar pagamentos
                approved_payments = await monitor_nubank_imap_payments()
                
                if approved_payments:
                    self.stats["total_approved"] += len(approved_payments)
                    
                    print(f"\n✅ {len(approved_payments)} pagamento(s) aprovado(s)!")
                    
                    for payment in approved_payments:
                        print(f"   💰 {payment['cart_id']} - R$ {payment['amount']:.2f}")
                        
                        # Chamar callback se definido
                        if self.callback:
                            try:
                                await self.callback(payment)
                            except Exception as e:
                                print(f"   ⚠️ Erro no callback: {e}")
                
                # Log periódico (a cada 10 verificações)
                if self.stats["total_checks"] % 10 == 0:
                    print(f"📊 Estatísticas: {self.stats['total_checks']} verificações, "
                          f"{self.stats['total_approved']} aprovados, "
                          f"{self.stats['errors']} erros")
            
            except Exception as e:
                self.stats["errors"] += 1
                print(f"❌ Erro no monitoramento: {e}")
            
            # Aguardar próximo ciclo
            await asyncio.sleep(self.interval)
    
    def start(self):
        """Inicia o monitoramento"""
        if self.running:
            print("⚠️ Monitoramento já está em execução")
            return
        
        self.running = True
        self.stats["started_at"] = datetime.utcnow().isoformat()
        self.task = asyncio.create_task(self._monitor_loop())
        print(f"✅ Scheduler iniciado")
    
    def stop(self):
        """Para o monitoramento"""
        if not self.running:
            print("⚠️ Monitoramento não está em execução")
            return
        
        self.running = False
        
        if self.task and not self.task.done():
            self.task.cancel()
        
        print(f"⏹️ Scheduler parado")
        self._print_stats()
    
    def _print_stats(self):
        """Imprime estatísticas finais"""
        print("\n" + "="*60)
        print("📊 ESTATÍSTICAS DO MONITORAMENTO")
        print("="*60)
        print(f"Iniciado em: {self.stats['started_at']}")
        print(f"Última verificação: {self.stats['last_check']}")
        print(f"Total de verificações: {self.stats['total_checks']}")
        print(f"Pagamentos aprovados: {self.stats['total_approved']}")
        print(f"Erros: {self.stats['errors']}")
        print("="*60)
    
    async def run_forever(self):
        """Executa o scheduler até ser interrompido"""
        self.start()
        
        # Aguardar até ser parado
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.stop()


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

async def default_callback(payment: dict):
    """
    Callback padrão chamado quando um pagamento é aprovado
    
    Args:
        payment: Dados do pagamento aprovado
    """
    cart_id = payment.get("cart_id")
    amount = payment.get("amount")
    payer_name = payment.get("payer_name")
    
    print(f"\n🎉 PAGAMENTO APROVADO!")
    print(f"   Carrinho: {cart_id}")
    print(f"   Valor: R$ {amount:.2f}")
    if payer_name:
        print(f"   Pagador: {payer_name}")
    
    # Aqui você implementa sua lógica de negócio
    # Exemplo:
    # - Liberar produto
    # - Dar cargo no Discord
    # - Enviar notificação
    # - Atualizar banco de dados
    # - etc.


# ============================================================================
# EXEMPLO DE USO COM DISCORD BOT
# ============================================================================

async def discord_bot_callback(payment: dict):
    """
    Callback para integração com Discord bot
    
    Args:
        payment: Dados do pagamento aprovado
    """
    # Buscar informações do pedido
    cart_id = payment.get("cart_id")
    
    # Exemplo: extrair user_id do cart_id
    # Formato esperado: CART{user_id}{timestamp}
    try:
        user_id = int(cart_id.replace("CART", "").split("_")[0])
        
        # Buscar usuário no Discord
        # user = await bot.fetch_user(user_id)
        
        # Enviar DM
        # await user.send(f"✅ Pagamento aprovado! Valor: R$ {payment['amount']:.2f}")
        
        # Liberar produto
        # await deliver_product(user_id, cart_id)
        
        print(f"✅ Produto liberado para usuário {user_id}")
    
    except Exception as e:
        print(f"❌ Erro ao processar pagamento {cart_id}: {e}")


# ============================================================================
# INTEGRAÇÃO COM DISCORD.PY
# ============================================================================

class DiscordPaymentMonitor:
    """Monitor de pagamentos integrado com Discord.py"""
    
    def __init__(self, bot, interval: int = 30):
        self.bot = bot
        self.scheduler = NubankPaymentScheduler(
            interval=interval,
            callback=self._handle_payment
        )
    
    async def _handle_payment(self, payment: dict):
        """Processa um pagamento aprovado"""
        cart_id = payment.get("cart_id")
        amount = payment.get("amount")
        
        try:
            # Buscar informações do pedido no database
            # order = get_order_by_cart_id(cart_id)
            
            # Extrair user_id (ajuste conforme seu formato)
            # user_id = order["user_id"]
            
            # Buscar usuário no Discord
            # user = await self.bot.fetch_user(user_id)
            
            # Enviar confirmação
            # embed = discord.Embed(
            #     title="✅ Pagamento Aprovado!",
            #     description=f"Seu pagamento de R$ {amount:.2f} foi confirmado!",
            #     color=discord.Color.green()
            # )
            # await user.send(embed=embed)
            
            # Liberar produto/cargo
            # await self.deliver_product(user_id, order["product_id"])
            
            print(f"✅ Pedido {cart_id} processado com sucesso")
        
        except Exception as e:
            print(f"❌ Erro ao processar pagamento {cart_id}: {e}")
    
    def start(self):
        """Inicia o monitoramento"""
        self.scheduler.start()
    
    def stop(self):
        """Para o monitoramento"""
        self.scheduler.stop()


# ============================================================================
# SCRIPT STANDALONE
# ============================================================================

async def main():
    """Função principal para execução standalone"""
    print("\n" + "="*60)
    print("🤖 NUBANK IMAP PAYMENT MONITOR")
    print("="*60)
    print("\nMonitorando pagamentos via IMAP...")
    print("Pressione Ctrl+C para parar\n")
    
    # Criar scheduler com callback
    scheduler = NubankPaymentScheduler(
        interval=30,  # Verificar a cada 30 segundos
        callback=default_callback
    )
    
    # Setup para capturar Ctrl+C
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        print("\n\n⏸️  Interrupção detectada...")
        scheduler.stop()
        loop.stop()
    
    # Registrar handler de sinal
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    # Executar
    try:
        await scheduler.run_forever()
    except KeyboardInterrupt:
        scheduler.stop()


# ============================================================================
# EXEMPLO DE USO COMO MÓDULO
# ============================================================================

async def exemplo_modulo():
    """Exemplo de uso como módulo importado"""
    
    # Definir callback customizado
    async def meu_callback(payment):
        print(f"💰 Recebi R$ {payment['amount']:.2f}")
        # Sua lógica aqui
    
    # Criar e iniciar scheduler
    scheduler = NubankPaymentScheduler(
        interval=30,
        callback=meu_callback
    )
    
    scheduler.start()
    
    # Aguardar 5 minutos
    await asyncio.sleep(300)
    
    # Parar
    scheduler.stop()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até logo!")


"""
Integração do Sistema de Saldo com o Checkout
Adiciona funcionalidade de usar saldo como desconto no carrinho
"""
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .balance_manager import BalanceManager


class SaldoCheckoutIntegration(commands.Cog):
    """Integração de saldo com o checkout"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @staticmethod
    def get_cart_balance_info(cart: dict, user_id: int) -> dict:
        """
        Obtém informações de saldo aplicáveis ao carrinho
        
        Returns:
            dict: {
                "enabled": bool,
                "user_balance": float,
                "usable_amount": float,
                "applied_amount": float,
                "can_apply": bool
            }
        """
        result = {
            "enabled": False,
            "user_balance": 0,
            "usable_amount": 0,
            "applied_amount": 0,
            "can_apply": False
        }
        
        # Verificar se sistema está ativo
        if not BalanceManager.is_enabled():
            return result
        
        result["enabled"] = True
        
        # Obter saldo do usuário
        user_balance = BalanceManager.get_user_balance(user_id)
        result["user_balance"] = user_balance
        
        if user_balance <= 0:
            return result
        
        # Calcular valor total do carrinho
        total_price = cart.get("total_price", 0)
        discount_amount = cart.get("discount_amount", 0) or 0
        final_price = max(0, total_price - discount_amount)
        
        # Calcular quanto pode ser usado
        usable_amount = BalanceManager.calculate_usable_amount(user_id, final_price)
        result["usable_amount"] = usable_amount
        
        # Verificar se já tem saldo aplicado
        result["applied_amount"] = cart.get("balance_applied", 0) or 0
        
        # Pode aplicar se tem saldo usável
        result["can_apply"] = usable_amount > 0
        
        return result
    
    @staticmethod
    def apply_balance_to_cart(cart_id: str, user_id: int, amount: float) -> tuple[bool, str]:
        """
        Aplica saldo ao carrinho
        
        Args:
            cart_id: ID do carrinho
            user_id: ID do usuário
            amount: Valor a aplicar
            
        Returns:
            tuple: (success, message)
        """
        loja_data = db.get_document("loja_data") or {}
        carts = loja_data.get("carts", {})
        cart = carts.get(cart_id)
        
        if not cart:
            return False, "Carrinho não encontrado"
        
        # Verificar saldo do usuário
        user_balance = BalanceManager.get_user_balance(user_id)
        if user_balance < amount:
            return False, f"Saldo insuficiente. Seu saldo é R$ {user_balance:.2f}"
        
        # Verificar valor máximo usável
        total_price = cart.get("total_price", 0)
        discount_amount = cart.get("discount_amount", 0) or 0
        final_price = max(0, total_price - discount_amount)
        
        usable = BalanceManager.calculate_usable_amount(user_id, final_price)
        if amount > usable:
            return False, f"Valor máximo que pode ser usado é R$ {usable:.2f}"
        
        # Aplicar saldo ao carrinho
        cart["balance_applied"] = amount
        cart["balance_user_id"] = user_id
        carts[cart_id] = cart
        loja_data["carts"] = carts
        db.save_document("loja_data", loja_data)
        
        return True, f"Saldo de R$ {amount:.2f} aplicado com sucesso!"
    
    @staticmethod
    def remove_balance_from_cart(cart_id: str) -> tuple[bool, str]:
        """
        Remove saldo aplicado do carrinho
        
        Args:
            cart_id: ID do carrinho
            
        Returns:
            tuple: (success, message)
        """
        loja_data = db.get_document("loja_data") or {}
        carts = loja_data.get("carts", {})
        cart = carts.get(cart_id)
        
        if not cart:
            return False, "Carrinho não encontrado"
        
        if "balance_applied" not in cart or cart.get("balance_applied", 0) <= 0:
            return False, "Nenhum saldo aplicado neste carrinho"
        
        # Remover saldo
        cart["balance_applied"] = 0
        cart["balance_user_id"] = None
        carts[cart_id] = cart
        loja_data["carts"] = carts
        db.save_document("loja_data", loja_data)
        
        return True, "Saldo removido do carrinho"
    
    @staticmethod
    async def process_balance_deduction(cart: dict, bot) -> bool:
        """
        Processa dedução do saldo após pagamento aprovado
        
        Args:
            cart: Dados do carrinho
            bot: Instância do bot
            
        Returns:
            bool: True se dedução foi bem sucedida
        """
        balance_applied = cart.get("balance_applied", 0)
        balance_user_id = cart.get("balance_user_id")
        
        if not balance_applied or balance_applied <= 0 or not balance_user_id:
            return True  # Nada a deduzir
        
        cart_id = cart.get("cart_id", cart.get("thread_id", "unknown"))
        
        # Deduzir saldo do usuário
        success, msg = BalanceManager.use_balance(
            user_id=int(balance_user_id),
            amount=balance_applied,
            reference_id=str(cart_id),
            description=f"Pagamento de compra #{cart_id[:8]}"
        )
        
        return success
    
    @commands.Cog.listener("on_button_click")
    async def on_balance_button(self, inter: disnake.MessageInteraction):
        """Handler para botões de saldo no carrinho"""
        custom_id = inter.component.custom_id
        
        # Aplicar saldo
        if custom_id.startswith("cart_apply_balance:"):
            parts = custom_id.split(":")
            cart_id = parts[1] if len(parts) > 1 else None
            
            if not cart_id:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado.",
                    ephemeral=True
                )
                return
            
            # Obter carrinho
            loja_data = db.get_document("loja_data") or {}
            cart = loja_data.get("carts", {}).get(cart_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado.",
                    ephemeral=True
                )
                return
            
            # Obter info de saldo
            balance_info = self.get_cart_balance_info(cart, inter.user.id)
            
            if not balance_info["enabled"]:
                await inter.response.send_message(
                    f"{emoji.wrong} Sistema de saldo não está disponível.",
                    ephemeral=True
                )
                return
            
            if not balance_info["can_apply"]:
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem saldo disponível para usar.",
                    ephemeral=True
                )
                return
            
            # Modal para informar valor
            class BalanceAmountModal(disnake.ui.Modal):
                def __init__(modal_self, max_amount: float, current_balance: float):
                    modal_self.max_amount = max_amount
                    modal_self.current_balance = current_balance
                    modal_self.cart_id = cart_id
                    
                    components = [
                        disnake.ui.TextInput(
                            label=f"Valor (máx R$ {max_amount:.2f})",
                            placeholder=f"Seu saldo: R$ {current_balance:.2f}",
                            custom_id="amount",
                            style=disnake.TextInputStyle.short,
                            value=f"{max_amount:.2f}",
                            required=True,
                            max_length=15
                        )
                    ]
                    super().__init__(title="Usar Saldo", components=components)
                
                async def callback(modal_self, modal_inter: disnake.ModalInteraction):
                    amount_str = modal_inter.text_values.get("amount", "").strip()
                    amount_str = amount_str.replace(",", ".").replace("R$", "").replace(" ", "")
                    
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        await modal_inter.response.send_message(
                            f"{emoji.wrong} Valor inválido.",
                            ephemeral=True
                        )
                        return
                    
                    if amount <= 0:
                        await modal_inter.response.send_message(
                            f"{emoji.wrong} Valor deve ser maior que zero.",
                            ephemeral=True
                        )
                        return
                    
                    if amount > modal_self.max_amount:
                        await modal_inter.response.send_message(
                            f"{emoji.wrong} Valor máximo é R$ {modal_self.max_amount:.2f}",
                            ephemeral=True
                        )
                        return
                    
                    # Aplicar saldo
                    success, msg = SaldoCheckoutIntegration.apply_balance_to_cart(
                        modal_self.cart_id,
                        modal_inter.user.id,
                        amount
                    )
                    
                    if success:
                        await modal_inter.response.send_message(
                            f"{emoji.correct} {msg}\n-# O desconto será aplicado ao finalizar a compra.",
                            ephemeral=True
                        )
                        
                        # Atualizar mensagem do carrinho
                        await SaldoCheckoutIntegration.update_cart_message(
                            modal_self.cart_id,
                            modal_inter,
                            self.bot
                        )
                    else:
                        await modal_inter.response.send_message(
                            f"{emoji.wrong} {msg}",
                            ephemeral=True
                        )
            
            await inter.response.send_modal(
                BalanceAmountModal(
                    balance_info["usable_amount"],
                    balance_info["user_balance"]
                )
            )
        
        # Remover saldo
        elif custom_id.startswith("cart_remove_balance:"):
            parts = custom_id.split(":")
            cart_id = parts[1] if len(parts) > 1 else None
            
            if not cart_id:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado.",
                    ephemeral=True
                )
                return
            
            success, msg = self.remove_balance_from_cart(cart_id)
            
            if success:
                await inter.response.send_message(
                    f"{emoji.correct} {msg}",
                    ephemeral=True
                )
                
                # Atualizar mensagem do carrinho
                await self.update_cart_message(cart_id, inter, self.bot)
            else:
                await inter.response.send_message(
                    f"{emoji.wrong} {msg}",
                    ephemeral=True
                )
    
    @staticmethod
    async def update_cart_message(cart_id: str, inter: disnake.MessageInteraction, bot):
        """Atualiza a mensagem do carrinho após aplicar/remover saldo"""
        # Importar aqui para evitar circular import
        from modules.loja.cart.checkout import _build_cart_message
        
        loja_data = db.get_document("loja_data") or {}
        cart = loja_data.get("carts", {}).get(cart_id)
        
        if not cart:
            return
        
        thread_id = cart.get("thread_id")
        cart_message_id = cart.get("cart_message_id")
        
        if not thread_id or not cart_message_id:
            return
        
        try:
            thread = bot.get_channel(int(thread_id))
            if not thread:
                return
            
            mode = db.get_document("custom_mode").get("mode", "components")
            
            new_msg = await _build_cart_message(cart, thread, mode)
            
            if new_msg:
                # Atualizar referência da mensagem
                loja_data = db.get_document("loja_data")
                if cart_id in loja_data.get("carts", {}):
                    loja_data["carts"][cart_id]["cart_message_id"] = new_msg.id
                    db.save_document("loja_data", loja_data)
                
                # Tentar deletar mensagem antiga
                try:
                    old_msg = await thread.fetch_message(cart_message_id)
                    if old_msg:
                        await old_msg.delete()
                except:
                    pass
        except Exception as e:
            print(f"Erro ao atualizar mensagem do carrinho: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(SaldoCheckoutIntegration(bot))

"""
Sistema de limpeza automática de carrinhos
"""
import disnake
import asyncio
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from functions.database import database as db
from functions.emoji import emoji


class CartCleanup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.cleanup_approved_carts.is_running():
            self.cleanup_approved_carts.start()
        if not self.close_pending_carts.is_running():
            self.close_pending_carts.start()
        if not self.cleanup_orphaned_carts.is_running():
            self.cleanup_orphaned_carts.start()
    
    def cog_unload(self):
        self.cleanup_approved_carts.cancel()
        self.close_pending_carts.cancel()
        self.cleanup_orphaned_carts.cancel()
    
    @tasks.loop(hours=6)
    async def cleanup_approved_carts(self):
        """
        Remove carrinhos aprovados após 3 dias (exceto entrega manual)
        Executa a cada 6 horas
        """
        try:
            loja_data = db.get_document("loja_data")
            carts = loja_data.get("carts", {})
            
            if not carts:
                return
            
            now = int(datetime.utcnow().timestamp())
            three_days_ago = now - (3 * 24 * 60 * 60)  # 3 dias em segundos
            
            carts_to_remove = []
            
            for cart_id, cart in carts.items():
                # Verificar se está aprovado
                if cart.get("status") != "approved":
                    continue
                
                # Verificar se há itens de entrega manual (usar nova estrutura de items[])
                products = db.get_document("loja_products") or {}
                has_manual_item = False
                items = cart.get("items", [])
                if isinstance(items, list) and items:
                    for it in items:
                        pid = it.get("product_id")
                        if not pid:
                            continue
                        prod = products.get(pid, {}) or {}
                        info = prod.get("info") or {}
                        if info.get("delivery_type", "automatic") == "manual":
                            has_manual_item = True
                            break
                # Se houver qualquer item manual, não remover automaticamente
                if has_manual_item:
                    continue
                
                # Verificar se passou 3 dias desde a aprovação
                approved_at = cart.get("approved_at", cart.get("created_at", now))
                
                if approved_at < three_days_ago:
                    carts_to_remove.append(cart_id)
            
            # Remover carrinhos
            if carts_to_remove:
                for cart_id in carts_to_remove:
                    del carts[cart_id]
                
                loja_data["carts"] = carts
                db.save_document("loja_data", loja_data)
                
        
        except Exception as e:
            pass
    
    @tasks.loop(minutes=5)
    async def close_pending_carts(self):
        """
        Fecha e remove carrinhos pendentes após 15 minutos
        (Exceto PIX Manual que requer aprovação manual)
        Executa a cada 5 minutos
        """
        try:
            loja_data = db.get_document("loja_data")
            carts = loja_data.get("carts", {})
            
            if not carts:
                return
            
            now = int(datetime.utcnow().timestamp())
            fifteen_minutes_ago = now - (15 * 60)  # 15 minutos em segundos
            
            carts_to_close = []
            
            for cart_id, cart in carts.items():
                # Verificar se está pendente
                if cart.get("status") != "pending":
                    continue
                
                # Verificar se é PIX Manual (não fechar automaticamente)
                payment_method = cart.get("payment_method")
                payment_data = cart.get("payment_data", {})
                
                # Tentar nova estrutura primeiro
                local_data = payment_data.get("local", {})
                requires_manual_approval = local_data.get("requires_manual_approval", False)
                
                # Fallback para estrutura antiga
                if not requires_manual_approval:
                    requires_manual_approval = payment_data.get("raw", {}).get("requires_manual_approval", False)
                
                if requires_manual_approval or payment_method == "pix_manual":
                    continue  # Não fechar PIX Manual automaticamente
                
                # Verificar se passou 15 minutos desde a criação
                created_at = cart.get("created_at", now)
                
                if created_at < fifteen_minutes_ago:
                    carts_to_close.append((cart_id, cart))
            
            # Fechar e remover carrinhos
            if carts_to_close:
                for cart_id, cart in carts_to_close:
                    thread_deleted = False
                    
                    # Cancelar pagamento na Sync Pay API se aplicável
                    payment_data = cart.get("payment_data", {})
                    
                    # Tentar nova estrutura primeiro
                    provider_data = payment_data.get("provider", {})
                    payment_provider = provider_data.get("name")
                    
                    # Fallback para estrutura antiga
                    if not payment_provider:
                        payment_provider = payment_data.get("payment_provider")
                    
                    if payment_provider == "sync_wallet":
                        try:
                            from functions.payments.sync_wallet import cancel_sync_payment_from_settings
                            
                            # Tentar obter payment_id da nova estrutura
                            payment_id = provider_data.get("payment_id") or provider_data.get("correlation_id")
                            
                            # Fallback para estrutura antiga
                            if not payment_id:
                                raw_data = payment_data.get("raw", {}) or provider_data.get("raw_response", {})
                                payment_id = (
                                    raw_data.get("paymentId") or 
                                    raw_data.get("payment_id") or 
                                    raw_data.get("id") or
                                    payment_data.get("payment_id")
                                )
                            
                            if payment_id:
                                # Cancelar na Sync Pay API
                                result = await cancel_sync_payment_from_settings(payment_id)
                                print(f"✅ Pagamento Sync Wallet {payment_id} cancelado por expiração: {result}")
                            else:
                                print(f"⚠️ Payment ID não encontrado para cancelamento Sync Wallet")
                                
                        except Exception as e:
                            # Não falhar a limpeza se houver erro ao cancelar na API
                            print(f"❌ Erro ao cancelar pagamento Sync Wallet expirado: {e}")
                    
                    # Tentar deletar a thread e enviar DM
                    try:
                        thread_id = cart.get("thread_id")
                        guild_id = cart.get("guild_id")
                        user_id = cart.get("user_id")
                        items = cart.get("items", [])
                        
                        if thread_id and guild_id:
                            guild = self.bot.get_guild(int(guild_id))
                            if guild:
                                thread = guild.get_thread(int(thread_id))
                                if thread:
                                    mode = db.get_document("custom_mode").get("mode", "embed")
                                    
                                    # Enviar mensagem de expiração na thread
                                    if mode == "components":
                                        await thread.send(
                                            components=[
                                                disnake.ui.Container(
                                                    disnake.ui.TextDisplay(f"# {emoji.wrong}"),
                                                    disnake.ui.TextDisplay(
                                                        "**Carrinho Expirado**\n\n"
                                                        "Este carrinho foi fechado automaticamente após 15 minutos sem pagamento."
                                                    ),
                                                    accent_colour=disnake.Colour.red()
                                                )
                                            ],
                                            flags=disnake.MessageFlags(is_components_v2=True)
                                        )
                                    else:
                                        await thread.send(
                                            f"{emoji.wrong} **Carrinho Expirado**\n\n"
                                            f"Este carrinho foi fechado automaticamente após 15 minutos sem pagamento."
                                        )
                                    
                                    # Gerar e enviar transcript se habilitado (antes de deletar)
                                    try:
                                        from modules.loja.preferences.generate_transcript import generate_cart_transcript, send_cart_transcript_to_channel
                                        prefs = db.get_document("loja_preferences") or {}
                                        if prefs.get("transcript_enabled", False):
                                            transcript_channel_id = prefs.get("transcript_channel_id")
                                            if transcript_channel_id:
                                                transcript_file = await generate_cart_transcript(thread, self.bot, cart)
                                                if transcript_file:
                                                    await send_cart_transcript_to_channel(self.bot, transcript_file, int(transcript_channel_id), cart)
                                    except Exception as e:
                                        print(f"Erro ao gerar transcript: {e}")
                                    
                                    # Deletar thread
                                    try:
                                        await thread.delete()
                                        thread_deleted = True
                                    except disnake.errors.NotFound:
                                        # Thread já foi deletada, não fazer nada
                                        thread_deleted = True
                                    except Exception as delete_error:
                                        # Outro erro ao deletar, logar mas não quebrar
                                        print(f"Erro ao deletar thread {thread.id} no cleanup: {delete_error}")
                                        thread_deleted = True
                        
                        # Enviar DM para o usuário
                        if user_id:
                            try:
                                user = self.bot.get_user(int(user_id))
                                if not user:
                                    user = await self.bot.fetch_user(int(user_id))
                                
                                if user:
                                    # Montar resumo dos itens
                                    products = db.get_document("loja_products") or {}
                                    items_lines = []
                                    if isinstance(items, list) and items:
                                        for it in items:
                                            pid = it.get("product_id")
                                            cid = it.get("campo_id")
                                            qty = it.get("quantity", 1)
                                            prod = products.get(pid, {}) or {}
                                            campos = prod.get("campos", {}) or {}
                                            campo = campos.get(cid, {}) or {}
                                            pname = prod.get("name", "Produto")
                                            cname = campo.get("name", "Campo")
                                            items_lines.append(f"- {pname} — `{cname}` x{qty}")
                                    items_block = "\n".join(items_lines) if items_lines else "Sem itens listados."
                                    
                                    mode = db.get_document("custom_mode").get("mode", "embed")
                                    
                                    if mode == "components":
                                        await user.send(
                                            components=[
                                                disnake.ui.Container(
                                                    disnake.ui.TextDisplay(f"# {emoji.wrong}"),
                                                    disnake.ui.TextDisplay(
                                                        f"**Carrinho Expirado**\n\n"
                                                        f"Seu carrinho foi fechado automaticamente após 15 minutos sem pagamento.\n\n"
                                                        f"**Itens:**\n{items_block}"
                                                    ),
                                                    accent_colour=disnake.Colour.red()
                                                )
                                            ],
                                            flags=disnake.MessageFlags(is_components_v2=True)
                                        )
                                    else:
                                        embed = disnake.Embed(
                                            title=f"{emoji.wrong} Carrinho Expirado",
                                            description=(
                                                f"Seu carrinho foi fechado automaticamente após 15 minutos sem pagamento.\n\n"
                                                f"**Itens:**\n{items_block}"
                                            ),
                                            color=disnake.Color.red()
                                        )
                                        await user.send(embed=embed)
                                    
                            except Exception as e:
                                pass
                    
                    except Exception as e:
                        pass
                    
                    # Remover do database
                    del carts[cart_id]
                
                loja_data["carts"] = carts
                db.save_document("loja_data", loja_data)
                
        
        except Exception as e:
            pass
    
    @cleanup_approved_carts.before_loop
    async def before_cleanup_approved(self):
        await self.bot.wait_until_ready()
    
    @close_pending_carts.before_loop
    async def before_close_pending(self):
        await self.bot.wait_until_ready()
    
    @tasks.loop(hours=1)
    async def cleanup_orphaned_carts(self):
        """
        Remove carrinhos órfãos (sem thread válida)
        Executa a cada 1 hora
        """
        try:
            loja_data = db.get_document("loja_data")
            carts = loja_data.get("carts", {})
            
            if not carts:
                return
            
            orphaned_carts = []
            
            for cart_id, cart in carts.items():
                # Verificar apenas carrinhos em status "cart" (antes do pagamento)
                if cart.get("status") != "cart":
                    continue
                
                thread_id = cart.get("thread_id")
                guild_id = cart.get("guild_id")
                
                if not thread_id or not guild_id:
                    orphaned_carts.append(cart_id)
                    continue
                
                # Verificar se a thread ainda existe
                try:
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        orphaned_carts.append(cart_id)
                        continue
                    
                    thread = guild.get_thread(int(thread_id))
                    if not thread:
                        # Tentar buscar a thread (pode estar em cache)
                        try:
                            thread = await guild.fetch_channel(int(thread_id))
                            if not isinstance(thread, disnake.Thread):
                                orphaned_carts.append(cart_id)
                        except:
                            orphaned_carts.append(cart_id)
                except Exception:
                    orphaned_carts.append(cart_id)
            
            # Remover carrinhos órfãos
            if orphaned_carts:
                for cart_id in orphaned_carts:
                    del carts[cart_id]
                
                loja_data["carts"] = carts
                db.save_document("loja_data", loja_data)
                
        
        except Exception as e:
            pass
    
    @cleanup_orphaned_carts.before_loop
    async def before_cleanup_orphaned(self):
        await self.bot.wait_until_ready()
        # Executar limpeza inicial após 30 segundos da inicialização
        await asyncio.sleep(30)


def setup(bot: commands.Bot):
    bot.add_cog(CartCleanup(bot))

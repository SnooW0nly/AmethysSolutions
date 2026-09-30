import disnake
from disnake.ext import commands
import time
from datetime import datetime
from functions.database import database as db
from functions.emoji import emoji
from functions.payments import approve_manual_pix_payment


class CancelCheckout(commands.Cog):
    """Gerencia cancelamento de checkouts"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener("on_button_click")
    async def on_close_cart_button(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Formato: "close_cart:<cart_id>"
        if custom_id.startswith("close_cart:"):
            cart_id = custom_id.split(":", 1)[1]
            
            # Verificar se é admin
            cargos_data = db.get_document("cargos")
            cargo_admin_id = cargos_data.get("cargo_admin")
            
            is_admin = inter.author.guild_permissions.administrator
            has_admin_role = False
            if cargo_admin_id:
                has_admin_role = any(role.id == int(cargo_admin_id) for role in inter.author.roles)
            
            if not (is_admin or has_admin_role):
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem permissão para encerrar este atendimento!",
                    ephemeral=True
                )
                return
            
            # Buscar carrinho
            loja_data = db.get_document("loja_data")
            cart = loja_data.get("carts", {}).get(cart_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            # Confirmar encerramento
            await inter.response.send_message(
                f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Encerrando atendimento...",
                ephemeral=True
            )
            
            try:
                # Cancelar pagamento na Sync Pay API se aplicável e ainda não aprovado
                if cart.get("status") not in ["approved", "cancelled"]:
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
                                print(f"✅ Pagamento Sync Wallet {payment_id} cancelado ao encerrar: {result}")
                            else:
                                print(f"⚠️ Payment ID não encontrado para cancelamento Sync Wallet")
                                
                        except Exception as e:
                            # Não falhar o encerramento se houver erro ao cancelar na API
                            print(f"❌ Erro ao cancelar pagamento Sync Wallet: {e}")
                
                thread = inter.channel
                user_id = cart.get("user_id")
                
                # Buscar usuário
                user = await self.bot.fetch_user(user_id)
                
                # Enviar notificação para o usuário (seguindo o modo)
                if user:
                    try:
                        mode = db.get_document("custom_mode").get("mode", "embed")
                        
                        if mode == "embed":
                            embed = disnake.Embed(
                                title=f"Atendimento Encerrado",
                                description=(
                                    f"Seu atendimento foi encerrado por {inter.author.mention}.\n\n"
                                    f"Obrigado pela preferência!"
                                ),
                                color=disnake.Color.green()
                            )
                            await user.send(embed=embed)
                        else:
                            # Modo Container
                            color_data = db.get_document("custom_colors") or {}
                            primary_color = color_data.get("primary")
                            container_kwargs = {}
                            if primary_color:
                                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color.replace("#", ""), 16))
                            
                            await user.send(
                                components=[
                                    disnake.ui.Container(
                                        disnake.ui.TextDisplay(f"# {emoji.cart}\n-# Atendimento Encerrado"),
                                        disnake.ui.Separator(),
                                        disnake.ui.TextDisplay(
                                            f"Seu atendimento foi encerrado por {inter.author.mention}.\n\n"
                                            f"Obrigado pela preferência!"
                                        ),
                                        **container_kwargs
                                    )
                                ],
                                flags=disnake.MessageFlags(is_components_v2=True)
                            )
                    except Exception as e:
                        pass
                
                # Mensagem administrativa
                await inter.edit_original_message(
                    content=f"{emoji.correct} Atendimento encerrado! O tópico será deletado em breve.",
                    embed=None,
                    components=[]
                )
                
                # Mensagem no thread
                if isinstance(thread, disnake.Thread):
                    await thread.send(
                        f"{emoji.correct} Atendimento encerrado por {inter.author.mention}."
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
                    
                    # Aguardar e deletar
                    import asyncio
                    await asyncio.sleep(5)
                    try:
                        await thread.delete()
                    except disnake.errors.NotFound:
                        # Thread já foi deletada, não fazer nada
                        pass
                    except Exception as delete_error:
                        # Outro erro ao deletar, logar mas não quebrar
                        print(f"Erro ao deletar thread {thread.id}: {delete_error}")
                
                # Remover do database
                if cart_id in loja_data.get("carts", {}):
                    del loja_data["carts"][cart_id]
                    db.save_document("loja_data", loja_data)
                    
            except disnake.errors.NotFound:
                # Thread ou mensagem não encontrada - pode ter sido deletada manualmente
                # Tentar enviar mensagem apenas se ainda existir
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            content=f"{emoji.correct} Atendimento encerrado!",
                            ephemeral=True
                        )
                    else:
                        try:
                            await inter.edit_original_message(
                                content=f"{emoji.correct} Atendimento encerrado!",
                                embed=None,
                                components=[]
                            )
                        except disnake.errors.NotFound:
                            # Mensagem original não existe mais, não fazer nada
                            pass
                except Exception:
                    # Se não conseguir enviar/editar, não fazer nada
                    pass
            except Exception as e:
                # Outros erros - tentar editar mensagem apenas se ainda existir
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            content=f"{emoji.wrong} Erro ao encerrar atendimento: {e}",
                            ephemeral=True
                        )
                    else:
                        try:
                            await inter.edit_original_message(
                                content=f"{emoji.wrong} Erro ao encerrar atendimento: {e}",
                                embed=None,
                                components=[]
                            )
                        except disnake.errors.NotFound:
                            # Mensagem original não existe mais, não fazer nada
                            pass
                except Exception:
                    # Se não conseguir enviar/editar, não fazer nada
                    pass
    
    @commands.Cog.listener("on_button_click")
    async def on_cancel_button(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Formato: "cancel_checkout:<thread_id>"
        if custom_id.startswith("cancel_checkout:"):
            thread_id = custom_id.split(":", 1)[1]
            
            # Verificar se é o dono do carrinho ou admin
            loja_data = db.get_document("loja_data")
            cart = loja_data.get("carts", {}).get(thread_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong if hasattr(emoji, 'error') else '❌'} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            # Verificar permissão
            is_owner = inter.author.id == cart["user_id"]
            is_admin = inter.author.guild_permissions.administrator
            
            if not (is_owner or is_admin):
                await inter.response.send_message(
                    f"{emoji.wrong if hasattr(emoji, 'error') else '❌'} Você não tem permissão para cancelar este checkout!",
                    ephemeral=True
                )
                return
            
            # Confirmar cancelamento
            await inter.response.send_message(
                f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Cancelando checkout...",
                ephemeral=True
            )
            
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
                        print(f"✅ Pagamento Sync Wallet {payment_id} cancelado: {result}")
                    else:
                        print(f"⚠️ Payment ID não encontrado para cancelamento Sync Wallet")
                        
                except Exception as e:
                    # Não falhar o cancelamento do checkout se houver erro ao cancelar na API
                    print(f"❌ Erro ao cancelar pagamento Sync Wallet: {e}")
            
            # Atualizar status do carrinho
            cart["status"] = "cancelled"
            cart["cancelled_at"] = int(datetime.utcnow().timestamp())
            cart["cancelled_by"] = inter.author.id
            cart["updated_at"] = int(datetime.utcnow().timestamp())
            loja_data["carts"][thread_id] = cart
            db.save_document("loja_data", loja_data)
            
            # Tentar deletar o tópico
            try:
                thread = inter.channel
                
                if isinstance(thread, disnake.Thread):
                    # Enviar mensagem de cancelamento no thread (sempre content simples)
                    await thread.send(
                        f"{emoji.wrong} "
                        f"Checkout cancelado por {inter.author.mention}."
                    )
                    
                    # Mensagem administrativa - sempre content simples
                    await inter.edit_original_message(
                        content=f"{emoji.correct} Checkout cancelado! O tópico será deletado em breve.",
                        embed=None,
                        components=[]
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
                    
                    # Aguardar 5 segundos
                    import asyncio
                    await asyncio.sleep(5)
                    
                    # Deletar o tópico
                    try:
                        await thread.delete()
                    except disnake.errors.NotFound:
                        # Thread já foi deletada, não fazer nada
                        pass
                    except Exception as delete_error:
                        # Outro erro ao deletar, logar mas não quebrar
                        print(f"Erro ao deletar thread {thread.id}: {delete_error}")
            except disnake.errors.NotFound as e:
                # Thread ou mensagem não encontrada - pode ter sido deletada manualmente
                # Tentar editar mensagem apenas se ainda existir
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            content=f"{emoji.correct} Checkout cancelado!",
                            ephemeral=True
                        )
                    else:
                        try:
                            await inter.edit_original_message(
                                content=f"{emoji.correct} Checkout cancelado!",
                                embed=None,
                                components=[]
                            )
                        except disnake.errors.NotFound:
                            # Mensagem original não existe mais, não fazer nada
                            pass
                except Exception:
                    # Se não conseguir enviar/editar, não fazer nada
                    pass
            except Exception as e:
                # Outros erros - tentar editar mensagem apenas se ainda existir
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            content=f"{emoji.wrong if hasattr(emoji, 'error') else '❌'} Erro ao processar cancelamento: {e}",
                            ephemeral=True
                        )
                    else:
                        try:
                            await inter.edit_original_message(
                                content=f"{emoji.wrong if hasattr(emoji, 'error') else '❌'} Erro ao processar cancelamento: {e}",
                                embed=None,
                                components=[]
                            )
                        except disnake.errors.NotFound:
                            # Mensagem original não existe mais, não fazer nada
                            pass
                except Exception:
                    # Se não conseguir enviar/editar, não fazer nada
                    pass
    
    @commands.Cog.listener("on_button_click")
    async def on_copy_pix_button(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Formato: "copy_pix:<thread_id>"
        if custom_id.startswith("copy_pix:"):
            thread_id = custom_id.split(":", 1)[1]
            
            # Buscar código PIX
            loja_data = db.get_document("loja_data")
            cart = loja_data.get("carts", {}).get(thread_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong if hasattr(emoji, 'error') else '❌'} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            payment_data = cart.get("payment_data", {})
            
            # Tentar nova estrutura primeiro
            local_data = payment_data.get("local", {})
            copy_code = local_data.get("copy_code")
            
            # Fallback para estrutura antiga
            if not copy_code:
                copy_code = payment_data.get("copy_code")
            
            # Fallback para raw data
            if not copy_code:
                raw_data = payment_data.get("raw", {}) or payment_data.get("provider", {}).get("raw_response", {})
                copy_code = raw_data.get("pix_copia_cola") or raw_data.get("copy_paste") or raw_data.get("emv") or raw_data.get("qrCode")
            
            if not copy_code:
                await inter.response.send_message(
                    f"{emoji.wrong if hasattr(emoji, 'error') else '❌'} Código PIX não disponível!",
                    ephemeral=True
                )
                return
            
            # Enviar código PIX
            await inter.response.send_message(
                f"{copy_code}",
                ephemeral=True
            )
    
    @commands.Cog.listener("on_button_click")
    async def on_approve_manual_pix_button(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Formato: "approve_manual_pix:<thread_id>"
        if custom_id.startswith("approve_manual_pix:"):
            thread_id = custom_id.split(":", 1)[1]
            
            # Verificar se tem permissão (admin ou cargo específico)
            cargos_data = db.get_document("cargos")
            cargo_admin_id = cargos_data.get("cargo_admin")
            
            is_admin = inter.author.guild_permissions.administrator
            has_admin_role = False
            if cargo_admin_id:
                has_admin_role = any(role.id == int(cargo_admin_id) for role in inter.author.roles)
            
            if not (is_admin or has_admin_role):
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem permissão para aprovar pagamentos!",
                    ephemeral=True
                )
                return
            
            # Buscar carrinho (pode estar salvo como thread_id ou como string)
            loja_data = db.get_document("loja_data")
            cart_id = str(thread_id)  # Usar thread_id como cart_id (padrão)
            cart = loja_data.get("carts", {}).get(cart_id)
            
            # Se não encontrou, tentar buscar por thread_id como int
            if not cart:
                cart = loja_data.get("carts", {}).get(thread_id)
                if cart:
                    cart_id = thread_id
            
            # Se ainda não encontrou, buscar por thread_id no valor
            if not cart:
                for cart_key, cart_value in loja_data.get("carts", {}).items():
                    if cart_value.get("thread_id") == int(thread_id):
                        cart = cart_value
                        cart_id = cart_key  # Usar o cart_id correto encontrado
                        break
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            # Verificar se já foi aprovado
            if cart.get("status") == "approved":
                await inter.response.send_message(
                    f"{emoji.wrong} Este pagamento já foi aprovado!",
                    ephemeral=True
                )
                return
            
            # Fazer defer imediatamente para evitar timeout
            await inter.response.defer(ephemeral=True)
            
            try:
                payment_data = cart.get("payment_data", {})
                
                # Tentar nova estrutura primeiro
                provider_data = payment_data.get("provider", {})
                payment_id = provider_data.get("payment_id") or provider_data.get("charge_id")
                
                # Fallback para estrutura antiga
                if not payment_id:
                    payment_id = payment_data.get("payment_id") or payment_data.get("id")
                
                if payment_id:
                    await approve_manual_pix_payment(payment_id)
                
                # Atualizar status do carrinho
                cart["status"] = "approved"
                cart["approved_at"] = int(datetime.utcnow().timestamp())
                cart["approved_by"] = inter.author.id
                cart["updated_at"] = int(datetime.utcnow().timestamp())
                loja_data["carts"][cart_id] = cart
                db.save_document("loja_data", loja_data)
                
                # Notificar no tópico
                thread = inter.channel
                
                # A renomeação da thread será feita em _handle_payment_approved
                # baseada no tipo de entrega dos produtos (✅ para automático, ⌚ para manual)
                
                # Mensagem no thread - sempre content simples
                if isinstance(thread, disnake.Thread):
                    await thread.send(
                        f"{emoji.correct} **Pagamento aprovado por {inter.author.mention}!**"
                    )
                
                # Mensagem administrativa - usar followup já que fizemos defer
                await inter.followup.send(
                    content=f"{emoji.correct} Pagamento aprovado com sucesso! Processando entrega...",
                    ephemeral=True
                )
                
                # Processar entrega automática - USAR _handle_payment_approved para consistência
                # _handle_payment_approved já processa tudo (entrega, mensagens, logs, atualização da mensagem de checkout, etc.)
                from .checkout import _handle_payment_approved
                await _handle_payment_approved(cart_id, self.bot)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                # Mensagem administrativa - usar followup já que fizemos defer
                await inter.followup.send(
                    content=f"{emoji.wrong} Erro ao aprovar pagamento: {e}",
                    ephemeral=True
                )


def setup(bot: commands.Bot):
    bot.add_cog(CancelCheckout(bot))

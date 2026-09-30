"""
Task de monitoramento contínuo do Nubank IMAP
Verifica emails de 5 em 5 segundos automaticamente
"""
import asyncio
from datetime import datetime
from disnake.ext import commands, tasks
import disnake

from functions.database import database as db
from functions.payments.imap_nubank import monitor_nubank_imap_payments
from functions.emoji import emoji


class NubankMonitorTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stats = {
            "total_checks": 0,
            "total_approved": 0,
            "errors": 0,
            "started_at": None,
            "last_check": None,
            "last_approval": None
        }
        self.nubank_monitor.start()
        print("✅ Nubank IMAP Monitor iniciado (verifica a cada 5 segundos)")
    
    def cog_unload(self):
        """Para o monitor quando o cog for descarregado"""
        self.nubank_monitor.cancel()
        print("⏹️ Nubank IMAP Monitor parado")
    
    @tasks.loop(seconds=5)
    async def nubank_monitor(self):
        """Monitora emails do Nubank a cada 5 segundos"""
        try:
            # Verificar se está habilitado
            config = db.get_document("payment_configs") or {}
            nubank_config = config.get("nubank_imap", {})
            
            if not nubank_config.get("enabled"):
                # Log apenas a cada 60 verificações (5 minutos) para não poluir
                if self.stats["total_checks"] % 60 == 0:
                    print("⚠️ Nubank Monitor: Desabilitado (verifique as configurações)")
                return
            
            # Atualizar estatísticas
            self.stats["last_check"] = datetime.utcnow().isoformat()
            self.stats["total_checks"] += 1
            
            # Log de debug a cada 12 verificações (1 minuto)
            if self.stats["total_checks"] % 12 == 0:
                pending = db.get_document("nubank_pending_payments") or {}
                pending_count = sum(1 for p in pending.values() if isinstance(p, dict) and p.get("status") == "pending")
                print(f"🔍 Nubank Monitor: Verificando... ({self.stats['total_checks']} verificações, {pending_count} pendentes)")
            
            # Verificar emails
            approved_payments = await monitor_nubank_imap_payments()
            
            if approved_payments:
                self.stats["total_approved"] += len(approved_payments)
                self.stats["last_approval"] = datetime.utcnow().isoformat()
                
                print(f"\n✅ Nubank Monitor: {len(approved_payments)} pagamento(s) aprovado(s)!")
                
                # Processar cada pagamento aprovado
                for payment in approved_payments:
                    await self._handle_approved_payment(payment)
            
            # Verificar pagamentos pendentes antigos (a cada 20 verificações = 100 segundos)
            if self.stats["total_checks"] % 20 == 0:
                await self._check_pending_payments()
            
            # Log periódico a cada 100 verificações (8 minutos)
            if self.stats["total_checks"] % 100 == 0:
                pending = db.get_document("nubank_pending_payments") or {}
                pending_count = sum(1 for p in pending.values() if isinstance(p, dict) and p.get("status") == "pending")
                print(f"📊 Nubank Monitor: {self.stats['total_checks']} verificações, "
                      f"{self.stats['total_approved']} aprovados, "
                      f"{self.stats['errors']} erros, "
                      f"{pending_count} pendentes")
        
        except Exception as e:
            self.stats["errors"] += 1
            import traceback
            print(f"❌ Erro no Nubank Monitor: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
    
    @nubank_monitor.before_loop
    async def before_nubank_monitor(self):
        """Aguarda o bot estar pronto antes de iniciar"""
        await self.bot.wait_until_ready()
        self.stats["started_at"] = datetime.utcnow().isoformat()
    
    async def _check_pending_payments(self):
        """
        Verifica pagamentos pendentes antigos que podem ter sido perdidos
        Executa a cada 100 segundos (20 verificações)
        Otimizado: usa monitor_nubank_imap_payments que já processa tudo em batch
        """
        try:
            pending_payments = db.get_document("nubank_pending_payments") or {}
            
            # Filtrar apenas pagamentos pendentes
            pending_list = [
                (payment_id, data)
                for payment_id, data in pending_payments.items()
                if isinstance(data, dict) and data.get("status") == "pending"
            ]
            
            if not pending_list:
                return
            
            print(f"\n🔍 Verificando {len(pending_list)} pagamento(s) pendente(s) em batch...")
            
            # Usar a função de monitoramento que já processa tudo de uma vez
            # Isso é muito mais rápido que verificar um por um
            from functions.payments.imap_nubank import monitor_nubank_imap_payments
            
            # Esta função já busca todos os emails e compara com todos os pendentes de uma vez
            approved_payments = await monitor_nubank_imap_payments()
            
            if approved_payments:
                print(f"✅ {len(approved_payments)} pagamento(s) pendente(s) aprovado(s) em batch!")
                
                # Processar cada pagamento aprovado
                for payment in approved_payments:
                    await self._handle_approved_payment(payment)
                    self.stats["total_approved"] += 1
                    self.stats["last_approval"] = datetime.utcnow().isoformat()
            else:
                print(f"   ⏳ Nenhum pagamento pendente foi aprovado nesta verificação")
        
        except Exception as e:
            import traceback
            print(f"❌ Erro ao verificar pagamentos pendentes: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
    
    async def _handle_approved_payment(self, payment: dict):
        """
        Processa um pagamento aprovado automaticamente
        
        Args:
            payment: Dados do pagamento aprovado
        """
        payment_id = payment.get("payment_id")
        cart_id = payment.get("cart_id")
        amount = payment.get("amount")
        payer_name = payment.get("payer_name")
        
        print(f"💰 Processando pagamento aprovado: {payment_id}")
        print(f"   Carrinho: {cart_id}")
        print(f"   Valor: R$ {amount:.2f}")
        print(f"   Pagador: {payer_name or 'N/A'}")
        
        # Buscar informações do pagamento no tracking
        tracking = db.get_document("payment_tracking") or {"items": {}}
        
        # Procurar pelo payment_id nas mensagens de pagamento
        for msg_id, rec in tracking.get("items", {}).items():
            # Verificar se o payment_id corresponde
            rec_ids = rec.get("ids") or {}
            rec_payment_id = rec_ids.get("payment_id") or rec_ids.get("id")
            
            if rec_payment_id == payment_id or rec_payment_id == cart_id:
                # Encontrou! Atualizar a mensagem
                await self._update_payment_message(msg_id, rec, amount, payer_name)
                break
    
    async def _update_payment_message(self, msg_id: str, rec: dict, amount: float, payer_name: str = None):
        """
        Atualiza a mensagem de pagamento para 'Aprovado'
        
        Args:
            msg_id: ID da mensagem
            rec: Dados do registro de pagamento
            amount: Valor pago
            payer_name: Nome do pagador
        """
        try:
            # Atualizar status no tracking
            tracking = db.get_document("payment_tracking") or {"items": {}}
            if msg_id in tracking.get("items", {}):
                tracking["items"][msg_id]["status"] = "approved"
                db.save_document("payment_tracking", tracking)
            
            # Buscar e atualizar a mensagem no Discord
            channel_id = rec.get("channel_id")
            if not channel_id:
                return
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            try:
                message = await channel.fetch_message(int(msg_id))
                
                # Atualizar embed
                embed = message.embeds[0] if message.embeds else disnake.Embed(title="Pagamento")
                embed.color = disnake.Color.green()
                
                # Remover campo de status antigo se existir
                new_fields = [f for f in embed.fields if f.name.lower() != "status"]
                embed.clear_fields()
                for field in new_fields:
                    embed.add_field(name=field.name, value=field.value, inline=field.inline)
                
                # Adicionar novo status
                embed.add_field(
                    name="Status", 
                    value=f"{emoji.correct} **Aprovado**", 
                    inline=False
                )
                
                if payer_name:
                    embed.add_field(
                        name="Pagador",
                        value=payer_name,
                        inline=True
                    )
                
                embed.timestamp = datetime.utcnow()
                
                # Remover imagem do QR Code
                try:
                    embed.set_image(url=None)
                except:
                    pass
                
                # Atualizar mensagem
                await message.edit(embed=embed, components=[], attachments=[])
                
                print(f"✅ Mensagem {msg_id} atualizada para 'Aprovado'")
            
            except disnake.NotFound:
                print(f"⚠️ Mensagem {msg_id} não encontrada")
            except Exception as e:
                print(f"❌ Erro ao atualizar mensagem {msg_id}: {e}")
            
            # Enviar DM para o usuário
            user_id = rec.get("user_id")
            if user_id:
                await self._send_approval_dm(user_id, rec, amount, payer_name)
        
        except Exception as e:
            print(f"❌ Erro ao processar mensagem {msg_id}: {e}")
    
    async def _send_approval_dm(self, user_id: int, rec: dict, amount: float, payer_name: str = None):
        """
        Envia DM para o usuário informando que o pagamento foi aprovado
        
        Args:
            user_id: ID do usuário
            rec: Dados do registro de pagamento
            amount: Valor pago
            payer_name: Nome do pagador
        """
        try:
            user = self.bot.get_user(user_id)
            if not user:
                user = await self.bot.fetch_user(user_id)
            
            if not user:
                return
            
            # Criar embed de aprovação
            amount_str = f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            embed = disnake.Embed(
                title=f"{emoji.correct} Pagamento Aprovado!",
                description=f"Seu pagamento foi confirmado e aprovado automaticamente pelo sistema Nubank IMAP.",
                color=disnake.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="💰 Valor",
                value=amount_str,
                inline=True
            )
            
            embed.add_field(
                name="📦 Método",
                value=rec.get("method_label", "Nubank IMAP"),
                inline=True
            )
            
            if payer_name:
                embed.add_field(
                    name="👤 Pagador",
                    value=payer_name,
                    inline=True
                )
            
            if rec.get("description"):
                embed.add_field(
                    name="📝 Descrição",
                    value=rec.get("description"),
                    inline=False
                )
            
            # Link para a mensagem original
            guild_id = rec.get("guild_id")
            channel_id = rec.get("channel_id")
            message_id = rec.get("message_id")
            
            if guild_id and channel_id and message_id:
                url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
                components = [
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Ver Mensagem Original",
                            style=disnake.ButtonStyle.link,
                            url=url
                        )
                    )
                ]
                await user.send(embed=embed, components=components)
            else:
                await user.send(embed=embed)
            
            print(f"✅ DM de aprovação enviada para usuário {user_id}")
        
        except disnake.Forbidden:
            print(f"⚠️ Não foi possível enviar DM para usuário {user_id} (DMs fechadas)")
        except Exception as e:
            print(f"❌ Erro ao enviar DM para usuário {user_id}: {e}")
    
    @commands.slash_command(
        name="nubank-status",
        description="Ver estatísticas do monitor Nubank IMAP"
    )
    async def nubank_status(self, inter: disnake.AppCmdInter):
        """Mostra estatísticas do monitor Nubank IMAP"""
        from functions.perms import perms
        
        if not await perms.check(inter.author.id):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            return
        
        config = db.get_document("payment_configs") or {}
        nubank_config = config.get("nubank_imap", {})
        
        embed = disnake.Embed(
            title="📊 Nubank IMAP Monitor - Estatísticas",
            color=disnake.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Status
        is_enabled = nubank_config.get("enabled", False)
        is_running = self.nubank_monitor.is_running()
        
        status_emoji = emoji.on if is_enabled and is_running else emoji.off
        status_text = "Ativo ✅" if is_enabled and is_running else "Inativo ❌"
        
        embed.add_field(
            name="Status",
            value=f"{status_emoji} {status_text}",
            inline=True
        )
        
        embed.add_field(
            name="Intervalo",
            value="5 segundos",
            inline=True
        )
        
        embed.add_field(
            name="Total de Verificações",
            value=f"{self.stats['total_checks']:,}",
            inline=True
        )
        
        embed.add_field(
            name="Pagamentos Aprovados",
            value=f"{self.stats['total_approved']:,}",
            inline=True
        )
        
        embed.add_field(
            name="Erros",
            value=f"{self.stats['errors']:,}",
            inline=True
        )
        
        # Tempo de atividade
        if self.stats["started_at"]:
            started = datetime.fromisoformat(self.stats["started_at"])
            uptime = datetime.utcnow() - started
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
            
            embed.add_field(
                name="Tempo Ativo",
                value=uptime_str,
                inline=True
            )
        
        if self.stats["last_check"]:
            embed.add_field(
                name="Última Verificação",
                value=f"<t:{int(datetime.fromisoformat(self.stats['last_check']).timestamp())}:R>",
                inline=True
            )
        
        if self.stats["last_approval"]:
            embed.add_field(
                name="Última Aprovação",
                value=f"<t:{int(datetime.fromisoformat(self.stats['last_approval']).timestamp())}:R>",
                inline=True
            )
        
        # Configuração
        if nubank_config.get("email"):
            embed.add_field(
                name="Email Configurado",
                value=f"✅ {nubank_config.get('email')}",
                inline=False
            )
        
        if nubank_config.get("pix_key"):
            embed.add_field(
                name="Chave PIX",
                value=f"✅ {nubank_config.get('pix_key')} ({nubank_config.get('pix_key_type', 'N/A')})",
                inline=False
            )
        
        # Pagamentos pendentes
        pending = db.get_document("nubank_pending_payments") or {}
        pending_count = sum(1 for p in pending.values() if isinstance(p, dict) and p.get("status") == "pending")
        
        embed.add_field(
            name="Pagamentos Aguardando",
            value=f"⏳ {pending_count}",
            inline=True
        )
        
        embed.set_footer(text="Monitor Nubank IMAP automático")
        
        await inter.response.send_message(embed=embed, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(NubankMonitorTask(bot))


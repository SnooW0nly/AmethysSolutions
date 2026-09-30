"""
Handler de depósito de saldo
Gerencia o fluxo completo de depósito: tópico, pagamento, aprovação e adição de saldo
"""
import disnake
import asyncio
import io
from disnake.ext import commands
from datetime import datetime
from typing import Optional
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from ..balance_manager import BalanceManager
from .editor import DepositAmountModal


class DepositHandler(commands.Cog):
    """Handler para depósitos de saldo"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pending_deposits = {}
    
    def _get_config(self) -> dict:
        """Obtém configuração do sistema de saldo"""
        return db.get_document("loja_saldo_config") or {}
    
    async def _create_deposit_thread(
        self,
        inter: disnake.MessageInteraction,
        channel_id: int
    ) -> Optional[disnake.Thread]:
        """Cria tópico privado para o depósito no canal configurado"""
        try:
            channel = inter.guild.get_channel(channel_id)
            if not channel:
                return None
            
            # Nome do tópico
            thread_name = f"deposito-{inter.user.name}-{datetime.now().strftime('%d%m%H%M')}"
            
            # Criar tópico privado no canal
            thread = await channel.create_thread(
                name=thread_name,
                type=disnake.ChannelType.private_thread,
                invitable=False,
                reason=f"Depósito de saldo - {inter.user}"
            )
            
            # Não adicionar usuário explicitamente, será via menção na mensagem
            # await thread.add_user(inter.user)
            
            return thread
        except Exception as e:
            print(f"Erro ao criar tópico de depósito: {e}")
            return None
    
    async def _build_deposit_message(
        self,
        thread: disnake.Thread,
        user: disnake.User,
        config: dict,
        mode: str
    ) -> disnake.Message:
        """Constrói mensagem inicial do depósito"""
        deposit_settings = config.get("deposit_settings", {})
        min_deposit = deposit_settings.get("min_deposit", 5.0)
        max_deposit = deposit_settings.get("max_deposit", 1000.0)
        terms = deposit_settings.get("terms")
        
        # Calcular bônus
        bonus = config.get("bonus", {})
        bonus_type = bonus.get("type", "disabled")
        bonus_value = bonus.get("value", 0)
        
        bonus_text = ""
        if bonus_type == "percentage" and bonus_value > 0:
            bonus_text = f"\n{emoji.correct} **Bônus:** +{bonus_value}% no valor depositado!"
        elif bonus_type == "fixed" and bonus_value > 0:
            bonus_text = f"\n{emoji.correct} **Bônus:** +R$ {bonus_value:.2f} por depósito!"
        
        # Obter cor
        color_data = db.get_document("custom_colors") or {}
        primary_color = color_data.get("primary")
        
        # Botões
        buttons = [
            disnake.ui.Button(
                label="Definir Valor",
                emoji=emoji.dollar,
                style=disnake.ButtonStyle.green,
                custom_id="deposit_set_amount"
            ),
            disnake.ui.Button(
                label="Cancelar",
                emoji=emoji.wrong,
                style=disnake.ButtonStyle.danger,
                custom_id="deposit_cancel"
            )
        ]
        
        if terms:
            buttons.append(
                disnake.ui.Button(
                    label="Ver Termos",
                    emoji=emoji.textc,
                    style=disnake.ButtonStyle.grey,
                    custom_id="deposit_view_terms"
                )
            )
        
        action_row = disnake.ui.ActionRow(*buttons)
        
        # Preparar menções
        notify_role_id = deposit_settings.get("notify_role_id")
        mentions = f"{user.mention}"
        if notify_role_id:
            mentions += f" <@&{notify_role_id}>"
        
        # Enviar menções em mensagem separada e deletar
        mention_msg = await thread.send(mentions)
        await asyncio.sleep(0.5)  # Dar tempo para notificação processar
        try:
            await mention_msg.delete()
        except:
            pass
        
        if mode == "components":
            container_kwargs = {}
            if primary_color:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color.replace("#", ""), 16))
                except:
                    pass
            
            content_text = (
                f"# {emoji.wallet} Depósito de Saldo\n"
                f"Configure o valor do seu depósito abaixo.\n\n"
                f"{emoji.dollar} **Faixa de Depósito:** `R$ {min_deposit:.2f}` - `R$ {max_deposit:.2f}`"
                f"{bonus_text}"
            )
            
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(content_text),
                disnake.ui.Separator(),
                action_row,
                **container_kwargs
            )
            
            msg = await thread.send(
                components=[container],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            embed_kwargs = {}
            if primary_color:
                try:
                    embed_kwargs["color"] = int(primary_color.replace("#", ""), 16)
                except:
                    pass
            
            embed = disnake.Embed(
                title=f"{emoji.wallet} Depósito de Saldo",
                description=(
                    f"Configure o valor do seu depósito abaixo.\n\n"
                    f"{emoji.dollar} **Faixa de Depósito:** `R$ {min_deposit:.2f}` - `R$ {max_deposit:.2f}`"
                    f"{bonus_text}"
                ),
                **embed_kwargs
            )
            
            msg = await thread.send(embed=embed, components=[action_row])
        
        return msg
    
    @commands.Cog.listener("on_button_click")
    async def on_deposit_button(self, inter: disnake.MessageInteraction):
        """Handler para botões de depósito"""
        custom_id = inter.component.custom_id
        
        # Botão de abrir depósito no painel
        if custom_id == "deposit_saldo_open":
            config = self._get_config()
            
            if not config.get("enabled"):
                await inter.response.send_message(
                    f"{emoji.wrong} Sistema de saldo não está disponível no momento.",
                    ephemeral=True
                )
                return
            
            deposit_panel = config.get("deposit_panel", {})
            channel_id = deposit_panel.get("channel_id")
            
            if not channel_id:
                await inter.response.send_message(
                    f"{emoji.wrong} Canal de depósitos não configurado.",
                    ephemeral=True
                )
                return
            
            await inter.response.defer(ephemeral=True)
            
            # Criar tópico no canal
            thread = await self._create_deposit_thread(inter, int(channel_id))
            
            if not thread:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao criar tópico de depósito. Tente novamente.",
                    ephemeral=True
                )
                return
            
            # Enviar mensagem inicial
            mode = db.get_document("custom_mode").get("mode", "components")
            msg = await self._build_deposit_message(thread, inter.user, config, mode)
            
            # Salvar depósito pendente
            deposit_id = str(thread.id)
            self.pending_deposits[deposit_id] = {
                "user_id": inter.user.id,
                "guild_id": inter.guild.id,
                "thread_id": thread.id,
                "message_id": msg.id,
                "created_at": int(datetime.utcnow().timestamp()),
                "status": "awaiting_amount"
            }
            
            await inter.followup.send(
                f"{emoji.correct} Tópico de depósito criado! Acesse: {thread.mention}",
                ephemeral=True
            )
        
        # Definir valor
        elif custom_id == "deposit_set_amount":
            config = self._get_config()
            deposit_settings = config.get("deposit_settings", {})
            
            await inter.response.send_modal(
                DepositAmountModal(
                    min_amount=deposit_settings.get("min_deposit", 5.0),
                    max_amount=deposit_settings.get("max_deposit", 1000.0),
                    thread_id=inter.channel.id
                )
            )
        
        # Cancelar depósito
        elif custom_id == "deposit_cancel":
            thread = inter.channel
            if isinstance(thread, disnake.Thread):
                await inter.response.send_message(
                    f"{emoji.correct} Depósito cancelado. Tópico será deletado.",
                    ephemeral=True
                )
                
                # Limpar do pending
                deposit_id = str(thread.id)
                if deposit_id in self.pending_deposits:
                    del self.pending_deposits[deposit_id]
                
                # Deletar tópico
                try:
                    await asyncio.sleep(2)
                    await thread.delete()
                except Exception as e:
                    print(f"Erro ao deletar tópico de depósito: {e}")
        
        # Ver termos
        elif custom_id == "deposit_view_terms":
            config = self._get_config()
            terms = config.get("deposit_settings", {}).get("terms")
            
            if terms:
                await inter.response.send_message(
                    f"**Termos e Condições:**\n\n{terms}",
                    ephemeral=True
                )
            else:
                await inter.response.send_message(
                    f"{emoji.wrong} Termos não configurados.",
                    ephemeral=True
                )
        
        # Confirmar depósito (após definir valor)
        elif custom_id.startswith("deposit_confirm:"):
            parts = custom_id.split(":")
            if len(parts) >= 2:
                try:
                    amount = float(parts[1])
                    await self._process_deposit_payment(inter, amount)
                except ValueError:
                    await inter.response.send_message(
                        f"{emoji.wrong} Erro ao processar valor.",
                        ephemeral=True
                    )
    
    async def _process_deposit_payment(self, inter: disnake.MessageInteraction, amount: float):
        """Processa o pagamento do depósito"""
        await inter.response.defer()
        
        config = self._get_config()
        thread = inter.channel
        deposit_id = str(thread.id)
        
        # Calcular bônus
        bonus = BalanceManager.calculate_bonus(amount)
        total_credit = amount + bonus
        
        # Importar função de criar pagamento e extrair dados
        try:
            from modules.loja.cart.checkout import (
                _create_payment, _extract_urls, _extract_qr_image, 
                _extract_payment_ids, _http_get_bytes, _api_base_root
            )
        except ImportError:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao processar pagamento.",
                ephemeral=True
            )
            return
        
        # Criar pagamento PIX
        payment_data = await _create_payment(
            payment_method="pix",
            amount=amount,
            user=inter.user,
            description=f"Depósito de saldo - R$ {amount:.2f}"
        )
        
        if not payment_data or "error" in payment_data:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao gerar pagamento: {payment_data.get('error') if payment_data else 'Sem dados'}",
                ephemeral=True
            )
            return
        
        # Extrair dados do pagamento (igual ao cart)
        checkout_url, copy_code = _extract_urls(payment_data or {})
        qr_bytes, qr_url = _extract_qr_image(payment_data or {})
        
        # Fallback para dados diretos
        if not qr_bytes and payment_data and payment_data.get("qr_code_bytes"):
            qr_bytes = payment_data.get("qr_code_bytes")
        
        if not copy_code and payment_data:
            copy_code = payment_data.get("pix_copia_cola") or payment_data.get("copy_paste") or payment_data.get("emv")
        
        payment_ids = _extract_payment_ids(payment_data or {})
        payment_provider = payment_data.get("_provider") if payment_data else None
        
        # Se tiver URL do QR Code, tentar baixar os bytes
        if qr_url and not qr_bytes:
            base_root = _api_base_root()
            full_url = str(qr_url)
            if full_url.startswith("/"):
                full_url = base_root + full_url
            fetched = await _http_get_bytes(full_url)
            if fetched:
                qr_bytes = fetched
                qr_url = None
        
        # Atualizar depósito pendente
        if deposit_id in self.pending_deposits:
            self.pending_deposits[deposit_id]["status"] = "awaiting_payment"
            self.pending_deposits[deposit_id]["amount"] = amount
            self.pending_deposits[deposit_id]["bonus"] = bonus
            self.pending_deposits[deposit_id]["payment_ids"] = payment_ids
            self.pending_deposits[deposit_id]["payment_provider"] = payment_provider
        
        # Obter cor e modo
        mode = db.get_document("custom_mode").get("mode", "components")
        color_data = db.get_document("custom_colors") or {}
        primary_color = color_data.get("primary")
        
        # Botão de cancelar
        cancel_btn = disnake.ui.Button(
            label="Cancelar",
            emoji=emoji.wrong,
            style=disnake.ButtonStyle.danger,
            custom_id="deposit_cancel"
        )
        
        bonus_text = ""
        if bonus > 0:
            bonus_text = f"\n{emoji.correct} **Bônus:** `+R$ {bonus:.2f}`\n{emoji.wallet} **Total a Creditar:** `R$ {total_credit:.2f}`"
        
        if mode == "components":
            container_kwargs = {}
            if primary_color:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color.replace("#", ""), 16))
                except:
                    pass
            
            # Construir itens do container
            container_items = []
            
            # Texto principal
            content_text = (
                f"# {emoji.wallet} Pagamento do Depósito\n\n"
                f"{emoji.dollar} **Valor:** `R$ {amount:.2f}`{bonus_text}\n\n"
                f"Escaneie o QR Code ou copie o código PIX abaixo:"
            )
            container_items.append(disnake.ui.TextDisplay(content_text))
            
            # Preparar arquivo QR Code
            files = []
            if qr_bytes:
                files.append(disnake.File(io.BytesIO(qr_bytes), filename="qrcode.png"))
                # Adicionar MediaGallery no mesmo container
                container_items.append(
                    disnake.ui.MediaGallery(
                        disnake.MediaGalleryItem(media="attachment://qrcode.png")
                    )
                )
            
            # Adicionar código PIX
            if copy_code:
                container_items.append(disnake.ui.Separator())
                container_items.append(disnake.ui.TextDisplay(f"```{copy_code}```"))
            
            # Adicionar botão cancelar
            container_items.append(disnake.ui.Separator())
            container_items.append(disnake.ui.ActionRow(cancel_btn))
            
            # Montar container único
            container = disnake.ui.Container(*container_items, **container_kwargs)
            
            # Apagar mensagem antiga e enviar nova
            try:
                deposit_data = self.pending_deposits.get(deposit_id)
                if deposit_data:
                    message_id = deposit_data.get("message_id")
                    if message_id:
                        try:
                            old_msg = await thread.fetch_message(message_id)
                            await old_msg.delete()
                        except:
                            pass
            except:
                pass
            
            # Enviar nova mensagem com container único
            new_msg = await thread.send(
                components=[container],
                files=files if files else None,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            
            # Atualizar message_id
            if deposit_id in self.pending_deposits:
                self.pending_deposits[deposit_id]["message_id"] = new_msg.id
        else:
            embed_kwargs = {}
            if primary_color:
                try:
                    embed_kwargs["color"] = int(primary_color.replace("#", ""), 16)
                except:
                    pass
            
            embed = disnake.Embed(
                title=f"{emoji.wallet} Pagamento do Depósito",
                description=(
                    f"{emoji.dollar} **Valor:** `R$ {amount:.2f}`{bonus_text}\n\n"
                    f"Escaneie o QR Code ou copie o código PIX abaixo."
                ),
                **embed_kwargs
            )
            
            if copy_code:
                embed.add_field(name="Código PIX", value=f"```{copy_code}```", inline=False)
            
            # Preparar arquivo QR Code se tiver
            files = []
            if qr_bytes:
                files.append(disnake.File(io.BytesIO(qr_bytes), filename="qrcode.png"))
                embed.set_image(url="attachment://qrcode.png")
            elif qr_url:
                embed.set_image(url=qr_url)
            
            # Apagar mensagem antiga e enviar nova
            try:
                deposit_data = self.pending_deposits.get(deposit_id)
                if deposit_data:
                    message_id = deposit_data.get("message_id")
                    if message_id:
                        try:
                            old_msg = await thread.fetch_message(message_id)
                            await old_msg.delete()
                        except:
                            pass
            except:
                pass
            
            new_msg = await thread.send(
                embed=embed, 
                components=[disnake.ui.ActionRow(cancel_btn)],
                files=files if files else None
            )
            
            # Atualizar message_id
            if deposit_id in self.pending_deposits:
                self.pending_deposits[deposit_id]["message_id"] = new_msg.id
        
        # Iniciar monitoramento do pagamento
        self.bot.loop.create_task(
            self._monitor_deposit_payment(
                deposit_id=deposit_id,
                payment_ids=payment_ids,
                payment_provider=payment_provider,
                user=inter.user,
                guild=inter.guild,
                channel=thread,
                amount=amount,
                bonus=bonus
            )
        )
    
    async def _monitor_deposit_payment(
        self,
        deposit_id: str,
        payment_ids: dict,
        payment_provider: str,
        user: disnake.User,
        guild: disnake.Guild,
        channel: disnake.Thread,
        amount: float,
        bonus: float
    ):
        """Monitora o pagamento do depósito"""
        try:
            from modules.loja.cart.checkout import _check_single_payment_status
        except ImportError:
            return
        
        payment_id = payment_ids.get("payment_id") or payment_ids.get("paymentId") or payment_ids.get("id") or payment_ids.get("txid")
        
        if not payment_id:
            return
        
        max_attempts = 360  # 60 minutos
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            await asyncio.sleep(10)  # Verificar a cada 10 segundos
            
            # Verificar se depósito ainda está pendente
            if deposit_id not in self.pending_deposits:
                return  # Cancelado
            
            try:
                is_finished, status = await _check_single_payment_status(
                    cart_id=deposit_id,
                    payment_id=payment_id,
                    payment_method="pix",
                    payment_provider=payment_provider,
                    bot=self.bot
                )
                
                if is_finished:
                    if status == "approved":
                        await self._handle_deposit_approved(
                            deposit_id=deposit_id,
                            user=user,
                            guild=guild,
                            channel=channel,
                            amount=amount,
                            bonus=bonus
                        )
                    else:
                        await self._handle_deposit_failed(
                            deposit_id=deposit_id,
                            channel=channel,
                            reason="Pagamento não aprovado"
                        )
                    return
            except Exception as e:
                print(f"Erro ao verificar pagamento de depósito: {e}")
        
        # Timeout
        await self._handle_deposit_failed(
            deposit_id=deposit_id,
            channel=channel,
            reason="Pagamento expirado"
        )
    
    async def _handle_deposit_approved(
        self,
        deposit_id: str,
        user: disnake.User,
        guild: disnake.Guild,
        channel: disnake.Thread,
        amount: float,
        bonus: float
    ):
        """Processa depósito aprovado"""
        # Adicionar saldo
        BalanceManager.add_balance(
            user_id=user.id,
            amount=amount,
            bonus=bonus,
            deposit_id=deposit_id,
            payment_method="pix"
        )
        
        total_credit = amount + bonus
        
        # Obter cor e modo
        mode = db.get_document("custom_mode").get("mode", "components")
        color_data = db.get_document("custom_colors") or {}
        primary_color = color_data.get("primary")
        
        bonus_text = ""
        if bonus > 0:
            bonus_text = f"\n{emoji.correct} **Bônus:** `+R$ {bonus:.2f}`"
        
        if mode == "components":
            container_kwargs = {}
            if primary_color:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color.replace("#", ""), 16))
                except:
                    pass
            
            # Apagar mensagem antiga e enviar nova
            try:
                deposit_data = self.pending_deposits.get(deposit_id)
                if deposit_data:
                    message_id = deposit_data.get("message_id")
                    if message_id:
                        try:
                            old_msg = await channel.fetch_message(message_id)
                            await old_msg.delete()
                        except:
                            pass
            except:
                pass
            
            await channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.correct} Depósito Aprovado!\n\n"
                            f"{emoji.dollar} **Valor:** `R$ {amount:.2f}`{bonus_text}\n"
                            f"{emoji.wallet} **Total Creditado:** `R$ {total_credit:.2f}`\n\n"
                            f"Seu saldo foi atualizado com sucesso!"
                        ),
                        **container_kwargs
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            embed_kwargs = {}
            if primary_color:
                try:
                    embed_kwargs["color"] = int(primary_color.replace("#", ""), 16)
                except:
                    pass
            
            embed = disnake.Embed(
                title=f"{emoji.correct} Depósito Aprovado!",
                description=(
                    f"{emoji.dollar} **Valor:** `R$ {amount:.2f}`{bonus_text}\n"
                    f"{emoji.wallet} **Total Creditado:** `R$ {total_credit:.2f}`\n\n"
                    f"Seu saldo foi atualizado com sucesso!"
                ),
                **embed_kwargs
            )
            
            # Apagar mensagem antiga e enviar nova
            try:
                deposit_data = self.pending_deposits.get(deposit_id)
                if deposit_data:
                    message_id = deposit_data.get("message_id")
                    if message_id:
                        try:
                            old_msg = await channel.fetch_message(message_id)
                            await old_msg.delete()
                        except:
                            pass
            except:
                pass
            
            await channel.send(embed=embed)
        
        # Limpar do pending
        if deposit_id in self.pending_deposits:
            del self.pending_deposits[deposit_id]
        
        # Enviar log
        try:
            from modules.loja.logs.purchase_logs import PurchaseLogsSystem
            logs_system = PurchaseLogsSystem(self.bot)
            
            await logs_system.send_order_log(
                guild=guild,
                user=user,
                action="deposit_approved",
                details={
                    "amount": amount,
                    "bonus": bonus,
                    "total_credit": total_credit,
                    "deposit_id": deposit_id
                }
            )
        except Exception as e:
            print(f"Erro ao enviar log de depósito: {e}")
        
        # Fechar tópico após 30 segundos
        await asyncio.sleep(30)
        try:
            await channel.edit(archived=True, locked=True)
        except:
            pass
    
    async def _handle_deposit_failed(
        self,
        deposit_id: str,
        channel: disnake.Thread,
        reason: str
    ):
        """Processa depósito falho"""
        # Obter cor e modo
        mode = db.get_document("custom_mode").get("mode", "components")
        color_data = db.get_document("custom_colors") or {}
        primary_color = color_data.get("primary")
        
        if mode == "components":
            container_kwargs = {}
            if primary_color:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color.replace("#", ""), 16))
                except:
                    pass
            
            # Apagar mensagem antiga e enviar nova
            try:
                deposit_data = self.pending_deposits.get(deposit_id)
                if deposit_data:
                    message_id = deposit_data.get("message_id")
                    if message_id:
                        try:
                            old_msg = await channel.fetch_message(message_id)
                            await old_msg.delete()
                        except:
                            pass
            except:
                pass
            
            await channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.wrong} Depósito Cancelado\n\n"
                            f"**Motivo:** {reason}\n\n"
                            f"Você pode tentar novamente usando o painel de depósito."
                        ),
                        **container_kwargs
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            embed_kwargs = {}
            if primary_color:
                try:
                    embed_kwargs["color"] = int(primary_color.replace("#", ""), 16)
                except:
                    pass
            
            embed = disnake.Embed(
                title=f"{emoji.wrong} Depósito Cancelado",
                description=(
                    f"**Motivo:** {reason}\n\n"
                    f"Você pode tentar novamente usando o painel de depósito."
                ),
                **embed_kwargs
            )

            # Apagar mensagem antiga e enviar nova
            try:
                deposit_data = self.pending_deposits.get(deposit_id)
                if deposit_data:
                    message_id = deposit_data.get("message_id")
                    if message_id:
                        try:
                            old_msg = await channel.fetch_message(message_id)
                            await old_msg.delete()
                        except:
                            pass
            except:
                pass
            
            await channel.send(embed=embed)
        
        # Limpar do pending
        if deposit_id in self.pending_deposits:
            del self.pending_deposits[deposit_id]
        
        # Fechar tópico após 10 segundos
        await asyncio.sleep(10)
        try:
            await channel.edit(archived=True, locked=True)
        except:
            pass


def setup(bot: commands.Bot):
    bot.add_cog(DepositHandler(bot))

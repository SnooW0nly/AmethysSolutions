import disnake
import time
from typing import Optional
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils

class SubscriptionManager:
    @staticmethod
    def is_vip(user_id: int, system: str = None) -> bool:
        """
        Verifica se um usuário possui uma assinatura VIP ativa.
        Se 'system' for fornecido, verifica se a integração específica está ativa.
        """
        subs_doc = db.get_document("loja_subscriptions") or {}
        user_subs = subs_doc.get(str(user_id), {})
        now = int(time.time())
        
        for sub_data in user_subs.values():
            expires_at = sub_data.get("expires_at", 0)
            if expires_at == 0 or expires_at > now:
                if system:
                    integracao = sub_data.get("integracao_vip", {})
                    if integracao.get(system):
                        return True
                else:
                    return True
        return False

    @staticmethod
    async def activate_subscription(
        user: disnake.User,
        product_id: str,
        campo_id: str,
        product_name: str,
        campo_name: str,
        guild: Optional[disnake.Guild] = None,
        thread: Optional[disnake.Thread] = None
    ) -> bool:
        """
        Ativa ou renova uma assinatura para o usuário.
        """
        try:
            products = db.get_document("loja_products")
            product = products.get(product_id, {})
            campo = product.get("campos", {}).get(campo_id, {})
            
            cargos_config = campo.get("cargos") or {}
            duracao_minutos = cargos_config.get("duracao_minutos", 0)
            
            # Carregar assinaturas do usuário
            subs_doc = db.get_document("loja_subscriptions") or {}
            user_id_str = str(user.id)
            user_subs = subs_doc.get(user_id_str, {})
            
            # Chave única para esta assinatura (produto + campo)
            sub_key = f"{product_id}:{campo_id}"
            current_sub = user_subs.get(sub_key, {})
            
            now = int(time.time())
            
            # Calcular nova expiração
            if duracao_minutos > 0:
                duration_seconds = duracao_minutos * 60
                # Se já tiver uma assinatura ativa, somar os dias
                if current_sub and current_sub.get("expires_at", 0) > now:
                    new_expiry = current_sub["expires_at"] + duration_seconds
                else:
                    new_expiry = now + duration_seconds
            else:
                new_expiry = 0  # Permanente
            
            # Atualizar dados da assinatura
            user_subs[sub_key] = {
                "product_id": product_id,
                "campo_id": campo_id,
                "product_name": product_name,
                "campo_name": campo_name,
                "activated_at": now,
                "expires_at": new_expiry,
                "integracao_vip": campo.get("integracao_vip", {}),
                "cargos": cargos_config
            }
            
            subs_doc[user_id_str] = user_subs
            db.save_document("loja_subscriptions", subs_doc)
            
            # Aplicar cargos se estiver no servidor
            roles_added = []
            if guild:
                member = guild.get_member(user.id)
                if member:
                    # Adicionar cargos
                    for role_id in cargos_config.get("adicionar", []):
                        role = guild.get_role(int(role_id))
                        if role:
                            try:
                                await member.add_roles(role)
                                roles_added.append(role.name)
                            except:
                                pass
                    
                    # Remover cargos
                    for role_id in cargos_config.get("remover", []):
                        role = guild.get_role(int(role_id))
                        if role:
                            try:
                                await member.remove_roles(role)
                            except:
                                pass

            # Enviar mensagem de ativação
            await SubscriptionManager._send_activation_message(
                user=user,
                product_name=product_name,
                campo_name=campo_name,
                new_expiry=new_expiry,
                roles_added=roles_added,
                thread=thread
            )
            
            return True
            
        except Exception as e:
            print(f"[Subscription] Erro ao ativar assinatura: {e}")
            return False

    @staticmethod
    async def _send_activation_message(
        user: disnake.User,
        product_name: str,
        campo_name: str,
        new_expiry: int,
        roles_added: list,
        thread: Optional[disnake.Thread] = None
    ):
        expiry_text = f"<t:{new_expiry}:F> (<t:{new_expiry}:R>)" if new_expiry > 0 else "Permanente"
        roles_text = f"\n- Cargos recebidos: {', '.join(roles_added)}" if roles_added else ""
        
        msg_content = (
            f"# {emoji.correct} **Assinatura Ativada!**\n"
            f"Sua assinatura de **{product_name} ({campo_name})** foi ativada com sucesso!\n\n"
            f"- Validade: {expiry_text}{roles_text}\n"
            f"- Use `/vip` para ver seus benefícios."
        )

        # Tentar enviar na DM
        try:
            await user.send(msg_content)
        except disnake.Forbidden:
            if thread:
                await thread.send(f"{emoji.warn} {user.mention}, sua DM está fechada! Sua assinatura foi ativada.\n{msg_content}")
        
        # Se tiver thread, confirmar lá também
        if thread:
            await thread.send(f"{emoji.correct} Assinatura ativada para {user.mention}!")

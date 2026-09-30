import disnake
import io
import asyncio
from datetime import datetime
from functions.emoji import emoji
from functions.database import database as db
from .update_api import get_websocket_manager, start_recover_members, get_recovery_status
from .task_manager import create_task, update_task_status, get_task

class CreateTaskModal(disnake.ui.Modal):
    def __init__(self, bot=None):
        self.bot = bot
        components = [
            disnake.ui.Label(
                "Tipo de Tarefa",
                disnake.ui.StringSelect(
                    custom_id="task_type",
                    placeholder="Selecione o tipo de tarefa",
                    options=[
                        disnake.SelectOption(
                            label="Recuperar membros",
                            value="recover_members",
                            emoji=emoji.reload,
                            description="Recuperar membros verificados no OAuth2"
                        ),
                        disnake.SelectOption(
                            label="Verificar membros",
                            value="verify_members",
                            emoji=emoji.double_check,
                            description="Verificar membros verificados no OAuth2"
                        ),
                        disnake.SelectOption(
                            label="Listar membros",
                            value="list_members",
                            emoji=emoji.embed,
                            description="Listar membros verificados no OAuth2"
                        )
                    ]
                ),
            ),
            # Campo opcional para informar o ID do servidor alvo
            disnake.ui.TextInput(
                label="ID do Servidor (opcional)",
                custom_id="guild_id",
                placeholder="Cole o ID do servidor (deixe vazio para usar o atual)",
                required=False,
                max_length=25,
            ),
        ]

        super().__init__(
            title="Criar Nova Task",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        valores = inter.resolved_values
        
        task_type = valores.get("task_type", "")
        guild_id_str = (valores.get("guild_id") or "").strip()
        
        if isinstance(task_type, list):
            task_type = task_type[0] if task_type else ""
        
        # Valida os dados
        if not task_type.strip():
            await inter.response.send_message(f"{emoji.wrong} Tipo de tarefa é obrigatório!", ephemeral=True)
            return
        # Validar guild_id se informado
        if guild_id_str and not guild_id_str.isdigit():
            await inter.response.send_message(f"{emoji.wrong} ID do servidor inválido. Use apenas números.", ephemeral=True)
            return
        
        # Por enquanto, apenas confirma que recebeu a seleção
        task_names = {
            "recover_members": "Recuperar membros",
            "verify_members": "Verificar membros", 
            "send_dms": "Enviar DMs",
            "list_members": "Listar membros"
        }
        
        task_name = task_names.get(task_type, "Tarefa desconhecida")
        
        # Criar task na database (inclui guild_id se informado)
        task_initial_data = {}
        if guild_id_str:
            task_initial_data["guild_id"] = guild_id_str

        task_id = create_task(task_type, str(inter.user.id), inter.user.display_name, task_initial_data)
        
        if not task_id:
            await inter.response.send_message("❌ Erro ao criar task na database.", ephemeral=True)
            return
        
        # Se for listar membros, executar a lógica específica
        if task_type == "list_members":
            await self._handle_list_members(inter, task_id)
        elif task_type == "verify_members":
            await self._handle_verify_members(inter, task_id)
        elif task_type == "recover_members":
            await self._handle_recover_members(inter, task_id)
        else:
            # Para outras tasks, apenas marcar como finalizada por enquanto
            update_task_status(task_id, "finished", {"message": "Task criada com sucesso"})
            await inter.response.send_message(f"{emoji.correct} Task '{task_name}' criada com sucesso!\n\n**Tipo:** `{task_type}`\n\n*Implementação da lógica da task será adicionada em breve.*", ephemeral=True)

    async def _handle_list_members(self, inter: disnake.ModalInteraction, task_id: str):
        """Manipula a tarefa de listar membros"""
        try:
            # Enviar mensagem de loading
            await inter.response.send_message(f"{emoji.loading} Aguarde enquanto fazemos tudo por você...", ephemeral=True)
            
            # Obter configuração do cloud
            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            
            if not bot_id:
                update_task_status(task_id, "error", {"error": "Bot não configurado"})
                await inter.edit_original_message(f"{emoji.wrong} Bot não configurado. Configure as credenciais primeiro.")
                return
            
            # Obter WebSocket manager
            ws_manager = get_websocket_manager()
            
            if not ws_manager.is_connected():
                update_task_status(task_id, "error", {"error": "WebSocket não conectado"})
                await inter.edit_original_message(f"{emoji.wrong} WebSocket não está conectado. Verifique a conexão.")
                return
            
            # Fazer requisição para listar membros
            response = await ws_manager.list_members(bot_id)
            
            if not response.get("success"):
                update_task_status(task_id, "error", {"error": response.get('message', 'Erro desconhecido')})
                await inter.edit_original_message(f"{emoji.wrong} Erro ao listar membros: {response.get('message', 'Erro desconhecido')}")
                return
            
            # Processar dados dos membros
            members_data = response.get("data", {}).get("members", [])
            
            if not members_data:
                update_task_status(task_id, "finished", {"members_count": 0, "message": "Nenhum membro encontrado"})
                await inter.edit_original_message(f"{emoji.information} Nenhum membro encontrado.")
                return
            
            # Gerar arquivo TXT
            txt_content = self._generate_members_txt(members_data)
            
            # Criar arquivo
            txt_file = disnake.File(
                io.StringIO(txt_content),
                filename=f"membros_lista_{len(members_data)}.txt",
                description="Lista de membros do servidor"
            )
            
            # Enviar arquivo no privado
            try:
                await inter.user.send(
                    f"**Total de membros:** {len(members_data)}\n"
                    f"**Gerado em:** <t:{int(disnake.utils.utcnow().timestamp())}:F>",
                    file=txt_file
                )
                
                update_task_status(task_id, "finished", {
                    "members_count": len(members_data),
                    "message": "Lista de membros enviada no privado"
                })
                await inter.edit_original_message(f"{emoji.correct} Lista de membros enviada no seu privado!")
                
            except disnake.Forbidden:
                update_task_status(task_id, "error", {"error": "Não foi possível enviar no privado"})
                await inter.edit_original_message(f"{emoji.wrong} Não foi possível enviar no seu privado. Verifique se você permite DMs do bot.")
            except Exception as e:
                update_task_status(task_id, "error", {"error": str(e)})
                await inter.edit_original_message(f"{emoji.wrong} Erro ao enviar arquivo: {str(e)}")
                
        except Exception as e:
            update_task_status(task_id, "error", {"error": str(e)})
            await inter.edit_original_message(f"{emoji.wrong} Erro ao processar solicitação: {str(e)}")

    def _generate_members_txt(self, members_data: list) -> str:
        """Gera o conteúdo do arquivo TXT com os dados dos membros"""
        txt_lines = []
        
        for i, member in enumerate(members_data, 1):
            txt_lines.extend([
                f"--- {member.get('username', 'N/A')}#{member.get('discriminator', '0000')} ---",
                f"ID: {member.get('id', 'N/A')}",
                f"Email: {member.get('email', 'N/A')}",
                f"IP: {member.get('ip', 'N/A')}",
                f"Verificado: {'Sim' if member.get('verified', False) else 'Não'}",
                f"Data de verificação: {member.get('verified_at', 'N/A')}",
                ""
            ])
        
        return "\n".join(txt_lines)

    async def _handle_verify_members(self, inter: disnake.ModalInteraction, task_id: str):
        """Manipula a tarefa de verificar membros"""
        try:
            # Enviar mensagem de loading
            await inter.response.send_message(f"{emoji.loading} Aguarde enquanto verificamos todos os membros...", ephemeral=True)
            
            # Obter configuração do cloud
            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            
            if not bot_id:
                update_task_status(task_id, "error", {"error": "Bot não configurado"})
                await inter.edit_original_message(f"{emoji.wrong} Bot não configurado. Configure as credenciais primeiro.")
                return
            
            # Obter WebSocket manager
            ws_manager = get_websocket_manager()
            
            if not ws_manager.is_connected():
                update_task_status(task_id, "error", {"error": "WebSocket não conectado"})
                await inter.edit_original_message(f"{emoji.wrong} WebSocket não está conectado. Verifique a conexão.")
                return
            
            # Fazer requisição para listar membros primeiro
            response = await ws_manager.list_members(bot_id)
            
            if not response.get("success"):
                update_task_status(task_id, "error", {"error": response.get('message', 'Erro desconhecido')})
                await inter.edit_original_message(f"{emoji.wrong} Erro ao obter lista de membros: {response.get('message', 'Erro desconhecido')}")
                return
            
            # Processar dados dos membros
            members_data = response.get("data", {}).get("members", [])
            
            if not members_data:
                update_task_status(task_id, "finished", {"verified_count": 0, "unverified_count": 0, "message": "Nenhum membro encontrado para verificar"})
                await inter.edit_original_message(f"{emoji.information} Nenhum membro encontrado para verificar.")
                return
            
            # Verificar cada membro individualmente
            verified_count = 0
            unverified_count = 0
            unverified_members = []
            
            for member in members_data:
                try:
                    # Fazer verificação individual do membro
                    verification_result = await self._verify_single_member(member, bot_id)
                    
                    if verification_result.get("verified", False):
                        verified_count += 1
                    else:
                        unverified_count += 1
                        unverified_members.append({
                            "id": member.get("id"),
                            "username": member.get("username"),
                            "reason": verification_result.get("reason", "Desautorizou a verificação")
                        })
                        
                        # Enviar log de desverificação se houver
                        if verification_result.get("unverified"):
                            await self._send_unverified_log(member, verification_result.get("reason", "Desautorizou a verificação"))
                    
                    # Pequena pausa entre verificações para não sobrecarregar
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"Erro ao verificar membro {member.get('id', 'unknown')}: {e}")
                    unverified_count += 1
            
            # Atualizar status da task
            update_task_status(task_id, "finished", {
                "verified_count": verified_count,
                "unverified_count": unverified_count,
                "total_members": len(members_data),
                "unverified_members": unverified_members,
                "message": f"Verificação concluída: {verified_count} verificados, {unverified_count} desverificados"
            })
            
            # Mostrar mensagem de conclusão
            await inter.edit_original_message("O processo de verificação de membro foi concluído.")
                
        except Exception as e:
            update_task_status(task_id, "error", {"error": str(e)})
            await inter.edit_original_message(f"{emoji.wrong} Erro ao processar verificação: {str(e)}")

    async def _verify_single_member(self, member: dict, bot_id: str) -> dict:
        """Verifica um único membro"""
        try:
            # Aqui você pode implementar a lógica específica de verificação
            # Por enquanto, vou simular uma verificação
            # Em uma implementação real, você faria uma requisição para a API do Discord
            # ou para o sistema de verificação do bot
            
            # Simular verificação (substitua por lógica real)
            import random
            is_verified = random.choice([True, True, True, False])  # 75% chance de estar verificado
            
            if is_verified:
                return {"verified": True}
            else:
                return {
                    "verified": False,
                    "unverified": True,
                    "reason": "Desautorizou a verificação"
                }
                
        except Exception as e:
            print(f"Erro ao verificar membro individual: {e}")
            return {"verified": False, "reason": f"Erro na verificação: {str(e)}"}

    async def _send_unverified_log(self, member: dict, reason: str):
        """Envia log de desverificação"""
        try:
            from .auth_logs import send_auth_log
            
            # Criar dados de log para desverificação
            auth_data = {
                "success": False,
                "user": {
                    "id": member.get("id"),
                    "username": member.get("username"),
                    "discriminator": member.get("discriminator", "0000"),
                    "email": member.get("email"),
                    "ip": member.get("ip"),
                    "unverified_at": disnake.utils.utcnow().isoformat(),
                    "reason": reason
                }
            }
            
            # Enviar log
            await send_auth_log(self.bot, auth_data)
            
        except Exception as e:
            # Apenas logar o erro, não enviar mensagem para o usuário
            print(f"Erro ao enviar log de desverificação: {e}")

    async def _handle_recover_members(self, inter: disnake.ModalInteraction, task_id: str):
        """Manipula a tarefa de recuperar membros verificados"""
        try:
            # Enviar mensagem de loading
            await inter.response.send_message(f"{emoji.loading} Iniciando recuperação... Validando configurações e conectando à API.", ephemeral=True)
            
            # Obter configuração do cloud
            cloud_config = db.get_document("cloud_data") or {}
            auth_bot_id = cloud_config.get("client_id")
            
            if not auth_bot_id:
                update_task_status(task_id, "error", {"error": "Bot não configurado"})
                await inter.edit_original_message(f"{emoji.wrong} Bot não configurado. Configure as credenciais primeiro.")
                return
            
            # Determinar servidor alvo (pode não estar no cache deste bot)
            target_guild_id = None
            try:
                task = get_task(task_id)
                target_guild_id = (task or {}).get("data", {}).get("guild_id")
            except Exception:
                target_guild_id = None

            if not target_guild_id:
                target_guild_id = str(inter.guild.id)

            # Obter guild de destino
            target_guild = self.bot.get_guild(int(target_guild_id))
            if not target_guild:
                update_task_status(task_id, "error", {"error": "Servidor não encontrado"})
                await inter.edit_original_message(f"{emoji.wrong} Servidor com ID `{target_guild_id}` não encontrado. Verifique se o bot principal está neste servidor.")
                return

            # Verificar se o bot de Auth está no servidor
            auth_bot_present = False
            auth_bot_member = None
            if auth_bot_id:
                try:
                    auth_bot_member = target_guild.get_member(int(auth_bot_id))
                    if not auth_bot_member:
                        # Tentar buscar se não estiver no cache
                        try:
                            auth_bot_member = await target_guild.fetch_member(int(auth_bot_id))
                        except disnake.NotFound:
                            auth_bot_member = None
                    auth_bot_present = auth_bot_member is not None
                except Exception:
                    auth_bot_present = False
                    auth_bot_member = None

            # Verificar se o bot principal está no servidor
            main_bot_member = target_guild.get_member(self.bot.user.id)
            main_bot_present = main_bot_member is not None

            # Se algum bot não estiver presente, enviar mensagem com botão de convite
            if not auth_bot_present or not main_bot_present:
                missing_bots = []
                invite_buttons = []

                if not auth_bot_present:
                    missing_bots.append("Bot de Autenticação")
                    auth_invite_url = f"https://discord.com/api/oauth2/authorize?client_id={auth_bot_id}&permissions=8&scope=bot%20applications.commands"
                    invite_buttons.append(
                        disnake.ui.Button(
                            label="Adicionar Bot de Autenticação",
                            style=disnake.ButtonStyle.link,
                            url=auth_invite_url
                        )
                    )

                if not main_bot_present:
                    missing_bots.append("Bot Principal")
                    main_bot_invite_url = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands"
                    invite_buttons.append(
                        disnake.ui.Button(
                            label="Adicionar Bot Principal",
                            style=disnake.ButtonStyle.link,
                            url=main_bot_invite_url
                        )
                    )

                missing_bots_text = " e ".join(missing_bots)
                error_message = f"**{missing_bots_text} não {'está' if len(missing_bots) == 1 else 'estão'} presente(s) no servidor.**\n\nClique no botão abaixo para adicionar {'o bot' if len(missing_bots) == 1 else 'os bots'} necessário(s) antes de iniciar a recuperação."

                view = disnake.ui.View()
                for button in invite_buttons:
                    view.add_item(button)

                update_task_status(task_id, "error", {"error": f"{missing_bots_text} não presente(s) no servidor"})
                await inter.edit_original_message(content=error_message, view=view)
                return

            # Chamar API HTTP para iniciar recuperação (igual fluxo do gift)
            start_response = await start_recover_members(str(target_guild_id))
            if not start_response.get("success"):
                update_task_status(task_id, "error", {"error": start_response.get("message", "Erro desconhecido")})
                await inter.edit_original_message(f"{emoji.wrong} Erro ao iniciar recuperação: {start_response.get('message', 'Erro desconhecido')}")
                return
            
            resp_data = start_response.get("data", {})
            recovery_id = resp_data.get("recovery_id")
            estimated_time = resp_data.get("estimated_time")
            estimated_ts = resp_data.get("estimated_completion_timestamp")

            update_task_status(task_id, "running", {
                "recovery_id": recovery_id,
                "server_id": str(target_guild_id),
                "estimated_time": estimated_time,
                "estimated_completion": estimated_ts
            })

            status_msg = f"{emoji.correct} **Recuperação iniciada!**\n\n"
            status_msg += f"**Servidor alvo:** `{target_guild_id}`\n"
            if estimated_time:
                status_msg += f"**Estimativa:** {estimated_time}\n"
            if estimated_ts:
                status_msg += f"**Conclusão estimada:** <t:{int(estimated_ts)}:R>\n"
            if recovery_id:
                status_msg += f"**ID do processo:** `{recovery_id}`\n"
            status_msg += "\nVou atualizar o progresso aqui a cada 5s."

            await inter.edit_original_message(status_msg)

            # Iniciar polling via HTTP até concluir
            asyncio.create_task(self._poll_recovery_status(inter, task_id, recovery_id))
                
        except Exception as e:
            update_task_status(task_id, "error", {"error": str(e)})
            await inter.edit_original_message(f"{emoji.wrong} Erro ao processar recuperação: {str(e)}")

    async def _recover_single_member(self, member: dict, guild: disnake.Guild) -> dict:
        """Recupera um único membro para o servidor usando access_token"""
        try:
            user_id = int(member.get("id"))
            access_token = member.get("access_token")
            
            # Verificar se o usuário já está no servidor
            existing_member = guild.get_member(user_id)
            if existing_member:
                return {
                    "success": False,
                    "reason": "Usuário já está no servidor"
                }
            
            # Verificar se tem access_token
            if not access_token:
                return {
                    "success": False,
                    "reason": "Usuário não tem access_token válido"
                }
            
            # Usar a API do Discord para adicionar o membro ao servidor usando access_token
            try:
                import aiohttp
                
                # Endpoint da API do Discord para adicionar membro ao servidor
                url = f"https://discord.com/api/v10/guilds/{guild.id}/members/{user_id}"
                
                # Obter token do bot do arquivo cloud/data.json
                from functions.database import database as db
                cloud_config = db.get_document("cloud_data") or {}
                bot_token = cloud_config.get("token")
                
                if not bot_token:
                    return {
                        "success": False,
                        "reason": "Token do bot não encontrado no cloud/data.json"
                    }
                
                headers = {
                    "Authorization": f"Bot {bot_token}",
                    "Content-Type": "application/json"
                }
                
                # Dados para adicionar o membro
                data = {
                    "access_token": access_token
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.put(url, headers=headers, json=data) as response:
                        response_text = await response.text()
                        
                        if response.status == 201:
                            return {
                                "success": True,
                                "message": "Usuário adicionado ao servidor"
                            }
                        elif response.status == 204:
                            return {
                                "success": True,
                                "message": "Usuário já estava no servidor"
                            }
                        else:
                            error_data = await response.json() if response_text else {}
                            error_message = error_data.get('message', f'Erro HTTP {response.status}')
                            return {
                                "success": False,
                                "reason": f"Erro da API: {error_message}"
                            }
                    
            except Exception as api_error:
                return {
                    "success": False,
                    "reason": f"Erro na API do Discord: {str(api_error)}"
                }
                
        except Exception as e:
            print(f"Erro ao recuperar membro individual: {e}")
            return {"success": False, "reason": f"Erro na recuperação: {str(e)}"}

    async def _poll_recovery_status(self, inter: disnake.ModalInteraction, task_id: str, recovery_id: str):
        """Faz polling do status de recuperação e finaliza a task quando concluir."""
        try:
            # Poll a cada 5s até status final
            final_states = {"completed", "completed_with_errors", "failed", "aborted"}
            start_time = datetime.now()
            timeout_warned = False
            
            while True:
                await asyncio.sleep(5)
                
                # Verificar se passou de 15 minutos
                elapsed_time = (datetime.now() - start_time).total_seconds()
                if elapsed_time > 900 and not timeout_warned:  # 15 minutos = 900 segundos
                    timeout_warned = True
                    try:
                        timeout_msg = f"{emoji.clock} **Aviso:** A task está demorando mais de 15 minutos.\n\n"
                        timeout_msg += "As mensagens efêmeras têm limite de tempo. Você será notificado no canal de logs quando a task finalizar."
                        await inter.edit_original_message(timeout_msg)
                    except Exception:
                        pass  # Mensagem efêmera pode ter expirado
                
                status_resp = await get_recovery_status(recovery_id)
                if not status_resp.get("success"):
                    # Não conseguimos obter status agora; continuar tentando
                    continue
                data = status_resp.get("data", {})
                status = str(data.get("status", "")).lower()
                processed = data.get("processed_members", 0)
                total = data.get("total_members", 0)
                failed = data.get("failed_members", 0)
                skipped = data.get("skipped_already_in_guild", 0)
                progress = data.get("progress")
                success_rate = data.get("success_rate") or data.get("success_rate")
                succeeded = max(0, processed - failed - skipped)

                # Atualização parcial da task
                update_task_status(task_id, "running", {
                    "processed": processed,
                    "total": total,
                    "failed": failed,
                    "skipped": skipped,
                    "progress": progress,
                    "status": status,
                })

                # Atualizar mensagem de progresso para o usuário
                try:
                    progress_text = f"{emoji.loading} **Recuperação em andamento...**\n\n"
                    progress_text += f"**Servidor:** `{(get_task(task_id) or {}).get('data', {}).get('server_id') or ''}`\n"
                    if progress is not None:
                        progress_text += f"**Progresso:** `{progress}%`\n"
                    progress_text += f"**Processados:** `{processed}/{total}`\n"
                    progress_text += f"**Adicionados:** `{succeeded}`\n"
                    progress_text += f"**Falhas:** `{failed}` | **Já estavam:** `{skipped}`"
                    await inter.edit_original_message(progress_text)
                except Exception:
                    pass

                if status in final_states:
                    failures = data.get("failures", [])
                    update_task_status(task_id, "finished", {
                        "recovered_count": max(0, processed - failed - skipped),
                        "failed_count": failed,
                        "skipped_already_in_guild": skipped,
                        "total_verified": total,
                        "failed_members": failures,
                        "final_status": status,
                        "message": f"Recuperação finalizada: {processed - failed - skipped} adicionados, {failed} falhas, {skipped} já no servidor"
                    })

                    # Mensagem final
                    final_msg = f"{emoji.correct} **Recuperação concluída!**\n\n"
                    final_msg += f"**Servidor:** `{(get_task(task_id) or {}).get('data', {}).get('server_id') or ''}`\n"
                    final_msg += f"**Adicionados:** `{max(0, processed - failed - skipped)}`\n"
                    final_msg += f"**Falhas:** `{failed}` | **Já estavam:** `{skipped}`\n"
                    final_msg += f"**Total processados:** `{processed}/{total}`\n"
                    
                    # Tentar atualizar mensagem efêmera
                    try:
                        await inter.edit_original_message(final_msg)
                    except Exception:
                        pass  # Mensagem efêmera expirou
                    
                    # Enviar notificação no canal de logs do sistema
                    await self._send_task_completion_log(inter, task_id, {
                        "type": "recover_members",
                        "server_id": (get_task(task_id) or {}).get('data', {}).get('server_id') or '',
                        "added": max(0, processed - failed - skipped),
                        "failed": failed,
                        "skipped": skipped,
                        "total": processed,
                        "elapsed_time": elapsed_time
                    })
                    
                    break
        except Exception as e:
            update_task_status(task_id, "error", {"error": str(e)})

    async def _send_task_completion_log(self, inter: disnake.ModalInteraction, task_id: str, task_data: dict):
        """Envia notificação de conclusão da task no canal de logs do sistema"""
        try:
            # Obter canal de logs do sistema
            canais_config = db.get_document("canais") or {}
            log_channel_id = canais_config.get("canal_de_logs_do_sistema")
            
            if not log_channel_id:
                return  # Sem canal configurado, não envia
            
            log_channel = self.bot.get_channel(int(log_channel_id))
            if not log_channel:
                return  # Canal não encontrado
            
            # Obter informações da task
            task = get_task(task_id)
            if not task:
                return
            
            # Formatar tempo decorrido
            elapsed_seconds = int(task_data.get("elapsed_time", 0))
            elapsed_minutes = elapsed_seconds // 60
            elapsed_hours = elapsed_minutes // 60
            elapsed_minutes = elapsed_minutes % 60
            
            if elapsed_hours > 0:
                time_str = f"{elapsed_hours}h {elapsed_minutes}m"
            else:
                time_str = f"{elapsed_minutes}m {elapsed_seconds % 60}s"
            
            # Criar embed de notificação
            custom_colors = db.get_document("custom_colors") or {}
            primary_color = custom_colors.get("primary", "#7289da")
            
            embed = disnake.Embed(
                title=f"{emoji.correct} Task Concluída",
                description=f"A task **{task.get('name', 'Desconhecida')}** foi finalizada com sucesso!",
                color=int(primary_color.replace("#", ""), 16),
                timestamp=datetime.now()
            )
            
            # Adicionar campos baseados no tipo de task
            task_type = task_data.get("type", "")
            
            if task_type == "recover_members":
                embed.add_field(
                    name=f"{emoji.arrow} Servidor",
                    value=f"`{task_data.get('server_id', 'N/A')}`",
                    inline=True
                )
                embed.add_field(
                    name=f"{emoji.member} Membros Adicionados",
                    value=f"`{task_data.get('added', 0)}`",
                    inline=True
                )
                embed.add_field(
                    name=f"{emoji.clock} Tempo Decorrido",
                    value=f"`{time_str}`",
                    inline=True
                )
                embed.add_field(
                    name=f"{emoji.wrong} Falhas",
                    value=f"`{task_data.get('failed', 0)}`",
                    inline=True
                )
                embed.add_field(
                    name=f"{emoji.information} Já no Servidor",
                    value=f"`{task_data.get('skipped', 0)}`",
                    inline=True
                )
                embed.add_field(
                    name=f"{emoji.reload} Total Processados",
                    value=f"`{task_data.get('total', 0)}`",
                    inline=True
                )
            
            # Adicionar informações do criador
            created_by = task.get("created_by", {})
            embed.set_footer(
                text=f"Iniciado por {created_by.get('name', 'Desconhecido')}",
                icon_url=inter.user.display_avatar.url if inter.user.display_avatar else None
            )
            
            # Enviar mensagem com @everyone
            await log_channel.send(
                content="@everyone",
                embed=embed,
                allowed_mentions=disnake.AllowedMentions(everyone=True)
            )
            
        except Exception as e:
            print(f"Erro ao enviar log de conclusão da task: {e}")
            import traceback
            traceback.print_exc()
    
    async def _show_add_bot_button(self, inter: disnake.ModalInteraction, task_id: str, bot_id: str):
        """Mostra botão para adicionar o bot de auth ao servidor"""
        try:
            # Gerar link de convite para o bot com scopes corretos
            invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot_id}&permissions=8&scope=bot%20applications.commands"
            
            # Atualizar status da task
            update_task_status(task_id, "error", {
                "error": "Bot de auth não está no servidor",
                "bot_id": bot_id,
                "invite_url": invite_url
            })
            
            # Criar embed com informações
            embed = disnake.Embed(
                title="Bot de Autenticação Não Encontrado",
                description=f"O bot de autenticação (`{bot_id}`) não está presente neste servidor.\n\nPara recuperar membros, você precisa adicionar o bot de autenticação ao servidor primeiro.",
                color=0xff6b6b
            )
            
            # Criar botão com link
            components = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Bot de Auth",
                        style=disnake.ButtonStyle.url,
                        url=invite_url,
                        emoji="🔗"
                    )
                )
            ]
            
            await inter.edit_original_message(embed=embed, components=components)
            
        except Exception as e:
            print(f"Erro ao mostrar botão de adicionar bot: {e}")
            await inter.edit_original_message(f"{emoji.wrong} Erro ao gerar link de convite: {str(e)}")

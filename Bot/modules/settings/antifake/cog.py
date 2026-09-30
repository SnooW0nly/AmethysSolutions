import disnake
from disnake.ext import commands
from datetime import datetime, timezone
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class AntiFakeConfig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return AntiFakeConfig._panel_embed(inter) if mode == "embed" else AntiFakeConfig._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        config = db.get_document("antifake_config") or {}
        
        enabled = config.get("enabled", False)
        min_days = config.get("min_days", 7)
        block_bots = config.get("block_bots", False)
        block_no_avatar = config.get("block_no_avatar", False)
        
        # Obter canal de logs do documento canais
        canais_config = db.get_document("canais") or {}
        log_channel_id = canais_config.get("canal_de_logs_de_anti_falso")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        status_text = f"{emoji.on if enabled else emoji.off} **Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        status_text += f"{emoji.on if block_bots else emoji.off}  **Bloquear bots:** `{'Ativado' if block_bots else 'Desativado'}`\n"
        status_text += f"{emoji.on if block_no_avatar else emoji.off}  **Bloquear sem foto de perfil:** `{'Ativado' if block_no_avatar else 'Desativado'}`\n"
        status_text += f"{emoji.calendar} **Dias mínimos:** `{min_days} dias`\n"
        
        if log_channel_id:
            channel = inter.guild.get_channel(int(log_channel_id)) if inter.guild else None
            if channel:
                status_text += f"{emoji.textc} **Canal de logs:** {channel.mention}\n"
            else:
                status_text += f"{emoji.wrong} **Canal de logs:** Canal não encontrado\n"
        else:
            status_text += f"{emoji.textc} **Canal de logs:** Não configurado\n"
            status_text += f"{emoji.textc} Configure em: Configurações > Canais\n"

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Configurações > **Anti-Fake**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(status_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar" if not enabled else "Desativar",
                        emoji=emoji.power,
                        style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                        custom_id="Antifake_Toggle"
                    ),
                    disnake.ui.Button(
                        label="Definições",
                        emoji=emoji.settings2,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Antifake_ConfigDays"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Configuracoes")
            )
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        config = db.get_document("antifake_config") or {}
        
        enabled = config.get("enabled", False)
        min_days = config.get("min_days", 7)
        block_bots = config.get("block_bots", False)
        block_no_avatar = config.get("block_no_avatar", False)
        
        # Obter canal de logs do documento canais
        canais_config = db.get_document("canais") or {}
        log_channel_id = canais_config.get("canal_de_logs_de_anti_falso")

        status_text = f"{emoji.on if enabled else emoji.off} **Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        status_text += f"{emoji.calendar} **Dias mínimos:** `{min_days} dias`\n"
        status_text += f"{emoji.on if block_bots else emoji.off} **Bloquear bots:** `{'Ativado' if block_bots else 'Desativado'}`\n"
        status_text += f"{emoji.on if block_no_avatar else emoji.off} **Bloquear sem foto de perfil:** `{'Ativado' if block_no_avatar else 'Desativado'}`\n"
        
        if log_channel_id:
            channel = inter.guild.get_channel(int(log_channel_id)) if inter.guild else None
            if channel:
                status_text += f"{emoji.textc} **Canal de logs:** {channel.mention}\n"
            else:
                status_text += f"{emoji.wrong} **Canal de logs:** Canal não encontrado\n"
        else:
            status_text += f"{emoji.textc} **Canal de logs:** Não configurado\n"
            status_text += f"{emoji.textc} **Configure em:** Configurações > Canais\n"

        embed = disnake.Embed(
            title="Anti-Fake",
            description=(
                "-# Painel > Configurações > **Anti-Fake**\n\n"
                f"{status_text}"
            )
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ativar" if not enabled else "Desativar",
                    emoji=emoji.power,
                    style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                    custom_id="Antifake_Toggle"
                ),
                disnake.ui.Button(
                    label="Definições",
                    emoji=emoji.settings2,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Antifake_ConfigDays"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Configuracoes")
            )
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Antifake_Toggle":
            config = db.get_document("antifake_config") or {}
            if not isinstance(config, dict):
                config = {}
            
            current = config.get("enabled", False)
            config["enabled"] = not current
            db.save_document("antifake_config", config)
            
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = AntiFakeConfig.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Antifake_ConfigDays":
            config = db.get_document("antifake_config") or {}
            current_days = str(config.get("min_days", 7))
            current_block_bots = config.get("block_bots", False)
            current_block_no_avatar = config.get("block_no_avatar", False)
            await inter.response.send_modal(ConfigDaysModal(current_days, current_block_bots, current_block_no_avatar))


class ConfigDaysModal(disnake.ui.Modal):
    """Modal para configurar dias mínimos"""
    
    def __init__(self, current_days: str = "7", block_bots: bool = False, block_no_avatar: bool = False):
        components = [
            disnake.ui.TextInput(
                label="Dias mínimos",
                custom_id="min_days",
                placeholder="7",
                value=current_days,
                max_length=4,
                required=True
            ),
            disnake.ui.Label(
                text="Bloquear bots",
                component=disnake.ui.StringSelect(
                    placeholder="Bloquear bots ou não",
                    custom_id="block_bots",
                    required=True,
                    options=[
                        disnake.SelectOption(
                            label="Ativado",
                            description="Bots também serão bloqueados",
                            emoji=emoji.on,
                            value="block_bots_True",
                            default=block_bots
                        ),
                        disnake.SelectOption(
                            label="Desativado",
                            description="Bots não serão bloqueados",
                            emoji=emoji.off,
                            value="block_bots_False",
                            default=not block_bots
                        ),
                    ],
                ),
                description="Define se bots também devem ser bloqueados pelo sistema.",
            ),
            disnake.ui.Label(
                text="Bloquear contas sem foto de perfil",
                component=disnake.ui.StringSelect(
                    placeholder="Bloquear contas sem foto de perfil ou não",
                    custom_id="block_no_avatar",
                    required=True,
                    options=[
                        disnake.SelectOption(
                            label="Ativado",
                            description="Contas sem foto de perfil serão bloqueadas",
                            emoji=emoji.on,
                            value="block_no_avatar_True",
                            default=block_no_avatar
                        ),
                        disnake.SelectOption(
                            label="Desativado",
                            description="Contas sem foto de perfil não serão bloqueadas",
                            emoji=emoji.off,
                            value="block_no_avatar_False",
                            default=not block_no_avatar
                        ),
                    ],
                ),
                description="Define se contas sem foto de perfil também devem ser bloqueadas.",
            ),
        ]
        super().__init__(title="Definições Anti Fake", components=components, custom_id="antifake_days_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        try:
            days_str = inter.text_values.get("min_days", "7").strip()
            try:
                min_days = int(days_str)
                if min_days < 0:
                    raise ValueError("Dias não podem ser negativos")
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.wrong} Valor inválido! Digite um número válido maior ou igual a 0.",
                    ephemeral=True
                )
                return
            
            # Obter valor do select de bloquear bots
            valores = inter.resolved_values
            block_bots_value = valores.get("block_bots")
            if isinstance(block_bots_value, (list, tuple)):
                block_bots_value = block_bots_value[0] if block_bots_value else None
            block_bots = True if block_bots_value == "block_bots_True" else False
            
            # Obter valor do select de bloquear sem foto de perfil
            block_no_avatar_value = valores.get("block_no_avatar")
            if isinstance(block_no_avatar_value, (list, tuple)):
                block_no_avatar_value = block_no_avatar_value[0] if block_no_avatar_value else None
            block_no_avatar = True if block_no_avatar_value == "block_no_avatar_True" else False
            
            # Salvar configuração
            config = db.get_document("antifake_config") or {}
            if not isinstance(config, dict):
                config = {}
            
            config["min_days"] = min_days
            config["block_bots"] = block_bots
            config["block_no_avatar"] = block_no_avatar
            db.save_document("antifake_config", config)
            
            # Atualizar painel diretamente
            mode = db.get_document("custom_mode").get("mode")
            panel = AntiFakeConfig.panel(inter)
            if mode == "embed":
                await inter.response.edit_message(content=None, **panel)
            else:
                await inter.response.edit_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao processar modal: {str(e)}",
                    ephemeral=True
                )


class AntiFakeSystem(commands.Cog):
    """Sistema que verifica e expulsa contas suspeitas"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener("on_member_join")
    async def on_member_join_check(self, member: disnake.Member):
        try:
            # Verificar se o membro tem guild válida
            if not member.guild:
                return
            
            config = db.get_document("antifake_config") or {}
            
            # Verificar se está ativado
            if not config.get("enabled", False):
                return
            
            # Verificar se deve bloquear bots
            block_bots = config.get("block_bots", False)
            if not block_bots and member.bot:
                return  # Ignorar bots se não estiver configurado para bloquear
            
            # Verificar se deve bloquear contas sem foto de perfil
            block_no_avatar = config.get("block_no_avatar", False)
            
            # Verificar se o usuário já está autorizado
            authorized_users = db.get_document("antifake_authorized") or {}
            if not isinstance(authorized_users, dict):
                authorized_users = {}
            
            authorized_list = authorized_users.get("users", [])
            if str(member.id) in authorized_list or member.id in authorized_list:
                return  # Usuário autorizado, não fazer nada
            
            # Obter configurações
            min_days = config.get("min_days", 7)
            
            # Obter canal de logs do documento canais
            canais_config = db.get_document("canais") or {}
            log_channel_id = canais_config.get("canal_de_logs_de_anti_falso")
            
            # Calcular idade da conta
            account_age = (datetime.now(timezone.utc) - member.created_at).days
            
            # Verificar se conta não tem foto de perfil (quando configurado)
            has_no_avatar = member.avatar is None
            
            # Se a conta tiver menos dias que o mínimo OU não tiver foto (quando configurado), expulsar
            if account_age < min_days or (block_no_avatar and has_no_avatar):
                # Salvar informações do membro ANTES de expulsar (para usar no log)
                member_info = {
                    "id": member.id,
                    "name": str(member),
                    "mention": member.mention,
                    "created_at": member.created_at
                }
                
                # Criar log ID único
                log_id = f"{member.id}_{int(datetime.now(timezone.utc).timestamp())}"
                
                # EXPULSAR O MEMBRO PRIMEIRO (antes de criar o log)
                kicked = False
                try:
                    # Verificar se o bot tem permissão para expulsar
                    bot_member = member.guild.me
                    if not bot_member.guild_permissions.kick_members:
                        pass  # Sem permissão
                    # Verificar hierarquia de cargos
                    elif bot_member.top_role <= member.top_role and member.id != member.guild.owner_id:
                        pass  # Cargo muito alto
                    else:
                        # Expulsar o membro
                        await member.kick(reason=f"Anti-Fake: Conta com {account_age} dias (mínimo: {min_days} dias)" + (" | Sem foto de perfil" if block_no_avatar and has_no_avatar else ""))
                        kicked = True
                except disnake.Forbidden:
                    pass  # Sem permissão
                except disnake.HTTPException:
                    pass  # Erro HTTP
                except disnake.NotFound:
                    kicked = True  # Já foi removido por outro sistema
                except Exception:
                    pass  # Outro erro
                
                # Salvar log
                logs_data = db.get_document("antifake_logs") or {}
                if not isinstance(logs_data, dict):
                    logs_data = {}
                
                if "logs" not in logs_data:
                    logs_data["logs"] = {}
                
                logs_data["logs"][log_id] = {
                    "user_id": member_info["id"],
                    "username": member_info["name"],
                    "account_age_days": account_age,
                    "min_days_required": min_days,
                    "no_avatar": has_no_avatar,
                    "status": "pending",
                    "kicked": kicked,
                    "created_at": int(datetime.now(timezone.utc).timestamp()),
                    "guild_id": member.guild.id if member.guild else None
                }
                db.save_document("antifake_logs", logs_data)
                
                # Enviar log no canal se configurado
                if log_channel_id:
                    channel = member.guild.get_channel(int(log_channel_id)) if member.guild else None
                    if channel:
                        mode = db.get_document("custom_mode").get("mode", "embed")
                        colors = db.get_document("custom_colors") or {}
                        primary_color_hex = colors.get("primary")
                        
                        if mode == "components":
                            container_kwargs = {}
                            if primary_color_hex:
                                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                            
                            try:
                                log_msg = await channel.send(
                                    components=[
                                        disnake.ui.Container(
                                            disnake.ui.TextDisplay(f"# {emoji.shield}\n-# **Anti-Fake - Conta Suspeita**"),
                                            disnake.ui.Separator(),
                                            disnake.ui.TextDisplay(
                                                f"-# **Usuário:** {member_info['mention']} (`{member_info['id']}`)\n"
                                                f"-# **Idade da conta:** `{account_age} dias`\n"
                                                f"-# **Mínimo exigido:** `{min_days} dias`\n"
                                                f"-# **Sem foto de perfil:** `{'Sim' if has_no_avatar else 'Não'}`\n"
                                                f"-# **Conta criada:** <t:{int(member_info['created_at'].timestamp())}:f>"
                                            ),
                                            **container_kwargs
                                        ),
                                        disnake.ui.ActionRow(
                                            disnake.ui.Button(
                                                label="Liberar Entrada",
                                                emoji=emoji.correct,
                                                style=disnake.ButtonStyle.green,
                                                custom_id=f"antifake_approve:{log_id}"
                                            )
                                        )
                                    ],
                                    flags=disnake.MessageFlags(is_components_v2=True)
                                )
                            except Exception:
                                log_msg = None
                        else:
                            embed_color = disnake.Color.red()
                            if primary_color_hex:
                                try:
                                    embed_color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                                except:
                                    pass
                            
                            embed = disnake.Embed(
                                title=f"{emoji.shield} Anti-Fake - Conta Suspeita",
                                color=embed_color,
                                timestamp=datetime.now(timezone.utc)
                            )
                            embed.add_field(name="Usuário", value=f"{member_info['mention']} (`{member_info['id']}`)", inline=True)
                            embed.add_field(name="Idade da Conta", value=f"{account_age} dias", inline=True)
                            embed.add_field(name="Mínimo Exigido", value=f"{min_days} dias", inline=True)
                            embed.add_field(name="Sem Foto de Perfil", value="Sim" if has_no_avatar else "Não", inline=True)
                            embed.add_field(name="Conta Criada", value=f"<t:{int(member_info['created_at'].timestamp())}:f>", inline=False)
                            
                            try:
                                log_msg = await channel.send(
                                    embed=embed,
                                    components=[
                                        disnake.ui.ActionRow(
                                            disnake.ui.Button(
                                                label="Liberar Entrada",
                                                emoji=emoji.correct,
                                                style=disnake.ButtonStyle.green,
                                                custom_id=f"antifake_approve:{log_id}"
                                            )
                                        )
                                    ]
                                )
                            except Exception:
                                log_msg = None
                        
                        # Salvar message_id se a mensagem foi enviada com sucesso
                        if log_msg:
                            logs_data["logs"][log_id]["message_id"] = log_msg.id
                            db.save_document("antifake_logs", logs_data)
                    
        except Exception:
            # Erro silencioso - não quebrar o fluxo
            pass


class AntiFakeModeration(commands.Cog):
    """Handler para aprovar usuários"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener("on_button_click")
    async def on_approve_user(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id.startswith("antifake_approve:"):
            # Verificar permissão (admin)
            cargos_data = db.get_document("cargos") or {}
            cargo_admin_id = cargos_data.get("cargo_admin")
            
            is_admin = inter.author.guild_permissions.administrator
            has_admin_role = False
            if cargo_admin_id:
                has_admin_role = any(role.id == int(cargo_admin_id) for role in inter.author.roles)
            
            if not (is_admin or has_admin_role):
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem permissão para aprovar usuários!",
                    ephemeral=True
                )
                return
            
            log_id = custom_id.split(":")[1] if ":" in custom_id else None
            
            if not log_id:
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao processar aprovação.",
                    ephemeral=True
                )
                return
            
            # Carregar log
            logs_data = db.get_document("antifake_logs") or {}
            log_entry = logs_data.get("logs", {}).get(log_id)
            
            if not log_entry:
                await inter.response.send_message(
                    f"{emoji.wrong} Log não encontrado!",
                    ephemeral=True
                )
                return
            
            if log_entry.get("status") != "pending":
                await inter.response.send_message(
                    f"{emoji.wrong} Este usuário já foi processado!",
                    ephemeral=True
                )
                return
            
            # Adicionar usuário à lista de autorizados
            authorized_users = db.get_document("antifake_authorized") or {}
            if not isinstance(authorized_users, dict):
                authorized_users = {}
            
            if "users" not in authorized_users:
                authorized_users["users"] = []
            
            user_id = log_entry["user_id"]
            if str(user_id) not in authorized_users["users"] and user_id not in authorized_users["users"]:
                authorized_users["users"].append(str(user_id))
                db.save_document("antifake_authorized", authorized_users)
            
            # Atualizar status do log
            logs_data["logs"][log_id]["status"] = "approved"
            logs_data["logs"][log_id]["approved_by"] = inter.author.id
            logs_data["logs"][log_id]["approved_at"] = int(datetime.now(timezone.utc).timestamp())
            db.save_document("antifake_logs", logs_data)
            
            # Atualizar mensagem
            mode = db.get_document("custom_mode").get("mode", "embed")
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            
            if mode == "components":
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                await inter.response.edit_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.correct}\n-# **Usuário Aprovado**"),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay(
                                f"-# **Usuário:** <@{user_id}>\n"
                                f"-# **Idade da conta:** `{log_entry['account_age_days']} dias`\n"
                                f"-# **Mínimo exigido:** `{log_entry['min_days_required']} dias`\n"
                                f"-# **Aprovado por:** {inter.author.mention}"
                            ),
                            **container_kwargs
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            else:
                embed = disnake.Embed(
                    title=f"{emoji.correct} Usuário Aprovado",
                    color=disnake.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Usuário", value=f"<@{user_id}>", inline=True)
                embed.add_field(name="Idade da Conta", value=f"{log_entry['account_age_days']} dias", inline=True)
                embed.add_field(name="Mínimo Exigido", value=f"{log_entry['min_days_required']} dias", inline=True)
                embed.add_field(name="Aprovado por", value=inter.author.mention, inline=False)
                
                await inter.response.edit_message(embed=embed, components=[])
            
            await inter.followup.send(
                f"{emoji.correct} Usuário aprovado! Ele poderá entrar no servidor mesmo com menos dias que o configurado.",
                ephemeral=True
            )


def setup(bot: commands.Bot):
    bot.add_cog(AntiFakeConfig(bot))
    bot.add_cog(AntiFakeSystem(bot))
    bot.add_cog(AntiFakeModeration(bot))
"""
Monitor centralizado de interações do bot.
Captura todas as interações (buttons, modals, selects, commands) sem precisar modificar outros códigos.
Imprime todas as interações no console e envia para webhook do Discord.
"""
import asyncio
import os
from datetime import datetime

import aiohttp
import disnake
from disnake.ext import commands

from functions.database import database as db


class InteractionMonitor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._config_data = None
        self._load_config()
    
    def _load_config(self):
        """Carrega informações do config.json"""
        try:
            self._config_data = db.obter("config.json")
        except:
            self._config_data = {}
    
    def _get_bot_info(self) -> tuple[str, str]:
        """Retorna (botID, bot_id) do config.json"""
        bot_id = self._config_data.get("botID", "N/A")
        bot_discord_id = self._config_data.get("bot", {}).get("id", "N/A")
        return bot_id, bot_discord_id
    
    def _get_channel_name(self, channel) -> str:
        """Retorna o nome do canal, tratando DMChannel"""
        if isinstance(channel, disnake.DMChannel):
            return "DM"
        elif hasattr(channel, 'name'):
            return channel.name
        else:
            return "Unknown"
    
    def _is_enabled(self) -> bool:
        """
        Verifica se o monitor está ativado.
        CORREÇÃO: o documento pode não existir no MongoDB → o .get("enabled", False)
        retornava False e o monitor nunca enviava webhooks.
        Agora o padrão é True (ativado), a menos que esteja explicitamente desabilitado.
        """
        try:
            config = db.get_document("interaction_monitor_config")
            # Se o documento não existir, get_document retorna {} ou None
            if not config:
                return True  # padrão: ativado
            return config.get("enabled", True)
        except Exception:
            return True  # em caso de erro, mantém ativado
    
    def _get_interaction_info(self, inter: disnake.Interaction) -> dict:
        """Extrai informações básicas de uma interação"""
        info = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": inter.type.name if hasattr(inter.type, 'name') else str(inter.type),
            "user_id": str(inter.user.id) if inter.user else None,
            "user_name": str(inter.user) if inter.user else None,
            "guild_id": str(inter.guild_id) if inter.guild_id else None,
            "guild_name": inter.guild.name if inter.guild else None,
            "channel_id": str(inter.channel_id) if inter.channel_id else None,
            "channel_name": self._get_channel_name(inter.channel) if hasattr(inter, 'channel') and inter.channel else None,
        }
        
        # Informações específicas por tipo de interação
        if isinstance(inter, disnake.MessageInteraction):
            if hasattr(inter, 'component'):
                info["component_type"] = type(inter.component).__name__
                info["custom_id"] = getattr(inter.component, 'custom_id', None)
                if isinstance(inter.component, disnake.ui.Select):
                    info["selected_values"] = inter.values if hasattr(inter, 'values') else []
        
        elif isinstance(inter, disnake.ModalInteraction):
            info["modal_custom_id"] = inter.custom_id
            info["text_values"] = dict(inter.text_values) if hasattr(inter, 'text_values') else {}
        
        elif isinstance(inter, disnake.ApplicationCommandInteraction):
            info["command_name"] = inter.application_command.name if inter.application_command else None
            # Tentar obter ID do comando de diferentes formas
            if inter.application_command:
                if hasattr(inter.application_command, 'id') and inter.application_command.id:
                    info["command_id"] = str(inter.application_command.id)
                elif hasattr(inter, 'data') and inter.data:
                    # Tentar obter do data da interação
                    cmd_id = inter.data.get("id") if isinstance(inter.data, dict) else None
                    if cmd_id:
                        info["command_id"] = str(cmd_id)
                    else:
                        info["command_id"] = None
                else:
                    info["command_id"] = None
            else:
                info["command_id"] = None
            
            if hasattr(inter, 'data') and inter.data:
                info["options"] = inter.data.get("options", []) if isinstance(inter.data, dict) else []
        
        return info
    
    async def _print_interaction(self, inter: disnake.Interaction, status: str = "received"):
        """Imprime informações da interação no console"""
        try:
            # CORREÇÃO: usa _is_enabled() com padrão True em vez de False
            if not self._is_enabled():
                return
            
            info = self._get_interaction_info(inter)
            
            # Formatar timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Informações básicas
            tipo_interacao = info.get("type", "Unknown")
            usuario = info.get("user_name", "Unknown")
            user_id = info.get("user_id", "N/A")
            guild_name = info.get("guild_name", "DM")
            channel_name = info.get("channel_name", "N/A")
            
            # Identificador da interação
            identifier = (
                info.get("custom_id") or 
                info.get("modal_custom_id") or 
                info.get("command_name") or 
                "N/A"
            )
            
            # Montar linha de log
            log_line = f"[{timestamp}] [{status.upper()}] {tipo_interacao}"
            log_line += f" | Usuário: {usuario} ({user_id})"
            log_line += f" | Servidor: {guild_name}"
            log_line += f" | Canal: {channel_name}"
            log_line += f" | ID: {identifier}"
            
            # Adicionar valores específicos
            if info.get("selected_values"):
                valores = ", ".join(info["selected_values"][:3])
                if len(info["selected_values"]) > 3:
                    valores += f" (+{len(info['selected_values']) - 3} mais)"
                log_line += f" | Valores: {valores}"
            
            if info.get("text_values"):
                campos = []
                for k, v in list(info["text_values"].items())[:3]:
                    valor = v[:30] + "..." if len(v) > 30 else v
                    campos.append(f"{k}={valor}")
                log_line += f" | Campos: {', '.join(campos)}"
            
            if info.get("options"):
                opts = []
                for opt in info["options"][:3]:
                    if isinstance(opt, dict):
                        opts.append(f"{opt.get('name', 'N/A')}={opt.get('value', 'N/A')}")
                if opts:
                    log_line += f" | Opções: {', '.join(opts)}"
            
            # print(log_line)  # Comentado - logs apenas via webhook
            
            # Enviar para webhook se configurado
            await self._send_webhook(info, status)
        
        except Exception as e:
            # Não quebrar o fluxo se houver erro no monitoramento
            print(f"[InteractionMonitor] Erro ao imprimir interação: {e}")
    
    async def _send_webhook(self, info: dict, status: str):
        """Envia log para webhook do Discord"""
        try:
            webhook_url = os.getenv("AMETHYS_INTERACTION_WEBHOOK_URL", "")
            if not webhook_url:
                return
            
            # Obter informações do bot
            bot_id, bot_discord_id = self._get_bot_info()
            
            # Determinar cor baseada no status
            color_map = {
                "received": 0x3498db,  # Azul
                "button_clicked": 0x2ecc71,  # Verde
                "dropdown_selected": 0x9b59b6,  # Roxo
                "modal_submitted": 0xe67e22,  # Laranja
                "slash_command": 0x1abc9c,  # Turquesa
                "user_command": 0x34495e,  # Cinza escuro
                "message_command": 0x95a5a6,  # Cinza
                "error": 0xe74c3c,  # Vermelho
            }
            color = color_map.get(status, 0x95a5a6)
            
            # Montar embed
            embed = disnake.Embed(
                title=f"🤖 Bot: {bot_id} | ID: {bot_discord_id}",
                description=f"**Interação Monitorada**",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            # Tipo e status
            tipo_interacao = info.get("type", "Unknown")
            embed.add_field(
                name="📋 Tipo",
                value=f"`{tipo_interacao}`\n**Status:** `{status.upper()}`",
                inline=True
            )
            
            # Usuário
            usuario = info.get("user_name", "Unknown")
            user_id = info.get("user_id", "N/A")
            embed.add_field(
                name="👤 Usuário",
                value=f"{usuario}\n`{user_id}`",
                inline=True
            )
            
            # Servidor e Canal
            guild_name = info.get("guild_name", "DM")
            channel_name = info.get("channel_name", "N/A")
            embed.add_field(
                name="🏠 Local",
                value=f"**Servidor:** {guild_name}\n**Canal:** {channel_name}",
                inline=False
            )
            
            # Identificador
            identifier = (
                info.get("custom_id") or 
                info.get("modal_custom_id") or 
                info.get("command_name") or 
                "N/A"
            )
            embed.add_field(
                name="🔑 ID",
                value=f"`{identifier}`",
                inline=True
            )
            
            # Valores específicos
            if info.get("selected_values"):
                valores = ", ".join(info["selected_values"][:5])
                if len(info["selected_values"]) > 5:
                    valores += f" (+{len(info['selected_values']) - 5} mais)"
                embed.add_field(
                    name="📝 Valores Selecionados",
                    value=f"`{valores}`",
                    inline=False
                )
            
            if info.get("text_values"):
                campos_texto = []
                for k, v in list(info["text_values"].items())[:5]:
                    valor = v[:100] + "..." if len(v) > 100 else v
                    campos_texto.append(f"**{k}:** `{valor}`")
                if campos_texto:
                    embed.add_field(
                        name="📄 Campos Preenchidos",
                        value="\n".join(campos_texto),
                        inline=False
                    )
            
            if info.get("options"):
                opts_texto = []
                for opt in info["options"][:5]:
                    if isinstance(opt, dict):
                        nome = opt.get("name", "N/A")
                        valor = opt.get("value", "N/A")
                        opts_texto.append(f"**{nome}:** `{valor}`")
                if opts_texto:
                    embed.add_field(
                        name="⚙️ Opções",
                        value="\n".join(opts_texto),
                        inline=False
                    )
            
            # Timestamp
            timestamp_str = info.get("timestamp", datetime.utcnow().isoformat())
            embed.set_footer(text=f"Timestamp: {timestamp_str}")
            
            # Enviar webhook com retry
            await self._send_webhook_with_retry(webhook_url, {
                "embeds": [embed.to_dict()],
                "username": f"{bot_id} - Interaction Monitor"
            })
        
        except Exception as e:
            # Não quebrar o fluxo se houver erro no webhook
            print(f"[InteractionMonitor] Erro ao enviar webhook: {e}")
    
    async def _send_webhook_with_retry(self, webhook_url: str, payload: dict, max_retries: int = 3, initial_delay: float = 2.0):
        """Envia webhook com sistema de retry e delay"""
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status in [200, 204]:
                            return  # Sucesso
                        
                        # Se for rate limit (429), esperar mais tempo
                        if response.status == 429:
                            retry_after = 5.0  # Esperar 5 segundos para rate limit
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_after)
                                continue
                        
                        # Outros erros HTTP
                        if attempt < max_retries - 1:
                            delay = initial_delay * (2 ** attempt)  # Backoff exponencial
                            await asyncio.sleep(delay)
                        
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
            
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
    
    @commands.Cog.listener("on_interaction")
    async def on_interaction(self, inter: disnake.Interaction):
        """Captura TODAS as interações antes do processamento"""
        await self._print_interaction(inter, "received")
    
    @commands.Cog.listener("on_button_click")
    async def on_button_click_monitor(self, inter: disnake.MessageInteraction):
        """Monitor específico para botões (executa após o listener principal)"""
        await self._print_interaction(inter, "button_clicked")
    
    @commands.Cog.listener("on_dropdown")
    async def on_dropdown_monitor(self, inter: disnake.MessageInteraction):
        """Monitor específico para selects (executa após o listener principal)"""
        await self._print_interaction(inter, "dropdown_selected")
    
    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit_monitor(self, inter: disnake.ModalInteraction):
        """Monitor específico para modais (executa após o listener principal)"""
        await self._print_interaction(inter, "modal_submitted")
    
    @commands.Cog.listener("on_slash_command")
    async def on_slash_command_monitor(self, inter: disnake.ApplicationCommandInteraction):
        """Monitor específico para comandos slash"""
        await self._print_interaction(inter, "slash_command")
    
    @commands.Cog.listener("on_user_command")
    async def on_user_command_monitor(self, inter: disnake.ApplicationCommandInteraction):
        """Monitor específico para comandos de usuário"""
        await self._print_interaction(inter, "user_command")
    
    @commands.Cog.listener("on_message_command")
    async def on_message_command_monitor(self, inter: disnake.ApplicationCommandInteraction):
        """Monitor específico para comandos de mensagem"""
        await self._print_interaction(inter, "message_command")
    
    @commands.Cog.listener("on_slash_command_error")
    async def on_slash_command_error_monitor(self, inter: disnake.ApplicationCommandInteraction, error: Exception):
        """Monitor de erros em comandos slash"""
        try:
            info = self._get_interaction_info(inter)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            usuario = info.get("user_name", "Unknown")
            command_name = info.get("command_name", "N/A")
            error_type = type(error).__name__
            error_msg = str(error)
            
            await self._send_error_webhook(info, "slash_command", command_name, error_type, error_msg)
        except:
            pass
    
    @commands.Cog.listener("on_interaction_error")
    async def on_interaction_error_monitor(self, inter: disnake.Interaction, error: Exception):
        """Monitor de erros gerais em interações"""
        try:
            info = self._get_interaction_info(inter)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            usuario = info.get("user_name", "Unknown")
            tipo_interacao = info.get("type", "Unknown")
            identifier = info.get("custom_id") or info.get("modal_custom_id") or info.get("command_name") or "N/A"
            error_type = type(error).__name__
            error_msg = str(error)
            
            await self._send_error_webhook(info, tipo_interacao, identifier, error_type, error_msg)
        except:
            pass
    
    async def _send_error_webhook(self, info: dict, tipo_interacao: str, identifier: str, error_type: str, error_msg: str):
        """Envia erro para webhook"""
        try:
            webhook_url = os.getenv("AMETHYS_INTERACTION_WEBHOOK_URL", "")
            if not webhook_url:
                return
            
            # Obter informações do bot
            bot_id, bot_discord_id = self._get_bot_info()
            
            # Criar embed de erro
            embed = disnake.Embed(
                title=f"🤖 Bot: {bot_id} | ID: {bot_discord_id}",
                description="**❌ Erro em Interação**",
                color=0xe74c3c,  # Vermelho
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="📋 Tipo",
                value=f"`{tipo_interacao}`",
                inline=True
            )
            
            embed.add_field(
                name="🔑 ID",
                value=f"`{identifier}`",
                inline=True
            )
            
            usuario = info.get("user_name", "Unknown")
            user_id = info.get("user_id", "N/A")
            embed.add_field(
                name="👤 Usuário",
                value=f"{usuario}\n`{user_id}`",
                inline=True
            )
            
            guild_name = info.get("guild_name", "DM")
            channel_name = info.get("channel_name", "N/A")
            embed.add_field(
                name="🏠 Local",
                value=f"**Servidor:** {guild_name}\n**Canal:** {channel_name}",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Erro",
                value=f"**Tipo:** `{error_type}`\n**Mensagem:** `{error_msg[:500]}`",
                inline=False
            )
            
            embed.set_footer(text=f"Timestamp: {info.get('timestamp', datetime.utcnow().isoformat())}")
            
            # Enviar webhook com retry
            await self._send_webhook_with_retry(webhook_url, {
                "embeds": [embed.to_dict()],
                "username": f"{bot_id} - Error Monitor"
            })
        
        except Exception as e:
            print(f"[InteractionMonitor] Erro ao enviar webhook de erro: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(InteractionMonitor(bot))

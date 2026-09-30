import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.protecaogeral.comandosext import helpers


class MonProtComandosExt(commands.Cog):
    TIPOS = ("spam_bot_externo",)

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Mapa: guild_id -> tipo -> executor_id -> deque[timestamps]
        self._contadores: Dict[int, Dict[str, Dict[int, Deque[float]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: deque()))
        )
        # Mapa: guild_id -> tipo -> executor_id -> deque[(timestamp, info_extra)]
        self._alvos: Dict[int, Dict[str, Dict[int, Deque[tuple[float, str]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: deque()))
        )
        # Mapa para rastrear mensagens de bots: guild_id -> bot_id -> deque[(timestamp, message_id, channel_id)]
        self._mensagens_bots: Dict[int, Dict[int, Deque[tuple[float, int, int]]]] = defaultdict(
            lambda: defaultdict(lambda: deque())
        )

    # UI/log helpers
    @staticmethod
    def _criar_container_log(titulo: str, linhas: list[str]) -> disnake.ui.Container:
        linhas_filtradas = [l for l in linhas if l]
        corpo = "\n".join(linhas_filtradas) if linhas_filtradas else ""
        return disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# {titulo}"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(corpo),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"{emoji.calendar} **Data:** <t:{int(time.time())}:f> (<t:{int(time.time())}:R>)"
            ),
        )

    # Punição
    @staticmethod
    async def _aplicar_punicao(guild: disnake.Guild, executor: Optional[disnake.Member], punicao: str, motivo: str) -> str:
        if executor is None:
            return "Executor desconhecido — sem punição"
        try:
            if punicao == "ban":
                await guild.ban(executor, reason=motivo)
                return "Aplicada"
            if punicao == "kick":
                await guild.kick(executor, reason=motivo)
                return "Aplicada"
            if punicao == "remover_cargos":
                roles_to_remove = [r for r in executor.roles if not r.is_default()]
                if roles_to_remove:
                    await executor.remove_roles(*roles_to_remove, reason=motivo)
                return "Aplicada"
            return "Sem punição (configurado como none)"
        except Exception:
            return "Falha ao punir (Verifique as permissões do bot)"

    def _add_executor_info(self, linhas: list[str], executor: Optional[disnake.Member], bot_responsavel: bool = False):
        if executor:
            titulo = "Bot Responsável" if bot_responsavel else "Executor"
            info_executor = [
                f"{emoji.member} **{titulo}:** {executor.mention} ({executor.id})",
            ]
            if not executor.bot:
                info_executor.extend([
                    f"{emoji.information} **Cargo mais alto:** {executor.top_role.mention}",
                    f"{emoji.information} **Quantidade de cargos:** {len(executor.roles)}",
                ])
                if executor.joined_at:
                    info_executor.append(f"{emoji.information} **Entrou em:** <t:{int(executor.joined_at.timestamp())}:f> (<t:{int(executor.joined_at.timestamp())}:R>)")
                if executor.created_at:
                    info_executor.append(f"{emoji.information} **Conta criada em:** <t:{int(executor.created_at.timestamp())}:f> (<t:{int(executor.created_at.timestamp())}:R>)")
            linhas.extend(info_executor)
        else:
            linhas.append(f"{emoji.member} **Executor:** Desconhecido (N/A)")

    # Janela deslizante
    def _incrementar_contador(self, guild_id: int, tipo: str, executor_id: int, intervalo: int) -> int:
        agora = time.time()
        fila = self._contadores[guild_id][tipo][executor_id]
        while fila and (agora - fila[0]) > intervalo:
            fila.popleft()
        fila.append(agora)
        return len(fila)

    def _registrar_alvo(self, guild_id: int, tipo: str, executor_id: int, info_extra: str, intervalo: int) -> None:
        agora = time.time()
        fila = self._alvos[guild_id][tipo][executor_id]
        while fila and (agora - fila[0][0]) > intervalo:
            fila.popleft()
        fila.append((agora, info_extra))

    def _listar_alvos_mencionados(self, guild_id: int, tipo: str, executor_id: int, intervalo: int) -> list[str]:
        agora = time.time()
        fila = self._alvos[guild_id][tipo][executor_id]
        while fila and (agora - fila[0][0]) > intervalo:
            fila.popleft()
        # Informações dos comandos/bots, um por linha, com vírgula
        return [f"{info_extra}," for _, info_extra in list(fila)]



    @staticmethod
    def _bot_permitido(bot_id: int, config: dict) -> bool:
        bots_permitidos = config.get("bots_permitidos", [])
        return bot_id in bots_permitidos

    def _registrar_mensagem_bot(self, guild_id: int, bot_id: int, message_id: int, channel_id: int) -> None:
        """Registra uma mensagem de bot para possível reversão"""
        agora = time.time()
        fila = self._mensagens_bots[guild_id][bot_id]
        
        # Limpar mensagens antigas (mais de 5 minutos)
        while fila and (agora - fila[0][0]) > 300:
            fila.popleft()
        
        fila.append((agora, message_id, channel_id))

    def _limpar_mensagens_antigas_bot(self, guild_id: int, bot_id: int, intervalo: int) -> None:
        """Remove mensagens antigas da fila baseado no intervalo"""
        agora = time.time()
        fila = self._mensagens_bots[guild_id][bot_id]
        while fila and (agora - fila[0][0]) > intervalo:
            fila.popleft()

    async def _reverter_mensagens_bot(self, guild: disnake.Guild, bot_id: int, intervalo: int) -> tuple[int, int]:
        """
        Apaga todas as mensagens do bot no intervalo especificado
        Retorna (mensagens_apagadas, canais_afetados)
        """
        agora = time.time()
        guild_id = guild.id
        fila = self._mensagens_bots[guild_id][bot_id]
        
        # Limpar mensagens antigas primeiro
        self._limpar_mensagens_antigas_bot(guild_id, bot_id, intervalo)
        
        mensagens_para_apagar = []
        canais_afetados = set()
        
        # Coletar mensagens no intervalo
        for timestamp, message_id, channel_id in list(fila):
            if (agora - timestamp) <= intervalo:
                mensagens_para_apagar.append((message_id, channel_id))
                canais_afetados.add(channel_id)
        
        mensagens_apagadas = 0
        
        # Agrupar mensagens por canal para bulk delete
        mensagens_por_canal = {}
        for message_id, channel_id in mensagens_para_apagar:
            if channel_id not in mensagens_por_canal:
                mensagens_por_canal[channel_id] = []
            mensagens_por_canal[channel_id].append(message_id)
        
        # Apagar mensagens canal por canal
        for channel_id, message_ids in mensagens_por_canal.items():
            try:
                channel = guild.get_channel(channel_id)
                if not channel:
                    continue
                
                # Tentar bulk delete para mensagens recentes (menos de 14 dias)
                if len(message_ids) > 1:
                    try:
                        # Filtrar mensagens que ainda existem e são recentes
                        messages_to_delete = []
                        for msg_id in message_ids[:100]:  # Limite do Discord para bulk delete
                            try:
                                msg = await channel.fetch_message(msg_id)
                                # Verificar se a mensagem tem menos de 14 dias
                                if (disnake.utils.utcnow() - msg.created_at).days < 14:
                                    messages_to_delete.append(msg)
                            except:
                                continue
                        
                        if len(messages_to_delete) > 1:
                            await channel.delete_messages(messages_to_delete)
                            mensagens_apagadas += len(messages_to_delete)
                        elif len(messages_to_delete) == 1:
                            await messages_to_delete[0].delete()
                            mensagens_apagadas += 1
                    except Exception:
                        # Fallback para delete individual
                        for msg_id in message_ids:
                            try:
                                msg = await channel.fetch_message(msg_id)
                                await msg.delete()
                                mensagens_apagadas += 1
                            except:
                                continue
                else:
                    # Delete individual para uma mensagem
                    for msg_id in message_ids:
                        try:
                            msg = await channel.fetch_message(msg_id)
                            await msg.delete()
                            mensagens_apagadas += 1
                        except:
                            continue
            except Exception:
                continue
        
        # Limpar as mensagens que foram processadas da fila
        nova_fila = deque()
        for timestamp, message_id, channel_id in fila:
            if (agora - timestamp) > intervalo or (message_id, channel_id) not in mensagens_para_apagar:
                nova_fila.append((timestamp, message_id, channel_id))
        
        self._mensagens_bots[guild_id][bot_id] = nova_fila
        
        return mensagens_apagadas, len(canais_afetados)

    # Listeners
    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        # Detectar uso de comandos de bots externos e spam de bots
        if not message.guild:
            return
        
        # Ignorar mensagens do próprio bot
        if message.author == self.bot.user:
            return
        
        config = helpers.carregar_config()
        
        # Se é um bot externo enviando mensagens
        if message.author.bot and message.author.id != self.bot.user.id:
            # Verificar se o bot está na whitelist
            if not self._bot_permitido(message.author.id, config.get("comandosext_avancado", {})):
                # Só registrar a mensagem se o bot não estiver na whitelist
                self._registrar_mensagem_bot(message.guild.id, message.author.id, message.id, message.channel.id)
                await self._processar("spam_bot_externo", message, "mensagem_bot_externo")
            return



    async def _processar(self, tipo: str, obj, acao_info: str, executor: Optional[disnake.Member] = None):
        if tipo not in self.TIPOS:
            return
            
        # Determinar guild e executor baseado no tipo de objeto
        if hasattr(obj, 'guild'):
            guild = obj.guild
        else:
            return
            
        if not guild:
            return
            
        if executor is None:
            if hasattr(obj, 'author'):
                # Para spam de bot externo, o "executor" é o próprio bot
                if tipo == "spam_bot_externo" and obj.author.bot:
                    executor = obj.author if isinstance(obj.author, disnake.Member) else guild.get_member(obj.author.id)
                else:
                    executor = obj.author if isinstance(obj.author, disnake.Member) else guild.get_member(obj.author.id)
            elif hasattr(obj, 'user'):
                executor = obj.user if isinstance(obj.user, disnake.Member) else guild.get_member(obj.user.id)
        
        config = helpers.carregar_config()
        if not config:
            return

        # Carregar configurações do tipo
        config_tipo = config.get("comandosext", {})
        config_avancado = config.get("comandosext_avancado", {})
        
        ativado = bool(config_tipo.get("ativado", False))
        limite = int(config_tipo.get("limite", 1))
        intervalo = int(config_tipo.get("intervalo", 30))

        # Verificar se haverá lista de ações afetadas
        tem_lista_acoes = False
        if executor:
            fila = self._alvos[guild.id][tipo][executor.id]
            agora = time.time()
            # Simular limpeza da fila para ver se há alvos
            alvos_validos = [(ts, info) for ts, info in fila if (agora - ts) <= intervalo]
            tem_lista_acoes = len(alvos_validos) > 0
        
        # Montar log base
        linhas = []
        
        # Mostrar informação específica da ação
        if not tem_lista_acoes:
            if tipo == "spam_bot_externo":
                if hasattr(obj, 'author'):
                    linhas.append(f"{emoji.warn} **Bot:** `{obj.author.name}` ({obj.author.id})")
                if hasattr(obj, 'channel'):
                    linhas.append(f"{emoji.textc} **Canal:** <#{obj.channel.id}> ({obj.channel.id})")
                if hasattr(obj, 'content') and obj.content:
                    mensagem = obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
                    linhas.append(f"{emoji.message} **Mensagem:** `{mensagem}`")
        
        # Para spam de bot, o "executor" é o próprio bot
        is_bot_spam = tipo == "spam_bot_externo" and executor and executor.bot
        self._add_executor_info(linhas, executor, bot_responsavel=is_bot_spam)

        # Quando executor é desconhecido, deixar explícito o tipo de ação
        if executor is None:
            linhas.append(f"{emoji.warn} **Ação:** Spam de Bot Externo")

        # Mesmo desativado: logar executor e alvos recentes
        if not ativado:
            if executor:
                info_extra = f"Bot: {obj.author.name}" if hasattr(obj, 'author') and hasattr(obj.author, 'name') else f"{acao_info}"
                self._registrar_alvo(guild.id, tipo, executor.id, info_extra, intervalo)
                mencoes = self._listar_alvos_mencionados(guild.id, tipo, executor.id, intervalo)
                if mencoes:
                    linhas.extend(mencoes)
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada (spam de bot externo)")
            await enviar_log(guild, config_avancado.get("canal_logs"), "Proteção de Spam de Bots - Logs", linhas)
            return

        # Contagem
        contagem = 0
        if executor:
            contagem = self._incrementar_contador(guild.id, tipo, executor.id, intervalo)
            
            info_extra = f"Bot: {obj.author.name}" if hasattr(obj, 'author') and hasattr(obj.author, 'name') else f"{acao_info}"
                
            self._registrar_alvo(guild.id, tipo, executor.id, info_extra, intervalo)
            linhas.append(f"{emoji.chart} **Contagem:** {contagem}/{limite} em {intervalo}s")
            mencoes = self._listar_alvos_mencionados(guild.id, tipo, executor.id, intervalo)
            if mencoes:
                linhas.extend(mencoes)

        excedeu = executor and contagem > limite
        if excedeu:
            linhas.append(f"{emoji.warn} **Ação:** Limite excedido (spam de bot externo)")
            
            # Reversão sempre ativa (independente da punição)
            if executor and executor.bot:
                try:
                    mensagens_apagadas, canais_afetados = await self._reverter_mensagens_bot(guild, executor.id, intervalo)
                    if mensagens_apagadas > 0:
                        linhas.append(f"{emoji.delete} **Reversão:** {mensagens_apagadas} mensagens apagadas em {canais_afetados} canal(is)")
                    else:
                        linhas.append(f"{emoji.delete} **Reversão:** Nenhuma mensagem encontrada para apagar")
                except Exception as e:
                    linhas.append(f"{emoji.wrong} **Reversão:** Falha ao apagar mensagens - {str(e)[:50]}")
            
            # Aplicar punição (se configurada)
            punicao = config_avancado.get("punicao", "ban")
            if punicao != "none":
                motivo = f"Violou proteção de spam de bot externo"
                if hasattr(obj, 'author'):
                    motivo += f" - Bot: {obj.author.name}"
                
                # Tentar encontrar quem adicionou o bot
                target_member = executor
                if executor and executor.bot:
                    # Tentar encontrar quem adicionou este bot
                    try:
                        agora = disnake.utils.utcnow()
                        async for entry in guild.audit_logs(action=disnake.AuditLogAction.bot_add, limit=50):
                            if entry.target and entry.target.id == executor.id:
                                # Bot foi adicionado recentemente (últimas 24h)
                                if (agora - entry.created_at).total_seconds() <= 86400:
                                    adder = entry.user if isinstance(entry.user, disnake.Member) else guild.get_member(entry.user.id)
                                    if adder and not adder.bot:
                                        target_member = adder
                                        motivo += f" - Quem adicionou: {adder.name}"
                                        linhas.append(f"{emoji.flag} **Quem adicionou o bot:** <@{adder.id}> ({adder.id})")
                                        break
                    except Exception:
                        pass
                
                resultado = await self._aplicar_punicao(
                    guild,
                    target_member,
                    punicao,
                    motivo=motivo
                )
                linhas.append(f"{emoji.wand} **Punição:** {punicao.capitalize()} — {resultado}")
            else:
                linhas.append(f"{emoji.wand} **Punição:** Nenhuma (configurado)")

            await enviar_log(guild, config_avancado.get("canal_logs"), "Proteção de Spam de Bots - Logs", linhas)
            return

        # Sem excesso: logar
        await enviar_log(guild, config_avancado.get("canal_logs"), "Proteção de Spam de Bots - Logs", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(MonProtComandosExt(bot))

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

import disnake
from disnake.ext import commands, tasks

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.protecaogeral.webhooks import helpers


class MonProtWebhooks(commands.Cog):
    TIPOS = ("criacao_webhook", "edicao_webhook", "exclusao_webhook", "spam_webhook")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Mapa: guild_id -> tipo -> executor_id -> deque[timestamps]
        self._contadores: Dict[int, Dict[str, Dict[int, Deque[float]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: deque()))
        )
        # Mapa: guild_id -> tipo -> executor_id -> deque[(timestamp, alvo_id)]
        self._alvos: Dict[int, Dict[str, Dict[int, Deque[tuple[float, int]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: deque()))
        )
        # Sistema anti-duplicação: guild_id -> webhook_id -> timestamp
        self._processados_recentemente: Dict[int, Dict[int, float]] = defaultdict(dict)
        # Cache de criadores de webhooks: webhook_id -> creator_id
        self._webhook_creators: Dict[int, int] = {}
        # Contagem de mensagens de webhooks para detecção de spam
        self._webhook_message_counts: Dict[int, Dict[int, Deque[float]]] = defaultdict(
            lambda: defaultdict(lambda: deque())
        )
        # Anti-duplicação para punições de spam
        self._spam_processado: Dict[int, Dict[int, float]] = defaultdict(dict)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.cleanup_task.is_running():
            self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @tasks.loop(minutes=5)
    async def cleanup_task(self):
        # Limpar caches antigos para evitar consumo de memória
        agora = time.time()
        for guild_id in list(self._spam_processado.keys()):
            for webhook_id in list(self._spam_processado[guild_id].keys()):
                if (agora - self._spam_processado[guild_id][webhook_id]) > 3600: # 1 hora
                    del self._spam_processado[guild_id][webhook_id]
            if not self._spam_processado[guild_id]:
                del self._spam_processado[guild_id]

    # UI/log helpers
    @staticmethod
    def _criar_container_log(titulo: str, linhas: list[str], **kwargs) -> disnake.ui.Container:
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

    def _add_executor_info(self, linhas: list[str], executor: Optional[disnake.Member]):
        if executor:
            info_executor = [
                f"{emoji.member} **Executor:** {executor.mention} ({executor.id})",
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

    # Audit-log helpers
    async def _resolver_executor(self, guild: disnake.Guild, target_obj, action: disnake.AuditLogAction, limite_segundos: int = 120) -> Optional[disnake.Member]:
        for _ in range(8):
            try:
                agora = disnake.utils.utcnow()
                async for entry in guild.audit_logs(action=action, limit=25):
                    alvo = getattr(entry, "target", None)
                    alvo_id = getattr(alvo, "id", None)
                    if alvo_id and alvo_id == getattr(target_obj, "id", None):
                        if (agora - entry.created_at).total_seconds() <= limite_segundos:
                            usuario = entry.user
                            membro = usuario if isinstance(usuario, disnake.Member) else guild.get_member(getattr(usuario, 'id', 0))
                            if membro and (not self.bot.user or membro.id != self.bot.user.id):
                                if membro.id not in self._webhook_creators:
                                    self._webhook_creators[alvo_id] = membro.id
                                return membro
            except Exception:
                pass
            await asyncio.sleep(1.2)
        return None

    # Janela deslizante
    def _incrementar_contador(self, guild_id: int, tipo: str, executor_id: int, intervalo: int) -> int:
        agora = time.time()
        fila = self._contadores[guild_id][tipo][executor_id]
        while fila and (agora - fila[0]) > intervalo:
            fila.popleft()
        fila.append(agora)
        return len(fila)

    def _registrar_alvo(self, guild_id: int, tipo: str, executor_id: int, alvo_id: int, intervalo: int) -> None:
        agora = time.time()
        fila = self._alvos[guild_id][tipo][executor_id]
        while fila and (agora - fila[0][0]) > intervalo:
            fila.popleft()
        fila.append((agora, int(alvo_id)))

    def _listar_alvos_mencionados(self, guild_id: int, tipo: str, executor_id: int, intervalo: int) -> list[str]:
        agora = time.time()
        fila = self._alvos[guild_id][tipo][executor_id]
        while fila and (agora - fila[0][0]) > intervalo:
            fila.popleft()
        # Webhooks como ID (não há menção específica para webhooks), um por linha, com vírgula
        return [f"{emoji.website} **Webhook ID:** {alvo_id}," for _, alvo_id in list(fila)]

    def _listar_alvos_ids(self, guild_id: int, tipo: str, executor_id: int, intervalo: int) -> list[int]:
        agora = time.time()
        fila = self._alvos[guild_id][tipo][executor_id]
        while fila and (agora - fila[0][0]) > intervalo:
            fila.popleft()
        return [alvo_id for _, alvo_id in list(fila)]

    @staticmethod
    def _executor_imune(executor: Optional[disnake.Member], config: dict) -> bool:
        if not executor:
            return False
        ids = set(config.get("cargos_imunes", []))
        if not ids:
            return False
        try:
            return any(r.id in ids for r in getattr(executor, "roles", []))
        except Exception:
            return False

    # Listeners
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: disnake.TextChannel):
        # Este evento é disparado quando webhooks são criados, editados ou deletados
        # Vamos processar as mudanças através de audit logs
        await self._processar_webhooks_update(channel)

    async def _processar_webhooks_update(self, channel: disnake.TextChannel):
        guild = channel.guild
        if not guild:
            return
        
        # Sistema anti-duplicação: evitar processar o mesmo evento múltiplas vezes em pouco tempo
        agora = time.time()
        guild_id = guild.id
        
        # Verificar se já foi processado recentemente (últimos 2 segundos)
        channel_id = getattr(channel, 'id', 0)
        if channel_id in self._processados_recentemente[guild_id]:
            ultimo_processamento = self._processados_recentemente[guild_id][channel_id]
            if (agora - ultimo_processamento) < 2.0:
                return  # Ignorar duplicação
        
        # Marcar como processado
        self._processados_recentemente[guild_id][channel_id] = agora
        
        # Limpar entradas antigas (mais de 10 segundos)
        for gid in list(self._processados_recentemente.keys()):
            for cid in list(self._processados_recentemente[gid].keys()):
                if (agora - self._processados_recentemente[gid][cid]) > 10.0:
                    del self._processados_recentemente[gid][cid]
            if not self._processados_recentemente[gid]:
                del self._processados_recentemente[gid]
        
        config = helpers.carregar_config()
        if not config or "webhooks" not in config or "webhooks_avancado" not in config:
            return

        try:
            await asyncio.sleep(1.0)
        except Exception:
            pass

        # Verificar audit logs para determinar o tipo de ação e o webhook afetado
        try:
            agora_dt = disnake.utils.utcnow()
            webhook_actions = [
                disnake.AuditLogAction.webhook_create,
                disnake.AuditLogAction.webhook_update,
                disnake.AuditLogAction.webhook_delete
            ]
            
            for action in webhook_actions:
                try:
                    async for entry in guild.audit_logs(action=action, limit=5):
                        if (agora_dt - entry.created_at).total_seconds() <= 10:  # Últimos 10 segundos
                            webhook = entry.target
                            if webhook and hasattr(webhook, 'channel_id') and webhook.channel_id == channel.id:
                                tipo = {
                                    disnake.AuditLogAction.webhook_create: "criacao_webhook",
                                    disnake.AuditLogAction.webhook_update: "edicao_webhook",
                                    disnake.AuditLogAction.webhook_delete: "exclusao_webhook"
                                }.get(action)
                                
                                if tipo:
                                    await self._processar(tipo, webhook, entry.user, channel)
                except Exception:
                    continue
        except Exception:
            pass

    async def _processar(self, tipo: str, webhook, executor_user, channel: disnake.TextChannel):
        if tipo not in self.TIPOS:
            return
        guild = channel.guild
        if not guild:
            return
        
        config = helpers.carregar_config()
        if not config or "webhooks" not in config or "webhooks_avancado" not in config:
            return

        # Resolver executor
        executor = None
        if executor_user:
            if isinstance(executor_user, disnake.Member):
                executor = executor_user
            else:
                executor = guild.get_member(getattr(executor_user, 'id', 0))

        if tipo == "criacao_webhook" and executor:
            webhook_id = getattr(webhook, 'id', 0)
            if webhook_id:
                self._webhook_creators[webhook_id] = executor.id

        # Carregar configurações do tipo
        config_geral = config["webhooks"]
        config_avancado = config["webhooks_avancado"]

        tipo_sem_prefixo = tipo.replace("_webhook", "")
        # Para criação, edição e exclusão, as configurações são as mesmas.
        ativado = bool(config_geral.get("ativado", False))
        limite = int(config_geral.get("limite", 1))
        intervalo = int(config_geral.get("intervalo", 10))

        # Verificar se haverá lista de webhooks afetados
        tem_lista_webhooks = False
        if executor:
            fila = self._alvos[guild.id][tipo][executor.id]
            agora = time.time()
            # Simular limpeza da fila para ver se há alvos
            alvos_validos = [(ts, alvo_id) for ts, alvo_id in fila if (agora - ts) <= intervalo]
            tem_lista_webhooks = len(alvos_validos) > 0
        
        # Montar log base
        linhas = []
        
        # Só mostrar webhook individual se não houver lista de webhooks afetados
        if not tem_lista_webhooks:
            webhook_id = getattr(webhook, 'id', 0)
            webhook_name = getattr(webhook, 'name', 'Desconhecido')
            linhas.append(f"{emoji.website} **Webhook:** `{webhook_name}` ({webhook_id})")
        
        linhas.append(f"{emoji.textc} **Canal:** <#{channel.id}> ({channel.id})")
        self._add_executor_info(linhas, executor)

        # Verificar se haverá limite excedido (para não mostrar detalhes de edição desnecessários)
        vai_exceder_limite = False
        if executor and ativado:
            # Simular contagem para verificar se vai exceder
            contagem_simulada = self._incrementar_contador(guild.id, tipo, executor.id, intervalo)
            # Reverter a contagem simulada
            if self._contadores[guild.id][tipo][executor.id]:
                self._contadores[guild.id][tipo][executor.id].pop()
            vai_exceder_limite = contagem_simulada > limite

        # Detalhes específicos de edição: propriedades alteradas
        if tipo == "edicao_webhook" and not vai_exceder_limite:
            try:
                webhook_name = getattr(webhook, 'name', 'Desconhecido')
                webhook_avatar = getattr(webhook, 'avatar', None)
                linhas.append(f"{emoji.edit} **Nome:** `{webhook_name}`")
                if webhook_avatar:
                    linhas.append(f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} **Avatar:** Alterado")
            except Exception:
                pass

        # Quando executor é desconhecido, deixar explícito o tipo de ação
        if executor is None:
            try:
                acao_nome = {"criacao_webhook": "Criação de Webhook", "edicao_webhook": "Edição de Webhook", "exclusao_webhook": "Exclusão de Webhook"}[tipo]
                acao_emoji = {"criacao_webhook": emoji.plus, "edicao_webhook": emoji.edit, "exclusao_webhook": emoji.delete}[tipo]
                linhas.append(f"{acao_emoji} **Ação:** {acao_nome}")
            except Exception:
                linhas.append(f"{emoji.flag} **Ação:** {tipo.replace('_', ' ').capitalize()}")

            if tipo in {"criacao_webhook", "exclusao_webhook"}:
                try:
                    webhook_name = getattr(webhook, 'name', 'Desconhecido')
                    webhook_id = getattr(webhook, 'id', 0)
                    linhas.append(f"{emoji.edit} **Nome:** `{webhook_name}`")
                    linhas.append(f"{emoji.website} **ID:** `{webhook_id}`")
                except Exception:
                    pass

        # Mesmo desativado: logar executor e alvos recentes
        if not ativado:
            if executor:
                webhook_id = getattr(webhook, 'id', 0)
                self._registrar_alvo(guild.id, tipo, executor.id, webhook_id, intervalo)
                mencoes = self._listar_alvos_mencionados(guild.id, tipo, executor.id, intervalo)
                if mencoes:
                    linhas.extend(mencoes)
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada ({tipo.replace('_', ' ')})")
            await enviar_log(guild, config_avancado.get("canal_logs"), "Proteção de Webhooks - Logs", linhas)
            return

        # Contagem
        contagem = 0
        if executor:
            webhook_id = getattr(webhook, 'id', 0)
            contagem = self._incrementar_contador(guild.id, tipo, executor.id, intervalo)
            self._registrar_alvo(guild.id, tipo, executor.id, webhook_id, intervalo)
            linhas.append(f"{emoji.chart} **Contagem:** {contagem}/{limite} em {intervalo}s")
            mencoes = self._listar_alvos_mencionados(guild.id, tipo, executor.id, intervalo)
            if mencoes:
                linhas.extend(mencoes)

        # Imunidades
        executor_imune = self._executor_imune(executor, config_avancado)

        excedeu = executor and contagem > limite
        if excedeu:
            linhas.append(f"{emoji.warn} **Ação:** Limite excedido ({tipo.replace('_', ' ')})")
            if not executor_imune:
                punicao = config_avancado.get("punicao", "ban")
                if punicao != "none":
                    webhook_id = getattr(webhook, 'id', 0)
                    resultado = await self._aplicar_punicao(
                        guild,
                        executor,
                        punicao,
                        motivo=f"**Violou proteção de webhooks ({tipo.replace('_', ' ')}) - Webhook ID:** {webhook_id}"
                    )
                    linhas.append(f"{emoji.wand} **Punição:** {punicao.capitalize()} — {resultado}")

                    # Deletar webhooks criados
                    if tipo == "criacao_webhook":
                        webhooks_para_deletar = self._listar_alvos_ids(guild.id, tipo, executor.id, intervalo)
                        deletados = 0
                        for wh_id in webhooks_para_deletar:
                            try:
                                wh = await self.bot.fetch_webhook(wh_id)
                                await wh.delete(reason=f"Limite de criação de webhooks excedido por {executor.name}")
                                deletados += 1
                            except disnake.NotFound:
                                pass # Já foi deletado
                            except Exception:
                                pass # Sem permissão ou outro erro
                        if deletados > 0:
                            linhas.append(f"{emoji.delete} **Ação:** {deletados} webhooks foram deletados.")
                else:
                    linhas.append(f"{emoji.wand} **Punição:** Nenhuma (configurado)")
            else:
                linhas.append(f"{emoji.shield} **Ação:** Executor imune — punição não aplicada")

            await enviar_log(guild, config_avancado.get("canal_logs"), "Proteção de Webhooks - Logs", linhas)
            return

        # Sem excesso: logar
        await enviar_log(guild, config_avancado.get("canal_logs"), "Proteção de Webhooks - Logs", linhas)

    async def _find_webhook_creator(self, guild: disnake.Guild, webhook_id: int) -> Optional[disnake.Member]:
        if webhook_id in self._webhook_creators:
            creator_id = self._webhook_creators[webhook_id]
            member = guild.get_member(creator_id)
            if member:
                return member

        try:
            async for entry in guild.audit_logs(action=disnake.AuditLogAction.webhook_create, limit=100):
                if entry.target and entry.target.id == webhook_id:
                    if entry.user:
                        self._webhook_creators[webhook_id] = entry.user.id
                        return guild.get_member(entry.user.id)
        except (disnake.Forbidden, disnake.HTTPException):
            pass

        return None

    @commands.Cog.listener("on_message")
    async def on_webhook_message(self, message: disnake.Message):
        if not message.guild or not message.webhook_id or message.author.bot:
            return

        config = helpers.carregar_config()
        if not config or "webhooks" not in config or "webhooks_avancado" not in config:
            return

        config_avancado = config["webhooks_avancado"]
        
        # A configuração de spam pode não existir, então usamos .get()
        spam_config = config.get("spam_webhook", {})
        if not spam_config.get("ativado", False):
            return

        limite = int(spam_config.get("limite", 7))
        intervalo = int(spam_config.get("intervalo", 3))
        punicao = spam_config.get("punicao", "ban")

        agora = time.time()
        fila = self._webhook_message_counts[message.guild.id][message.webhook_id]
        while fila and (agora - fila[0]) > intervalo:
            fila.popleft()
        fila.append(agora)

        if len(fila) > limite:
            if message.webhook_id in self._spam_processado[message.guild.id]:
                if (agora - self._spam_processado[message.guild.id][message.webhook_id]) < (intervalo * 5):
                    return
            self._spam_processado[message.guild.id][message.webhook_id] = agora

            creator = await self._find_webhook_creator(message.guild, message.webhook_id)
            if not creator:
                return

            if self._executor_imune(creator, config_avancado):
                return
            
            motivo = f"Proteção: Spam de mensagens via webhook (ID: {message.webhook_id})"
            resultado_punicao = await self._aplicar_punicao(message.guild, creator, punicao, motivo)

            try:
                webhook = await self.bot.fetch_webhook(message.webhook_id)
                await webhook.delete(reason=motivo)
            except Exception:
                pass

            try:
                await message.channel.purge(
                    limit=limite * 3,
                    check=lambda m: m.webhook_id == message.webhook_id
                )
            except Exception:
                pass

            linhas = [f"{emoji.warn} **Ação:** Spam de webhook detectado."]
            self._add_executor_info(linhas, creator)
            linhas.extend([
                f"{emoji.textc} **Canal:** {message.channel.mention} (`{message.channel.id}`)",
                f"{emoji.website} **Webhook ID:** `{message.webhook_id}`",
                f"{emoji.wand} **Punição:** {punicao.capitalize()} — {resultado_punicao}"
            ])
            await enviar_log(message.guild, config_avancado.get("canal_logs"), "Proteção de Webhooks - Spam", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(MonProtWebhooks(bot))

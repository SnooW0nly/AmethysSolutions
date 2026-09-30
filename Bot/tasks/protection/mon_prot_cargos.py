import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.protecaogeral.cargos import helpers


class MonProtCargos(commands.Cog):
    TIPOS = ("criacao_cargo", "edicao_cargo", "exclusao_cargo")

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
        # Sistema anti-duplicação: guild_id -> role_id -> timestamp
        self._processados_recentemente: Dict[int, Dict[int, float]] = defaultdict(dict)

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
        # Cargos como menção <@&id>, um por linha, com vírgula
        return [f"<@&{alvo_id}>," for _, alvo_id in list(fila)]

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
    async def on_guild_role_create(self, role: disnake.Role):
        await self._processar("criacao_cargo", role)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: disnake.Role, after: disnake.Role):
        await self._processar("edicao_cargo", after, before)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: disnake.Role):
        await self._processar("exclusao_cargo", role)

    async def _processar(self, tipo: str, role: disnake.Role, before: Optional[disnake.Role] = None):
        if tipo not in self.TIPOS:
            return
        guild = role.guild
        if not guild:
            return
        
        # Sistema anti-duplicação: evitar processar o mesmo cargo múltiplas vezes em pouco tempo
        agora = time.time()
        role_id = getattr(role, 'id', 0)
        guild_id = guild.id
        
        # Verificar se já foi processado recentemente (últimos 3 segundos)
        if role_id in self._processados_recentemente[guild_id]:
            ultimo_processamento = self._processados_recentemente[guild_id][role_id]
            if (agora - ultimo_processamento) < 3.0:
                return  # Ignorar duplicação
        
        # Marcar como processado
        self._processados_recentemente[guild_id][role_id] = agora
        
        # Limpar entradas antigas (mais de 10 segundos)
        for gid in list(self._processados_recentemente.keys()):
            for rid in list(self._processados_recentemente[gid].keys()):
                if (agora - self._processados_recentemente[gid][rid]) > 10.0:
                    del self._processados_recentemente[gid][rid]
            if not self._processados_recentemente[gid]:
                del self._processados_recentemente[gid]
        
        config = helpers.carregar_config()
        if not config:
            return

        try:
            await asyncio.sleep(0.75)
        except Exception:
            pass

        action = {
            "criacao_cargo": disnake.AuditLogAction.role_create,
            "edicao_cargo": disnake.AuditLogAction.role_update,
            "exclusao_cargo": disnake.AuditLogAction.role_delete,
        }[tipo]
        executor = await self._resolver_executor(guild, role, action)

        # Carregar configurações do tipo
        tipo_sem_prefixo = tipo.replace("_cargo", "")
        ativado = bool(config.get(tipo_sem_prefixo, {}).get("ativado", False))
        limite = int(config.get(tipo_sem_prefixo, {}).get("limite", 1))
        intervalo = int(config.get(tipo_sem_prefixo, {}).get("intervalo", 10))

        # Verificar se haverá lista de cargos afetados
        tem_lista_cargos = False
        if executor:
            fila = self._alvos[guild.id][tipo][executor.id]
            agora = time.time()
            # Simular limpeza da fila para ver se há alvos
            alvos_validos = [(ts, alvo_id) for ts, alvo_id in fila if (agora - ts) <= intervalo]
            tem_lista_cargos = len(alvos_validos) > 0
        
        # Montar log base
        linhas = []
        
        # Só mostrar cargo individual se não houver lista de cargos afetados
        if not tem_lista_cargos:
            linhas.append(f"{emoji.role} **Cargo:** <@&{getattr(role, 'id', 0)}> ({getattr(role, 'id', 0)})")
        
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

        # Detalhes específicos de edição: nome antes/depois e propriedades alteradas
        # Só mostrar se não vai exceder limite (evita mostrar detalhes de apenas 1 cargo quando a punição é por múltiplos)
        if tipo == "edicao_cargo" and before is not None and not vai_exceder_limite:
            try:
                nome_antes = getattr(before, "name", "?")
                nome_depois = getattr(role, "name", "?")
                if nome_antes != nome_depois:
                    linhas.append(f"{emoji.edit} **Nome:** `{nome_antes}` → `{nome_depois}`")
            except Exception:
                pass

            # Propriedades do cargo
            try:
                def fmt_bool(v: Optional[bool]) -> str:
                    if v is True:
                        return "Ativado"
                    if v is False:
                        return "Desativado"
                    return "Indefinido"

                def fmt_color(color) -> str:
                    if not color or color == disnake.Color.default():
                        return "Padrão"
                    try:
                        return f"#{color.value:06x}"
                    except Exception:
                        return str(color)

                def fmt_permissions(perms) -> str:
                    if not perms:
                        return "Nenhuma"
                    try:
                        # Todas as permissões possíveis do Discord
                        todas_perms = []
                        
                        # Permissões Gerais
                        if perms.administrator:
                            todas_perms.append("Administrador")
                        if perms.view_audit_log:
                            todas_perms.append("Ver Logs de Auditoria")
                        if perms.manage_guild:
                            todas_perms.append("Gerenciar Servidor")
                        if perms.manage_roles:
                            todas_perms.append("Gerenciar Cargos")
                        if perms.manage_channels:
                            todas_perms.append("Gerenciar Canais")
                        if perms.kick_members:
                            todas_perms.append("Expulsar Membros")
                        if perms.ban_members:
                            todas_perms.append("Banir Membros")
                        if perms.create_instant_invite:
                            todas_perms.append("Criar Convite")
                        if perms.change_nickname:
                            todas_perms.append("Alterar Apelido")
                        if perms.manage_nicknames:
                            todas_perms.append("Gerenciar Apelidos")
                        if perms.manage_emojis:
                            todas_perms.append("Gerenciar Emojis")
                        if perms.manage_webhooks:
                            todas_perms.append("Gerenciar Webhooks")
                        if perms.view_guild_insights:
                            todas_perms.append("Ver Insights do Servidor")
                        if hasattr(perms, 'moderate_members') and perms.moderate_members:
                            todas_perms.append("Moderar Membros")
                        if hasattr(perms, 'manage_events') and perms.manage_events:
                            todas_perms.append("Gerenciar Eventos")
                        if hasattr(perms, 'manage_threads') and perms.manage_threads:
                            todas_perms.append("Gerenciar Threads")
                        if hasattr(perms, 'create_public_threads') and perms.create_public_threads:
                            todas_perms.append("Criar Threads Públicas")
                        if hasattr(perms, 'create_private_threads') and perms.create_private_threads:
                            todas_perms.append("Criar Threads Privadas")
                        if hasattr(perms, 'send_messages_in_threads') and perms.send_messages_in_threads:
                            todas_perms.append("Enviar Mensagens em Threads")
                        
                        # Permissões de Texto
                        if perms.view_channel:
                            todas_perms.append("Ver Canais")
                        if perms.send_messages:
                            todas_perms.append("Enviar Mensagens")
                        if perms.send_tts_messages:
                            todas_perms.append("Enviar Mensagens TTS")
                        if perms.manage_messages:
                            todas_perms.append("Gerenciar Mensagens")
                        if perms.embed_links:
                            todas_perms.append("Inserir Links")
                        if perms.attach_files:
                            todas_perms.append("Anexar Arquivos")
                        if perms.read_message_history:
                            todas_perms.append("Ver Histórico de Mensagens")
                        if perms.mention_everyone:
                            todas_perms.append("Mencionar @everyone")
                        if perms.external_emojis:
                            todas_perms.append("Usar Emojis Externos")
                        if perms.add_reactions:
                            todas_perms.append("Adicionar Reações")
                        if hasattr(perms, 'use_slash_commands') and perms.use_slash_commands:
                            todas_perms.append("Usar Comandos de Barra")
                        if hasattr(perms, 'external_stickers') and perms.external_stickers:
                            todas_perms.append("Usar Stickers Externos")
                        
                        # Permissões de Voz
                        if perms.connect:
                            todas_perms.append("Conectar")
                        if perms.speak:
                            todas_perms.append("Falar")
                        if perms.stream:
                            todas_perms.append("Transmitir")
                        if perms.mute_members:
                            todas_perms.append("Mutar Membros")
                        if perms.deafen_members:
                            todas_perms.append("Ensurdecer Membros")
                        if perms.move_members:
                            todas_perms.append("Mover Membros")
                        if perms.use_voice_activation:
                            todas_perms.append("Usar Ativação por Voz")
                        if perms.priority_speaker:
                            todas_perms.append("Orador Prioritário")
                        if hasattr(perms, 'request_to_speak') and perms.request_to_speak:
                            todas_perms.append("Pedir para Falar")
                        if hasattr(perms, 'use_embedded_activities') and perms.use_embedded_activities:
                            todas_perms.append("Usar Atividades")
                        
                        # Retornar formatado
                        if todas_perms:
                            if len(todas_perms) <= 5:
                                return ", ".join(todas_perms)
                            else:
                                return ", ".join(todas_perms[:5]) + f" (+{len(todas_perms)-5} outras)"
                        return "Básicas"
                    except Exception:
                        return "Indefinido"

                # Cor
                cor_antes = getattr(before, "color", None)
                cor_depois = getattr(role, "color", None)
                if cor_antes != cor_depois:
                    linhas.append(f"{emoji.role} **Cor:** `{fmt_color(cor_antes)}` → `{fmt_color(cor_depois)}`")

                # Mencionável
                ment_antes = getattr(before, "mentionable", None)
                ment_depois = getattr(role, "mentionable", None)
                if ment_antes != ment_depois:
                    linhas.append(f"{emoji.flag} **Mencionável:** {fmt_bool(ment_antes)} → {fmt_bool(ment_depois)}")

                # Separado
                sep_antes = getattr(before, "hoist", None)
                sep_depois = getattr(role, "hoist", None)
                if sep_antes != sep_depois:
                    linhas.append(f"{emoji.pin} **Separado:** {fmt_bool(sep_antes)} → {fmt_bool(sep_depois)}")

                # Posição
                pos_antes = getattr(before, "position", None)
                pos_depois = getattr(role, "position", None)
                if pos_antes != pos_depois:
                    linhas.append(f"{emoji.chart} **Posição:** {pos_antes} → {pos_depois}")

                # Permissões (detectar mudanças em QUALQUER permissão)
                perms_antes = getattr(before, "permissions", None)
                perms_depois = getattr(role, "permissions", None)
                if perms_antes != perms_depois and perms_antes and perms_depois:
                    # Lista completa de todas as permissões possíveis
                    todas_permissoes = [
                        # Permissões Gerais
                        "administrator", "view_audit_log", "manage_guild", "manage_roles", 
                        "manage_channels", "kick_members", "ban_members", "create_instant_invite",
                        "change_nickname", "manage_nicknames", "manage_emojis", "manage_webhooks",
                        "view_guild_insights", "moderate_members", "manage_events", "manage_threads",
                        "create_public_threads", "create_private_threads", "send_messages_in_threads",
                        
                        # Permissões de Texto
                        "view_channel", "send_messages", "send_tts_messages", "manage_messages",
                        "embed_links", "attach_files", "read_message_history", "mention_everyone",
                        "external_emojis", "add_reactions", "use_slash_commands", "external_stickers",
                        
                        # Permissões de Voz
                        "connect", "speak", "stream", "mute_members", "deafen_members", "move_members",
                        "use_voice_activation", "priority_speaker", "request_to_speak", "use_embedded_activities"
                    ]
                    
                    mudou_permissao = False
                    for perm in todas_permissoes:
                        if hasattr(perms_antes, perm) and hasattr(perms_depois, perm):
                            if getattr(perms_antes, perm, False) != getattr(perms_depois, perm, False):
                                mudou_permissao = True
                                break
                    
                    if mudou_permissao:
                        linhas.append(f"{emoji.shield} **Permissões:** `{fmt_permissions(perms_antes)}` → `{fmt_permissions(perms_depois)}`")

            except Exception:
                pass

        # Quando executor é desconhecido, deixar explícito o tipo de ação e detalhar criação/exclusão
        if executor is None:
            try:
                acao_nome = {"criacao_cargo": "Criação de Cargo", "edicao_cargo": "Edição de Cargo", "exclusao_cargo": "Exclusão de Cargo"}[tipo]
                acao_emoji = {"criacao_cargo": emoji.plus, "edicao_cargo": emoji.edit, "exclusao_cargo": emoji.delete}[tipo]
                linhas.append(f"{acao_emoji} **Ação:** {acao_nome}")
            except Exception:
                linhas.append(f"{emoji.flag} **Ação:** {tipo.replace('_', ' ').capitalize()}")

            if tipo in {"criacao_cargo", "exclusao_cargo"}:
                try:
                    def fmt_bool(v: Optional[bool]) -> str:
                        if v is True:
                            return "Ativado"
                        if v is False:
                            return "Desativado"
                        return "Indefinido"

                    def fmt_color(color) -> str:
                        if not color or color == disnake.Color.default():
                            return "Padrão"
                        try:
                            return f"#{color.value:06x}"
                        except Exception:
                            return str(color)

                    def fmt_permissions(perms) -> str:
                        if not perms:
                            return "Nenhuma"
                        try:
                            # Todas as permissões possíveis do Discord
                            todas_perms = []
                            
                            # Permissões Gerais
                            if perms.administrator:
                                todas_perms.append("Administrador")
                            if perms.view_audit_log:
                                todas_perms.append("Ver Logs de Auditoria")
                            if perms.manage_guild:
                                todas_perms.append("Gerenciar Servidor")
                            if perms.manage_roles:
                                todas_perms.append("Gerenciar Cargos")
                            if perms.manage_channels:
                                todas_perms.append("Gerenciar Canais")
                            if perms.kick_members:
                                todas_perms.append("Expulsar Membros")
                            if perms.ban_members:
                                todas_perms.append("Banir Membros")
                            if perms.create_instant_invite:
                                todas_perms.append("Criar Convite")
                            if perms.change_nickname:
                                todas_perms.append("Alterar Apelido")
                            if perms.manage_nicknames:
                                todas_perms.append("Gerenciar Apelidos")
                            if perms.manage_emojis:
                                todas_perms.append("Gerenciar Emojis")
                            if perms.manage_webhooks:
                                todas_perms.append("Gerenciar Webhooks")
                            if perms.view_guild_insights:
                                todas_perms.append("Ver Insights do Servidor")
                            if hasattr(perms, 'moderate_members') and perms.moderate_members:
                                todas_perms.append("Moderar Membros")
                            if hasattr(perms, 'manage_events') and perms.manage_events:
                                todas_perms.append("Gerenciar Eventos")
                            if hasattr(perms, 'manage_threads') and perms.manage_threads:
                                todas_perms.append("Gerenciar Threads")
                            if hasattr(perms, 'create_public_threads') and perms.create_public_threads:
                                todas_perms.append("Criar Threads Públicas")
                            if hasattr(perms, 'create_private_threads') and perms.create_private_threads:
                                todas_perms.append("Criar Threads Privadas")
                            if hasattr(perms, 'send_messages_in_threads') and perms.send_messages_in_threads:
                                todas_perms.append("Enviar Mensagens em Threads")
                            
                            # Permissões de Texto
                            if perms.view_channel:
                                todas_perms.append("Ver Canais")
                            if perms.send_messages:
                                todas_perms.append("Enviar Mensagens")
                            if perms.send_tts_messages:
                                todas_perms.append("Enviar Mensagens TTS")
                            if perms.manage_messages:
                                todas_perms.append("Gerenciar Mensagens")
                            if perms.embed_links:
                                todas_perms.append("Inserir Links")
                            if perms.attach_files:
                                todas_perms.append("Anexar Arquivos")
                            if perms.read_message_history:
                                todas_perms.append("Ver Histórico de Mensagens")
                            if perms.mention_everyone:
                                todas_perms.append("Mencionar @everyone")
                            if perms.external_emojis:
                                todas_perms.append("Usar Emojis Externos")
                            if perms.add_reactions:
                                todas_perms.append("Adicionar Reações")
                            if hasattr(perms, 'use_slash_commands') and perms.use_slash_commands:
                                todas_perms.append("Usar Comandos de Barra")
                            if hasattr(perms, 'external_stickers') and perms.external_stickers:
                                todas_perms.append("Usar Stickers Externos")
                            
                            # Permissões de Voz
                            if perms.connect:
                                todas_perms.append("Conectar")
                            if perms.speak:
                                todas_perms.append("Falar")
                            if perms.stream:
                                todas_perms.append("Transmitir")
                            if perms.mute_members:
                                todas_perms.append("Mutar Membros")
                            if perms.deafen_members:
                                todas_perms.append("Ensurdecer Membros")
                            if perms.move_members:
                                todas_perms.append("Mover Membros")
                            if perms.use_voice_activation:
                                todas_perms.append("Usar Ativação por Voz")
                            if perms.priority_speaker:
                                todas_perms.append("Orador Prioritário")
                            if hasattr(perms, 'request_to_speak') and perms.request_to_speak:
                                todas_perms.append("Pedir para Falar")
                            if hasattr(perms, 'use_embedded_activities') and perms.use_embedded_activities:
                                todas_perms.append("Usar Atividades")
                            
                            # Retornar formatado
                            if todas_perms:
                                if len(todas_perms) <= 5:
                                    return ", ".join(todas_perms)
                                else:
                                    return ", ".join(todas_perms[:5]) + f" (+{len(todas_perms)-5} outras)"
                            return "Básicas"
                        except Exception:
                            return "Indefinido"

                    # Nome atual
                    nome_atual = getattr(role, "name", "?")
                    linhas.append(f"{emoji.edit} **Nome:** `{nome_atual}`")

                    # Cor
                    cor_atual = getattr(role, "color", None)
                    if cor_atual:
                        linhas.append(f"{emoji.role} **Cor:** `{fmt_color(cor_atual)}`")

                    # Mencionável
                    ment_atual = getattr(role, "mentionable", None)
                    if ment_atual is not None:
                        linhas.append(f"{emoji.flag} **Mencionável:** {fmt_bool(ment_atual)}")

                    # Separado
                    sep_atual = getattr(role, "hoist", None)
                    if sep_atual is not None:
                        linhas.append(f"{emoji.pin} **Separado:** {fmt_bool(sep_atual)}")

                    # Posição
                    pos_atual = getattr(role, "position", None)
                    if pos_atual is not None:
                        linhas.append(f"{emoji.chart} **Posição:** {pos_atual}")

                    # Permissões
                    perms_atual = getattr(role, "permissions", None)
                    if perms_atual:
                        linhas.append(f"{emoji.shield} **Permissões:** `{fmt_permissions(perms_atual)}`")

                except Exception:
                    pass

        # Mesmo desativado: logar executor e alvos recentes
        if not ativado:
            if executor:
                self._registrar_alvo(guild.id, tipo, executor.id, getattr(role, 'id', 0), intervalo)
                mencoes = self._listar_alvos_mencionados(guild.id, tipo, executor.id, intervalo)
                if mencoes:
                    linhas.extend(mencoes)
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada ({tipo.replace('_', ' ')})")
            await enviar_log(guild, config.get("cargos_avancado", {}).get("canal_logs"), "Proteção de Cargos - Logs", linhas)
            return

        # Contagem
        contagem = 0
        if executor:
            contagem = self._incrementar_contador(guild.id, tipo, executor.id, intervalo)
            self._registrar_alvo(guild.id, tipo, executor.id, getattr(role, 'id', 0), intervalo)
            linhas.append(f"{emoji.chart} **Contagem:** {contagem}/{limite} em {intervalo}s")
            mencoes = self._listar_alvos_mencionados(guild.id, tipo, executor.id, intervalo)
            if mencoes:
                linhas.extend(mencoes)

        # Imunidades
        executor_imune = self._executor_imune(executor, config.get("cargos_avancado", {}))

        excedeu = executor and contagem > limite
        if excedeu:
            linhas.append(f"{emoji.warn} **Ação:** Limite excedido ({tipo.replace('_', ' ')})")
            if not executor_imune:
                punicao = config.get("cargos_avancado", {}).get("punicao", "ban")
                if punicao != "none":
                    resultado = await self._aplicar_punicao(
                        guild,
                        executor,
                        punicao,
                        motivo=f"Violou proteção de cargos ({tipo.replace('_', ' ')}) em <@&{getattr(role,'id',0)}>"
                    )
                    linhas.append(f"{emoji.wand} **Punição:** {punicao.capitalize()} — {resultado}")
                else:
                    linhas.append(f"{emoji.wand} **Punição:** Nenhuma (configurado)")
            else:
                linhas.append(f"{emoji.shield} **Ação:** Executor imune — punição não aplicada")

            await enviar_log(guild, config.get("cargos_avancado", {}).get("canal_logs"), "Proteção de Cargos - Logs", linhas)
            return

        # Sem excesso: logar
        await enviar_log(guild, config.get("cargos_avancado", {}).get("canal_logs"), "Proteção de Cargos - Logs", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(MonProtCargos(bot))

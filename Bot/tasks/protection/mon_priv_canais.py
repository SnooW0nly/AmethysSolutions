import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.protecaogeral.canais import helpers


class MonProtCanais(commands.Cog):
    TIPOS = ("criacao", "edicao", "exclusao")

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

    # Punicao
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
        # Canais como menção <#id>, um por linha, com vírgula
        return [f"<#${alvo_id}>,".replace('$', '') for _, alvo_id in list(fila)]

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

    @staticmethod
    def _canal_categoria_imune(channel: disnake.abc.GuildChannel, config: dict) -> bool:
        try:
            categoria_id = getattr(getattr(channel, 'category', None), 'id', None)
            if not categoria_id:
                return False
            ids = set(config.get("categorias_imunes", []))
            return categoria_id in ids
        except Exception:
            return False

    # Listeners
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: disnake.abc.GuildChannel):
        await self._processar("criacao", channel)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        await self._processar("edicao", after, before)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
        await self._processar("exclusao", channel)

    async def _processar(self, tipo: str, channel: disnake.abc.GuildChannel, before: Optional[disnake.abc.GuildChannel] = None):
        if tipo not in self.TIPOS:
            return
        guild = channel.guild
        if not guild:
            return
        
        config = helpers.carregar_config()
        if not config:
            return
        
        avancado = config.get("canais_avancado", {})

        try:
            await asyncio.sleep(0.75)
        except Exception:
            pass

        action = {
            "criacao": disnake.AuditLogAction.channel_create,
            "edicao": disnake.AuditLogAction.channel_update,
            "exclusao": disnake.AuditLogAction.channel_delete,
        }[tipo]
        executor = await self._resolver_executor(guild, channel, action)

        # Carregar configurações do tipo
        ativado = bool(config.get(tipo, {}).get("ativado", False))
        limite = int(config.get(tipo, {}).get("limite", 1))
        intervalo = int(config.get(tipo, {}).get("intervalo", 10))

        # Verificar se haverá lista de canais afetados
        tem_lista_canais = False
        if executor:
            fila = self._alvos[guild.id][tipo][executor.id]
            agora = time.time()
            # Simular limpeza da fila para ver se há alvos
            alvos_validos = [(ts, alvo_id) for ts, alvo_id in fila if (agora - ts) <= intervalo]
            tem_lista_canais = len(alvos_validos) > 0
        
        # Montar log base
        linhas = []
        
        # Só mostrar canal individual se não houver lista de canais afetados
        if not tem_lista_canais:
            linhas.append(f"{emoji.dir} **Canal:** <#{getattr(channel, 'id', 0)}> ({getattr(channel, 'id', 0)})")
        
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
        # Só mostrar se não vai exceder limite (evita mostrar detalhes de apenas 1 canal quando a punição é por múltiplos)
        if tipo == "edicao" and before is not None and not vai_exceder_limite:
            try:
                nome_antes = getattr(before, "name", "?")
                nome_depois = getattr(channel, "name", "?")
                if nome_antes != nome_depois:
                    linhas.append(f"{emoji.edit} **Nome:** `{nome_antes}` → `{nome_depois}`")
            except Exception:
                pass

            # Propriedades comuns de canais
            try:
                def fmt_bool(v: Optional[bool]) -> str:
                    if v is True:
                        return "Ativado"
                    if v is False:
                        return "Desativado"
                    return "Indefinido"

                def fmt_topic(v: Optional[str]) -> str:
                    txt = (v or "").strip()
                    if not txt:
                        return "Vazio"
                    if len(txt) > 120:
                        txt = txt[:117] + "..."
                    return txt.replace('`', "ʼ")

                def fmt_seconds(v: Optional[int]) -> str:
                    if v is None:
                        return "Indefinido"
                    return f"{int(v)}s"

                def fmt_bitrate(v: Optional[int]) -> str:
                    if v is None:
                        return "Indefinido"
                    try:
                        return f"{int(v)//1000} kbps"
                    except Exception:
                        return str(v)

                def fmt_category(cat) -> str:
                    if not cat:
                        return "Sem categoria"
                    try:
                        nome = getattr(cat, "name", "?")
                        cid = getattr(cat, "id", "?")
                        return f"{nome} ({cid})"
                    except Exception:
                        return "?"

                nsfw_before = getattr(before, "nsfw", None)
                nsfw_after = getattr(channel, "nsfw", None)
                if nsfw_before != nsfw_after:
                    linhas.append(f"{emoji.warn} **NSFW:** {fmt_bool(nsfw_before)} → {fmt_bool(nsfw_after)}")

                topic_before = getattr(before, "topic", None)
                topic_after = getattr(channel, "topic", None)
                if topic_before != topic_after:
                    linhas.append(f"{emoji.textc} **Tópico:** `{fmt_topic(topic_before)}` → `{fmt_topic(topic_after)}`")

                slow_before = getattr(before, "slowmode_delay", getattr(before, "rate_limit_per_user", None))
                slow_after = getattr(channel, "slowmode_delay", getattr(channel, "rate_limit_per_user", None))
                if slow_before != slow_after and (slow_before is not None or slow_after is not None):
                    linhas.append(f"{emoji.clock} **Slowmode:** {fmt_seconds(slow_before)} → {fmt_seconds(slow_after)}")

                bitrate_before = getattr(before, "bitrate", None)
                bitrate_after = getattr(channel, "bitrate", None)
                if bitrate_before != bitrate_after and (bitrate_before is not None or bitrate_after is not None):
                    linhas.append(f"{emoji.streaming} **Bitrate:** {fmt_bitrate(bitrate_before)} → {fmt_bitrate(bitrate_after)}")

                ul_before = getattr(before, "user_limit", None)
                ul_after = getattr(channel, "user_limit", None)
                if ul_before != ul_after and (ul_before is not None or ul_after is not None):
                    linhas.append(f"{emoji.members} **Limite de usuários:** {ul_before if ul_before is not None else 'Indefinido'} → {ul_after if ul_after is not None else 'Indefinido'}")

                pos_before = getattr(before, "position", None)
                pos_after = getattr(channel, "position", None)
                if pos_before != pos_after and (pos_before is not None or pos_after is not None):
                    linhas.append(f"{emoji.pin} **Posição:** {pos_before if pos_before is not None else 'Indefinido'} → {pos_after if pos_after is not None else 'Indefinido'}")

                cat_before = getattr(before, "category", None)
                cat_after = getattr(channel, "category", None)
                if getattr(cat_before, 'id', None) != getattr(cat_after, 'id', None):
                    linhas.append(f"{emoji.dir} **Categoria:** `{fmt_category(cat_before)}` → `{fmt_category(cat_after)}`")
            except Exception:
                pass

            # Diff de permissões (overwrites)
            try:
                def map_overwrites(ch: disnake.abc.GuildChannel):
                    try:
                        return {t.id: (t, ow) for t, ow in getattr(ch, "overwrites", {}).items()}
                    except Exception:
                        return {}

                def ow_to_dict(ow: disnake.PermissionOverwrite) -> dict:
                    try:
                        return dict(getattr(ow, "_values", {}))
                    except Exception:
                        # Fallback vazio se não for possível inspecionar
                        return {}

                def format_target(t) -> str:
                    try:
                        if isinstance(t, disnake.Role):
                            return f"<@&{t.id}> ({t.id})"
                        if isinstance(t, disnake.Member):
                            return f"<@{t.id}> ({t.id})"
                        # Pode ser RolePlaceholder/UserPlaceholder em audit-log; usar genérico
                        mention = getattr(t, "mention", None)
                        if mention:
                            return f"{mention} ({getattr(t, 'id', '??')})"
                        return f"ID {getattr(t, 'id', '??')}"
                    except Exception:
                        return f"ID {getattr(t, 'id', '??')}"

                before_map = map_overwrites(before)
                after_map = map_overwrites(channel)
                todos_ids = set(before_map.keys()) | set(after_map.keys())

                alteracoes_formatadas: list[str] = []
                for tid in sorted(todos_ids):
                    t_before = before_map.get(tid)
                    t_after = after_map.get(tid)

                    ow_before = t_before[1] if t_before else None
                    ow_after = t_after[1] if t_after else None

                    dict_before = ow_to_dict(ow_before) if ow_before else {}
                    dict_after = ow_to_dict(ow_after) if ow_after else {}

                    # Detectar remoção/adição completa de overwrite
                    if dict_before == dict_after:
                        continue

                    alvo_obj = (t_after or t_before)[0] if (t_after or t_before) else None
                    cabecalho = f"• {format_target(alvo_obj)}"

                    # Quais permissões mudaram
                    chaves = set(dict_before.keys()) | set(dict_after.keys())
                    linhas_perm: list[str] = []
                    for perm in sorted(chaves):
                        antes = dict_before.get(perm)
                        depois = dict_after.get(perm)
                        if antes == depois:
                            continue
                        def v(vv):
                            return "Permitir" if vv is True else ("Negar" if vv is False else "Neutro")
                        linhas_perm.append(f"- `{perm}`: {v(antes)} → {v(depois)}")

                    if not linhas_perm:
                        continue

                    alteracoes_formatadas.append(cabecalho)
                    alteracoes_formatadas.extend(linhas_perm)

                if alteracoes_formatadas:
                    linhas.append(f"{emoji.perm if hasattr(emoji, 'perm') else emoji.role} **Permissões alteradas:**")
                    linhas.extend(alteracoes_formatadas)
            except Exception:
                # Evitar quebrar o monitor por falha no diff de permissões
                pass

        # Quando executor é desconhecido, deixar explícito o tipo de ação e detalhar criação/exclusão
        if executor is None:
            try:
                acao_nome = {"criacao": "Criação", "edicao": "Edição", "exclusao": "Exclusão"}.get(tipo, tipo.capitalize())
                acao_emoji = {"criacao": emoji.plus, "edicao": emoji.edit, "exclusao": emoji.delete}.get(tipo, emoji.flag)
                linhas.append(f"{acao_emoji} **Ação:** {acao_nome}")
            except Exception:
                linhas.append(f"{emoji.flag} **Ação:** {tipo.capitalize()}")

            if tipo in {"criacao", "exclusao"}:
                try:
                    def fmt_bool(v: Optional[bool]) -> str:
                        if v is True:
                            return "Ativado"
                        if v is False:
                            return "Desativado"
                        return "Indefinido"

                    def fmt_topic(v: Optional[str]) -> str:
                        txt = (v or "").strip()
                        if not txt:
                            return "Vazio"
                        if len(txt) > 120:
                            txt = txt[:117] + "..."
                        return txt.replace('`', "ʼ")

                    def fmt_seconds(v: Optional[int]) -> str:
                        if v is None:
                            return "Indefinido"
                        return f"{int(v)}s"

                    def fmt_bitrate(v: Optional[int]) -> str:
                        if v is None:
                            return "Indefinido"
                        try:
                            return f"{int(v)//1000} kbps"
                        except Exception:
                            return str(v)

                    def fmt_category(cat) -> str:
                        if not cat:
                            return "Sem categoria"
                        try:
                            nome = getattr(cat, "name", "?")
                            cid = getattr(cat, "id", "?")
                            return f"{nome} ({cid})"
                        except Exception:
                            return "?"

                    def detectar_tipo_canal(ch) -> str:
                        try:
                            tp = getattr(ch, "type", None)
                            name = getattr(tp, "name", str(tp))
                            mapa = {
                                "text": "Texto",
                                "voice": "Voz",
                                "category": "Categoria",
                                "stage_voice": "Stage",
                                "forum": "Fórum",
                                "news": "Anúncios",
                                "public_thread": "Thread Pública",
                                "private_thread": "Thread Privada",
                                "news_thread": "Thread de Anúncios",
                            }
                            return mapa.get(name, name or "Desconhecido")
                        except Exception:
                            return "Desconhecido"

                    # Nome e tipo atuais
                    nome_atual = getattr(channel, "name", "?")
                    linhas.append(f"{emoji.edit} **Nome:** `{nome_atual}`")
                    linhas.append(f"{emoji.route} **Tipo:** {detectar_tipo_canal(channel)}")

                    # Categoria
                    cat_atual = getattr(channel, "category", None)
                    linhas.append(f"{emoji.dir} **Categoria:** `{fmt_category(cat_atual)}`")

                    # Propriedades possíveis
                    nsfw_val = getattr(channel, "nsfw", None)
                    if nsfw_val is not None:
                        linhas.append(f"{emoji.warn} **NSFW:** {fmt_bool(nsfw_val)}")

                    topic_val = getattr(channel, "topic", None)
                    if topic_val is not None:
                        linhas.append(f"{emoji.textc} **Tópico:** `{fmt_topic(topic_val)}`")

                    slow_val = getattr(channel, "slowmode_delay", getattr(channel, "rate_limit_per_user", None))
                    if slow_val is not None:
                        linhas.append(f"{emoji.clock} **Slowmode:** {fmt_seconds(slow_val)}")

                    bitrate_val = getattr(channel, "bitrate", None)
                    if bitrate_val is not None:
                        linhas.append(f"{emoji.streaming} **Bitrate:** {fmt_bitrate(bitrate_val)}")

                    user_limit_val = getattr(channel, "user_limit", None)
                    if user_limit_val is not None:
                        linhas.append(f"{emoji.members} **Limite de usuários:** {user_limit_val}")

                    pos_val = getattr(channel, "position", None)
                    if pos_val is not None:
                        linhas.append(f"{emoji.pin} **Posição:** {pos_val}")
                except Exception:
                    pass

        # Mesmo desativado: logar executor e alvos recentes
        if not ativado:
            if executor:
                self._registrar_alvo(guild.id, tipo, executor.id, getattr(channel, 'id', 0), intervalo)
                mencoes = self._listar_alvos_mencionados(guild.id, tipo, executor.id, intervalo)
                if mencoes:
                    linhas.extend(mencoes)
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada ({tipo})")
            await enviar_log(guild, avancado.get("canal_logs"), "Proteção de Canais - Logs", linhas)
            return

        # Contagem
        contagem = 0
        if executor:
            contagem = self._incrementar_contador(guild.id, tipo, executor.id, intervalo)
            self._registrar_alvo(guild.id, tipo, executor.id, getattr(channel, 'id', 0), intervalo)
            linhas.append(f"{emoji.chart} **Contagem:** {contagem}/{limite} em {intervalo}s")
            mencoes = self._listar_alvos_mencionados(guild.id, tipo, executor.id, intervalo)
            if mencoes:
                linhas.extend(mencoes)

        # Imunidades
        executor_imune = self._executor_imune(executor, avancado)
        categoria_imune = self._canal_categoria_imune(channel, avancado)

        excedeu = executor and contagem > limite
        if excedeu:
            linhas.append(f"{emoji.warn} **Ação:** Limite excedido ({tipo})")
            if not (executor_imune or categoria_imune):
                punicao = avancado.get("punicao", "ban")
                if punicao != "none":
                    resultado = await self._aplicar_punicao(
                        guild,
                        executor,
                        punicao,
                        motivo=f"Violou proteção de canais ({tipo}) em <#{getattr(channel,'id',0)}>"
                    )
                    linhas.append(f"{emoji.wand} **Punição:** {punicao.capitalize()} — {resultado}")
                else:
                    linhas.append(f"{emoji.wand} **Punição:** Nenhuma (configurado)")
            else:
                if executor_imune:
                    linhas.append(f"{emoji.shield} **Ação:** Executor imune — punição não aplicada")
                if categoria_imune:
                    linhas.append(f"{emoji.shield} **Ação:** Categoria imune — punição não aplicada")

            await enviar_log(guild, avancado.get("canal_logs"), "Proteção de Canais - Logs", linhas)
            return

        # Sem excesso: logar
        await enviar_log(guild, avancado.get("canal_logs"), "Proteção de Canais - Logs", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(MonProtCanais(bot))


import asyncio
import datetime
import time
from typing import List, Optional, Set

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.privatizacoes.perms import helpers


class MonPrivPerms(commands.Cog):
    """Monitora concessão de permissões perigosas via atribuição de cargos.

    Lê de database/protection/privatizacoes.json a subchave "permissoes" com o formato:
      {
        "ativado": bool,
        "canal_logs": channel_id | null,
        "punicao": "ban" | "kick" | "remover_cargos" | "none",
        "cargos_imunes": [role_ids...] (opcional)
      }
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # UI/log helpers
    @staticmethod
    def _formatar_punicao(valor: str) -> str:
        return {
            "ban": "Banir",
            "kick": "Expulsar",
            "remover_cargos": "Remover Cargos",
            "none": "Nenhum",
        }.get(valor, valor.capitalize())

    @staticmethod
    def _criar_container_log(titulo: str, linhas: List[str], **kwargs) -> disnake.ui.Container:
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
            **kwargs,
        )

    # Punição
    @staticmethod
    async def _aplicar_punicao(guild: disnake.Guild, executor: Optional[disnake.Member], punicao: str, motivo: str) -> str:
        if executor is None:
            return "Executor desconhecido — sem punição"
        try:
            if punicao == "ban":
                await guild.ban(executor, reason=motivo, clean_history_duration=datetime.timedelta(seconds=0))
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

    # Audit log helpers
    def _ids_from_roles_like(self, roles_like) -> Set[int]:
        ids: Set[int] = set()
        if not roles_like:
            return ids
        try:
            for item in roles_like:
                if hasattr(item, 'id'):
                    ids.add(int(item.id))
                elif isinstance(item, dict) and 'id' in item:
                    try:
                        ids.add(int(item['id']))
                    except Exception:
                        pass
                elif hasattr(item, 'role') and hasattr(item.role, 'id'):
                    ids.add(int(item.role.id))
                elif isinstance(item, int):
                    ids.add(int(item))
        except TypeError:
            item = roles_like
            if hasattr(item, 'id'):
                ids.add(int(item.id))
            elif isinstance(item, dict) and 'id' in item:
                try:
                    ids.add(int(item['id']))
                except Exception:
                    pass
            elif hasattr(item, 'role') and hasattr(item.role, 'id'):
                ids.add(int(item.role.id))
            elif isinstance(item, int):
                ids.add(int(item))
        return ids

    def _extract_added_role_ids_from_entry(self, entry) -> Set[int]:
        try:
            before_roles = getattr(getattr(entry, 'before', None), 'roles', None)
            after_roles = getattr(getattr(entry, 'after', None), 'roles', None)
            before_ids = self._ids_from_roles_like(before_roles)
            after_ids = self._ids_from_roles_like(after_roles)
            if after_ids or before_ids:
                added = after_ids - before_ids
                if added:
                    return added
        except Exception:
            pass
        try:
            changes = getattr(entry, 'changes', None)
            roles_change = getattr(changes, 'roles', None)
            added_list = getattr(roles_change, 'added', None) or getattr(roles_change, '$add', None) or getattr(roles_change, 'new_value', None)
            removed_list = getattr(roles_change, 'removed', None) or getattr(roles_change, '$remove', None) or getattr(roles_change, 'old_value', None)
            added_ids = self._ids_from_roles_like(added_list)
            removed_ids = self._ids_from_roles_like(removed_list)
            if added_ids:
                if removed_ids:
                    return added_ids - removed_ids
                return added_ids
        except Exception:
            pass
        return set()

    async def _resolver_executor(self, guild: disnake.Guild, alvo: disnake.Member, roles_adicionados: List[disnake.Role], limite_segundos: int = 120) -> Optional[disnake.Member]:
        for _ in range(8):
            try:
                agora = disnake.utils.utcnow()
                async for entry in guild.audit_logs(action=disnake.AuditLogAction.member_role_update, limit=25):
                    if getattr(entry, "target", None) and entry.target.id == alvo.id:
                        if (agora - entry.created_at).total_seconds() <= limite_segundos:
                            added_ids = self._extract_added_role_ids_from_entry(entry)
                            novos_ids = {r.id for r in roles_adicionados if r}
                            usuario = entry.user
                            membro = usuario if isinstance(usuario, disnake.Member) else guild.get_member(getattr(usuario, 'id', 0))
                            if membro and (not self.bot.user or membro.id != self.bot.user.id):
                                if not novos_ids or not added_ids or (novos_ids & added_ids):
                                    return membro
            except Exception:
                pass
            await asyncio.sleep(1.2)

        # Fallback: cargo gerenciado por bot
        for role in roles_adicionados:
            try:
                tags = getattr(role, 'tags', None)
                bot_id = getattr(tags, 'bot_id', None) if tags else None
                if bot_id:
                    membro = guild.get_member(int(bot_id))
                    if membro:
                        return membro
            except Exception:
                continue
        return None

    async def _resolver_executor_role_update(self, guild: disnake.Guild, role: disnake.Role, limite_segundos: int = 120) -> Optional[disnake.Member]:
        for _ in range(8):
            try:
                agora = disnake.utils.utcnow()
                async for entry in guild.audit_logs(action=disnake.AuditLogAction.role_update, limit=25):
                    if getattr(entry, "target", None) and entry.target.id == role.id:
                        if (agora - entry.created_at).total_seconds() <= limite_segundos:
                            usuario = entry.user
                            membro = usuario if isinstance(usuario, disnake.Member) else guild.get_member(getattr(usuario, 'id', 0))
                            if membro and (not self.bot.user or membro.id != self.bot.user.id):
                                return membro
            except Exception:
                pass
            await asyncio.sleep(1.2)
        return None

    # Perms helpers
    @staticmethod
    def _permissoes_perigosas() -> Set[str]:
        # Conjunto ampliado cobrindo permissões administrativas críticas
        return {
            'administrator',
            'ban_members',
            'kick_members',
            'manage_guild',
            'view_audit_log',
            'manage_roles',
            'manage_channels',   # inclui criar/editar/apagar canais
            'manage_webhooks',
            'manage_messages',
            'mention_everyone',
            'moderate_members',
            'manage_nicknames',
            'manage_threads',
            'manage_events',
            # variações para emojis/expressões conforme versão do disnake
            'manage_emojis',                 # muito antigo
            'manage_emojis_and_stickers',    # legacy
            'manage_expressions',            # mais novo
        }

    @staticmethod
    def _label_perm(nome: str) -> str:
        mapa = {
            'administrator': 'Administrador',
            'ban_members': 'Banir Membros',
            'kick_members': 'Expulsar Membros',
            'manage_guild': 'Gerenciar Servidor',
            'view_audit_log': 'Ver Registro de Auditoria',
            'manage_roles': 'Gerenciar Cargos',
            'manage_channels': 'Gerenciar Canais',
            'manage_webhooks': 'Gerenciar Webhooks',
            'manage_messages': 'Gerenciar Mensagens',
            'mention_everyone': 'Mencionar @everyone/@here',
            'moderate_members': 'Silenciar/Timeout Membros',
            'manage_nicknames': 'Gerenciar Apelidos',
            'manage_threads': 'Gerenciar Tópicos',
            'manage_events': 'Gerenciar Eventos',
            'manage_emojis': 'Gerenciar Emojis',
            'manage_emojis_and_stickers': 'Gerenciar Emojis/Stickers',
            'manage_expressions': 'Gerenciar Expressões',
        }
        return mapa.get(nome, nome)

    @classmethod
    def _formatar_perms(cls, perms: Set[str]) -> str:
        if not perms:
            return 'Nenhuma'
        return ', '.join(sorted([cls._label_perm(p) for p in perms]))

    @classmethod
    def _formatar_perms_resumido(cls, perms: Set[str]) -> str:
        if not perms:
            return 'Nenhuma'
        if 'administrator' in perms:
            return 'Administrador (todas)'
        labels = [cls._label_perm(p) for p in perms]
        labels_sorted = sorted(labels)
        limite = 4
        if len(labels_sorted) <= limite:
            return ', '.join(labels_sorted)
        return f"{', '.join(labels_sorted[:limite])} e +{len(labels_sorted) - limite}"

    @classmethod
    def _permissoes_True_set(cls, perms: disnake.Permissions) -> Set[str]:
        perigosas = cls._permissoes_perigosas()
        ativas = set()
        for nome in perigosas:
            if getattr(perms, nome, False):
                ativas.add(nome)
        return ativas

    @classmethod
    def _permissoes_adicionadas(cls, before: disnake.Member, after: disnake.Member) -> Set[str]:
        try:
            antes = cls._permissoes_True_set(before.guild_permissions)
            depois = cls._permissoes_True_set(after.guild_permissions)
            return depois - antes
        except Exception:
            return set()

    @classmethod
    def _permissoes_dos_roles(cls, roles: List[disnake.Role]) -> Set[str]:
        perigosas = cls._permissoes_perigosas()
        result: Set[str] = set()
        for role in roles:
            try:
                if not role:
                    continue
                for nome in perigosas:
                    if getattr(role.permissions, nome, False):
                        result.add(nome)
            except Exception:
                continue
        return result

    @staticmethod
    def _roles_adicionados(before: disnake.Member, after: disnake.Member) -> List[disnake.Role]:
        before_ids = {r.id for r in getattr(before, 'roles', [])}
        after_ids = {r.id for r in getattr(after, 'roles', [])}
        novos_ids = list(after_ids - before_ids)
        if not novos_ids:
            return []
        guild = after.guild
        return [guild.get_role(rid) for rid in novos_ids if guild.get_role(rid)]

    @staticmethod
    def _roles_causadores_perms(roles: List[disnake.Role], perms_perigosas: Set[str]) -> List[disnake.Role]:
        causadores = []
        for role in roles:
            try:
                if not role:
                    continue
                # disnake.Role.permissions -> Permissions
                for nome in perms_perigosas:
                    if getattr(role.permissions, nome, False):
                        causadores.append(role)
                        break
            except Exception:
                continue
        return causadores

    @staticmethod
    def _mencionar_roles(roles: List[disnake.Role]) -> str:
        if not roles:
            return "Nenhum"
        mencoes = [r.mention for r in roles]
        return ", ".join(mencoes[:2]) + ("..." if len(mencoes) > 2 else "")

    @staticmethod
    def _mencionar_membros(membros: List[disnake.Member]) -> str:
        if not membros:
            return "Nenhum"
        mencoes = [m.mention for m in membros]
        return ", ".join(mencoes[:2]) + ("..." if len(mencoes) > 2 else "")

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        if after.bot:
            return

        config = helpers.carregar_config()
        dados_base = config.get(helpers.CHAVE, {})
        dados_avancados = config.get(f"{helpers.CHAVE}_avancado", {})

        if not config:
            return

        # Quais cargos foram adicionados
        roles_add = self._roles_adicionados(before, after)
        if not roles_add:
            return

        # Cargos causadores (possuem as permissões perigosas)
        causadores = self._roles_causadores_perms(roles_add, self._permissoes_perigosas())
        if not causadores:
            # Pode haver timing no cálculo do aggregate; ainda assim tentar detectar perms pelo diff global
            perms_diff = self._permissoes_adicionadas(before, after)
            if not perms_diff:
                return
            causadores = roles_add

        # Permissões acrescentadas: usar diff global; se vazio, inferir a partir das roles causadoras
        perms_add = self._permissoes_adicionadas(before, after)
        if not perms_add:
            perms_add = self._permissoes_dos_roles(causadores)

        guild = after.guild

        # Imunidade do alvo por cargo
        cargos_imunes_ids: Set[int] = set(dados_avancados.get("cargos_imunes", []))
        if any(r.id in cargos_imunes_ids for r in after.roles):
            linhas = [
                f"{emoji.member} **Membro:** {after.mention} ({after.id})",
                f"{emoji.wand} **Permissões adicionadas:** {self._formatar_perms_resumido(perms_add)}",
                f"{emoji.role} **Cargos adicionados com permissão:** {self._mencionar_roles(causadores)}",
            ]
            # Resolver executor via registro de auditoria mesmo com alvo imune
            try:
                await asyncio.sleep(0.75)
            except Exception:
                pass
            executor_imune = await self._resolver_executor(guild, after, roles_add)
            if executor_imune:
                self._add_executor_info(linhas, executor_imune)
            linhas.append(f"{emoji.shield} **Ação:** O membro é imune a proteção")
            await enviar_log(
                guild,
                dados_avancados.get("canal_logs"),
                "Privatização de Permissões - Logs",
                linhas,
            )
            return

        # Pequeno delay para audit log
        try:
            await asyncio.sleep(0.75)
        except Exception:
            pass

        executor = await self._resolver_executor(guild, after, roles_add)

        linhas = [
            f"{emoji.member} **Membro:** {after.mention} ({after.id})",
            f"{emoji.wand} **Permissões adicionadas:** {self._formatar_perms_resumido(perms_add)}",
            f"{emoji.role} **Cargos adicionados com permissão:** {self._mencionar_roles(causadores)}",
        ]
        if executor:
            self._add_executor_info(linhas, executor)

        if dados_base.get("ativado", False):
            # Reverter: remover apenas as roles causadoras
            try:
                if causadores:
                    await after.remove_roles(*causadores, reason="Proteção: permissões privadas")
                    linhas.append(f"{emoji.reload} **Reversão:** Cargos causadores removidos do alvo")
            except Exception:
                linhas.append(f"{emoji.wrong} **Reversão:** Falhou ao remover cargos (permissões?)")

            punicao = dados_avancados.get("punicao", "kick")
            resultado = await self._aplicar_punicao(
                guild,
                executor,
                punicao,
                motivo=f"Violou proteção de permissões privadas ao conceder {', '.join(sorted(perms_add))} ao membro {after}"
            )
            if punicao != "none":
                linhas.append(f"{emoji.wand} **Punição:** {self._formatar_punicao(punicao)} — {resultado}")

            await enviar_log(
                guild,
                dados_avancados.get("canal_logs"),
                "Privatização de Permissões - Logs",
                linhas,
            )
        else:
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada")
            await enviar_log(
                guild,
                dados_avancados.get("canal_logs"),
                "Privatização de Permissões - Logs",
                linhas,
            )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: disnake.Role, after: disnake.Role):
        # Detectar permissões perigosas adicionadas a um cargo já existente
        config = helpers.carregar_config()
        dados_base = config.get(helpers.CHAVE, {})
        dados_avancados = config.get(f"{helpers.CHAVE}_avancado", {})

        if not config:
            return
        perigosas = self._permissoes_perigosas()
        try:
            antes = self._permissoes_True_set(before.permissions)
            depois = self._permissoes_True_set(after.permissions)
            adicionadas = (depois - antes) & perigosas
        except Exception:
            adicionadas = set()
        if not adicionadas:
            return

        guild = after.guild

        # Alvos impactados: todos membros que possuem o cargo editado
        membros_afetados: List[disnake.Member] = list(getattr(after, 'members', []))
        if not membros_afetados:
            # ninguém com o cargo; ainda assim, logar a alteração
            executor = await self._resolver_executor_role_update(guild, after)
            linhas = [
                f"{emoji.role} **Cargo editado:** {after.mention} ({after.id})",
                f"{emoji.wand} **Permissões adicionadas ao cargo:** {self._formatar_perms(adicionadas)}",
            ]
            if executor:
                self._add_executor_info(linhas, executor)
            if dados_base.get("ativado", False):
                linhas.append(f"{emoji.reload} **Reversão:** Nenhuma (sem membros afetados)")
            else:
                linhas.append(f"{emoji.shield} **Ação:** Proteção desativada")
            await enviar_log(guild, dados_avancados.get("canal_logs"), "Privatização de Permissões - Logs", linhas)
            return

        # Filtrar alvos imunes
        cargos_imunes_ids: Set[int] = set(dados_avancados.get("cargos_imunes", []))
        membros_nao_imunes = [m for m in membros_afetados if not any(r.id in cargos_imunes_ids for r in m.roles)]

        # Resolver executor do update do cargo
        try:
            await asyncio.sleep(0.75)
        except Exception:
            pass
        executor = await self._resolver_executor_role_update(guild, after)

        linhas = [
            f"{emoji.role} **Cargo editado:** {after.mention} ({after.id})",
            f"{emoji.wand} **Permissões adicionadas ao cargo:** {self._formatar_perms(adicionadas)}",
            f"{emoji.members} **Membros afetados:** {len(membros_afetados)} ({self._mencionar_membros(membros_afetados)})",
        ]
        if executor:
            self._add_executor_info(linhas, executor)

        if dados_base.get("ativado", False):
            # Remover o cargo dos membros não imunes
            removidos = 0
            for m in membros_nao_imunes:
                try:
                    await m.remove_roles(after, reason="Proteção: permissões privadas (cargo editado)")
                    removidos += 1
                except Exception:
                    continue
            linhas.append(f"{emoji.reload} **Reversão:** Cargo removido de {removidos} membro(s) não imunes")

            # Punir executor
            punicao = dados_avancados.get("punicao", "kick")
            resultado = await self._aplicar_punicao(
                guild,
                executor,
                punicao,
                motivo=f"Violou proteção de permissões privadas ao adicionar {self._formatar_perms(adicionadas)} no cargo {after.name}"
            )
            if punicao != "none":
                linhas.append(f"{emoji.wand} **Punição:** {self._formatar_punicao(punicao)} — {resultado}")

            await enviar_log(guild, dados_avancados.get("canal_logs"), "Privatização de Permissões - Logs", linhas)
        else:
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada")
            await enviar_log(guild, dados_avancados.get("canal_logs"), "Privatização de Permissões - Logs", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(MonPrivPerms(bot))



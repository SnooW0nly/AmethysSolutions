import asyncio
import datetime
import time
from typing import List, Optional, Set

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.privatizacoes.cargos import helpers


class MonPrivCargos(commands.Cog):
    """Monitora atribuições de cargos privados e aplica ações conforme configuração."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Utilidades de log
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

    # Utilidades de punição
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
                # remove todos os cargos (exceto @everyone)
                roles_to_remove = [r for r in executor.roles if r.is_default() is False]
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

    @staticmethod
    def _mencionar_cargos(roles: List[disnake.Role]) -> str:
        if not roles:
            return "Nenhum"
        mencoes = [r.mention for r in roles]
        return ", ".join(mencoes[:2]) + ("..." if len(mencoes) > 2 else "")

    # Resolvedor de executor via audit log
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
            # Não iterável: tentar direto
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
        """Tenta extrair quais cargos foram adicionados nesse entry de audit log."""
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
        # Tentativa alternativa: alguns formatos trazem changes diretas
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

    async def _resolver_executor(self, guild: disnake.Guild, alvo: disnake.Member, violacoes_roles: List[disnake.Role], limite_segundos: int = 120) -> Optional[disnake.Member]:
        # Retry no audit log para lidar com latência
        for _ in range(8):
            try:
                # usar timezone-aware para comparar com created_at do audit log
                agora = disnake.utils.utcnow()
                async for entry in guild.audit_logs(action=disnake.AuditLogAction.member_role_update, limit=25):
                    if getattr(entry, "target", None) and entry.target.id == alvo.id:
                        if (agora - entry.created_at).total_seconds() <= limite_segundos:
                            # Validar que os cargos adicionados neste entry incluem os violados
                            added_ids = self._extract_added_role_ids_from_entry(entry)
                            violados_ids = {r.id for r in violacoes_roles if r}
                            usuario = entry.user
                            membro = usuario if isinstance(usuario, disnake.Member) else guild.get_member(getattr(usuario, 'id', 0))
                            if membro and (not self.bot.user or membro.id != self.bot.user.id):
                                if not violados_ids or not added_ids or (violados_ids & added_ids):
                                    return membro
            except Exception:
                pass
            await asyncio.sleep(1.2)

        # Fallback: se algum cargo for gerenciado por bot, usar o bot do cargo
        for role in violacoes_roles:
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

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        # Ignorar bots como alvos
        if after.bot:
            return

        config = helpers.carregar_config()
        dados_base = config.get(helpers.CHAVE, {})
        dados_avancados = config.get(f"{helpers.CHAVE}_avancado", {})

        cargos_privados_ids: Set[int] = set(dados_avancados.get("cargos_privados", []))
        if not cargos_privados_ids:
            return

        # Detectar cargos adicionados
        before_ids = {r.id for r in getattr(before, "roles", [])}
        after_ids = {r.id for r in getattr(after, "roles", [])}
        adicionados_ids = list(after_ids - before_ids)
        if not adicionados_ids:
            return

        # Filtrar apenas cargos privados
        violacoes_ids = [rid for rid in adicionados_ids if rid in cargos_privados_ids]
        if not violacoes_ids:
            return

        guild = after.guild
        # Resolver objetos Role das violações
        violacoes_roles: List[disnake.Role] = [guild.get_role(rid) for rid in violacoes_ids if guild.get_role(rid)]

        # Checar imunidade do alvo
        cargos_imunes_ids: Set[int] = set(dados_avancados.get("cargos_imunes", []))
        if any(r.id in cargos_imunes_ids for r in after.roles):
            # Apenas logar como ignorado por imunidade (Container)
            linhas = [
                f"{emoji.member} **Membro:** {after.mention} ({after.id})",
                f"{emoji.role} **Cargos privados adicionados:** {self._mencionar_cargos(violacoes_roles)}",
                f"{emoji.shield} **Ação:** Alvo imune — somente log",
            ]
            await enviar_log(
                guild,
                dados_avancados.get("canal_logs"),
                "Privatização de Cargos - Logs",
                linhas,
            )
            return

        # Aguardar levemente para o registro de auditoria ser persistido
        try:
            await asyncio.sleep(0.75)
        except Exception:
            pass
        # Encontrar executor via registro de auditoria
        executor = await self._resolver_executor(guild, after, violacoes_roles)

        # Montar linhas base do log (Container)
        linhas = [
            f"{emoji.member} **Membro:** {after.mention} ({after.id})",
            f"{emoji.role} **Cargos privados adicionados:** {self._mencionar_cargos(violacoes_roles)}",
        ]
        if executor:
            self._add_executor_info(linhas, executor)

        # Se ativado: reverter e punir; se desativado: apenas logar
        if dados_base.get("ativado", False):
            # Reverter cargos privados adicionados
            try:
                roles_to_remove = [r for r in violacoes_roles if r is not None]
                if roles_to_remove:
                    await after.remove_roles(*roles_to_remove, reason="Proteção: cargo privado")
                    linhas.append(f"{emoji.reload} **Reversão:** Cargos privados removidos do alvo")
            except Exception:
                linhas.append(f"{emoji.wrong} **Reversão:** Verifique as permissões do bot")

            punicao = dados_avancados.get("punicao", "kick")
            resultado = await self._aplicar_punicao(
                guild,
                executor,
                punicao,
                motivo=f"Violou proteção de cargos privados ao atribuir {self._mencionar_cargos(violacoes_roles)} para {after}"
            )
            if punicao != "none":
                linhas.append(f"{emoji.wand} **Punição:** {self._formatar_punicao(punicao)} — {resultado}")
            await enviar_log(
                guild,
                dados_avancados.get("canal_logs"),
                "Privatização de Cargos - Logs",
                linhas,
            )
        else:
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada")
            await enviar_log(
                guild,
                dados_avancados.get("canal_logs"),
                "Privatização de Cargos - Logs",
                linhas,
            )


def setup(bot: commands.Bot):
    bot.add_cog(MonPrivCargos(bot))


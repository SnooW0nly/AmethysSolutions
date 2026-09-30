import asyncio
import time
from typing import List, Optional

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.privatizacoes.apps import helpers


class MonPrivAplicacoes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

    async def _resolver_executor(self, guild: disnake.Guild, bot_member: disnake.Member, limite_segundos: int = 120) -> Optional[disnake.Member]:
        # Tenta encontrar quem adicionou o bot via audit log
        for _ in range(8):
            try:
                agora = disnake.utils.utcnow()
                async for entry in guild.audit_logs(action=disnake.AuditLogAction.bot_add, limit=10):
                    if getattr(entry, "target", None) and entry.target.id == bot_member.id:
                        if (agora - entry.created_at).total_seconds() <= limite_segundos:
                            usuario = entry.user
                            membro = usuario if isinstance(usuario, disnake.Member) else guild.get_member(getattr(usuario, 'id', 0))
                            if membro and (not self.bot.user or membro.id != self.bot.user.id):
                                return membro
            except Exception:
                pass
            await asyncio.sleep(1.2)
        return None

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        if not member.bot:
            return
        guild = member.guild
        config = helpers.carregar_config()
        dados_base = config.get(helpers.CHAVE, {})
        dados_avancados = config.get(f"{helpers.CHAVE}_avancado", {})

        if not dados_base.get("ativado", False):
            return
        
        cargos_imunes_ids = set(dados_avancados.get("cargos_imunes", []))
        # Pequeno delay para garantir que o audit log foi atualizado
        try:
            await asyncio.sleep(0.75)
        except Exception:
            pass
        executor = await self._resolver_executor(guild, member)
        linhas = [
            f"{emoji.member} **Bot adicionado:** {member.mention} ({member.id})",
        ]
        if executor:
            self._add_executor_info(linhas, executor)
        # Se o executor for imune, apenas loga
        if executor and any(r.id in cargos_imunes_ids for r in getattr(executor, "roles", [])):
            linhas.append(f"{emoji.shield} **Ação:** Executor imune à proteção")
            await enviar_log(
                guild,
                dados_avancados.get("canal_logs"),
                "Privatização de Aplicações - Logs",
                linhas,
            )
            return
        # Remover o bot
        try:
            await guild.kick(member, reason="Proteção: adição de bot não autorizada")
            linhas.append(f"{emoji.reload} **Reversão:** Bot removido do servidor")
        except Exception:
            linhas.append(f"{emoji.wrong} **Reversão:** Falhou ao remover o bot (permissões?)")
        # Punir executor
        punicao = dados_avancados.get("punicao", "kick")
        if punicao != "none":
            resultado = await self._aplicar_punicao(
                guild,
                executor,
                punicao,
                motivo=f"Violou proteção de aplicações ao adicionar o bot {member.mention} ({member.id})"
            )
            linhas.append(f"{emoji.wand} **Punição:** {self._formatar_punicao(punicao)} — {resultado}")
        await enviar_log(
            guild,
            dados_avancados.get("canal_logs"),
            "Privatização de Aplicações - Logs",
            linhas,
        )

def setup(bot: commands.Bot):
    bot.add_cog(MonPrivAplicacoes(bot))

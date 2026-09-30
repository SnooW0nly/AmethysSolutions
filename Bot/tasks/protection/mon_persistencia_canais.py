import asyncio
import time
from typing import Optional
from functions.database import database as db

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.privatizacoes.persistencia import helpers

class MonPersistenciaCanais(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Config helpers
    @classmethod
    def _carregar_config(cls) -> dict:
        doc = db.get_document(cls.COLLECTION_NAME)
        
        base = doc.get(cls.CHAVE_PRINCIPAL, {})
        avancado = doc.get(f"{cls.CHAVE_PRINCIPAL}_avancado", {})

        config = {
            "ativado": base.get("ativado", cls.PADRAO["ativado"]),
            "punicao": avancado.get("punicao", cls.PADRAO["punicao"]),
            "cargos_imunes": avancado.get("cargos_imunes", cls.PADRAO["cargos_imunes"]),
            "categorias_imunes": avancado.get("categorias_imunes", cls.PADRAO["categorias_imunes"]),
            "canal_logs": avancado.get("canal_logs", cls.PADRAO["canal_logs"]),
        }
        return config

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
            **kwargs,
        )

    def _canal_imune(self, channel: disnake.abc.GuildChannel, config_avancado: dict) -> bool:
        if not hasattr(channel, 'category') or channel.category is None:
            return False
        categorias_imunes_ids = set(config_avancado.get("categorias_imunes", []))
        return channel.category.id in categorias_imunes_ids

    def _categoria_imune(self, channel: disnake.abc.GuildChannel, config_avancado: dict) -> bool:
        if not hasattr(channel, 'category') or channel.category is None:
            return False
        categorias_imunes_ids = set(config_avancado.get("categorias_imunes", []))
        return channel.category.id in categorias_imunes_ids

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

    async def _resolver_executor(self, guild: disnake.Guild, channel: disnake.abc.GuildChannel, limite_segundos: int = 120) -> Optional[disnake.Member]:
        # Busca no audit log quem deletou o canal
        for _ in range(8):
            try:
                agora = disnake.utils.utcnow()
                async for entry in guild.audit_logs(action=disnake.AuditLogAction.channel_delete, limit=10):
                    if getattr(entry, "target", None) and entry.target.id == channel.id:
                        if (agora - entry.created_at).total_seconds() <= limite_segundos:
                            usuario = entry.user
                            membro = usuario if isinstance(usuario, disnake.Member) else guild.get_member(getattr(usuario, 'id', 0))
                            if membro and (not self.bot.user or membro.id != self.bot.user.id):
                                return membro
            except Exception:
                pass
            await asyncio.sleep(1.2)
        return None

    def _add_executor_info(self, linhas: list[str], executor: Optional[disnake.Member]):
        if executor:
            info_executor = [
                f"{emoji.member} **Executor:** {executor.mention} ({executor.id})",
                f"{emoji.information} **Cargo mais alto:** {executor.top_role.mention}",
                f"{emoji.information} **Quantidade de cargos:** {len(executor.roles)}",
            ]
            if executor.joined_at:
                info_executor.append(f"{emoji.information} **Entrou em:** <t:{int(executor.joined_at.timestamp())}:f> (<t:{int(executor.joined_at.timestamp())}:R>)")
            if executor.created_at:
                info_executor.append(f"{emoji.information} **Conta criada em:** <t:{int(executor.created_at.timestamp())}:f> (<t:{int(executor.created_at.timestamp())}:R>)")
            linhas.extend(info_executor)
        else:
            linhas.append(f"{emoji.member} **Executor:** Desconhecido (N/A)")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
        guild = channel.guild
        config = helpers.carregar_config()
        dados_base = config.get(helpers.CHAVE, {})
        dados_avancados = config.get(f"{helpers.CHAVE}_avancado", {})

        punicao_configurada_str = f"{emoji.settings2} **Punição configurada:** {({'ban': 'Banir', 'kick': 'Expulsar', 'remover_cargos': 'Remover Cargos', 'none': 'Nenhuma'}.get(dados_avancados.get('punicao', 'ban'), 'N/A'))}"

        if not dados_base.get("ativado", False):
            executor = await self._resolver_executor(guild, channel)
            linhas = [f"{emoji.dir} **Canal deletado:** {channel.name} ({channel.id})"]
            self._add_executor_info(linhas, executor)
            linhas.extend([
                f"{emoji.shield} **Ação:** Proteção desativada",
                punicao_configurada_str,
                f"{emoji.shield} **Resultado:** Proteção desativada"
            ])
            await enviar_log(guild, dados_avancados.get("canal_logs"), "Persistência de Canais - Logs", linhas)
            return
        
        if self._categoria_imune(channel, dados_avancados):
            executor = await self._resolver_executor(guild, channel)
            linhas = [f"{emoji.dir} **Canal deletado:** {channel.name} ({channel.id})"]
            self._add_executor_info(linhas, executor)
            linhas.extend([
                f"{emoji.shield} **Ação:** Categoria imune",
                punicao_configurada_str,
                f"{emoji.shield} **Resultado:** Categoria imune"
            ])
            await enviar_log(guild, dados_avancados.get("canal_logs"), "Persistência de Canais - Logs", linhas)
            return

        # Buscar executor
        try:
            await asyncio.sleep(0.75)
        except Exception:
            pass
        executor = await self._resolver_executor(guild, channel)
        
        linhas = [f"{emoji.dir} **Canal deletado:** {channel.name} ({channel.id})"]
        self._add_executor_info(linhas, executor)

        # Checar imunidade do executor
        cargos_imunes_ids = set(dados_avancados.get("cargos_imunes", []))
        if executor and any(r.id in cargos_imunes_ids for r in getattr(executor, "roles", [])):
            linhas.extend([
                f"{emoji.shield} **Ação:** Executor imune à proteção",
                punicao_configurada_str,
                f"{emoji.shield} **Resultado:** Executor imune"
            ])
            await enviar_log(guild, dados_avancados.get("canal_logs"), "Persistência de Canais - Logs", linhas)
            return

        # Tenta restaurar o canal
        linhas.extend([
            f"{emoji.shield} **Ação:** Tentativa de reversão e punição",
            punicao_configurada_str
        ])
        
        try:
            novo_canal = await guild.create_text_channel(
                name=channel.name,
                category=guild.get_channel(channel.category_id) if channel.category_id else None,
                overwrites=channel.overwrites,
                position=channel.position,
                topic=getattr(channel, "topic", None),
                slowmode_delay=getattr(channel, "slowmode_delay", 0),
                nsfw=getattr(channel, "nsfw", False),
                reason="Persistência de canais: restauração automática"
            ) if isinstance(channel, disnake.TextChannel) else (
                await guild.create_voice_channel(
                    name=channel.name,
                    category=guild.get_channel(channel.category_id) if channel.category_id else None,
                    overwrites=channel.overwrites,
                    position=channel.position,
                    bitrate=getattr(channel, "bitrate", None),
                    user_limit=getattr(channel, "user_limit", None),
                    reason="Persistência de canais: restauração automática"
                ) if isinstance(channel, disnake.VoiceChannel) else None
            )
            if novo_canal:
                linhas.append(f"{emoji.reload} **Reversão:** Canal restaurado: {novo_canal.mention} ({novo_canal.id})")
            else:
                linhas.append(f"{emoji.wrong} **Reversão:** Tipo de canal não suportado para restauração automática")
        except Exception as e:
            linhas.append(f"{emoji.wrong} **Reversão:** Falhou ao restaurar canal ({e})")
        
        # Punição
        punicao = dados_avancados.get("punicao", "ban")
        if punicao != "none":
            resultado = await self._aplicar_punicao(
                guild,
                executor,
                punicao,
                motivo=f"Persistência de canais: exclusão do canal {channel.name} ({channel.id})"
            )
            linhas.append(f"{emoji.ban} **Punição:** {punicao.capitalize()} — {resultado}")
        else:
            linhas.append(f"{emoji.ban} **Punição:** Nenhuma - apenas restaurar")
        
        await enviar_log(guild, dados_avancados.get("canal_logs"), "Persistência de Canais - Logs", linhas)

def setup(bot: commands.Bot):
    bot.add_cog(MonPersistenciaCanais(bot))

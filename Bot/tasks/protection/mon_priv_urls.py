import asyncio
import re
import time
from typing import List, Optional

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.privatizacoes.urls import helpers


class MonPrivUrl(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
    async def _aplicar_punicao(guild: disnake.Guild, autor: Optional[disnake.Member], punicao: str, motivo: str) -> str:
        if autor is None:
            return "Autor desconhecido — sem punição"
        try:
            if punicao == "ban":
                await guild.ban(autor, reason=motivo)
                return "Aplicada"
            if punicao == "kick":
                await guild.kick(autor, reason=motivo)
                return "Aplicada"
            if punicao == "remover_cargos":
                roles_to_remove = [r for r in autor.roles if not r.is_default()]
                if roles_to_remove:
                    await autor.remove_roles(*roles_to_remove, reason=motivo)
                return "Aplicada"
            return "Sem punição (configurado como none)"
        except Exception:
            return "Falha ao punir (Verifique as permissões do bot)"

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

    @staticmethod
    def _autor_imune(autor: disnake.Member, config_avancado: dict) -> bool:
        ids = set(config_avancado.get("cargos_imunes", []))
        if not ids:
            return False
        return any(r.id in ids for r in autor.roles)

    @staticmethod
    def _canal_imune(canal: disnake.abc.GuildChannel, config_avancado: dict) -> bool:
        canais_ids = set(config_avancado.get("canais_imunes", []))
        if not canais_ids:
            return False
        try:
            canal_id = canal.id
        except Exception:
            return False
        return canal_id in canais_ids

    @staticmethod
    def _resumo_conteudo(conteudo: str, limite: int = 200) -> str:
        if not conteudo:
            return "(sem conteúdo)"
        return conteudo if len(conteudo) <= limite else conteudo[:limite - 3] + "..."

    @staticmethod
    def _detectar_urls(conteudo: str) -> List[str]:
        # Regex simples para URLs/domínios
        url_regex = re.compile(r"(https?://\S+|www\.\S+|\b[a-zA-Z0-9.-]+\.(com|net|org|br|io|gg|xyz|me|app|site|shop|store|info|dev|link|live|tv|co|edu|gov|mil|biz|club|online|pro|tech|ai|ca|us|uk|es|fr|it|de|ru|jp|cn|in|au|ar|pt|pl|tr|nl|se|no|fi|dk|be|ch|at|cz|gr|hu|ie|il|lt|lu|lv|ro|sk|si|ua|za|cl|mx|pe|ve|uy|ec|bo|py|do|cr|gt|hn|ni|pa|sv|bz|jm|tt|bs|bb|ag|ai|aw|bm|bq|vg|ky|ms|tc|kn|lc|vc|sx|mf|gp|mq|re|yt|pm|bl|wf|pf|nc|tf|pf|sb|vu|fj|pg|ws|to|tv|ck|nu|tk|fm|mh|pw|nr|ki|tv|cx|cc|nf|hm|gs|aq|io|sh|ac|su|asia|cat|jobs|mobi|museum|name|post|tel|travel|arpa|int|aero|coop|edu|gov|mil|museum|name|pro|tel|travel|xxx)\b)", re.IGNORECASE)
        return url_regex.findall(conteudo or "")

    async def _processar_mensagem(self, msg: disnake.Message, editado: bool = False):
        if not msg.guild or msg.author.bot:
            return
        config = helpers.carregar_config()
        dados_base = config.get(helpers.CHAVE, {})
        dados_avancados = config.get(f"{helpers.CHAVE}_avancado", {})

        if not config:
            return
        urls = self._detectar_urls(msg.content)
        if not urls:
            return
        # Se desativado, apenas loga
        if not dados_base.get("ativado", False):
            linhas = [
                f"{emoji.textc} **Canal:** {msg.channel.mention} ({msg.channel.id})",
                f"{emoji.message} **Conteúdo:** {self._resumo_conteudo(msg.content)}",
                f"{emoji.website} **URLs detectadas:** {', '.join([u[0] for u in urls])}",
            ]
            self._add_executor_info(linhas, msg.author)
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada")
            await enviar_log(msg.guild, dados_avancados.get("canal_logs"), "Privatização de URLs - Logs", linhas)
            return
        # Se canal imune, apenas loga
        if self._canal_imune(msg.channel, dados_avancados):
            linhas = [
                f"{emoji.textc} **Canal:** {msg.channel.mention} ({msg.channel.id})",
                f"{emoji.message} **Conteúdo:** {self._resumo_conteudo(msg.content)}",
                f"{emoji.website} **URLs detectadas:** {', '.join([u[0] for u in urls])}",
            ]
            self._add_executor_info(linhas, msg.author)
            linhas.append(f"{emoji.shield} **Ação:** O canal é imune à proteção")
            await enviar_log(msg.guild, dados_avancados.get("canal_logs"), "Privatização de URLs - Logs", linhas)
            return
        # Se imune, apenas loga
        if self._autor_imune(msg.author, dados_avancados):
            linhas = [
                f"{emoji.textc} **Canal:** {msg.channel.mention} ({msg.channel.id})",
                f"{emoji.message} **Conteúdo:** {self._resumo_conteudo(msg.content)}",
                f"{emoji.website} **URLs detectadas:** {', '.join([u[0] for u in urls])}",
            ]
            self._add_executor_info(linhas, msg.author)
            linhas.append(f"{emoji.shield} **Ação:** O membro é imune à proteção")
            await enviar_log(msg.guild, dados_avancados.get("canal_logs"), "Privatização de URLs - Logs", linhas)
            return
        # Apagar mensagem
        linhas = [
            f"{emoji.textc} **Canal:** {msg.channel.mention} ({msg.channel.id})",
            f"{emoji.message} **Conteúdo:** {self._resumo_conteudo(msg.content)}",
            f"{emoji.website} **URLs detectadas:** {', '.join([u[0] for u in urls])}",
        ]
        self._add_executor_info(linhas, msg.author)
        try:
            await msg.delete()
            linhas.append(f"{emoji.delete} **Reversão:** Mensagem deletada")
        except Exception:
            linhas.append(f"{emoji.wrong} **Reversão:** Falhou ao deletar a mensagem (permissões?)")
        # Punir autor
        punicao = dados_avancados.get("punicao", "kick")
        if punicao != "none":
            resultado = await self._aplicar_punicao(
                msg.guild, msg.author, punicao, motivo=f"Privatização de URLs: {', '.join([u[0] for u in urls])} em {msg.channel}"
            )
            linhas.append(f"{emoji.wand} **Punição:** {punicao.capitalize()} — {resultado}")
        await enviar_log(msg.guild, dados_avancados.get("canal_logs"), "Privatização de URLs - Logs", linhas)

    @commands.Cog.listener()
    async def on_message(self, msg: disnake.Message):
        await self._processar_mensagem(msg, editado=False)

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        try:
            await asyncio.sleep(0.1)
        except Exception:
            pass
        await self._processar_mensagem(after, editado=True)

def setup(bot: commands.Bot):
    bot.add_cog(MonPrivUrl(bot))

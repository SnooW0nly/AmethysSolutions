import asyncio
import io
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

import aiohttp
import disnake
from disnake.ext import commands, tasks

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.protecaogeral.imagens_mrbeast import helpers


# ---------------------------------------------------------------------------
# Perceptual hash — usa imagehash + Pillow
# ---------------------------------------------------------------------------

MRBEAST_HASHES = [
    "00000000ffffffff0000d9ddb999dddddfdd0110333300000000000000000000",
    "00000000ffffffffffff44440000dddd8888cccc4cc4ba000000000000000000",
    "00008cc8ffffceeceeee44444cc4ceeccccccccccc8c00000000000000000000",
    "000011937667ffffbbbbbbbb33330000ffff6626222200000000000000000000",
]

HAMMING_THRESHOLD = 10


def _calcular_hash(img_bytes: bytes) -> Optional[str]:
    try:
        import imagehash
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        return str(imagehash.phash(img, hash_size=8))
    except Exception:
        return None


def _hamming(h1: str, h2: str) -> int:
    try:
        # imagehash retorna hex de 16 chars (64 bits)
        return bin(int(h1, 16) ^ int(h2, 16)).count("1")
    except Exception:
        return 64


def _is_mrbeast_image(img_hash: str) -> bool:
    for known in MRBEAST_HASHES:
        h1 = img_hash.ljust(16, "0")[:16]
        h2 = known.ljust(16, "0")[:16]
        if _hamming(h1, h2) <= HAMMING_THRESHOLD:
            return True
    return False


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class MonProtImagensMrBeast(commands.Cog):
    """Monitora e remove mensagens com imagens de spam MrBeast (selfbots)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> author_id -> deque[timestamps]
        self._contadores: Dict[int, Dict[int, Deque[float]]] = defaultdict(
            lambda: defaultdict(lambda: deque())
        )
        # Anti-duplicação de punições: guild_id -> author_id -> timestamp
        self._punidos_recentemente: Dict[int, Dict[int, float]] = defaultdict(dict)
        self._session: Optional[aiohttp.ClientSession] = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        if not self.cleanup_task.is_running():
            self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())

    @tasks.loop(minutes=10)
    async def cleanup_task(self):
        agora = time.time()
        for guild_id in list(self._punidos_recentemente.keys()):
            for uid in list(self._punidos_recentemente[guild_id].keys()):
                if (agora - self._punidos_recentemente[guild_id][uid]) > 3600:
                    del self._punidos_recentemente[guild_id][uid]
            if not self._punidos_recentemente[guild_id]:
                del self._punidos_recentemente[guild_id]

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    @staticmethod
    def _formatar_punicao(valor: str) -> str:
        return {
            "ban": "Banir",
            "kick": "Expulsar",
            "remover_cargos": "Remover Cargos",
            "none": "Nenhum",
        }.get(valor, valor.capitalize())

    @staticmethod
    async def _aplicar_punicao(
        guild: disnake.Guild,
        membro: Optional[disnake.Member],
        punicao: str,
        motivo: str,
    ) -> str:
        if membro is None:
            return "Executor desconhecido — sem punição"
        try:
            if punicao == "ban":
                await guild.ban(membro, reason=motivo)
                return "Aplicada"
            if punicao == "kick":
                await guild.kick(membro, reason=motivo)
                return "Aplicada"
            if punicao == "remover_cargos":
                roles_to_remove = [r for r in membro.roles if not r.is_default()]
                if roles_to_remove:
                    await membro.remove_roles(*roles_to_remove, reason=motivo)
                return "Aplicada"
            return "Sem punição (configurado como none)"
        except Exception:
            return "Falha ao punir (Verifique as permissões do bot)"

    def _add_autor_info(self, linhas: list[str], membro: Optional[disnake.Member]):
        if membro:
            info = [f"{emoji.member} **Autor:** {membro.mention} ({membro.id})"]
            if not membro.bot:
                info.extend([
                    f"{emoji.information} **Cargo mais alto:** {membro.top_role.mention}",
                    f"{emoji.information} **Quantidade de cargos:** {len(membro.roles)}",
                ])
                if membro.joined_at:
                    info.append(
                        f"{emoji.information} **Entrou em:** "
                        f"<t:{int(membro.joined_at.timestamp())}:f> "
                        f"(<t:{int(membro.joined_at.timestamp())}:R>)"
                    )
                if membro.created_at:
                    info.append(
                        f"{emoji.information} **Conta criada em:** "
                        f"<t:{int(membro.created_at.timestamp())}:f> "
                        f"(<t:{int(membro.created_at.timestamp())}:R>)"
                    )
            linhas.extend(info)
        else:
            linhas.append(f"{emoji.member} **Autor:** Desconhecido (N/A)")

    def _incrementar_contador(self, guild_id: int, author_id: int, intervalo: int) -> int:
        agora = time.time()
        fila = self._contadores[guild_id][author_id]
        while fila and (agora - fila[0]) > intervalo:
            fila.popleft()
        fila.append(agora)
        return len(fila)

    async def _baixar_imagem(self, url: str) -> Optional[bytes]:
        try:
            session = self._session or aiohttp.ClientSession()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Listener principal
    # ------------------------------------------------------------------

    @commands.Cog.listener("on_message")
    async def on_message_mrbeast(self, message: disnake.Message):
        if not message.guild:
            return
        if self.bot.user and message.author.id == self.bot.user.id:
            return

        # Coletar URLs de imagens da mensagem
        candidatos: list[str] = []
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                candidatos.append(att.url)
        for emb in message.embeds:
            if emb.image and emb.image.url:
                candidatos.append(emb.image.url)
            if emb.thumbnail and emb.thumbnail.url:
                candidatos.append(emb.thumbnail.url)

        if not candidatos:
            return

        config = helpers.carregar_config()
        dados_base = config.get(helpers.CHAVE, {})
        dados_avancados = config.get(f"{helpers.CHAVE}_avancado", {})

        canal_logs        = dados_avancados.get("canal_logs")
        punicao_cfg       = dados_avancados.get("punicao", "ban")
        cargos_imunes_ids = set(dados_avancados.get("cargos_imunes", []))
        limite            = int(dados_avancados.get("limite", 1))
        intervalo         = int(dados_avancados.get("intervalo", 60))

        guild  = message.guild
        author = message.author
        membro = guild.get_member(author.id)

        # Verificar cada imagem contra os hashes conhecidos
        match_encontrado = False
        hash_detectado   = ""
        for url in candidatos:
            img_bytes = await self._baixar_imagem(url)
            if img_bytes is None:
                continue
            h = await asyncio.get_event_loop().run_in_executor(None, _calcular_hash, img_bytes)
            if h and _is_mrbeast_image(h):
                match_encontrado = True
                hash_detectado = h
                break

        if not match_encontrado:
            return

        # Proteção desativada — só loga
        if not dados_base.get("ativado", False):
            linhas = [
                f"{emoji.warn} **Imagem MrBeast detectada** (spam de selfbot)",
                f"{emoji.textc} **Canal:** {message.channel.mention} (`{message.channel.id}`)",
                f"{emoji.information} **Hash detectado:** `{hash_detectado}`",
            ]
            self._add_autor_info(linhas, membro)
            linhas.append(f"{emoji.shield} **Ação:** Proteção desativada")
            await enviar_log(guild, canal_logs, "Proteção MrBeast - Logs", linhas)
            return

        # Imunidade por cargo
        if membro and any(r.id in cargos_imunes_ids for r in membro.roles):
            linhas = [
                f"{emoji.warn} **Imagem MrBeast detectada** (spam de selfbot)",
                f"{emoji.textc} **Canal:** {message.channel.mention} (`{message.channel.id}`)",
                f"{emoji.information} **Hash detectado:** `{hash_detectado}`",
            ]
            self._add_autor_info(linhas, membro)
            linhas.append(f"{emoji.shield} **Ação:** Autor imune — somente log")
            await enviar_log(guild, canal_logs, "Proteção MrBeast - Logs", linhas)
            return

        # Contagem na janela deslizante
        contagem = self._incrementar_contador(guild.id, author.id, intervalo)

        linhas = [
            f"{emoji.warn} **Imagem MrBeast detectada** (spam de selfbot)",
            f"{emoji.textc} **Canal:** {message.channel.mention} (`{message.channel.id}`)",
            f"{emoji.information} **Hash detectado:** `{hash_detectado}`",
            f"{emoji.chart} **Contagem:** {contagem}/{limite} em {intervalo}s",
        ]
        self._add_autor_info(linhas, membro)

        # Deletar a mensagem
        try:
            await message.delete()
            linhas.append(f"{emoji.delete} **Mensagem:** Removida com sucesso")
        except Exception:
            linhas.append(f"{emoji.wrong} **Mensagem:** Falhou ao remover (permissões?)")

        # Punir ao atingir o limite
        if contagem >= limite:
            agora = time.time()
            ultimo = self._punidos_recentemente[guild.id].get(author.id, 0)
            if (agora - ultimo) < (intervalo * 2):
                linhas.append(f"{emoji.shield} **Punição:** Já aplicada recentemente — ignorando")
                await enviar_log(guild, canal_logs, "Proteção MrBeast - Logs", linhas)
                return

            self._punidos_recentemente[guild.id][author.id] = agora

            if punicao_cfg != "none":
                resultado = await self._aplicar_punicao(
                    guild,
                    membro,
                    punicao_cfg,
                    motivo=f"Spam de imagens MrBeast (selfbot) — {contagem} detecções em {intervalo}s",
                )
                linhas.append(f"{emoji.wand} **Punição:** {self._formatar_punicao(punicao_cfg)} — {resultado}")
            else:
                linhas.append(f"{emoji.wand} **Punição:** Nenhuma (configurado como none)")
        else:
            linhas.append(f"{emoji.shield} **Ação:** Mensagem removida — aguardando limite para punir")

        await enviar_log(guild, canal_logs, "Proteção MrBeast - Logs", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(MonProtImagensMrBeast(bot))
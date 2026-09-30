import re
import io
import os
import base64
import aiohttp
import disnake
from disnake.ext import commands
from urllib.parse import urlparse, unquote

from ..anunciar import Anunciar
from functions.database import database
from functions.emoji import emoji

AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav", ".flac", ".m4a", ".webm")

AUDIO_URL_RE = re.compile(
    r"https?://\S+\.(?:mp3|ogg|wav|flac|m4a|webm)(?:\?[^\s]*)?",
    re.IGNORECASE,
)


def _is_audio_url(url: str) -> bool:
    return bool(AUDIO_URL_RE.match(url.strip()))


def _is_audio_attachment(att: disnake.Attachment) -> bool:
    return (
        att.filename.lower().endswith(AUDIO_EXTENSIONS)
        or (att.content_type or "").startswith("audio/")
    )


def _save_audio_url(url: str) -> None:
    """Salva apenas a URL (modo manual via modal)."""
    db = database.get_document("messages_anunciar")
    db.setdefault("message", {})["audio"] = url
    db["message"]["audio_data"] = None      # limpa cache de bytes anterior
    db["message"]["audio_filename"] = None
    database.save_document("messages_anunciar", {}, db)


def _save_audio_bytes(filename: str, data: bytes) -> None:
    """Salva os bytes do áudio em base64 no banco (modo automático via anexo)."""
    db = database.get_document("messages_anunciar")
    db.setdefault("message", {})["audio"] = filename           # exibe o nome no painel
    db["message"]["audio_data"] = base64.b64encode(data).decode()
    db["message"]["audio_filename"] = filename
    database.save_document("messages_anunciar", {}, db)


def _clear_audio() -> None:
    db = database.get_document("messages_anunciar")
    msg = db.setdefault("message", {})
    msg["audio"] = None
    msg["audio_data"] = None
    msg["audio_filename"] = None
    database.save_document("messages_anunciar", {}, db)


def _get_audio() -> str | None:
    db = database.get_document("messages_anunciar")
    return (db.get("message") or {}).get("audio")


def _build_panel(audio_url: str | None) -> list:
    if audio_url:
        filename = audio_url.split("/")[-1].split("?")[0] or audio_url
        status = f"🎵 `{filename}`"
    else:
        status = "`Nenhum áudio configurado`"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Anunciar > Áudio"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(
                "Configure o áudio que será enviado junto com a mensagem.\n\n"
                "**Como adicionar:**\n"
                "- **Automático:** envie um arquivo de áudio neste chat "
                "(`.mp3`, `.ogg`, `.wav`, `.flac`, `.m4a`, `.webm`) "
                "e o bot configura sozinho.\n"
                "- **Manual:** clique em **Definir URL** e cole o link direto.\n\n"
                f"**Áudio atual:** {status}"
            ),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Definir URL",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="Anunciar_DefinirAudio",
                ),
                disnake.ui.Button(
                    label="Remover áudio",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id="Anunciar_ApagarAudio",
                    disabled=audio_url is None,
                ),
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar", emoji=emoji.back, custom_id="Anunciar_PainelInicial"
            )
        ),
    ]


async def download_audio(url: str) -> disnake.File | None:
    """
    Tenta montar o arquivo de áudio para envio.
    Primeiro verifica se há bytes salvos no banco (anexo enviado pelo usuário).
    Se não houver, tenta baixar da URL (modo manual via modal).
    """
    db = database.get_document("messages_anunciar")
    msg_cfg = db.get("message") or {}
    audio_data_b64 = msg_cfg.get("audio_data")
    audio_filename = msg_cfg.get("audio_filename")

    # Usa bytes do banco se disponíveis (não expira)
    if audio_data_b64 and audio_filename:
        try:
            data = base64.b64decode(audio_data_b64)
            return disnake.File(fp=io.BytesIO(data), filename=audio_filename)
        except Exception:
            pass  # fallback para download abaixo

    # Fallback: tenta baixar da URL (modal manual)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                fname = unquote(os.path.basename(urlparse(url).path)) or "audio"
                if not any(fname.lower().endswith(e) for e in AUDIO_EXTENSIONS):
                    fname += ".mp3"
                data = await resp.read()
                return disnake.File(fp=io.BytesIO(data), filename=fname)
    except Exception:
        return None


class Audio(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class AudioModal(disnake.ui.Modal):
        def __init__(self):
            cur = _get_audio() or ""
            super().__init__(
                title="Definir Áudio — URL",
                custom_id="Anunciar_AudioModal",
                components=[
                    disnake.ui.TextInput(
                        label="URL do arquivo de áudio",
                        custom_id="audio_url",
                        style=disnake.TextInputStyle.short,
                        placeholder="https://exemplo.com/audio.mp3",
                        required=True,
                        max_length=500,
                        value=cur,
                    )
                ],
            )

        async def callback(self, inter: disnake.ModalInteraction):
            url = inter.text_values.get("audio_url", "").strip()
            if not _is_audio_url(url):
                await inter.response.send_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"{emoji.wrong} **URL inválida.**\n"
                                "-# Use um link direto para um arquivo de áudio "
                                "(.mp3, .ogg, .wav, .flac, .m4a, .webm)."
                            )
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True),
                    ephemeral=True,
                )
                return
            _save_audio_url(url)
            await inter.response.edit_message(components=_build_panel(url))

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # Abre modal de URL
        if cid == "Anunciar_DefinirAudio":
            await inter.response.send_modal(self.AudioModal())

        # Abre subpainel de áudio e registra ID do painel para o on_message
        elif cid == "Anunciar_AbrirAudio":
            db = database.get_document("messages_anunciar")
            meta = db.setdefault("_meta", {})
            meta["panel_message_id"]  = inter.message.id
            meta["panel_channel_id"]  = inter.channel.id
            meta["audio_mode"]        = "main"
            meta["audio_btn_editing"] = None   # garante que o listener do buttons.py não interfere
            database.save_document("messages_anunciar", {}, db)
            await inter.response.edit_message(components=_build_panel(_get_audio()))

    # Detecção automática de arquivo enviado no chat
    @commands.Cog.listener("on_message")
    async def on_message(self, msg: disnake.Message):
        if msg.author.bot or not msg.guild:
            return

        audio_att = next(
            (a for a in msg.attachments if _is_audio_attachment(a)), None
        )
        if not audio_att:
            return

        db       = database.get_document("messages_anunciar")
        meta     = db.get("_meta") or {}
        panel_ch = meta.get("panel_channel_id")

        # Só age se houver painel principal de áudio aberto neste canal
        if not panel_ch or int(panel_ch) != msg.channel.id:
            return
        if meta.get("audio_mode") != "main":
            return

        # Baixa os bytes imediatamente enquanto a URL do CDN ainda é válida
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    audio_att.url, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    resp.raise_for_status()
                    audio_bytes = await resp.read()
            _save_audio_bytes(audio_att.filename, audio_bytes)
        except Exception:
            # Se falhar o download, salva só a URL como fallback
            _save_audio_url(audio_att.url)

        # Atualiza o painel
        panel_msg_id = meta.get("panel_message_id")
        if panel_msg_id:
            try:
                panel_msg = await msg.channel.fetch_message(int(panel_msg_id))
                await panel_msg.edit(components=_build_panel(audio_att.filename))
            except Exception:
                pass

        # Confirma e limpa o chat
        try:
            await msg.reply(
                f"🎵 **Áudio detectado!** `{audio_att.filename}` foi configurado.",
                delete_after=8,
            )
        except Exception:
            pass
        try:
            await msg.delete(delay=1)
        except Exception:
            pass


def setup(bot: commands.Bot):
    bot.add_cog(Audio(bot))

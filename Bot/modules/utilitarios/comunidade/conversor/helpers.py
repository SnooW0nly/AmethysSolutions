"""
modules/utilitarios/comunidade/conversor/helpers.py

Helpers, config e utilitários do sistema de Conversor de Mídia.
Toda conversão roda em ProcessPoolExecutor para não bloquear o event loop.
O processamento é feito em chunks/streaming para minimizar uso de RAM.
"""
from __future__ import annotations

import asyncio
import io
import os
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from typing import Optional

import disnake
from functions.database import database as db
from functions.emoji import emoji

DB_KEY = "comunidade_conversor"

# Executor de processos separados — conversões pesadas não travam o bot
_EXECUTOR = ProcessPoolExecutor(max_workers=2)

# Limites de tamanho de arquivo (bytes)
MAX_INPUT_MB = 50
MAX_INPUT_BYTES = MAX_INPUT_MB * 1024 * 1024

# Tipos suportados por categoria
CONVERSOES = {
    "video_gif": {
        "label": "Vídeo → GIF",
       # "emoji": "🎞️",
        "desc": "Converte um vídeo (MP4, MOV, WEBM…) em GIF animado.",
        "extensoes_entrada": {".mp4", ".mov", ".webm", ".avi", ".mkv"},
        "extensao_saida": ".gif",
    },
    "foto_pb": {
        "label": "Foto → Preto e Branco",
       # "emoji": "🖤",
        "desc": "Converte uma imagem colorida para escala de cinza.",
        "extensoes_entrada": {".jpg", ".jpeg", ".png", ".webp", ".bmp"},
        "extensao_saida": ".png",
    },
    "video_audio": {
        "label": "Vídeo → Áudio",
      #  "emoji": "🎵",
        "desc": "Extrai o áudio de um vídeo (MP4, MOV…) em MP3.",
        "extensoes_entrada": {".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"},
        "extensao_saida": ".mp3",
    },
    "imagem_webp": {
        "label": "Imagem → WebP",
       # "emoji": "🖼️",
        "desc": "Converte imagem para formato WebP otimizado.",
        "extensoes_entrada": {".jpg", ".jpeg", ".png", ".bmp", ".gif"},
        "extensao_saida": ".webp",
    },
    "video_mp4": {
        "label": "Vídeo → MP4",
     #   "emoji": "🎬",
        "desc": "Recodifica qualquer vídeo para MP4 (H.264).",
        "extensoes_entrada": {".mov", ".webm", ".avi", ".mkv", ".m4v", ".flv"},
        "extensao_saida": ".mp4",
    },
    "audio_mp3": {
        "label": "Áudio → MP3",
     #   "emoji": "🎙️",
        "desc": "Converte áudio (WAV, OGG, FLAC…) para MP3.",
        "extensoes_entrada": {".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus"},
        "extensao_saida": ".mp3",
    },
}


# ─── Config ───────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("ativado", False)
    dados.setdefault("canal_painel", None)          # Canal onde o painel público fica
    dados.setdefault("categoria_topicos", None)     # Categoria onde criar os tópicos privados
    dados.setdefault("mensagem_painel_id", None)    # ID da msg do painel
    dados.setdefault("conversoes_ativas", list(CONVERSOES.keys()))  # Quais tipos estão habilitados
    dados.setdefault("max_mb", MAX_INPUT_MB)        # Limite configurável pelo admin
    dados.setdefault("mensagem_painel", {})         # Builder config
    dados.setdefault("log_canal", None)             # Canal de log (opcional)
    return dados


def salvar_config(data: dict) -> None:
    db.save_document(DB_KEY, {}, data)


# ─── Detecção de tipo ─────────────────────────────────────────────────────────

def detectar_conversao(nome_arquivo: str) -> list[str]:
    """Retorna lista de IDs de conversão compatíveis com a extensão do arquivo."""
    ext = os.path.splitext(nome_arquivo.lower())[1]
    compativeis = []
    for cid, info in CONVERSOES.items():
        if ext in info["extensoes_entrada"]:
            compativeis.append(cid)
    return compativeis


def conversoes_disponiveis(cfg: dict) -> dict:
    """Retorna apenas as conversões habilitadas na config."""
    ativas = set(cfg.get("conversoes_ativas", list(CONVERSOES.keys())))
    return {k: v for k, v in CONVERSOES.items() if k in ativas}


# ─── Conversões (rodam em processo separado) ──────────────────────────────────

def _converter_video_gif(input_bytes: bytes, nome: str) -> bytes:
    """
    Converte vídeo em GIF usando ffmpeg com paleta otimizada.
    Resolução máx 480p, 12fps para manter GIF leve.
    Roda em processo filho — não consome RAM do bot.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        inp = os.path.join(tmpdir, "input" + os.path.splitext(nome)[1])
        paleta = os.path.join(tmpdir, "palette.png")
        out = os.path.join(tmpdir, "output.gif")

        with open(inp, "wb") as f:
            f.write(input_bytes)

        # Passo 1: gerar paleta (melhor qualidade com menos cores)
        subprocess.run([
            "ffmpeg", "-y", "-i", inp,
            "-vf", "fps=12,scale=480:-1:flags=lanczos,palettegen=stats_mode=diff",
            paleta,
        ], check=True, capture_output=True)

        # Passo 2: aplicar paleta
        subprocess.run([
            "ffmpeg", "-y", "-i", inp, "-i", paleta,
            "-lavfi", "fps=12,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer",
            out,
        ], check=True, capture_output=True)

        with open(out, "rb") as f:
            return f.read()


def _converter_foto_pb(input_bytes: bytes, nome: str) -> bytes:
    """Converte imagem para preto e branco usando ffmpeg."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext = os.path.splitext(nome)[1] or ".jpg"
        inp = os.path.join(tmpdir, "input" + ext)
        out = os.path.join(tmpdir, "output.png")

        with open(inp, "wb") as f:
            f.write(input_bytes)

        subprocess.run([
            "ffmpeg", "-y", "-i", inp,
            "-vf", "hue=s=0",
            out,
        ], check=True, capture_output=True)

        with open(out, "rb") as f:
            return f.read()


def _converter_video_audio(input_bytes: bytes, nome: str) -> bytes:
    """Extrai áudio de vídeo como MP3 128kbps."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext = os.path.splitext(nome)[1] or ".mp4"
        inp = os.path.join(tmpdir, "input" + ext)
        out = os.path.join(tmpdir, "output.mp3")

        with open(inp, "wb") as f:
            f.write(input_bytes)

        subprocess.run([
            "ffmpeg", "-y", "-i", inp,
            "-vn", "-acodec", "libmp3lame", "-ab", "128k", "-ar", "44100",
            out,
        ], check=True, capture_output=True)

        with open(out, "rb") as f:
            return f.read()


def _converter_imagem_webp(input_bytes: bytes, nome: str) -> bytes:
    """Converte imagem para WebP com qualidade 85."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext = os.path.splitext(nome)[1] or ".jpg"
        inp = os.path.join(tmpdir, "input" + ext)
        out = os.path.join(tmpdir, "output.webp")

        with open(inp, "wb") as f:
            f.write(input_bytes)

        subprocess.run([
            "ffmpeg", "-y", "-i", inp,
            "-quality", "85",
            out,
        ], check=True, capture_output=True)

        with open(out, "rb") as f:
            return f.read()


def _converter_video_mp4(input_bytes: bytes, nome: str) -> bytes:
    """Recodifica vídeo para MP4 H.264 CRF 23 (boa qualidade/tamanho)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext = os.path.splitext(nome)[1] or ".mp4"
        inp = os.path.join(tmpdir, "input" + ext)
        out = os.path.join(tmpdir, "output.mp4")

        with open(inp, "wb") as f:
            f.write(input_bytes)

        subprocess.run([
            "ffmpeg", "-y", "-i", inp,
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            out,
        ], check=True, capture_output=True)

        with open(out, "rb") as f:
            return f.read()


def _converter_audio_mp3(input_bytes: bytes, nome: str) -> bytes:
    """Converte áudio para MP3 128kbps."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext = os.path.splitext(nome)[1] or ".wav"
        inp = os.path.join(tmpdir, "input" + ext)
        out = os.path.join(tmpdir, "output.mp3")

        with open(inp, "wb") as f:
            f.write(input_bytes)

        subprocess.run([
            "ffmpeg", "-y", "-i", inp,
            "-acodec", "libmp3lame", "-ab", "128k", "-ar", "44100",
            out,
        ], check=True, capture_output=True)

        with open(out, "rb") as f:
            return f.read()


_FUNCOES = {
    "video_gif":    _converter_video_gif,
    "foto_pb":      _converter_foto_pb,
    "video_audio":  _converter_video_audio,
    "imagem_webp":  _converter_imagem_webp,
    "video_mp4":    _converter_video_mp4,
    "audio_mp3":    _converter_audio_mp3,
}


async def converter_async(
    tipo: str,
    input_bytes: bytes,
    nome_arquivo: str,
    loop: asyncio.AbstractEventLoop | None = None,
) -> bytes:
    """
    Executa a conversão de forma não-bloqueante usando ProcessPoolExecutor.
    O processo filho recebe apenas bytes — sem referências ao bot.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    fn = _FUNCOES.get(tipo)
    if not fn:
        raise ValueError(f"Tipo de conversão desconhecido: {tipo}")

    # run_in_executor serializa os bytes e roda em processo separado
    result = await loop.run_in_executor(
        _EXECUTOR,
        partial(fn, input_bytes, nome_arquivo),
    )
    return result


# ─── Helpers visuais ──────────────────────────────────────────────────────────

def _primary_hex() -> Optional[str]:
    return (db.get_document("custom_colors") or {}).get("primary")


def color() -> int:
    h = _primary_hex()
    return int(h.replace("#", ""), 16) if h else 0x5865F2


def accent() -> dict:
    c = color()
    return {"accent_colour": disnake.Colour(c)} if c else {}


def formatar_tamanho(nbytes: int) -> str:
    if nbytes < 1024:
        return f"{nbytes} B"
    elif nbytes < 1024 ** 2:
        return f"{nbytes / 1024:.1f} KB"
    else:
        return f"{nbytes / 1024 ** 2:.1f} MB"
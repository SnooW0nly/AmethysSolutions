import json
import os
import base64

import disnake
from disnake.ext import commands
from functions.database import database as db

def load_config():
    return db.get_document("automations_cont_members")

def save_config(config):
    db.save_document("automations_cont_members", {}, config)

def sanitizar_prefixo(prefixo: str) -> str:
    """Remove caracteres inválidos do prefixo que não podem estar em nomes de canais/categorias."""
    # Caracteres inválidos em nomes de canais Discord: / \ < > : * ? " |
    caracteres_invalidos = ['/', '\\', '<', '>', ':', '*', '?', '"', '|']
    prefixo_sanitizado = prefixo
    for char in caracteres_invalidos:
        prefixo_sanitizado = prefixo_sanitizado.replace(char, '')
    # Remove espaços extras e limita o tamanho
    prefixo_sanitizado = ' '.join(prefixo_sanitizado.split())
    return prefixo_sanitizado[:50]  # Limita a 50 caracteres

def codificar_prefixo(prefixo: str) -> str:
    """Codifica o prefixo em base64 para uso seguro em custom_id."""
    return base64.urlsafe_b64encode(prefixo.encode('utf-8')).decode('utf-8')

def decodificar_prefixo(prefixo_codificado: str) -> str:
    """Decodifica o prefixo de base64."""
    try:
        return base64.urlsafe_b64decode(prefixo_codificado.encode('utf-8')).decode('utf-8')
    except Exception:
        return prefixo_codificado  # Retorna o original se falhar

def formatar_nome_canal(prefixo: str, contagem: int, estilo: int | None) -> str:
    estilo_seguro = int(estilo) if isinstance(estilo, int) else 0
    if estilo_seguro == 0:
        return f"{prefixo}: {contagem}"
    if estilo_seguro == 1:
        return f"{prefixo} {contagem}"
    if estilo_seguro == 2:
        return f"{contagem} {prefixo}"
    if estilo_seguro == 3:
        return f"{contagem}: {prefixo}"
    return f"{prefixo}: {contagem}"

def estilo_legenda(estilo: int | None) -> str:
    estilo_seguro = int(estilo) if isinstance(estilo, int) else 0
    mapa = {
        0: "Prefixo: Contagem",
        1: "Prefixo Contagem",
        2: "Contagem Prefixo",
        3: "Contagem: Prefixo",
    }
    return mapa.get(estilo_seguro, "Prefixo: Contagem")

async def atualizar_contadores_manual(bot: commands.Bot, guild: disnake.Guild, config: dict):
    for contador in config.get("contadores", []):
        try:
            if contador["guild_id"] != guild.id:
                continue

            canal = guild.get_channel(contador["canal_id"])
            if not canal or not isinstance(canal, disnake.VoiceChannel):
                continue

            cargo = guild.get_role(contador["cargo_id"])
            if not cargo:
                continue

            membros_com_cargo = len([member for member in guild.members if cargo in member.roles])
            
            novo_nome = formatar_nome_canal(
                contador.get('prefixo', 'Contador'),
                membros_com_cargo,
                int(config.get('estilo', 0))
            )
            if canal.name != novo_nome:
                await canal.edit(name=novo_nome, reason="Atualização manual do contador de membros")
                
        except Exception as e:
            print(f"Erro ao atualizar contador manual: {e}")

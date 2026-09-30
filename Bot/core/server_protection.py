"""
Sistema de proteção de servidor - Garante que o bot funcione apenas no servidor principal
"""
import disnake
from disnake.ext import commands
from typing import Any, Callable
from functools import wraps
import json

def get_main_server_id() -> int:
    """Obtém o ID do servidor principal do config.json"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            server_id = config.get("bot", {}).get("server")
            if server_id:
                return int(server_id)
    except Exception as e:
        print(f"Erro ao ler config.json: {e}")
    return None

def apply_server_protection(bot: commands.Bot):
    """
    Aplica proteção de servidor a todos os comandos e eventos do bot.
    Comandos marcados com _exclude_from_check=True não serão afetados.
    """
    main_server_id = get_main_server_id()
    
    if not main_server_id:
        print("⚠️ AVISO: ID do servidor principal não encontrado no config.json")
        return
    
    # Hook para interceptar comandos slash
    original_process_application_commands = bot.process_application_commands
    
    async def protected_process_application_commands(inter: disnake.ApplicationCommandInteraction):
        # Verifica se o comando tem a flag de exclusão
        command = None
        if inter.data.name:
            for cmd in bot.slash_commands:
                if cmd.name == inter.data.name:
                    command = cmd.callback
                    break
        
        # Se o comando não tem a flag de exclusão e não está no servidor principal
        if command and not getattr(command, '_exclude_from_check', False):
            if inter.guild_id != main_server_id:
                await inter.response.send_message(
                    "Acesso Negado: Este comando só pode ser usado no servidor principal.",
                    ephemeral=True
                )
                return
        
        # Processa o comando normalmente
        await original_process_application_commands(inter)
    
    bot.process_application_commands = protected_process_application_commands
    
    # Listener para interceptar interações (botões, select menus, modals)
    @bot.listen("on_button_click")
    @bot.listen("on_dropdown")
    @bot.listen("on_modal_submit")
    async def check_interaction(inter: disnake.MessageInteraction):
        if inter.guild_id and inter.guild_id != main_server_id:
            # Verifica se não é relacionado ao backup
            custom_id = inter.data.custom_id if hasattr(inter.data, 'custom_id') else None
            if custom_id and not custom_id.startswith("backup"):
                if not inter.response.is_done():
                    await inter.response.send_message(
                        "Acesso Negado: Esta ação só pode ser realizada no servidor principal.",
                        ephemeral=True
                    )
                # If interaction is already done, another handler processed it - just return

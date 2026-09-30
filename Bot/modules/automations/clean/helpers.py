import disnake
import datetime
from functions.database import database as db
from functions.emoji import emoji

def carregar_config() -> dict:
    """Carrega a configuração do banco de dados, definindo valores padrão."""
    dados = db.get_document("automations_clean") or {}
    if not isinstance(dados, dict):
        dados = {}
    
    dados.setdefault("ativado", False)
    dados.setdefault("canais", {})
    dados.setdefault("logs_ativados", False)
    
    return dados

def salvar_config(data: dict) -> None:
    """Salva a configuração no banco de dados."""
    atual = carregar_config()
    atual.update(data or {})
    db.save_document("automations_clean", {}, atual)

async def obter_canal_logs(bot: disnake.ext.commands.Bot) -> disnake.TextChannel | None:
    """Obtém o canal de logs do sistema a partir da configuração de canais."""
    try:
        canais_config = db.get_document("canais") or {}
        canal_logs_id = canais_config.get("canal_de_logs_do_sistema")
        
        if canal_logs_id:
            canal = bot.get_channel(int(canal_logs_id))
            if isinstance(canal, disnake.TextChannel):
                return canal
    except (ValueError, AttributeError):
        pass
    return None

async def enviar_log_sucesso(bot: disnake.ext.commands.Bot, canal: disnake.TextChannel, total_deleted: int, intervalo_minutos: int, proxima_limpeza: "datetime.datetime"):
    """Envia log de sucesso para o canal de logs do sistema."""
    try:
        config = carregar_config()
        if not config.get("logs_ativados", False):
            return

        canal_logs = await obter_canal_logs(bot)
        if not canal_logs:
            return

        if intervalo_minutos >= 60 and intervalo_minutos % 60 == 0:
            intervalo_text = f"{intervalo_minutos // 60}h"
        else:
            intervalo_text = f"{intervalo_minutos}min"

        mode = db.get_document("custom_mode").get("mode")
        description = (
            f"**Canal:** {canal.mention}\n"
            f"**Mensagens deletadas:** `{total_deleted}`\n"
            f"**Intervalo configurado:** `{intervalo_text}`\n"
            f"**Próxima limpeza:** <t:{int(proxima_limpeza.timestamp())}:f> (<t:{int(proxima_limpeza.timestamp())}:R>)"
        )

        if mode == "embed":
            primary_color_hex = db.get_document("custom_colors").get("primary")
            embed = disnake.Embed(
                title=f"Limpeza Automática de Canais",
                description=description
            )
            if primary_color_hex:
                embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            components = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Desativar Logs", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id="Limpeza_DesativarLogsViaLog")
                )
            ]
            await canal_logs.send(embed=embed, components=components)
        else:
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            await canal_logs.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Limpeza Automática de Canais"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(description),
                        **container_kwargs,
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Desativar Logs", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id="Limpeza_DesativarLogsViaLog")
                    )
                ]
            )
    except Exception:
        pass

async def enviar_log_erro(bot: disnake.ext.commands.Bot, mensagem: str):
    """Envia log de erro para o canal de logs do sistema."""
    try:
        config = carregar_config()
        if not config.get("logs_ativados", False):
            return

        canal_logs = await obter_canal_logs(bot)
        if not canal_logs:
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            danger_color_hex = db.get_document("custom_colors").get("danger", "#dc3545")
            embed = disnake.Embed(
                title=f"{emoji.wrong} Erro na Limpeza Automática",
                description=mensagem,
                color=disnake.Colour(int(danger_color_hex.replace("#", ""), 16))
            )
            await canal_logs.send(embed=embed)
        else:
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            await canal_logs.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.wrong} Erro na Limpeza Automática\n\n{mensagem}"),
                        **container_kwargs,
                    )
                ]
            )
    except Exception:
        pass

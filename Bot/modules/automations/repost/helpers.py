import disnake
import datetime
from functions.database import database as db
from functions.emoji import emoji

def carregar_config() -> dict:
    """Carrega a configuração do banco de dados, definindo valores padrão."""
    dados = db.get_document("automations_repost") or {}
    if not isinstance(dados, dict):
        dados = {}
    
    dados.setdefault("ativado", False)
    dados.setdefault("intervalo_horas", 24)
    dados.setdefault("proxima_repostagem", None)
    dados.setdefault("logs_ativados", False)
    
    return dados

def salvar_config(data: dict) -> None:
    """Salva a configuração no banco de dados."""
    atual = carregar_config()
    atual.update(data or {})
    db.save_document("automations_repost", {}, atual)

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

async def enviar_log_sucesso(bot: disnake.ext.commands.Bot, total_produtos: int, total_repostados: int, total_removidos: int, intervalo_horas: int, proxima_repostagem: "datetime.datetime"):
    """Envia log de sucesso para o canal de logs do sistema."""
    try:
        config = carregar_config()
        if not config.get("logs_ativados", False):
            return

        canal_logs = await obter_canal_logs(bot)
        if not canal_logs:
            return

        mode = db.get_document("custom_mode").get("mode")
        description = (
            f"**Produtos processados:** `{total_produtos}`\n"
            f"**Mensagens repostadas:** `{total_repostados}`\n"
            f"**Mensagens removidas:** `{total_removidos}`\n"
            f"**Intervalo configurado:** `{intervalo_horas}h`\n"
            f"**Próxima repostagem:** <t:{int(proxima_repostagem.timestamp())}:f> (<t:{int(proxima_repostagem.timestamp())}:R>)"
        )

        if mode == "embed":
            primary_color_hex = db.get_document("custom_colors").get("primary")
            embed = disnake.Embed(
                title=f"Repostagem Automática de Produtos",
                description=description
            )
            if primary_color_hex:
                embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            components = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Desativar Logs", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id="Repost_DesativarLogsViaLog")
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
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Repostagem Automática de Produtos"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(description),
                        **container_kwargs,
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Desativar Logs", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id="Repost_DesativarLogsViaLog")
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
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
                title=f"{emoji.wrong} Erro na Repostagem Automática",
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
                        disnake.ui.TextDisplay(f"# {emoji.wrong} Erro na Repostagem Automática\n\n{mensagem}"),
                        **container_kwargs,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
    except Exception:
        pass

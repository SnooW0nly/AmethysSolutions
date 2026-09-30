import disnake
import time
from functions.database import database
from functions.emoji import emoji

async def log_restart(bot: disnake.Client):
    try:
        info = database.obter("config.json")
        db_canais = database.get_document("canais")
        db_mode = database.get_document("custom_mode")
        db_color = database.get_document("custom_colors")

        canal_id_str = db_canais.get("canal_de_logs_do_sistema")
        if not canal_id_str:
            return
        
        canal_id = int(canal_id_str)
        canal_obj = bot.get_channel(canal_id)

        if not canal_obj:
            print(f"Canal de logs do sistema com ID {canal_id} não foi encontrado.")
            return

        mode = db_mode.get("mode", "components")
        primary_color_hex = db_color.get("primary")

        # ── Verifica se foi reiniciado por update em massa do painel ─────────
        # O massUpdate.js grava {"pending": true} em "restart_flag" antes do commit.
        # Reinicios da IA (aiMonitorService) NÃO gravam essa flag — são silenciosos.
        # Após ler, sempre limpa a flag para não disparar em próximos reinicios.
        restart_flag = database.get_document("restart_flag")
        is_update = restart_flag.get("pending", False)

        if is_update:
            restart_flag["pending"] = False
            database.save_document("restart_flag", restart_flag)

        description_text_embed = (
            f"{emoji.reload} O **Amethys Bot** foi reiniciado.\n"
            f"{emoji.robot} Versão atual: `{info['version']}`\n"
            f"{emoji.calendar} **Data:** <t:{int(time.time())}:f> (<t:{int(time.time())}:R>)"
        )
        description_text_container = (
            f"{emoji.reload} O **Amethys Bot** foi reiniciado"
            + (" @everyone" if is_update else "") + "\n"
            + f"{emoji.robot} Versão atual: `{info['version']}`\n"
            + f"{emoji.calendar} **Data:** <t:{int(time.time())}:f> (<t:{int(time.time())}:R>)"
        )

        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Ir para o Dashboard",
                style=disnake.ButtonStyle.link,
                url=f"https://discord.gg/amethysapp"
            ),
            disnake.ui.Button(
                label="Suporte",
                style=disnake.ButtonStyle.link,
                url=f"https://discord.gg/amethysapp"
            )
        )

        if mode == "embed":
            # No modo embed o @everyone vai no content (fora do embed) para funcionar o ping
            content_text = "@everyone" if is_update else None
            embed_kwargs = {}
            if primary_color_hex:
                embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
            embed = disnake.Embed(
                title=f"Informações do Sistema > Reinicialização",
                description=description_text_embed,
                **embed_kwargs,
            )
            await canal_obj.send(content=content_text, embed=embed, components=[buttons])

        else:
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.amethys}\n-# Informações do sistema > **Reinicialização**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(description_text_container),
                disnake.ui.Separator(),
                buttons,
                **container_kwargs
            )
            await canal_obj.send(components=[container], flags=disnake.MessageFlags(is_components_v2=True))
    
    except Exception as e:
        import traceback
        print(f"Ocorreu um erro em log_restart: {e}")
        traceback.print_exc()
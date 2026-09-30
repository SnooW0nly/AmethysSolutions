import disnake
from functions.database import database as db
from events._common import criar_container_log, criar_embed_log

async def log_giveaway_event(bot: disnake.Client, giveaway_id: str, title: str, lines: list[str]):
    config = db.obter("database/giveaways/giveaways_data.json")
    giveaway_data = config.get(giveaway_id, {})
    
    log_channel_id = giveaway_data.get("log_channel_id")
    if not log_channel_id:
        return

    guild = None
    try:
        channel = bot.get_channel(log_channel_id) or await bot.fetch_channel(log_channel_id)
        guild = channel.guild
    except (disnake.NotFound, disnake.Forbidden):
        return
        
    if not guild or not channel:
        return

    mode = db.get_document("custom_mode").get("mode")

    try:
        if mode == "components":
            container = criar_container_log(title, lines)
            await channel.send(
                components=[container],
                flags=disnake.MessageFlags(is_components_v2=True),
                allowed_mentions=disnake.AllowedMentions.none()
            )
        else: # mode == "embed"
            embed = criar_embed_log(guild, title, lines)
            await channel.send(
                embed=embed,
                allowed_mentions=disnake.AllowedMentions.none()
            )
    except Exception as e:
        print(f"Failed to send giveaway log for giveaway {giveaway_id}: {e}")

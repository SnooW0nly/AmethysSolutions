import disnake
from functions.emoji import emoji
from ..config_giveaways import get_giveaways
from functions.database import database as db

def ChannelSelectView_components(giveaway_id: str, task_id: str) -> list[disnake.ui.Container]:
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    task = next((t for t in giveaway_data.get("tasks", []) if t["id"] == task_id), None)
    task_name = task.get("name", task_id) if task else task_id

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > {giveaway_name} > Tarefa: {task_name} > **Definir Canal**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Selecione um canal...",
                custom_id=f"GiveawayTask_SelectChannel_{giveaway_id}_{task_id}",
                channel_types=[disnake.ChannelType.text],
                min_values=1,
                max_values=1,
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToEditor_{giveaway_id}_{task_id}")
    )
    
    return [container, buttons]

def ChannelSelectView_embed(inter: disnake.Interaction, giveaway_id: str, task_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    task = next((t for t in giveaway_data.get("tasks", []) if t["id"] == task_id), None)
    task_name = task.get("name", task_id) if task else task_id

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Definir Canal: {task_name}",
        description="Selecione o canal onde o sorteio será anunciado.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Selecione um canal...",
                custom_id=f"GiveawayTask_SelectChannel_{giveaway_id}_{task_id}",
                channel_types=[disnake.ChannelType.text],
                min_values=1,
                max_values=1,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToEditor_{giveaway_id}_{task_id}")
        )
    ]

    return embed, components

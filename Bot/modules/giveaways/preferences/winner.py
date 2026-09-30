import disnake
from functions.database import database as db
from functions.emoji import emoji
from ..config_giveaways import get_giveaways

# --- Main Winner Panel ---

def WinnerView_components(inter: disnake.Interaction, giveaway_id: str) -> list[disnake.ui.Container]:
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    winner_users = giveaway_data.get("winner_users", [])
    winner_roles = giveaway_data.get("winner_roles", [])

    user_mentions = [f"<@{uid}>" for uid in winner_users]
    role_mentions = [f"<@&{rid}>" for rid in winner_roles]
    
    status_text = (
        f"{emoji.member} **Usuários Ganhadores:** {', '.join(user_mentions) if user_mentions else '`Nenhum`'}\n"
        f"{emoji.role} **Cargos Ganhadores:** {', '.join(role_mentions) if role_mentions else '`Nenhum`'}"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > **Definir Ganhador**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.UserSelect(
                custom_id=f"GiveawayWinner_SelectUser_{giveaway_id}",
                placeholder="Adicionar/Editar usuários ganhadores...",
                min_values=0, max_values=25,
                default_values=[disnake.Object(id=uid) for uid in winner_users]
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                custom_id=f"GiveawayWinner_SelectRole_{giveaway_id}",
                placeholder="Adicionar/Editar cargos ganhadores...",
                min_values=0, max_values=25,
                default_values=[disnake.Object(id=rid) for rid in winner_roles]
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayPref_BackToPreferences_{giveaway_id}")
    )

    return [container, buttons]

def WinnerView_embed(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    winner_users = giveaway_data.get("winner_users", [])
    winner_roles = giveaway_data.get("winner_roles", [])

    user_mentions = [f"<@{uid}>" for uid in winner_users]
    role_mentions = [f"<@&{rid}>" for rid in winner_roles]

    description = (
        f"{emoji.member} **Usuários Ganhadores:** {', '.join(user_mentions) if user_mentions else '`Nenhum`'}\n"
        f"{emoji.role} **Cargos Ganhadores:** {', '.join(role_mentions) if role_mentions else '`Nenhum`'}"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(title=f"Definir Ganhador: {giveaway_name}", description=description, **embed_kwargs)
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.UserSelect(
                custom_id=f"GiveawayWinner_SelectUser_{giveaway_id}",
                placeholder="Adicionar/Editar usuários ganhadores...",
                min_values=0, max_values=25,
                default_values=[disnake.Object(id=uid) for uid in winner_users]
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                custom_id=f"GiveawayWinner_SelectRole_{giveaway_id}",
                placeholder="Adicionar/Editar cargos ganhadores...",
                min_values=0, max_values=25,
                default_values=[disnake.Object(id=rid) for rid in winner_roles]
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayPref_BackToPreferences_{giveaway_id}")
        )
    ]

    return embed, components

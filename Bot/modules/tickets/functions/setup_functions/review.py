import disnake

async def review(inter: disnake.MessageInteraction):
    await inter.response.send_message("Lógica para avaliar aqui.", ephemeral=True)

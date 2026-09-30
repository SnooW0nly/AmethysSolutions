import disnake

async def notes(inter: disnake.MessageInteraction):
    await inter.response.send_message("Lógica para anotações aqui.", ephemeral=True)

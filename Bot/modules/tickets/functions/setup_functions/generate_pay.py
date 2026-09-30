import disnake

async def generate_pay(inter: disnake.MessageInteraction):
    await inter.response.send_message("Lógica para pagamento aqui.", ephemeral=True)

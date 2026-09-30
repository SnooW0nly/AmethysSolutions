from disnake.ext import commands
from functions.plan import should_load_module

def setup(bot: commands.Bot):
    # Carrega tasks baseado no plano configurado
    if should_load_module("automations"):
        bot.load_extension("tasks.automations.cog")
    if should_load_module("backup"):
        bot.load_extension("tasks.backup")
    if should_load_module("protection"):
        bot.load_extension("tasks.protection")
    if should_load_module("bot"):
        bot.load_extension("tasks.bot.cog")
        bot.load_extension("tasks.bot.autorole")
    if should_load_module("giveaways"):
        bot.load_extension("tasks.giveaways.cog")
    if should_load_module("loja"):
        bot.load_extension("tasks.loja.cog")
    if should_load_module("extensions"):
        bot.load_extension("tasks.extensions.cog")

    # Task de backup/sync da database (sempre ativa)
    bot.load_extension("tasks.database.cog")

    # Nubank IMAP Monitor (sempre ativo se configurado)
    #bot.load_extension("tasks.payments.nubank_monitor")
    
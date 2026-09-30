from disnake.ext import commands


def setup(bot: commands.Bot):
    bot.load_extension("tasks.database.tsk_database_backup")

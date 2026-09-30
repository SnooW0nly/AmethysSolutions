def setup(bot):
    from .cog import BackupCog
    bot.add_cog(BackupCog(bot))

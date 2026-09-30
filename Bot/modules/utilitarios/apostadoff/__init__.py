def setup(bot):
    from .cog import ApostadoFFCog
    bot.add_cog(ApostadoFFCog(bot))
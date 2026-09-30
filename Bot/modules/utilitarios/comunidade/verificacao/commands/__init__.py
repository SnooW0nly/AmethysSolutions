from .codigos import CodigosCommand

def setup(bot):
    bot.add_cog(CodigosCommand(bot))
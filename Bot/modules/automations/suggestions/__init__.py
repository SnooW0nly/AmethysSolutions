from .cog import SuggestionsCog

def setup(bot):
    bot.add_cog(SuggestionsCog(bot))

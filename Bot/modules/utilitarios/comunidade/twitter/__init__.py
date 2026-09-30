from .cog import TwitterCog

def setup(bot):
    bot.add_cog(TwitterCog(bot))
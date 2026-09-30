from .cog import InstagramCog

def setup(bot):
    bot.add_cog(InstagramCog(bot))
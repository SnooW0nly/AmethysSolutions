def setup(bot):
    from .cog import ToolsCog
    bot.add_cog(ToolsCog(bot))
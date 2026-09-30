def setup(bot):
    bot.load_extension("modules.utilitarios.economia.cog")
    bot.load_extension("modules.utilitarios.comunidade.cog")
    bot.load_extension("modules.utilitarios.comunidade.instagram.cog")
    bot.load_extension("modules.utilitarios.comunidade.tellonym.cog")
    bot.load_extension("modules.utilitarios.comunidade.tagbio.cog")
    bot.load_extension("modules.utilitarios.comunidade.registro.cog")
    bot.load_extension("modules.utilitarios.comunidade.verificacao.cog")
    bot.load_extension("modules.utilitarios.comunidade.familia.cog")
    bot.load_extension("modules.utilitarios.comunidade.twitter.cog")
    bot.load_extension("modules.utilitarios.comunidade.formulario.cog")
    bot.load_extension("modules.utilitarios.comunidade.reputacao.cog")
    bot.load_extension("modules.utilitarios.comunidade.conversor.cog")

__all__ = ["setup"]
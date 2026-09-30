from . import cargos
from . import ban
from . import castigar
from . import botinfo
from . import limpar
from . import lock
from . import nuke
from . import unlock
from . import expulsar
from . import desbanir
from . import convites
from . import falar
from . import conectar
from . import enviar_dm
from . import webhook
from . import cargo_temporario

class mod:
    @staticmethod
    def setup(bot):
        cargos.setup(bot)
        bot.add_cog(ban.Banir(bot))
        bot.add_cog(castigar.Castigar(bot))
        bot.add_cog(botinfo.BotInfo(bot))
        bot.add_cog(limpar.Limpar(bot))
        bot.add_cog(lock.Lock(bot))
        bot.add_cog(nuke.Nuke(bot))
        bot.add_cog(unlock.Unlock(bot))
        bot.add_cog(expulsar.Expulsar(bot))
        bot.add_cog(desbanir.Desbanir(bot))
        bot.add_cog(convites.Convites(bot))
        bot.add_cog(falar.Falar(bot))
        bot.add_cog(conectar.ConectarCommand(bot))
        enviar_dm.setup(bot)
        webhook.setup(bot)
        cargo_temporario.setup(bot)
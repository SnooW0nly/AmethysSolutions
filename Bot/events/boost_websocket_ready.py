import disnake
from disnake.ext import commands
import asyncio

class BoostWebSocketReady(commands.Cog):
    """
    Cog legado para inicialização da websocket de extensões.
    Agora redireciona para o inicializador centralizado em connections.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.websocket_started = False

    @commands.Cog.listener()
    async def on_ready(self):
        """Inicializa o WebSocket de Extensões quando o bot estiver pronto"""
        if self.websocket_started:
            return
        
        self.websocket_started = True
        
        # Aguardar um pouco para garantir que o bot está completamente pronto
        await asyncio.sleep(3)
        
        try:
            from connections import initialize_extensions
            
            # Inicializa o manager unificado de extensões (Boost/Joiner)
            print("[Boost WebSocket] 🔄 Iniciando conexão unificada de extensões...")
            ws = await initialize_extensions(self.bot)
            
            if ws.is_connected():
                print("[Boost WebSocket] ✅ WebSocket de Extensões conectado")
            else:
                print("[Boost WebSocket] ⚠️ WebSocket de Extensões em processo de conexão...")
            
        except Exception as e:
            print(f"[Boost WebSocket] ❌ Erro ao inicializar WebSocket de Extensões: {e}")

def setup(bot: commands.Bot):
    bot.add_cog(BoostWebSocketReady(bot))

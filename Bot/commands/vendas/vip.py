import disnake
import time
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils

class VIPCommandCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="vip", 
        description="Veja suas assinaturas VIP ativas e benefícios.",
        guild_ids=[utils.obter_server_principal()]
    )
    async def vip(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        
        user_id_str = str(inter.author.id)
        subs_doc = db.get_document("loja_subscriptions") or {}
        user_subs = subs_doc.get(user_id_str, {})
        
        now = int(time.time())
        active_subs = []
        for sub_key, sub_data in user_subs.items():
            expires_at = sub_data.get("expires_at", 0)
            if expires_at == 0 or expires_at > now:
                active_subs.append(sub_data)

        if not active_subs:
            await inter.followup.send(f"{emoji.alert} Você não possui nenhuma assinatura VIP ativa.", ephemeral=True)
            return

        # Verificar modo de exibição
        mode = db.get_document("custom_mode").get("mode", "components")
        
        if mode == "components":
            # Modo Components v2 (Container)
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.king} Suas Assinaturas VIP\n-# Veja seus benefícios ativos"),
                    disnake.ui.Separator(),
                    **container_kwargs
                )
            ]
            
            for sub in active_subs:
                expires_at = sub.get("expires_at", 0)
                expiry_text = f"<t:{expires_at}:F> (<t:{expires_at}:R>)" if expires_at > 0 else "Permanente"
                
                integracao = sub.get("integracao_vip") or {}
                beneficios = []
                if integracao.get("familia"):
                    beneficios.append(f"{emoji.group} Sistema de Família")
                if integracao.get("tempcall"):
                    beneficios.append(f"{emoji.voice} Sistema de Temp Call")
                
                beneficios_text = "\n".join([f"- {b}" for b in beneficios]) if beneficios else "- Nenhum benefício extra configurado"
                
                sub_text = (
                    f"**Produto:** {sub.get('product_name')}\n"
                    f"**Plano:** {sub.get('campo_name')}\n"
                    f"**Validade:** {expiry_text}\n\n"
                    f"**Benefícios:**\n{beneficios_text}"
                )
                
                components.append(
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(sub_text),
                        **container_kwargs
                    )
                )
            
            components.append(
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"-# Solicitado por {inter.author.display_name}"),
                    **container_kwargs
                )
            )
            
            await inter.followup.send(components=components, ephemeral=True)
            
        else:
            # Modo Embed
            embed = disnake.Embed(
                title=f"{emoji.king} Suas Assinaturas VIP",
                color=disnake.Color.gold(),
                timestamp=disnake.utils.utcnow()
            )
            
            for sub in active_subs:
                expires_at = sub.get("expires_at", 0)
                expiry_text = f"<t:{expires_at}:F> (<t:{expires_at}:R>)" if expires_at > 0 else "Permanente"
                
                integracao = sub.get("integracao_vip") or {}
                beneficios = []
                if integracao.get("familia"):
                    beneficios.append(f"{emoji.group} Sistema de Família")
                if integracao.get("tempcall"):
                    beneficios.append(f"{emoji.voice} Sistema de Temp Call")
                
                beneficios_text = "\n".join([f"- {b}" for b in beneficios]) if beneficios else "- Nenhum benefício extra configurado"
                
                embed.add_field(
                    name=f"{sub.get('product_name')} - {sub.get('campo_name')}",
                    value=f"**Validade:** {expiry_text}\n**Benefícios:**\n{beneficios_text}",
                    inline=False
                )

            embed.set_footer(text=f"Solicitado por {inter.author.display_name}", icon_url=inter.author.display_avatar.url)
            await inter.followup.send(embed=embed, ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(VIPCommandCog(bot))
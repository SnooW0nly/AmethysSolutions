"""
Sistema de botão de dúvida para produtos
"""
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from typing import Optional


class DoubtButtonModal(disnake.ui.Modal):
    def __init__(self):
        data = db.get_document("loja_doubt_button")
        
        components = [
            disnake.ui.TextInput(
                label="Texto do Botão",
                custom_id="button_label",
                value=data.get("button_label", "Dúvidas"),
                max_length=30,
                required=True
            ),
            disnake.ui.TextInput(
                label="Emoji do Botão (opcional)",
                custom_id="button_emoji",
                value=data.get("button_emoji", "❓"),
                max_length=10,
                required=False
            ),
            disnake.ui.TextInput(
                label="ID do Canal de Dúvidas",
                custom_id="channel_id",
                value=str(data.get("channel_id", "")) if data.get("channel_id") else "",
                placeholder="ID do canal onde será criado o ticket/thread",
                max_length=30,
                required=True
            ),
            disnake.ui.TextInput(
                label="Mensagem Inicial",
                custom_id="message",
                value=data.get("message", ""),
                placeholder="Mensagem enviada quando alguém clica no botão",
                style=disnake.TextInputStyle.paragraph,
                max_length=1000,
                required=True
            )
        ]
        
        super().__init__(title="Configurar Botão de Dúvidas", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer()
        
        # Validar canal
        try:
            channel_id = int(inter.text_values["channel_id"])
            channel = inter.guild.get_channel(channel_id)
            if not channel:
                await inter.followup.send(
                    f"{emoji.wrong} Canal não encontrado!",
                    ephemeral=True
                )
                return
        except ValueError:
            await inter.followup.send(
                f"{emoji.wrong} ID de canal inválido!",
                ephemeral=True
            )
            return
        
        # Salvar configurações
        data = db.get_document("loja_doubt_button")
        data["button_label"] = inter.text_values["button_label"]
        data["button_emoji"] = inter.text_values.get("button_emoji", "")
        data["channel_id"] = channel_id
        data["message"] = inter.text_values["message"]
        data["enabled"] = True
        
        db.save_document("loja_doubt_button", data)
        
        await inter.followup.send(
            f"{emoji.correct} Botão de dúvidas configurado com sucesso!",
            ephemeral=True
        )


class DoubtButtonSystem:
    """Sistema de botão de dúvidas"""
    
    @staticmethod
    def get_doubt_button() -> Optional[disnake.ui.Button]:
        """Retorna o botão de dúvidas se estiver habilitado"""
        data = db.get_document("loja_doubt_button")
        
        if not data.get("enabled"):
            return None
        
        if not data.get("channel_id"):
            return None
        
        button = disnake.ui.Button(
            label=data.get("button_label", "Dúvidas"),
            emoji=data.get("button_emoji") if data.get("button_emoji") else None,
            style=disnake.ButtonStyle.secondary,
            custom_id="product_doubt_button"
        )
        
        return button
    
    @staticmethod
    async def handle_doubt_button(inter: disnake.MessageInteraction):
        """Processa clique no botão de dúvidas"""
        await inter.response.defer(ephemeral=True)
        
        data = db.get_document("loja_doubt_button")
        
        if not data.get("enabled"):
            await inter.followup.send(
                f"{emoji.wrong} Sistema de dúvidas não está configurado!",
                ephemeral=True
            )
            return
        
        channel_id = data.get("channel_id")
        if not channel_id:
            await inter.followup.send(
                f"{emoji.wrong} Canal de dúvidas não configurado!",
                ephemeral=True
            )
            return
        
        channel = inter.guild.get_channel(int(channel_id))
        if not channel:
            await inter.followup.send(
                f"{emoji.wrong} Canal de dúvidas não encontrado!",
                ephemeral=True
            )
            return
        
        # Obter informações do produto da mensagem
        product_name = "Produto"
        if inter.message.embeds:
            embed = inter.message.embeds[0]
            if embed.title:
                product_name = embed.title
        
        # Criar thread para dúvida
        try:
            thread = await channel.create_thread(
                name=f"Dúvida - {inter.author.name} - {product_name[:50]}",
                type=disnake.ChannelType.public_thread,
                auto_archive_duration=1440  # 24 horas
            )
            
            # Enviar mensagem inicial
            message = data.get("message", "").format(
                user=inter.author.mention,
                product=product_name
            )
            
            embed = disnake.Embed(
                title="❓ Nova Dúvida",
                description=message,
                color=disnake.Color.blue()
            )
            embed.add_field(
                name="Produto",
                value=product_name,
                inline=True
            )
            embed.add_field(
                name="Cliente",
                value=inter.author.mention,
                inline=True
            )
            embed.set_footer(text="Digite sua dúvida abaixo")
            
            await thread.send(
                content=inter.author.mention,
                embed=embed
            )
            
            await inter.followup.send(
                f"{emoji.correct} Thread de dúvida criada! {thread.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao criar thread: {e}",
                ephemeral=True
            )
    
    @staticmethod
    def panel_doubt_button(inter: disnake.Interaction) -> dict:
        """Painel de configuração do botão de dúvidas"""
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            return DoubtButtonSystem._panel_components(inter)
        return DoubtButtonSystem._panel_embed(inter)
    
    @staticmethod
    def _panel_components(inter: disnake.Interaction) -> dict:
        data = db.get_document("loja_doubt_button")
        
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        # Status
        if data.get("enabled"):
            status = f"{emoji.on} Ativado"
            channel_id = data.get("channel_id")
            if channel_id:
                channel = inter.guild.get_channel(int(channel_id))
                channel_text = channel.mention if channel else "Canal não encontrado"
            else:
                channel_text = "Não configurado"
        else:
            status = f"{emoji.off} Desativado"
            channel_text = "Não configurado"
        
        config_text = (
            f"**Status:** {status}\n"
            f"**Canal:** {channel_text}\n"
            f"**Botão:** {data.get('button_emoji', '')} {data.get('button_label', 'Dúvidas')}\n"
            f"**Mensagem:** {data.get('message', 'Não configurada')[:100]}..."
        )
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Loja > Personalizar > **Botão de Dúvidas**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure um botão de dúvidas que aparecerá em todos os produtos.\n"
                    "Quando clicado, criará uma thread para atendimento."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(config_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Configurar",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.config,
                        custom_id="Loja_DoubtButton_Config"
                    ),
                    disnake.ui.Button(
                        label="Ativar" if not data.get("enabled") else "Desativar",
                        style=disnake.ButtonStyle.green if not data.get("enabled") else disnake.ButtonStyle.red,
                        emoji=emoji.on if not data.get("enabled") else emoji.off,
                        custom_id="Loja_DoubtButton_Toggle"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Personalizar"
                )
            )
        ]}
    
    @staticmethod
    def _panel_embed(inter: disnake.Interaction):
        data = db.get_document("loja_doubt_button")
        
        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Botão de Dúvidas",
            description="Configure o botão de dúvidas dos produtos",
            color=disnake.Color.from_rgb(0, 202, 164)
        )
        
        if data.get("enabled"):
            embed.add_field(
                name="Status",
                value=f"{emoji.on} Ativado",
                inline=True
            )
            
            channel_id = data.get("channel_id")
            if channel_id:
                channel = inter.guild.get_channel(int(channel_id))
                embed.add_field(
                    name="Canal",
                    value=channel.mention if channel else "Não encontrado",
                    inline=True
                )
        else:
            embed.add_field(
                name="Status",
                value=f"{emoji.off} Desativado",
                inline=False
            )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.config,
                    custom_id="Loja_DoubtButton_Config"
                ),
                disnake.ui.Button(
                    label="Ativar" if not data.get("enabled") else "Desativar",
                    style=disnake.ButtonStyle.green if not data.get("enabled") else disnake.ButtonStyle.red,
                    emoji=emoji.on if not data.get("enabled") else emoji.off,
                    custom_id="Loja_DoubtButton_Toggle"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Personalizar"
                )
            )
        ]
        
        return embed, components

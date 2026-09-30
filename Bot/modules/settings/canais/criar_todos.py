import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .listar import CANAIS_OPCOES
from .cog import ConfigurarCanais

class MensagensCanais:
    @staticmethod
    def canal_criado_components(ch: disnake.TextChannel, auto: bool) -> disnake.ui.Container:
        return disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Criar Todos os Canais Automáticamente > Canal Criado" if auto else f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Criar Canal > Canal Criado"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Informações do canal:**\nID: `{ch.id}`\nNome: `{ch.name}`\nMenção: {ch.mention}"),
        )

    @staticmethod
    def canais_criados_components(criados: list[disnake.TextChannel]) -> list[disnake.ui.Container]:
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
**Informações dos canais criados:**
`{len(criados)}` canais criados com sucesso.
                """),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"{", ".join(f"{c.mention} (`{c.id}`)" for c in criados)}")
            )
        ]

    @staticmethod
    def canal_criado_embed(ch: disnake.TextChannel, auto: bool):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Canal Criado",
            description=f"**Informações do canal:**\nID: `{ch.id}`\nNome: `{ch.name}`\nMenção: {ch.mention}",
            # timestamp=disnake.utils.utcnow()
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color
        return embed, []

    @staticmethod
    def canais_criados_embed(criados: list[disnake.TextChannel]):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Canais Criados",
            description=f"`{len(criados)}` canais criados com sucesso.",
            # timestamp=disnake.utils.utcnow()
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color
        embed.add_field(
            name="Canais:",
            value=f"{", ".join(f"{c.mention} (`{c.id}`)" for c in criados)}"
        )
        return embed, []

class CriarTodosCanais(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def criar_todos_canais(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Configuracoes_CriarTodosCanais":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
                
            defs = db.get_document("canais") or {}
            guild = inter.guild
            if not guild:
                return

            try:
                cat_logs = next((c for c in guild.categories if (c.name or "").strip().lower() == "logs"), None)
                if cat_logs is None:
                    cat_logs = await guild.create_category("Logs", reason=f"Auto-criação de categoria de logs - {inter.author.name} ({inter.author.id})")
            except Exception:
                cat_logs = None

            FORCE_LOGS = {
                "canal_de_evento_de_compras",
                "canal_de_boas_vindas",
                "canal_de_feedback",
                "canal_de_logs_de_pedidos",
            }
            overwrites = {guild.default_role: disnake.PermissionOverwrite(view_channel=False)}
            criados = []

            for key, label, _ in CANAIS_OPCOES:
                ch_id = defs.get(key)
                if ch_id:
                    try:
                        if guild.get_channel(int(ch_id)):
                            continue
                    except (TypeError, ValueError):
                        pass

                name = key.removeprefix("canal_de_").replace("_", "-").lower()
                
                existing_channel_by_name = disnake.utils.get(guild.text_channels, name=name)
                if existing_channel_by_name:
                    defs[key] = str(existing_channel_by_name.id)
                    continue

                category = cat_logs if (("logs" in key) or (key in FORCE_LOGS)) and cat_logs else None

                try:
                    ch = await guild.create_text_channel(
                        name, overwrites=overwrites, category=category,
                        reason=f"Auto-criação pelo painel de configurações - {inter.author.name} ({inter.author.id})"
                    )
                    defs[key] = str(ch.id)
                    criados.append(ch)

                    if mode == "embed":
                        embed, components = MensagensCanais.canal_criado_embed(ch, auto=True)
                        await ch.send(embed=embed, components=components)
                    else:
                        await ch.send(components=MensagensCanais.canal_criado_components(ch, auto=True), flags=disnake.MessageFlags(is_components_v2=True))

                except Exception:
                    pass

            db.save_document("canais", {}, defs)

            if mode == "embed":
                embed, components = ConfigurarCanais.canais_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ConfigurarCanais.canais_components(inter))

            if len(criados) > 0:
                if mode == "embed":
                    embed, components = MensagensCanais.canais_criados_embed(criados)
                    await inter.followup.send(embed=embed, components=components, ephemeral=True)
                else:
                    await inter.followup.send(components=MensagensCanais.canais_criados_components(criados), flags=disnake.MessageFlags(is_components_v2=True), ephemeral=True)


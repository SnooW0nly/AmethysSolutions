import random
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .listar import CARGOS_OPCOES, CARGOS_CORES
from .cog import ConfigurarCargos

class MensagensCargos:
    @staticmethod
    def cargo_criado_components(cargo: disnake.Role, auto: bool) -> disnake.ui.Container:
        return disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Criar Todos os Cargos Automáticamente > Cargo Criado" if auto else f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Criar Cargo > Cargo Criado"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Informações do cargo:**\nID: `{cargo.id}`\nNome: `{cargo.name}`\nMenção: {cargo.mention}"),
        )

    @staticmethod
    def cargos_criados_components(criados: list[disnake.Role]) -> list[disnake.ui.Container]:
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
**Informações dos cargos criados:**
`{len(criados)}` cargos criados com sucesso.
                """),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"{", ".join(f"{c.mention} (`{c.id}`)" for c in criados)}")
            )
        ]

    @staticmethod
    def cargo_criado_embed(cargo: disnake.Role, auto: bool):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Cargo Criado",
            description=f"**Informações do cargo:**\nID: `{cargo.id}`\nNome: `{cargo.name}`\nMenção: {cargo.mention}",
            # timestamp=disnake.utils.utcnow()
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color
        return embed, []

    @staticmethod
    def cargos_criados_embed(criados: list[disnake.Role]):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Cargos Criados",
            description=f"`{len(criados)}` cargos criados com sucesso.",
            # timestamp=disnake.utils.utcnow()
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color
        embed.add_field(
            name="Cargos:",
            value=f"{', '.join(f'{c.mention} (`{c.id}`)' for c in criados)}"
        )
        return embed, []

class CriarTodosCargos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def criar_todos_cargos(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Configuracoes_CriarTodosCargos":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)

            defs = db.get_document("cargos") or {}
            guild = inter.guild
            if not guild:
                return

            criados = []
            for key, label, _ in CARGOS_OPCOES:
                role_id = defs.get(key)
                if role_id:
                    try:
                        if guild.get_role(int(role_id)):
                            continue
                    except (ValueError, TypeError):
                        pass

                existing_role_by_name = disnake.utils.get(guild.roles, name=label)
                if existing_role_by_name:
                    defs[key] = str(existing_role_by_name.id)
                    continue
                
                try:
                    cargo = await guild.create_role(
                        name=label,
                        reason=f"Auto-criação pelo painel de configurações - {inter.author.name} ({inter.author.id})",
                        color=disnake.Color(CARGOS_CORES[random.randint(0, len(CARGOS_CORES) - 1)])
                    )
                    defs[key] = str(cargo.id)
                    criados.append(cargo)

                except Exception as e:
                    print(e)
                    continue

            db.save_document("cargos", {}, defs)

            if mode == "embed":
                embed, components = ConfigurarCargos.cargos_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ConfigurarCargos.cargos_components(inter))

            if len(criados) > 0:
                if mode == "embed":
                    embed, components = MensagensCargos.cargos_criados_embed(criados)
                    await inter.followup.send(embed=embed, components=components, ephemeral=True)
                else:
                    await inter.followup.send(components=MensagensCargos.cargos_criados_components(criados), flags=disnake.MessageFlags(is_components_v2=True), ephemeral=True)


import asyncio

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from modules.automations.cont_members import helpers


class AdicionarContadorModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Prefixo do Contador",
                placeholder="Ex: Staff Online, Moderadores, etc.",
                custom_id="prefixo",
                style=disnake.TextInputStyle.short,
                max_length=50,
                required=True
            )
        ]
        super().__init__(title="Adicionar Contador de Membros", components=components, timeout=300)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(with_message=False)

        prefixo_raw = inter.text_values["prefixo"].strip()
        
        # Validar e sanitizar o prefixo
        if not prefixo_raw:
            await inter.followup.send(f"{emoji.wrong} O prefixo não pode estar vazio.", ephemeral=True)
            return
        
        prefixo = helpers.sanitizar_prefixo(prefixo_raw)
        
        if not prefixo:
            await inter.followup.send(f"{emoji.wrong} O prefixo contém apenas caracteres inválidos. Use apenas letras, números e espaços.", ephemeral=True)
            return
        
        if prefixo != prefixo_raw:
            await inter.followup.send(f"⚠️ Caracteres inválidos foram removidos do prefixo. Prefixo usado: `{prefixo}`", ephemeral=True)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            embed, components = ContMembrosCog.PainelSelecionarCanalEmbed(prefixo)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await message.wait(inter, send=False)
            await inter.edit_original_message(
            components=ContMembrosCog.PainelSelecionarCanal(prefixo)
        )

class ContMembrosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def Painel() -> list[disnake.ui.Container]:
        config = helpers.load_config()
        return ContMembrosCog.PainelFromConfig(config)

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.load_config()
        return ContMembrosCog.PainelFromConfigEmbed(config)

    @staticmethod
    def PainelFromConfig(config: dict) -> list[disnake.ui.Container]:
        ativado = bool(config.get("ativado", False))
        contadores = list(config.get("contadores", []))
        desativado_ou_sem = (not ativado) or (len(contadores) == 0)

        estilo_global = int(config.get("estilo", 0))
        status_texto = "Ativado" if ativado else "Desativado"

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="ContMembros_ToggleSistema"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.success, emoji=emoji.plus, custom_id="ContMembros_Adicionar", disabled=not ativado),
        ]
        if contadores:
            botoes_principais.append(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="ContMembros_Remover", disabled=not ativado)
            )
        botoes_principais.append(
            disnake.ui.Button(label="Atualizar", style=disnake.ButtonStyle.primary, emoji=emoji.reload, custom_id="ContMembros_AtualizarAgora", disabled=desativado_ou_sem)
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        containers: list[disnake.ui.Container | disnake.ui.ActionRow] = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > **Contador de Membros (Por Cargo)**
                """),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"""
Configure contadores automáticos de membros por cargo.
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"""
{emoji.on if ativado else emoji.off} **Status:** `{status_texto}`
{emoji.members} **Total de contadores:** `{len(contadores)}`
{emoji.edit} **Estilo atual:** `{helpers.estilo_legenda(estilo_global)}`
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*botoes_principais),
                **container_kwargs
            )
        ]

        containers.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
                disnake.ui.Button(label="Trocar Estilo", style=disnake.ButtonStyle.secondary, emoji=emoji.edit, custom_id="ContMembros_TrocarEstilo", disabled=desativado_ou_sem),
            )
        )

        return containers

    @staticmethod
    def PainelFromConfigEmbed(config: dict) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        ativado = bool(config.get("ativado", False))
        contadores = list(config.get("contadores", []))
        desativado_ou_sem = (not ativado) or (len(contadores) == 0)

        estilo_global = int(config.get("estilo", 0))
        status_texto = "Ativado" if ativado else "Desativado"

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="ContMembros_ToggleSistema"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.success, emoji=emoji.plus, custom_id="ContMembros_Adicionar", disabled=not ativado),
        ]
        if contadores:
            botoes_principais.append(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="ContMembros_Remover", disabled=not ativado)
            )
        botoes_principais.append(
            disnake.ui.Button(label="Atualizar", style=disnake.ButtonStyle.primary, emoji=emoji.reload, custom_id="ContMembros_AtualizarAgora", disabled=desativado_ou_sem)
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Contador de Membros (Por Cargo)",
            description="Configure contadores automáticos de membros por cargo."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status do sistema:** `{status_texto}`\n"
            f"{emoji.members} **Total de contadores:** `{len(contadores)}`\n"
            f"{emoji.edit} **Estilo atual:** `{helpers.estilo_legenda(estilo_global)}`"
        )
        embed.add_field(name="Configurações", value=resumo, inline=False)
        
        components = [
            disnake.ui.ActionRow(*botoes_principais),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
                disnake.ui.Button(label="Trocar Estilo", style=disnake.ButtonStyle.secondary, emoji=emoji.edit, custom_id="ContMembros_TrocarEstilo", disabled=desativado_ou_sem),
            )
        ]
        return embed, components

    @staticmethod
    def PainelRemover() -> list[disnake.ui.Container]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        config = helpers.load_config()
        contadores = list(config.get("contadores", []))

        if not contadores:
            return ContMembrosCog.Painel()

        options = []
        for i, contador in enumerate(contadores[:25]):
            prefixo = contador.get("prefixo", "Contador")
            cargo_id = contador.get("cargo_id")
            canal_id = contador.get("canal_id")
            descricao = f"Canal: {canal_id} | Cargo: {cargo_id}"
            options.append(
                disnake.SelectOption(
                    label=f"{prefixo}",
                    value=str(i),
                    description=descricao,
                    emoji=emoji.role
                )
            )
        
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > Contador de Membros (Por Cargo) > **Remover**"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Selecione um contador para remover",
                        options=options,
                        custom_id="ContMembros_SelectContador",
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ContMembros_VoltarGerenciar")
            )
        ]

    @staticmethod
    def PainelRemoverEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.load_config()
        contadores = list(config.get("contadores", []))

        if not contadores:
            return ContMembrosCog.PainelEmbed()

        options = []
        for i, contador in enumerate(contadores[:25]):
            prefixo = contador.get("prefixo", "Contador")
            cargo_id = contador.get("cargo_id")
            canal_id = contador.get("canal_id")
            descricao = f"Canal: {canal_id} | Cargo: {cargo_id}"
            options.append(
                disnake.SelectOption(
                    label=f"{prefixo}",
                    value=str(i),
                    description=descricao,
                    emoji=emoji.role
                )
            )
        
        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Remover Contador",
            description="Selecione um contador da lista abaixo para remover."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Selecione um contador para remover",
                    options=options,
                    custom_id="ContMembros_SelectContador",
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ContMembros_VoltarGerenciar")
            )
        ]
        return embed, components

    @staticmethod
    def PainelSelecionarCanal(prefixo) -> list[disnake.ui.Container]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        prefixo_codificado = helpers.codificar_prefixo(prefixo)
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > Contador de Membros (Por Cargo) > Adicionar Contador > **Selecionar Canal**
                """),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"""
**Prefixo:** {prefixo}

Selecione o canal de voz onde o contador será exibido.
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        placeholder="Selecione o canal de voz",
                        custom_id=f"ContMembros_SelecionarCanal:{prefixo_codificado}",
                        min_values=1,
                        max_values=1,
                        channel_types=[disnake.ChannelType.voice]
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ContMembros_VoltarGerenciar"),
            )
        ]

    @staticmethod
    def PainelSelecionarCanalEmbed(prefixo) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Adicionar Contador: Selecionar Canal",
            description=f"**Prefixo:** {prefixo}\n\nSelecione o canal de voz onde o contador será exibido."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        prefixo_codificado = helpers.codificar_prefixo(prefixo)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal de voz",
                    custom_id=f"ContMembros_SelecionarCanal:{prefixo_codificado}",
                    min_values=1,
                    max_values=1,
                    channel_types=[disnake.ChannelType.voice]
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ContMembros_VoltarGerenciar"),
            )
        ]
        return embed, components

    @staticmethod
    def PainelSelecionarCargo(prefixo, canal_id) -> list[disnake.ui.Container]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        prefixo_codificado = helpers.codificar_prefixo(prefixo)
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > Contador de Membros (Por Cargo)> Adicionar Contador > **Selecionar Cargo**
                """),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"""
**Prefixo:** {prefixo}
**Canal:** <#{canal_id}>

Selecione o cargo que será contado no contador.
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        placeholder="Selecione o cargo",
                        custom_id=f"ContMembros_SelecionarCargo:{prefixo_codificado}:{canal_id}",
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"ContMembros_VoltarSelecionarCanal:{prefixo_codificado}"),
            )
        ]

    @staticmethod
    def PainelSelecionarCargoEmbed(prefixo, canal_id) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Adicionar Contador: Selecionar Cargo",
            description=f"**Prefixo:** {prefixo}\n**Canal:** <#{canal_id}>\n\nSelecione o cargo que será contado no contador."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        prefixo_codificado = helpers.codificar_prefixo(prefixo)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Selecione o cargo",
                    custom_id=f"ContMembros_SelecionarCargo:{prefixo_codificado}:{canal_id}",
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"ContMembros_VoltarSelecionarCanal:{prefixo_codificado}"),
            )
        ]
        return embed, components


    @commands.Cog.listener("on_button_click")
    async def contmembros_button_listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("ContMembros_"):
            return

        if inter.component.custom_id == "ContMembros_Adicionar":
            modal = AdicionarContadorModal()
            await inter.response.send_modal(modal)
            return
        
        if inter.component.custom_id == "ContMembros_AtualizarAgora":
            config = helpers.load_config()
            if config.get("ativado", False):
                await inter.response.send_message(f"{emoji.clock} Os contadores estão sendo atualizados em segundo plano. Isso pode levar alguns minutos...", ephemeral=True)
                await helpers.atualizar_contadores_manual(self.bot, inter.guild, config)
            else:
                await inter.response.send_message(f"{emoji.wrong} Sistema desativado. Ative o sistema para atualizar contadores.", ephemeral=True)
            return

        mode = db.get_document("custom_mode").get("mode")

        if inter.component.custom_id == "ContMembros_Remover":
            if mode == "embed":
                embed, components = ContMembrosCog.PainelRemoverEmbed()
                await inter.response.edit_message(content=None, embed=embed, components=components)
            else:
                await inter.response.edit_message(components=ContMembrosCog.PainelRemover())
            return

        if inter.component.custom_id == "ContMembros_TrocarEstilo":
            config = helpers.load_config()
            estilo_atual = int(config.get("estilo", 0))
            proximo_estilo = (estilo_atual + 1) % 4
            config["estilo"] = proximo_estilo
            helpers.save_config(config)

            if mode == "embed":
                embed, components = ContMembrosCog.PainelFromConfigEmbed(config)
                await inter.response.edit_message(content=None, embed=embed, components=components)
            else:
                await inter.response.edit_message(components=ContMembrosCog.PainelFromConfig(config))

            if config.get("ativado", False):
                try:
                    asyncio.create_task(helpers.atualizar_contadores_manual(self.bot, inter.guild, config))
                except Exception:
                    pass
            return

        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await inter.response.defer(with_message=False)
        
        config = helpers.load_config()

        if mode != "embed":
            await message.wait(inter, send=False)

        if inter.component.custom_id == "ContMembros_ToggleSistema":
            config["ativado"] = not config.get("ativado", False)
            helpers.save_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ContMembrosCog.Painel())
        
        elif inter.component.custom_id == "ContMembros_VoltarGerenciar":
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ContMembrosCog.Painel())

        elif inter.component.custom_id.startswith("ContMembros_RemoverContador_"):
            contador_index = int(inter.component.custom_id.split("_")[-1])
            config["contadores"].pop(contador_index)
            helpers.save_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ContMembrosCog.Painel())
        
        elif inter.component.custom_id.startswith("ContMembros_VoltarSelecionarCanal:"):
            prefixo_codificado = inter.component.custom_id.split(":", 1)[1]
            prefixo = helpers.decodificar_prefixo(prefixo_codificado)
            if mode == "embed":
                embed, components = self.PainelSelecionarCanalEmbed(prefixo)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ContMembrosCog.PainelSelecionarCanal(prefixo))

    @commands.Cog.listener("on_dropdown")
    async def contmembros_select_listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("ContMembros_"):
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await inter.response.defer(with_message=False)
            await message.wait(inter, send=False)

        if inter.component.custom_id == "ContMembros_SelectContador":
            config = helpers.load_config()
            contador_index = int(inter.values[0])
            config["contadores"].pop(contador_index)
            helpers.save_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ContMembrosCog.Painel())
        
        elif inter.component.custom_id.startswith("ContMembros_SelecionarCanal:"):
            prefixo_codificado = inter.component.custom_id.split(":", 1)[1]
            prefixo = helpers.decodificar_prefixo(prefixo_codificado)
            canal_id = inter.values[0]
            
            canal = inter.guild.get_channel(int(canal_id))
            if not isinstance(canal, disnake.VoiceChannel):
                await inter.followup.send("O canal selecionado não é de voz. Selecione um canal de voz.", ephemeral=True)
                return
            
            if mode == "embed":
                embed, components = self.PainelSelecionarCargoEmbed(prefixo, canal_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ContMembrosCog.PainelSelecionarCargo(prefixo, canal_id))
        
        elif inter.component.custom_id.startswith("ContMembros_SelecionarCargo:"):
            parts = inter.component.custom_id.split(":", 2)
            if len(parts) < 3:
                await inter.followup.send("Erro interno: custom_id inválido.", ephemeral=True)
                return
            prefixo_codificado = parts[1]
            prefixo = helpers.decodificar_prefixo(prefixo_codificado)
            try:
                canal_id = int(parts[2])
            except ValueError:
                await inter.followup.send("Erro interno: ID de canal inválido.", ephemeral=True)
                return
            cargo_id = int(inter.values[0])
            
            cargo = inter.guild.get_role(cargo_id)
            canal = inter.guild.get_channel(canal_id)
            
            if not cargo or not canal:
                await inter.followup.send("Erro ao processar seleção. Tente novamente.", ephemeral=True)
                return
            
            config = helpers.load_config()
            contadores_existentes = config.get("contadores", [])
            contadores_filtrados = [c for c in contadores_existentes if not (c.get("guild_id") == inter.guild.id and c.get("canal_id") == canal_id)]
            config["contadores"] = contadores_filtrados
            
            novo_contador = {
                "guild_id": inter.guild.id,
                "canal_id": canal_id,
                "cargo_id": cargo_id,
                "prefixo": prefixo
            }
            
            if "contadores" not in config:
                config["contadores"] = []
            
            config["contadores"].append(novo_contador)
            helpers.save_config(config)
            
            if config.get("ativado", False):
                membros_com_cargo = len([member for member in inter.guild.members if cargo in member.roles])
                novo_nome = helpers.formatar_nome_canal(prefixo, membros_com_cargo, int(config.get("estilo", 0)))
                try:
                    await canal.edit(name=novo_nome, reason="Configuração do contador de membros")
                except:
                    pass
            
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=ContMembrosCog.Painel())

def setup(bot: commands.Bot):
    bot.add_cog(ContMembrosCog(bot))

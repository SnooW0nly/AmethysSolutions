import asyncio

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from . import helpers


class AdicionarContadorFeedbacksModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Prefixo do Contador",
                placeholder="Ex: Feedbacks, Total de Feedbacks",
                custom_id="prefixo",
                style=disnake.TextInputStyle.short,
                max_length=50,
                required=True,
            )
        ]
        super().__init__(title="Adicionar Contador de Feedbacks", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(with_message=False)
        prefixo_raw = inter.text_values["prefixo"].strip()

        if not prefixo_raw:
            await inter.followup.send(f"{emoji.wrong} O prefixo não pode estar vazio.", ephemeral=True)
            return

        prefixo = helpers.sanitizar_prefixo(prefixo_raw)

        if not prefixo:
            await inter.followup.send(
                f"{emoji.wrong} O prefixo contém apenas caracteres inválidos. Use apenas letras, números e espaços.",
                ephemeral=True,
            )
            return

        if prefixo != prefixo_raw:
            await inter.followup.send(
                f"⚠️ Caracteres inválidos foram removidos do prefixo. Prefixo usado: `{prefixo}`",
                ephemeral=True,
            )

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            embed, components = ContFeedbacksCog.PainelSelecionarTipoEmbed(prefixo)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=ContFeedbacksCog.PainelSelecionarTipo(prefixo))


class ContFeedbacksCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_task_cog(self):
        """Retorna a instância do cog de task para chamar atualizar_agora."""
        return self.bot.cogs.get("ContFeedbacksTask")

    # ──────────────────────────────────────────────────────────────
    # Panel: principal
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def Painel() -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        contadores = config.get("contadores", [])
        estilo = config.get("estilo", 0)

        canais_config = db.get_document("canais") or {}
        canal_feedback_id = canais_config.get("canal_de_feedback")
        canal_configurado = f"<#{canal_feedback_id}>" if canal_feedback_id else "`Não configurado`"

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.textc} **Canal de Feedbacks:** {canal_configurado}\n"
            f"{emoji.members} **Contadores:** `{len(contadores)}`\n"
            f"{emoji.edit} **Estilo:** `{helpers.estilo_legenda(estilo)}`"
        )

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="ContFeedbacks_ToggleSistema"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="ContFeedbacks_Adicionar", disabled=not ativado),
        ]

        if contadores:
            botoes_principais.append(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="ContFeedbacks_Remover", disabled=not ativado)
            )

        botoes_principais.append(
            disnake.ui.Button(label="Atualizar", style=disnake.ButtonStyle.blurple, emoji=emoji.reload, custom_id="ContFeedbacks_AtualizarAgora", disabled=not ativado or not contadores)
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        componentes = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > **Contador de Feedbacks**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure contadores automáticos com a quantidade de mensagens no canal de feedbacks."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*botoes_principais),
                **container_kwargs,
            )
        ]

        componentes.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
                disnake.ui.Button(label="Trocar Estilo", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="ContFeedbacks_TrocarEstilo", disabled=not ativado or not contadores),
            )
        )
        return componentes

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        contadores = config.get("contadores", [])
        estilo = config.get("estilo", 0)

        canais_config = db.get_document("canais") or {}
        canal_feedback_id = canais_config.get("canal_de_feedback")
        canal_configurado = f"<#{canal_feedback_id}>" if canal_feedback_id else "`Não configurado`"

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.textc} **Canal de Feedbacks:** {canal_configurado}\n"
            f"{emoji.members} **Contadores:** `{len(contadores)}`\n"
            f"{emoji.edit} **Estilo:** `{helpers.estilo_legenda(estilo)}`"
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title="Contador de Feedbacks",
            description="Configure contadores automáticos com a quantidade de mensagens no canal de feedbacks.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        embed.add_field(name="Configurações", value=resumo, inline=False)

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="ContFeedbacks_ToggleSistema"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="ContFeedbacks_Adicionar", disabled=not ativado),
        ]

        if contadores:
            botoes_principais.append(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="ContFeedbacks_Remover", disabled=not ativado)
            )

        botoes_principais.append(
            disnake.ui.Button(label="Atualizar", style=disnake.ButtonStyle.blurple, emoji=emoji.reload, custom_id="ContFeedbacks_AtualizarAgora", disabled=not ativado or not contadores)
        )

        components = [
            disnake.ui.ActionRow(*botoes_principais),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
                disnake.ui.Button(label="Trocar Estilo", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="ContFeedbacks_TrocarEstilo", disabled=not ativado or not contadores),
            ),
        ]
        return embed, components

    # ──────────────────────────────────────────────────────────────
    # Panel: Remover
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def PainelRemover() -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        contadores = config.get("contadores", [])

        if not contadores:
            return ContFeedbacksCog.Painel()

        opcoes = [
            disnake.SelectOption(
                label=c.get("prefixo", "Contador"),
                value=str(i),
                description=f"{'Canal de Voz' if c.get('tipo') == 'canal' else 'Categoria'}: {c.get('target_id')}",
            )
            for i, c in enumerate(contadores[:25])
        ]

        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > Contador de Feedbacks > **Remover**"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Selecione um contador para remover",
                        options=opcoes,
                        custom_id="ContFeedbacks_SelectContador",
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ContFeedbacks_Voltar")
            ),
        ]

    @staticmethod
    def PainelRemoverEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.carregar_config()
        contadores = config.get("contadores", [])

        if not contadores:
            return ContFeedbacksCog.PainelEmbed()

        opcoes = [
            disnake.SelectOption(
                label=c.get("prefixo", "Contador"),
                value=str(i),
                description=f"{'Canal de Voz' if c.get('tipo') == 'canal' else 'Categoria'}: {c.get('target_id')}",
            )
            for i, c in enumerate(contadores[:25])
        ]

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(title="Remover Contador de Feedbacks", description="Selecione um contador da lista abaixo para remover.")
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Selecione um contador para remover",
                    options=opcoes,
                    custom_id="ContFeedbacks_SelectContador",
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ContFeedbacks_Voltar")
            ),
        ]
        return embed, components

    # ──────────────────────────────────────────────────────────────
    # Panel: Selecionar Tipo (Canal de Voz / Canal de Texto / Categoria)
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def PainelSelecionarTipo(prefixo: str) -> list[disnake.ui.Container]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        prefixo_codificado = helpers.codificar_prefixo(prefixo)
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Contador de Feedbacks > **Selecionar Tipo**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Prefixo:** `{prefixo}`\nSelecione onde o contador será exibido:"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Canal de Voz", style=disnake.ButtonStyle.primary, emoji=emoji.voice, custom_id=f"ContFeedbacks_SelecionarCanal:{prefixo_codificado}"),
                    disnake.ui.Button(label="Canal de Texto", style=disnake.ButtonStyle.primary, emoji=emoji.textc, custom_id=f"ContFeedbacks_SelecionarCanalTexto:{prefixo_codificado}"),
                    disnake.ui.Button(label="Categoria", style=disnake.ButtonStyle.primary, emoji=emoji.dir, custom_id=f"ContFeedbacks_SelecionarCategoria:{prefixo_codificado}"),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ContFeedbacks_Voltar")
            ),
        ]

    @staticmethod
    def PainelSelecionarTipoEmbed(prefixo: str) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title="Adicionar Contador: Selecionar Tipo",
            description=f"**Prefixo:** `{prefixo}`\nSelecione onde o contador será exibido:",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        prefixo_codificado = helpers.codificar_prefixo(prefixo)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Canal de Voz", style=disnake.ButtonStyle.primary, emoji=emoji.voice, custom_id=f"ContFeedbacks_SelecionarCanal:{prefixo_codificado}"),
                disnake.ui.Button(label="Canal de Texto", style=disnake.ButtonStyle.primary, emoji=emoji.textc, custom_id=f"ContFeedbacks_SelecionarCanalTexto:{prefixo_codificado}"),
                disnake.ui.Button(label="Categoria", style=disnake.ButtonStyle.primary, emoji=emoji.dir, custom_id=f"ContFeedbacks_SelecionarCategoria:{prefixo_codificado}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ContFeedbacks_Voltar")
            ),
        ]
        return embed, components

    # ──────────────────────────────────────────────────────────────
    # Panel: Selecionar Target (ChannelSelect)
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def PainelSelecionarTarget(prefixo: str, tipo: str) -> list[disnake.ui.Container]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        tipo_label_map = {
            "canal": ("Canal de Voz", [disnake.ChannelType.voice]),
            "canal_texto": ("Canal de Texto", [disnake.ChannelType.text]),
            "categoria": ("Categoria", [disnake.ChannelType.category]),
        }
        label, channel_types = tipo_label_map.get(tipo, ("Canal", [disnake.ChannelType.voice]))
        placeholder = f"Selecione o {label.lower()}"
        prefixo_codificado = helpers.codificar_prefixo(prefixo)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Contador de Feedbacks > **Selecionar {label}**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Prefixo:** `{prefixo}`"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        placeholder=placeholder,
                        custom_id=f"ContFeedbacks_Confirmar:{prefixo_codificado}:{tipo}",
                        min_values=1,
                        max_values=1,
                        channel_types=channel_types,
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"ContFeedbacks_VoltarTipo:{prefixo_codificado}")
            ),
        ]

    @staticmethod
    def PainelSelecionarTargetEmbed(prefixo: str, tipo: str) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        tipo_label_map = {
            "canal": ("Canal de Voz", [disnake.ChannelType.voice]),
            "canal_texto": ("Canal de Texto", [disnake.ChannelType.text]),
            "categoria": ("Categoria", [disnake.ChannelType.category]),
        }
        label, channel_types = tipo_label_map.get(tipo, ("Canal", [disnake.ChannelType.voice]))
        placeholder = f"Selecione o {label.lower()}"

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Adicionar Contador: Selecionar {label}",
            description=f"**Prefixo:** `{prefixo}`",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        prefixo_codificado = helpers.codificar_prefixo(prefixo)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder=placeholder,
                    custom_id=f"ContFeedbacks_Confirmar:{prefixo_codificado}:{tipo}",
                    min_values=1,
                    max_values=1,
                    channel_types=channel_types,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"ContFeedbacks_VoltarTipo:{prefixo_codificado}")
            ),
        ]
        return embed, components

    # ──────────────────────────────────────────────────────────────
    # Button listener
    # ──────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def contfeedbacks_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("ContFeedbacks_"):
            return

        if custom_id == "ContFeedbacks_Adicionar":
            await inter.response.send_modal(AdicionarContadorFeedbacksModal())
            return

        if custom_id == "ContFeedbacks_AtualizarAgora":
            config = helpers.carregar_config()
            if config.get("ativado"):
                await inter.response.send_message(
                    f"{emoji.clock} Os contadores estão sendo atualizados em segundo plano. Isso pode levar alguns instantes...",
                    ephemeral=True,
                )
                task_cog = self._get_task_cog()
                if task_cog:
                    asyncio.create_task(task_cog.atualizar_agora(inter.guild))
            else:
                await inter.response.send_message("O sistema está desativado.", ephemeral=True)
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if custom_id == "ContFeedbacks_ToggleSistema":
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

        elif custom_id == "ContFeedbacks_TrocarEstilo":
            config = helpers.carregar_config()
            config["estilo"] = (config.get("estilo", 0) + 1) % 4
            helpers.salvar_config(config)
            if config.get("ativado"):
                task_cog = self._get_task_cog()
                if task_cog:
                    asyncio.create_task(task_cog.atualizar_agora(inter.guild))
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

        elif custom_id == "ContFeedbacks_Remover":
            if mode == "embed":
                embed, components = self.PainelRemoverEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelRemover())

        elif custom_id == "ContFeedbacks_Voltar":
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

        elif custom_id.startswith("ContFeedbacks_SelecionarCanal:") and not custom_id.startswith("ContFeedbacks_SelecionarCanalTexto:"):
            prefixo_codificado = custom_id.split(":", 1)[1]
            prefixo = helpers.decodificar_prefixo(prefixo_codificado)
            if mode == "embed":
                embed, components = self.PainelSelecionarTargetEmbed(prefixo, "canal")
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelSelecionarTarget(prefixo, "canal"))

        elif custom_id.startswith("ContFeedbacks_SelecionarCanalTexto:"):
            prefixo_codificado = custom_id.split(":", 1)[1]
            prefixo = helpers.decodificar_prefixo(prefixo_codificado)
            if mode == "embed":
                embed, components = self.PainelSelecionarTargetEmbed(prefixo, "canal_texto")
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelSelecionarTarget(prefixo, "canal_texto"))

        elif custom_id.startswith("ContFeedbacks_SelecionarCategoria:"):
            prefixo_codificado = custom_id.split(":", 1)[1]
            prefixo = helpers.decodificar_prefixo(prefixo_codificado)
            if mode == "embed":
                embed, components = self.PainelSelecionarTargetEmbed(prefixo, "categoria")
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelSelecionarTarget(prefixo, "categoria"))

        elif custom_id.startswith("ContFeedbacks_VoltarTipo:"):
            prefixo_codificado = custom_id.split(":", 1)[1]
            prefixo = helpers.decodificar_prefixo(prefixo_codificado)
            if mode == "embed":
                embed, components = self.PainelSelecionarTipoEmbed(prefixo)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelSelecionarTipo(prefixo))

    # ──────────────────────────────────────────────────────────────
    # Select/Dropdown listener
    # ──────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def contfeedbacks_select_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("ContFeedbacks_"):
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if custom_id == "ContFeedbacks_SelectContador":
            config = helpers.carregar_config()
            contador_index = int(inter.values[0])
            config["contadores"].pop(contador_index)
            helpers.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

        elif custom_id.startswith("ContFeedbacks_Confirmar:"):
            partes = custom_id.split(":", 2)
            if len(partes) < 3:
                await inter.followup.send("Erro interno: custom_id inválido.", ephemeral=True)
                return
            prefixo_codificado = partes[1]
            prefixo = helpers.decodificar_prefixo(prefixo_codificado)
            tipo = partes[2]

            try:
                target_id = int(inter.values[0])
            except ValueError:
                await inter.followup.send("Erro interno: ID de canal/categoria inválido.", ephemeral=True)
                return

            config = helpers.carregar_config()
            contadores = config.get("contadores", [])
            contadores = [c for c in contadores if not (c.get("guild_id") == inter.guild.id and c.get("target_id") == target_id)]

            novo_contador = {"guild_id": inter.guild.id, "target_id": target_id, "tipo": tipo, "prefixo": prefixo}
            contadores.append(novo_contador)
            config["contadores"] = contadores
            helpers.salvar_config(config)

            if config.get("ativado"):
                task_cog = self._get_task_cog()
                if task_cog:
                    asyncio.create_task(task_cog.atualizar_agora(inter.guild))

            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())


def setup(bot: commands.Bot):
    bot.add_cog(ContFeedbacksCog(bot))
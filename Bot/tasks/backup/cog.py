import disnake
from disnake.ext import commands
import os
import asyncio

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database
from functions.perms import perms

from .restore import Restore
from .sync import Sincronizacao
from .backup import Backup
from .backup_auto import BackupAutomatico
from .modal import BackupAutoConfigModal, RestoreGuildIDModal

BACKUP_DIR = 'database/backups'

class BackupCog(commands.Cog, name="Backup"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auto_backup_task = self.bot.loop.create_task(BackupAutomatico.AutoBackupLoop(bot))
        self.initial_backup_task = self.bot.loop.create_task(BackupAutomatico.RealizarBackupInicial(bot))

    async def display_backup_panel(self, inter: disnake.ApplicationCommandInteraction):
        mode = database.get_document("custom_mode").get("mode")

        if mode == "embed":
            await embed_message.wait(inter, send=True)
            embed, components = self.get_main_panel_components(pagina=0, embed_mode=True)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await message.wait(inter, send=True)
            components = self.get_main_panel_components(pagina=0)
            await inter.edit_original_message(components=components)

    def get_main_panel_components(self, pagina: int = 0, embed_mode: bool = False):
        backups = Backup.ListarBackups()
        por_pagina = 3
        total_paginas = max(1, (len(backups) + por_pagina - 1) // por_pagina)
        pagina = max(0, min(pagina, total_paginas - 1))
        inicio = pagina * por_pagina
        fim = inicio + por_pagina
        backups_pagina = backups[inicio:fim]

        if embed_mode:
            colors = database.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            primary_color = None
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)

            embed = disnake.Embed(
                title=f"Backups",
                description="Veja e gerencie os backups do servidor.",
                color=primary_color if primary_color else disnake.Color.default()
            )
            
            components = []
            action_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Criar um novo Backup",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.correct,
                    custom_id="backup_sincronizar"
                ),
                disnake.ui.Button(
                    label="Backup Automático",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.reload,
                    custom_id="backup_auto_menu"
                )
            )
            components.append(action_row)

            if not backups:
                embed.description += f"\n\n{emoji.alert} Nenhum backup encontrado."
            
            if backups_pagina:
                embed.description += "\n"
                for backup in backups_pagina:
                    if backup['timestamp']:
                        data_formatada = f"<t:{backup['timestamp']}:f> (<t:{backup['timestamp']}:R>)"
                    else:
                        data_formatada = backup['arquivo']
                    
                    embed.add_field(
                        name=f"Nome: `{backup['arquivo'].replace('.json', '')}`",
                        value=f"**Data:** {data_formatada}\n"
                            f"**Servidor:** `{backup['guild']}`\n"
                            f"**Estrutura:**\n"
                            f"{emoji.textc} Canais: `{str(backup['canais'])}` | {emoji.dir} Categorias: `{str(backup['categorias'])}`\n"
                            f"{emoji.role} Cargos: `{str(backup['cargos'])}` | {emoji.reaction} Emojis: `{str(backup['emojis'])}`\n"
                            f"{emoji.flag} Stickers: `{str(backup['stickers'])}` | {emoji.message if hasattr(emoji, 'message') else '💬'} Mensagens: `{str(backup['mensagens'])}`\n"
                            f"{emoji.members} Membros: {str(backup.get('membros', 0))}",
                        inline=False
                    )
            
            for backup in backups_pagina:
                components.append(disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Restaurar",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.reload,
                        custom_id=f"backup_restore:{backup['arquivo']}"
                    ),
                    disnake.ui.Button(
                        label="Apagar",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id=f"backup_delete:{backup['arquivo']}"
                    ),
                ))

            if total_paginas > 1:
                nav_buttons = [
                    disnake.ui.Button(
                        label="<",
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"backup_page:{pagina-1}",
                        disabled=pagina == 0
                    ),
                    disnake.ui.Button(
                        label=f"Página {pagina+1}/{total_paginas}",
                        style=disnake.ButtonStyle.grey,
                        custom_id="backup_page:info",
                        disabled=True
                    ),
                    disnake.ui.Button(
                        label=">",
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"backup_page:{pagina+1}",
                        disabled=pagina >= total_paginas-1
                    )
                ]
                components.append(disnake.ui.ActionRow(*nav_buttons))
            
            return embed, components

        colors = database.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        containers = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Backups\nVeja e gerencie os backups do servidor."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Criar um novo Backup",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.correct,
                        custom_id="backup_sincronizar"
                    ),
                    disnake.ui.Button(
                        label="Backup Automático",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.reload,
                        custom_id="backup_auto_menu"
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.Separator(),
        ]

        if not backups:
            containers.append(
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.alert} Nenhum backup encontrado."),
                    **container_kwargs,
                )
            )

        for backup in backups_pagina:
            if backup['timestamp']:
                data_formatada = f"<t:{backup['timestamp']}:f> (<t:{backup['timestamp']}:R>)"
            else:
                data_formatada = backup['arquivo']

            containers.append(
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"**Nome:** `{backup['arquivo'].replace('.json', '')}`\n"
                        f"**Data:** {data_formatada}\n"
                        f"**Servidor:** `{backup['guild']}`\n"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"\n**Estrutura:**\n"
                        f"{emoji.textc} Canais: {f'`{str(backup['canais'])}`'.ljust(4)}      {emoji.dir} Categorias: {f'`{str(backup['categorias'])}`'.ljust(4)}\n"
                        f"{emoji.role} Cargos: {f'`{str(backup['cargos'])}`'.ljust(4)}     {emoji.reaction} Emojis: {f'`{str(backup['emojis'])}`'.ljust(4)}\n"
                        f"{emoji.flag} Stickers: {f'`{str(backup['stickers'])}`'.ljust(4)}   {emoji.message if hasattr(emoji, 'message') else '💬'} Mensagens: {f'`{str(backup['mensagens'])}`'.ljust(4)}\n"
                        f"{emoji.members} Membros: {f'`{str(backup.get('membros', 0))}`'.ljust(4)}"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Restaurar",
                            style=disnake.ButtonStyle.green,
                            emoji=emoji.reload,
                            custom_id=f"backup_restore:{backup['arquivo']}"
                        ),
                        disnake.ui.Button(
                            label="Apagar",
                            style=disnake.ButtonStyle.red,
                            emoji=emoji.delete,
                            custom_id=f"backup_delete:{backup['arquivo']}"
                        ),
                    ),
                    **container_kwargs,
                )
            )

        if total_paginas > 1:
            nav_buttons = [
                disnake.ui.Button(
                    label="<",
                    style=disnake.ButtonStyle.grey,
                    custom_id=f"backup_page:{pagina-1}",
                    disabled=pagina == 0
                ),
                disnake.ui.Button(
                    label=f"Página {pagina+1}/{total_paginas}",
                    style=disnake.ButtonStyle.grey,
                    custom_id="backup_page:info",
                    disabled=True
                ),
                disnake.ui.Button(
                    label=">",
                    style=disnake.ButtonStyle.grey,
                    custom_id=f"backup_page:{pagina+1}",
                    disabled=pagina >= total_paginas-1
                )
            ]
            containers.append(disnake.ui.ActionRow(*nav_buttons))

        return containers

    def get_auto_backup_panel_components(self, embed_mode: bool = False):
        definicoes = database.obter("database/backup_configs.json")
        auto_ativo = definicoes.get("backup_auto_ativo", False)
        auto_minutos = definicoes.get("backup_auto_minutos", 0)
        status = f"Ativado ({auto_minutos} min)" if auto_ativo else "Desativado"
        if auto_ativo:
            orientacao = "Seu servidor está protegido! Use `/backup` para restaurar caso enfrente problemas."
        else:
            orientacao = "Configure o tempo de backup em **360 minutos** para que o backup seja feito a cada 6 horas."
        
        excluded = definicoes.get("backup_auto_exclude", [])
        
        options = [
            disnake.SelectOption(label="Canais", value="channels", emoji=emoji.textc, default="channels" in excluded, description="Canais do servidor"),
            disnake.SelectOption(label="Categorias", value="categories", emoji=emoji.dir, default="categories" in excluded, description="Categorias do servidor"),
            disnake.SelectOption(label="Cargos", value="roles", emoji=emoji.role, default="roles" in excluded, description="Cargos do servidor"),
            disnake.SelectOption(label="Membros", value="members", emoji=emoji.members, default="members" in excluded, description="Cargos dos membros do servidor"),
            disnake.SelectOption(label="Emojis", value="emojis", emoji=emoji.reaction, default="emojis" in excluded, description="Emojis do servidor"),
            disnake.SelectOption(label="Figurinhas", value="stickers", emoji=emoji.flag, default="stickers" in excluded, description="Figurinhas do servidor"),
            disnake.SelectOption(label="Mensagens", value="messages", emoji=getattr(emoji, 'message', '💬'), default="messages" in excluded, description="Últimas 100 Mensagens de todos os canais"),
        ]

        select_menu = disnake.ui.StringSelect(
            custom_id="backup_auto_exclude",
            placeholder="Selecione o que NÃO incluir no backup",
            min_values=0,
            max_values=len(options),
            options=options
        )

        if embed_mode:
            colors = database.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            primary_color = None
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
            
            embed = disnake.Embed(
                title=f"Backup > **Backup Automático**",
                description=f"{emoji.on if auto_ativo else emoji.off} **Status:** `{status}`\n\n"
                            f"**Orientação:**\n{orientacao}",
                color=primary_color if primary_color else disnake.Color.default()
            )
            
            components = [
                disnake.ui.ActionRow(select_menu),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar" if not auto_ativo else "Desativar",
                        style=disnake.ButtonStyle.green if not auto_ativo else disnake.ButtonStyle.red,
                        emoji=emoji.power,
                        custom_id="backup_auto_toggle"
                    ),
                    disnake.ui.Button(
                        label="Configurar Tempo",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.edit,
                        custom_id="backup_auto_config"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="backup_painel"),
                )
            ]
            return embed, components

        colors = database.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Backup > Backup Automático"),
                disnake.ui.TextDisplay(f"{emoji.on if auto_ativo else emoji.off} **Status:** `{status}`"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Orientação:**\n{orientacao}"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(select_menu),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar" if not auto_ativo else "Desativar",
                        style=disnake.ButtonStyle.green if not auto_ativo else disnake.ButtonStyle.red,
                        emoji=emoji.power,
                        custom_id="backup_auto_toggle"
                    ),
                    disnake.ui.Button(
                        label="Configurar Tempo",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.edit,
                        custom_id="backup_auto_config"
                    ),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="backup_painel"),
            )
        ]
    
    async def get_guild(self, inter: disnake.Interaction):
        guild = inter.guild
        if guild is None:
            server_id = int(database.obter("config.json")["bot"]["server"])
            guild = self.bot.get_guild(server_id)
            if guild is None:
                await message.error(inter, "Não foi possível encontrar o servidor principal para restaurar o backup.")
                return None
        return guild

    @commands.Cog.listener("on_button_click")
    async def backup_button_listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("backup_"):
            return

        custom_id = inter.component.custom_id
        
        mode = database.get_document("custom_mode").get("mode")

        if custom_id.startswith("backup_painel"):
            await self.handle_show_main_panel(inter, mode)
        elif custom_id == "backup_sincronizar":
            await self.handle_sincronizar(inter, mode)
        elif custom_id.startswith("backup_restore:"):
            await self.handle_restore_start(inter, mode)
        elif custom_id.startswith("backup_wipe_select:"):
            await self.handle_wipe_select(inter, mode)
        elif custom_id.startswith("backup_wipe_confirm:"):
            await self.handle_wipe_confirm(inter, mode)
        elif custom_id.startswith("backup_restore_do:"):
            await self.handle_restore_do(inter, mode)
        elif custom_id == "backup_cancel":
            await self.handle_cancel(inter, mode)
        elif custom_id.startswith("backup_delete:"):
            await self.handle_delete(inter, mode)
        elif custom_id.startswith("backup_page:"):
            await self.handle_page(inter, mode)
        elif custom_id == "backup_auto_menu":
            await self.handle_auto_menu(inter, mode)
        elif custom_id == "backup_auto_toggle":
            await self.handle_auto_toggle(inter, mode)
        elif custom_id == "backup_auto_config":
            await self.handle_auto_config(inter, mode)

    @commands.Cog.listener("on_string_select")
    async def backup_select_listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("backup_"):
            return
        
        custom_id = inter.component.custom_id
        mode = database.get_document("custom_mode").get("mode")
        
        if custom_id == "backup_auto_exclude":
            await self.handle_auto_exclude(inter, mode)

    @commands.Cog.listener("on_dropdown")
    async def backup_dropdown_listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("backup_"):
            return
        custom_id = inter.component.custom_id
        mode = database.get_document("custom_mode").get("mode")
        if custom_id == "backup_auto_exclude":
            await self.handle_auto_exclude(inter, mode)

    async def handle_show_main_panel(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            embed, components = self.get_main_panel_components(pagina=0, embed_mode=True)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=self.get_main_panel_components(pagina=0))

    async def handle_sincronizar(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        guild = await self.get_guild(inter)
        if not guild: return

        try:
            resumo = await Sincronizacao.BackupGuild(guild, self.bot)
            
            if mode == "embed":
                colors = database.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                primary_color = None
                if primary_color_hex:
                    primary_color = int(primary_color_hex.replace("#", ""), 16)
                
                embed = disnake.Embed(
                    title=f"{emoji.correct} Backup criado com sucesso!",
                    description=(
                        f"**Informações salvas na nuvem**\n"
                        f"{emoji.textc} Canais: `{resumo['canais']}`\n"
                        f"{emoji.dir} Categorias: `{resumo['categorias']}`\n"
                        f"{emoji.role} Cargos: `{resumo['cargos']}`\n"
                        f"{emoji.members} Membros: {resumo['membros']}\n"
                        f"{emoji.reaction} Emojis: `{resumo['emojis']}`\n"
                        f"{emoji.flag} Figurinhas: `{resumo['stickers']}`\n"
                        f"{emoji.message} Mensagens: `{resumo['mensagens']}`\n\n"
                        f"{emoji.loading} Você será redirecionado para o painel de backups em instantes."
                    ),
                    color=primary_color if primary_color else disnake.Color.green()
                )
                try:
                    await inter.edit_original_message(embed=embed, components=[])
                except disnake.errors.NotFound:
                    try:
                        await inter.followup.send(embed=embed, components=[])
                    except disnake.errors.NotFound:
                        await inter.author.send("A mensagem original foi apagada, continue a restauração por aqui:", embed=embed, components=[])
            else:
                colors = database.get_document("custom_colors")
                primary_color_hex = colors.get("primary")
                container_kwargs = {}
                if primary_color_hex:
                    primary_color = int(primary_color_hex.replace("#", ""), 16)
                    container_kwargs["accent_colour"] = disnake.Colour(primary_color)

                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"{emoji.correct} Backup criado com sucesso!\n\n"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"**Informações salvas na nuvem**\n"
                            f"{emoji.textc} Canais: `{resumo['canais']}`\n"
                            f"{emoji.dir} Categorias: `{resumo['categorias']}`\n"
                            f"{emoji.role} Cargos: `{resumo['cargos']}`\n"
                            f"{emoji.members} Membros: `{resumo['membros']}`\n"
                            f"{emoji.reaction} Emojis: `{resumo['emojis']}`\n"
                            f"{emoji.flag} Figurinhas: `{resumo['stickers']}`\n"
                            f"{emoji.message} Mensagens: `{resumo['mensagens']}`\n"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"{emoji.loading} Você será redirecionado para o painel de backups em instantes."
                        ),
                        **container_kwargs,
                    ),
                ])
            await asyncio.sleep(5)
            if mode == "embed":
                embed, components = self.get_main_panel_components(pagina=0, embed_mode=True)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.get_main_panel_components(pagina=0))
        except Exception as e:
            if mode == "embed":
                await embed_message.error(inter, f"Erro ao criar backup: {e}")
            else:
                await message.error(inter, f"Erro ao criar backup: {e}")
            await asyncio.sleep(2)
            if mode == "embed":
                embed, components = self.get_main_panel_components(pagina=0, embed_mode=True)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.get_main_panel_components(pagina=0))

    async def handle_restore_start(self, inter: disnake.MessageInteraction, mode: str):
        arquivo = inter.component.custom_id.split(":", 1)[1]
        await inter.response.send_modal(RestoreGuildIDModal(self, arquivo, mode))

    async def show_wipe_options(self, inter: disnake.MessageInteraction, arquivo: str, mode: str, target_guild: disnake.Guild = None):
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        guild_id = str(target_guild.id) if target_guild else ""
        
        main_buttons_action_row = disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Apagar tudo",
                style=disnake.ButtonStyle.red,
                emoji=emoji.delete,
                custom_id=f"backup_wipe_confirm:{arquivo}:all:{guild_id}"
            ),
            disnake.ui.Button(
                label="Selecionar o que apagar",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.edit,
                custom_id=f"backup_wipe_select:{arquivo}::{guild_id}"
            ),
            disnake.ui.Button(
                label="Não apagar nada",
                style=disnake.ButtonStyle.green,
                emoji=emoji.correct,
                custom_id=f"backup_wipe_confirm:{arquivo}:none:{guild_id}"
            ),
        )
        cancel_button_action_row = disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id=f"backup_painel"
            )
        )

        if mode == "embed":
            components = [main_buttons_action_row, cancel_button_action_row]
            colors = database.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            primary_color = None
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)

            embed = disnake.Embed(
                title=f"{emoji.delete} Apagar antes de restaurar?",
                description=f"Deseja apagar algo antes de restaurar o backup `{arquivo.replace('.json', '')}`?",
                color=primary_color if primary_color else disnake.Color.default()
            )
            try:
                await inter.edit_original_message(content=None, embed=embed, components=components)
            except disnake.errors.NotFound:
                try:
                    await inter.followup.send(embed=embed, components=components)
                except disnake.errors.NotFound:
                    await inter.author.send("A mensagem original foi apagada, continue a restauração por aqui:", embed=embed, components=components)
        else:
            colors = database.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            container_kwargs = {}
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
                container_kwargs["accent_colour"] = disnake.Colour(primary_color)
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.delete} Deseja apagar algo antes de restaurar o backup `{arquivo.replace('.json', '')}`?"),
                    disnake.ui.Separator(),
                    main_buttons_action_row,
                    **container_kwargs,
                ),
                cancel_button_action_row
            ])

    async def handle_wipe_select(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        parts = inter.component.custom_id.split(":")
        arquivo = parts[1]
        selecionados = set(parts[2].split(",")) if len(parts) > 2 and parts[2] else set()
        guild_id = parts[3] if len(parts) > 3 else ""
        
        opcoes = [
            ("channels", "Canais", emoji.dir),
            ("roles", "Cargos", emoji.role),
            ("members", "Membros", emoji.members),
            ("emojis", "Emojis", emoji.reaction),
            ("stickers", "Figurinhas", emoji.flag),
        ]
        action_row = []
        for key, label, emoji_item in opcoes:
            style = disnake.ButtonStyle.red if key in selecionados else disnake.ButtonStyle.blurple
            action_row.append(
                disnake.ui.Button(
                    label=label,
                    style=style,
                    emoji=emoji_item,
                    custom_id=f"backup_wipe_select:{arquivo}:{','.join(sorted((selecionados ^ {key})))}:{guild_id}"
                )
            )
        
        confirm_disabled = not selecionados
        
        action_rows = [
            disnake.ui.ActionRow(*action_row),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Confirmar",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id=f"backup_wipe_confirm:{arquivo}:{','.join(sorted(selecionados))}:{guild_id}",
                    disabled=confirm_disabled
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, emoji=emoji.wrong, custom_id=f"backup_restore:{arquivo}"),
            )
        ]

        if mode == "embed":
            colors = database.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            primary_color = None
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
            
            embed = disnake.Embed(
                title=f"{emoji.delete} Selecione o que apagar",
                description=f"Selecione o que deseja apagar antes de restaurar o backup `{arquivo.replace('.json', '')}`:",
                color=primary_color if primary_color else disnake.Color.default()
            )
            try:
                await inter.edit_original_message(embed=embed, components=action_rows)
            except disnake.errors.NotFound:
                try:
                    await inter.followup.send(embed=embed, components=action_rows)
                except disnake.errors.NotFound:
                    await inter.author.send("A mensagem original foi apagada, continue a restauração por aqui:", embed=embed, components=action_rows)
        else:
            colors = database.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            container_kwargs = {}
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
                container_kwargs["accent_colour"] = disnake.Colour(primary_color)
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.delete} Selecione o que deseja apagar antes de restaurar o backup `{arquivo.replace('.json', '')}`:"),
                    disnake.ui.Separator(),
                    action_rows[0],
                    disnake.ui.Separator(),
                    action_rows[1],
                    **container_kwargs,
                ),
                action_rows[2]
            ])

    async def handle_wipe_confirm(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        parts = inter.component.custom_id.split(":")
        arquivo = parts[1]
        wipe_tipos = parts[2]
        guild_id = parts[3] if len(parts) > 3 else ""

        if guild_id:
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                if mode == "embed":
                    await embed_message.error(inter, "Servidor alvo não encontrado.")
                else:
                    await message.error(inter, "Servidor alvo não encontrado.")
                return
        else:
            guild = await self.get_guild(inter)
            if not guild: return

        tipos_set = set(wipe_tipos.split(",")) if wipe_tipos not in ["all", "none"] else \
                    {"channels", "roles", "emojis", "stickers"} if wipe_tipos == "all" else set()

        if "channels" in tipos_set:
            for channel in list(guild.channels):
                try: 
                    await channel.delete(reason="[Sync] Backup wipe")
                except disnake.Forbidden:
                    pass  # Sem permissão, ignorar silenciosamente
                except disnake.NotFound:
                    pass  # Canal já foi deletado, ignorar
                except Exception as e: 
                    print(f"[Wipe] Erro ao apagar canal {getattr(channel, 'name', channel.id)}: {e}")
        
        if "roles" in tipos_set:
            for role in list(guild.roles):
                if not role.is_default():
                    try: 
                        await role.delete(reason="[Sync] Backup wipe")
                    except disnake.Forbidden:
                        pass  # Sem permissão (role acima do bot), ignorar silenciosamente
                    except disnake.HTTPException as e:
                        if e.code == 50028:  # Invalid Role
                            pass  # Role inválido (integração/managed), ignorar
                        else:
                            print(f"[Wipe] Erro ao apagar cargo {role.name}: {e}")
                    except disnake.NotFound:
                        pass  # Role já foi deletado, ignorar
                    except Exception as e: 
                        print(f"[Wipe] Erro ao apagar cargo {role.name}: {e}")
        
        if "emojis" in tipos_set:
            for emoji_item in list(guild.emojis):
                try: 
                    await emoji_item.delete(reason="[Sync] Backup wipe")
                except disnake.Forbidden:
                    pass  # Sem permissão, ignorar silenciosamente
                except disnake.NotFound:
                    pass  # Emoji já foi deletado, ignorar
                except Exception as e: 
                    print(f"[Wipe] Erro ao apagar emoji {emoji_item.name}: {e}")
        
        if "stickers" in tipos_set and hasattr(guild, 'stickers'):
            for sticker in list(guild.stickers):
                try: 
                    await sticker.delete(reason="[Sync] Backup wipe")
                except disnake.Forbidden:
                    pass  # Sem permissão, ignorar silenciosamente
                except disnake.NotFound:
                    pass  # Sticker já foi deletado, ignorar
                except Exception as e: 
                    print(f"[Wipe] Erro ao apagar figurinha {sticker.name}: {e}")
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Confirmar",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.correct,
                    custom_id=f"backup_restore_do:{arquivo}:all:{guild_id}"
                ),
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id="backup_cancel"
                ),
            )
        ]

        if mode == "embed":
            colors = database.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            primary_color = None
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
            
            embed = disnake.Embed(
                title=f"{emoji.reload} Confirmar Restauração",
                description="Tem certeza que deseja restaurar esse backup?",
                color=primary_color if primary_color else disnake.Color.default()
            )
            try:
                await inter.edit_original_message(content=None, embed=embed, components=components)
            except disnake.errors.NotFound:
                try:
                    await inter.followup.send(embed=embed, components=components)
                except disnake.errors.HTTPException as e:
                    if e.code == 10003: # Unknown Channel
                        await inter.author.send("O canal original foi apagado, continue a restauração por aqui:", embed=embed, components=components)
                    else:
                        raise
        else:
            colors = database.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            container_kwargs = {}
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
                container_kwargs["accent_colour"] = disnake.Colour(primary_color)
            
            new_components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.reload} Tem certeza que deseja restaurar esse backup?"),
                    disnake.ui.Separator(),
                    *components,
                    **container_kwargs,
                )
            ]
            try:
                await inter.edit_original_message(components=new_components)
            except disnake.errors.NotFound:
                try:
                    await inter.followup.send(components=new_components)
                except disnake.errors.HTTPException as e:
                    if e.code == 10003: # Unknown Channel
                        dm_components = [
                            disnake.ui.Container(
                                disnake.ui.TextDisplay("O canal original foi apagado, continue a restauração por aqui."),
                                disnake.ui.Separator(),
                                disnake.ui.TextDisplay(f"{emoji.reload} Tem certeza que deseja restaurar esse backup?"),
                                disnake.ui.Separator(),
                                *components,
                                **container_kwargs,
                            )
                        ]
                        await inter.author.send(components=dm_components)
                    else:
                        raise
    
    async def handle_restore_do(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        parts = inter.component.custom_id.split(":")
        arquivo = parts[1]
        tipo = parts[2] if len(parts) > 2 else "all"
        guild_id = parts[3] if len(parts) > 3 else ""
        
        if guild_id:
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                if mode == "embed":
                    await embed_message.error(inter, "Servidor alvo não encontrado.")
                else:
                    await message.error(inter, "Servidor alvo não encontrado.")
                return
        else:
            guild = await self.get_guild(inter)
            if not guild: return

        caminho = os.path.join(BACKUP_DIR, arquivo)
        data = database.obter(caminho)

        await Restore.RestoreGuildBackup(
            guild,
            data,
            tipo,
            inter=inter,
            painel_callback=lambda: self.restore_panel_callback(inter, mode),
            mode=mode
        )

    async def restore_panel_callback(self, inter: disnake.MessageInteraction, mode: str):
        if mode == "embed":
            embed, components = self.get_main_panel_components(pagina=0, embed_mode=True)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=self.get_main_panel_components(pagina=0))

    async def handle_cancel(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        await asyncio.sleep(1)
        if mode == "embed":
            embed, components = self.get_main_panel_components(pagina=0, embed_mode=True)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=self.get_main_panel_components(pagina=0))

    async def handle_delete(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        arquivo = inter.component.custom_id.split(":", 1)[1]
        try:
            os.remove(os.path.join(BACKUP_DIR, arquivo))
        except Exception as e:
            if mode == "embed":
                await embed_message.error(inter, f"Erro ao apagar backup: {e}")
            else:
                await message.error(inter, f"Erro ao apagar backup: {e}")
            await asyncio.sleep(2)
        
        if mode == "embed":
            embed, components = self.get_main_panel_components(pagina=0, embed_mode=True)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=self.get_main_panel_components(pagina=0))
        await inter.followup.send(f"{emoji.correct} Backup `{arquivo.replace('.json', '').replace('_', '')}` apagado com sucesso!", ephemeral=True)

    async def handle_page(self, inter: disnake.MessageInteraction, mode: str):
        pagina_str = inter.component.custom_id.split(":", 1)[1]
        if pagina_str == "info":
            await inter.response.defer(with_message=False)
            return
        try:
            pagina = int(pagina_str)
        except ValueError:
            pagina = 0
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            embed, components = self.get_main_panel_components(pagina=pagina, embed_mode=True)
            await inter.edit_original_message(embed=embed, components=components)
        else:
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=self.get_main_panel_components(pagina=pagina))

    async def handle_auto_menu(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            embed, components = self.get_auto_backup_panel_components(embed_mode=True)
            await inter.edit_original_message(embed=embed, components=components)
        else:
            await message.wait(inter, send=False)
            await inter.edit_original_message(components=self.get_auto_backup_panel_components())

    async def handle_auto_toggle(self, inter: disnake.MessageInteraction, mode: str):
        await inter.response.defer(with_message=False)
        definicoes = database.obter("database/backup_configs.json")
        auto_ativo = definicoes.get("backup_auto_ativo", False)
        definicoes["backup_auto_ativo"] = not auto_ativo
        database.salvar("database/backup_configs.json", definicoes)
        if mode == "embed":
            embed, components = self.get_auto_backup_panel_components(embed_mode=True)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=self.get_auto_backup_panel_components())

    async def handle_auto_config(self, inter: disnake.MessageInteraction, mode: str):
        definicoes = database.obter("database/backup_configs.json")
        minutos_atuais = definicoes.get("backup_auto_minutos", 360)
        await inter.response.send_modal(BackupAutoConfigModal(self, minutos_atuais, mode))

    async def handle_auto_exclude(self, inter: disnake.MessageInteraction, mode: str):
        try:
            await inter.response.defer(with_message=False)
            # Compatibilidade: tenta pegar os valores do select
            valores = getattr(inter, "values", None)
            if valores is None:
                # fallback para selected_options (caso alguma versão antiga)
                valores = getattr(inter, "selected_options", [])
            if valores is None:
                valores = []
            valores = list(valores)
            definicoes = await self.bot.loop.run_in_executor(
                None, database.obter, "database/backup_configs.json"
            )
            definicoes["backup_auto_exclude"] = valores
            await self.bot.loop.run_in_executor(
                None, database.salvar, "database/backup_configs.json", definicoes
            )
            if mode == "embed":
                embed, components = self.get_auto_backup_panel_components(embed_mode=True)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.get_auto_backup_panel_components())
        except Exception as e:
            print(f"Erro ao salvar exclusões de backup: {e}")
            if mode == "embed":
                await embed_message.error(inter, "Ocorreu um erro ao salvar as configurações. Tente novamente.")
            else:
                await message.error(inter, "Ocorreu um erro ao salvar as configurações. Tente novamente.")

def setup(bot: commands.Bot):
    bot.add_cog(BackupCog(bot))

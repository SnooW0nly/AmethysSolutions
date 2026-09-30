import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .edit_info import edit_info_bot_modal
from .edit_status import edit_status
from .edit_colors import EditColorsCog, EditColorsModal
from .edit_mode import EditMode
from .edit_prefix import edit_prefix
from .edit_emojis import EditEmojisCog
from .edit_bio import EditBioCog, EditBioModal

class Personalizacao(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def personalizacao_components(self, inter: disnake.MessageInteraction) -> list:
        colors          = db.get_document("custom_colors")
        primary_hex     = colors.get("primary") or "#5c5ef0"
        primary_color   = int(primary_hex.replace("#", ""), 16)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > **Personalização**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure e personalize o status, informações, cores e o modo de exibição do bot.\n"
                    "Selecione uma seção abaixo para configurar."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Personalizacao_Select",
                        placeholder="Selecione uma seção para configurar",
                        options=[
                            disnake.SelectOption(label="Editar Status",       value="editar_status",   description="Atualize tipo e nomes do status",              emoji=emoji.edit),
                            disnake.SelectOption(label="Editar Informações",  value="editar_info",     description="Atualize nome, avatar e informações do bot",    emoji=emoji.coupon),
                            disnake.SelectOption(label="Modo de Exibição",    value="modo_exibicao",   description="Alterne entre embed e components",              emoji=emoji.embed),
                            disnake.SelectOption(label="Editar Cores",        value="editar_cores",    description="Personalize as cores do bot",                   emoji=emoji.wand),
                            disnake.SelectOption(label="Editar Emojis",       value="editar_emojis",   description="Substitua qualquer emoji do bot",               emoji=emoji.colors),
                            disnake.SelectOption(label="Prefixo",             value="editar_prefixo",  description="Altere o prefixo dos comandos do bot",          emoji=emoji.edit),
                            disnake.SelectOption(label="Biografia",           value="editar_bio",      description="Adicione um texto personalizado à bio do bot",  emoji=emoji.edit),
                        ],
                    )
                ),
                accent_colour=disnake.Colour(primary_color),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="PainelInicial",
                ),
            ),
        ]

    def personalizacao_embed(self, inter: disnake.MessageInteraction):
        colors        = db.get_document("custom_colors")
        primary_hex   = colors.get("primary") or "#5c5ef0"
        primary_color = int(primary_hex.replace("#", ""), 16)

        embed = disnake.Embed(
            title="Personalização",
            description=(
                "Configure e personalize o status, informações, cores e o modo de exibição do bot.\n"
                "Selecione uma seção abaixo para configurar."
            ),
            color=primary_color,
        )

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Personalizacao_Select",
                    placeholder="Selecione uma seção para configurar",
                    options=[
                        disnake.SelectOption(label="Editar Status",       value="editar_status",   description="Atualize tipo e nomes do status",              emoji=emoji.edit),
                        disnake.SelectOption(label="Editar Informações",  value="editar_info",     description="Atualize nome, avatar e informações do bot",    emoji=emoji.coupon),
                        disnake.SelectOption(label="Modo de Exibição",    value="modo_exibicao",   description="Alterne entre embed e components",              emoji=emoji.embed),
                        disnake.SelectOption(label="Editar Cores",        value="editar_cores",    description="Personalize as cores do bot",                   emoji=emoji.wand),
                        disnake.SelectOption(label="Editar Emojis",       value="editar_emojis",   description="Substitua qualquer emoji do bot",               emoji=emoji.colors),
                        disnake.SelectOption(label="Prefixo",             value="editar_prefixo",  description="Altere o prefixo dos comandos do bot",          emoji=emoji.edit),
                        disnake.SelectOption(label="Biografia",           value="editar_bio",      description="Adicione um texto personalizado à bio do bot",  emoji=emoji.edit),
                    ],
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="PainelInicial",
                ),
            ),
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        cid  = inter.component.custom_id

        if cid == "Painel_Personalizacao":
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = self.personalizacao_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.personalizacao_components(inter))

        elif cid == "Personalizacao_EditarCores":
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = EditColorsCog.get_panel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=EditColorsCog.get_panel_components(inter))

        elif cid == "Personalizacao_EditarCores_Modal":
            await inter.response.send_modal(EditColorsModal())

        elif cid == "Personalizacao_VisualizarCores":
            await inter.response.defer(ephemeral=True)
            if mode == "embed":
                embeds, comps = EditColorsCog.get_preview_embed(inter)
                await inter.edit_original_response(embeds=embeds, components=comps)
            else:
                comps = EditColorsCog.get_preview_components(inter)
                await inter.edit_original_response(components=comps)

        elif cid == "Personalizacao_VisualizarCores_Voltar":
            await inter.response.defer()
            if mode == "embed":
                embed, comps = EditColorsCog.get_panel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                comps = EditColorsCog.get_panel_components(inter)
                await inter.edit_original_message(components=comps)

        elif cid == "Personalizacao_ModoExibicao":
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = EditMode.mode_change_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=EditMode.mode_change_components(inter))

        elif cid == "Personalizacao_EditarInfo":
            default_name = (inter.bot.user.name if getattr(inter.bot, "user", None) and inter.bot.user else None)
            await inter.response.send_modal(edit_info_bot_modal(default_name=default_name))

        elif cid == "Personalizacao_EditarStatus":
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = edit_status.get_main_panel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=edit_status.get_main_panel_components(inter))
                
        elif cid == "Personalizacao_AddStatus":
            await inter.response.send_modal(edit_status.add_status_modal())
            
        elif cid == "TaskBack":
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = edit_status.get_main_panel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=edit_status.get_main_panel_components(inter))

        elif cid.startswith("TaskEditName_"):
            idx = int(cid.split("_")[1])
            tasks = edit_status.get_tasks_from_db()
            if 0 <= idx < len(tasks):
                await inter.response.send_modal(edit_status.edit_task_name_modal(idx, tasks[idx]["name"]))

        elif cid.startswith("TaskDel_"):
            idx = int(cid.split("_")[1])
            await edit_status.delete_task(idx, inter.bot)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = edit_status.get_main_panel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=edit_status.get_main_panel_components(inter))

        elif cid.startswith("StatusPage_") and not cid.endswith("_Display"):
            page = int(cid.split("_")[1])
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = edit_status.get_main_panel_embed(inter, page)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=edit_status.get_main_panel_components(inter, page))

        elif cid == "Personalizacao_EditarPrefixo_Modal":
            await inter.response.send_modal(edit_prefix.edit_prefix_modal())

        elif cid == "Personalizacao_EditarBio_Modal":
            user_bio = (db.get_document("custom_bio") or {}).get("user_bio", "")
            await inter.response.send_modal(EditBioModal(current_user_bio=user_bio))

        elif cid == "Personalizacao_LimparBio":
            from core.change_bio import change_bio
            db.save_document("custom_bio", {}, {"user_bio": ""})
            try:
                change_bio()
            except Exception as e:
                print(f"[cog] Erro ao limpar bio: {e}")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = EditBioCog.get_panel_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=EditBioCog.get_panel_components(inter))

        elif cid == "Painel_EditarEmojis":
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = EditEmojisCog.get_panel_embed(0)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=EditEmojisCog.get_panel_components(0))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")

        if inter.component.custom_id == "Personalizacao_Select":
            choice = inter.values[0]

            if choice == "editar_info":
                default_name = (inter.bot.user.name if getattr(inter.bot, "user", None) and inter.bot.user else None)
                await inter.response.send_modal(edit_info_bot_modal(default_name=default_name))

            elif choice == "editar_cores":
                if mode == "embed":
                    await embed_message.wait(inter, send=False)
                    embed, comps = EditColorsCog.get_panel_embed(inter)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await message.wait(inter, send=False)
                    await inter.edit_original_message(components=EditColorsCog.get_panel_components(inter))

            elif choice == "editar_emojis":
                if mode == "embed":
                    await embed_message.wait(inter, send=False)
                    embed, comps = EditEmojisCog.get_panel_embed(0)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await message.wait(inter, send=False)
                    await inter.edit_original_message(components=EditEmojisCog.get_panel_components(0))

            elif choice == "modo_exibicao":
                if mode == "embed":
                    await embed_message.wait(inter, send=False)
                    embed, comps = EditMode.mode_change_embed(inter)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await message.wait(inter, send=False)
                    await inter.edit_original_message(components=EditMode.mode_change_components(inter))

            elif choice == "editar_status":
                if mode == "embed":
                    await embed_message.wait(inter, send=False)
                    embed, comps = edit_status.get_main_panel_embed(inter)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await message.wait(inter, send=False)
                    await inter.edit_original_message(components=edit_status.get_main_panel_components(inter))

            elif choice == "editar_prefixo":
                if mode == "embed":
                    await embed_message.wait(inter, send=False)
                    embed, comps = edit_prefix.get_panel_embed(inter)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await message.wait(inter, send=False)
                    await inter.edit_original_message(components=edit_prefix.get_panel_components(inter))

            elif choice == "editar_bio":
                if mode == "embed":
                    await embed_message.wait(inter, send=False)
                    embed, comps = EditBioCog.get_panel_embed(inter)
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await message.wait(inter, send=False)
                    await inter.edit_original_message(components=EditBioCog.get_panel_components(inter))

        elif inter.component.custom_id.startswith("TaskSelect_"):
            idx = int(inter.values[0])
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = edit_status.get_task_panel_embed(inter, idx)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=edit_status.get_task_panel_components(inter, idx))

        elif inter.component.custom_id.startswith("TaskEditType_"):
            idx = int(inter.component.custom_id.split("_")[1])
            new_type = inter.values[0]
            await edit_status.change_task_type(idx, new_type, inter.bot)
            
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = edit_status.get_task_panel_embed(inter, idx)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=edit_status.get_task_panel_components(inter, idx))

        elif inter.component.custom_id.startswith("TaskEditActivity_"):
            idx = int(inter.component.custom_id.split("_")[1])
            new_activity = inter.values[0]
            await edit_status.change_task_activity(idx, new_activity, inter.bot)

            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, comps = edit_status.get_task_panel_embed(inter, idx)
                await inter.edit_original_message(content=None, embed=embed, components=comps)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=edit_status.get_task_panel_components(inter, idx))

        elif inter.component.custom_id == "Personalizacao_EditarModoExibicao":
            await inter.response.defer()
            new_mode = inter.values[0]
            db.save_document("custom_mode", {}, {"mode": new_mode})
            await inter.delete_original_message()

            if new_mode == "embed":
                embed, comps = EditMode.mode_change_embed(inter)
                await inter.followup.send(embed=embed, components=comps, ephemeral=True)
            else:
                comps = EditMode.mode_change_components(inter)
                await inter.followup.send(
                    components=comps, ephemeral=True,
                    flags=disnake.MessageFlags(is_components_v2=True),
                )
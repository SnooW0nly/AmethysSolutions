import disnake
from disnake.ext import commands
from typing import List

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

class BlacklistAddIdModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="ID do Usuário",
                placeholder="Insira o ID do usuário para bloquear",
                custom_id="user_id",
                style=disnake.TextInputStyle.short,
                min_length=17,
                max_length=20,
                required=True
            )
        ]
        super().__init__(title="Adicionar à Blacklist", custom_id="blacklist_add_id_modal", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        # Determine mode for loading state
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        user_id = inter.text_values["user_id"]
        
        if user_id.isdigit():
            blacklist_doc = db.get_document("blacklist") or {"ids": []}
            current_ids = blacklist_doc.get("ids", [])
            
            if user_id not in current_ids:
                current_ids.append(user_id)
                blacklist_doc["ids"] = current_ids
                db.save_document("blacklist", blacklist_doc)
        
        # Refresh panel
        if mode == "embed":
            panel = ConfigurarBlacklist.panel(inter)
            await inter.edit_original_message(content=None, **panel)
        else:
            panel = ConfigurarBlacklist.panel(inter)
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


class ConfigurarBlacklist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.Interaction) -> dict:
        blacklist_doc = db.get_document("blacklist") or {"ids": []}
        blocked_ids = blacklist_doc.get("ids", [])
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        # Prepare content
        title = f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Configurações > **Blacklist**"
        description = (
            f"Gerencie os usuários bloqueados de utilizar o bot.\n"
            f"Usuários na blacklist não poderão interagir com comandos ou botões.\n\n"
            f"{emoji.lock} **Usuários Bloqueados:** `{len(blocked_ids)}`"
        )
        
        # Components
        components = []
        
        # 1. User Select for Blocking
        components.append(
            disnake.ui.ActionRow(
                disnake.ui.UserSelect(
                    custom_id="blacklist_block_select",
                    placeholder="Selecione usuários para bloquear",
                    min_values=1,
                    max_values=25
                )
            )
        )
        
        # 2. String Select for Unblocking
        # Limit to 25 options (Discord limit)
        unblock_options = []
        if blocked_ids:
            for uid in blocked_ids[:25]:
                unblock_options.append(
                    disnake.SelectOption(
                        label=f"Usuário {uid}", 
                        value=uid, 
                        emoji=emoji.unlock if hasattr(emoji, "unlock") else "🔓",
                        description="Clique para desbloquear"
                    )
                )
        
        unblock_select = disnake.ui.StringSelect(
            custom_id="blacklist_unblock_select",
            placeholder="Selecione para desbloquear" if unblock_options else "Nenhum usuário bloqueado",
            options=unblock_options if unblock_options else [disnake.SelectOption(label="Vazio", value="empty")],
            disabled=not unblock_options,
            min_values=1,
            max_values=min(len(unblock_options), 25) if unblock_options else 1
        )
        components.append(disnake.ui.ActionRow(unblock_select))
        
        # 3. Buttons Row
        action_buttons = [
             disnake.ui.Button(
                style=disnake.ButtonStyle.secondary, 
                label="Adicionar por ID", 
                emoji=emoji.plus if hasattr(emoji, "plus") else "➕",
                custom_id="blacklist_add_id"
            ),
             disnake.ui.Button(
                style=disnake.ButtonStyle.danger, 
                label="Desbloquear Geral", 
                emoji=emoji.unlock if hasattr(emoji, "unlock") else "🗑️",
                custom_id="blacklist_unblock_all",
                disabled=not blocked_ids
            )
        ]

        back_button = disnake.ui.Button(
            style=disnake.ButtonStyle.secondary, 
            label="Voltar", 
            emoji=emoji.back, 
            custom_id="Painel_Configuracoes"
        )
        
        # Return format based on mode
        mode = db.get_document("custom_mode").get("mode", "embed")
        
        if mode == "embed":
            embed = disnake.Embed(
                title="Configuração de Blacklist",
                description=description.replace("# ", "").replace("-# ", ""),
                color=disnake.Colour(int(primary_color_hex.replace("#", ""), 16)) if primary_color_hex else disnake.Colour.red()
            )
            # Add buttons row to components list for embed mode
            components.append(disnake.ui.ActionRow(*action_buttons))
            components.append(disnake.ui.ActionRow(back_button))
            return {"embed": embed, "components": components}
        else:
            container_kwargs = {}
            if primary_color_hex:
                 container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            # Helper to extract components from ActionRows or use directly
            container_items = [
                disnake.ui.TextDisplay(title),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(description),
                disnake.ui.Separator() # Optional visual separator before controls
            ]
            
            # Add User Select
            container_items.append(
                disnake.ui.ActionRow(
                    disnake.ui.UserSelect(
                        custom_id="blacklist_block_select",
                        placeholder="Selecione usuários para bloquear",
                        min_values=1,
                        max_values=25
                    )
                )
            )
            
            # Add Unblock Select
            container_items.append(disnake.ui.ActionRow(unblock_select))
            
            # Add Action Buttons (Add ID, Unblock All)
            container_items.append(disnake.ui.ActionRow(*action_buttons))

            container = disnake.ui.Container(
                *container_items,
                **container_kwargs
            )
            
            # Return Container + Back Button (Outside)
            return {"components": [container, disnake.ui.ActionRow(back_button)]}

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        mode = db.get_document("custom_mode").get("mode")

        if custom_id in ["blacklist_block_select", "blacklist_unblock_select"]:
             if mode == "embed":
                 await embed_message.wait(inter, send=False)
             else:
                 await message.wait(inter, send=False)
             
             blacklist_doc = db.get_document("blacklist") or {"ids": []}
             current_ids = blacklist_doc.get("ids", [])
             
             if custom_id == "blacklist_block_select":
                 users_to_block = inter.values
                 added_count = 0
                 for uid in users_to_block:
                     if uid not in current_ids:
                         current_ids.append(uid)
                         added_count += 1
                 if added_count > 0:
                     blacklist_doc["ids"] = current_ids
                     db.save_document("blacklist", blacklist_doc)
                     
             elif custom_id == "blacklist_unblock_select":
                 users_to_unblock = inter.values
                 removed_count = 0
                 for uid in users_to_unblock:
                     if uid in current_ids:
                         current_ids.remove(uid)
                         removed_count += 1
                 if removed_count > 0:
                     blacklist_doc["ids"] = current_ids
                     db.save_document("blacklist", blacklist_doc)

             # Refresh
             await self._refresh_panel(inter)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "blacklist_add_id":
             await inter.response.send_modal(BlacklistAddIdModal())
             
        elif custom_id == "blacklist_unblock_all":
             mode = db.get_document("custom_mode").get("mode")
             if mode == "embed":
                 await embed_message.wait(inter, send=False)
             else:
                 await message.wait(inter, send=False)
             
             blacklist_doc = db.get_document("blacklist") or {"ids": []}
             # count = len(blacklist_doc.get("ids", []))
             
             blacklist_doc["ids"] = []
             db.save_document("blacklist", blacklist_doc)
             
             await self._refresh_panel(inter)

    async def _refresh_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            # await embed_message.wait(inter, send=False) # Wait animation might be redundant if we just edit
            panel = self.panel(inter)
            await inter.edit_original_message(content=None, **panel)
        else:
            # await message.wait(inter, send=False)
            panel = self.panel(inter)
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

def setup(bot: commands.Bot):
    bot.add_cog(ConfigurarBlacklist(bot))

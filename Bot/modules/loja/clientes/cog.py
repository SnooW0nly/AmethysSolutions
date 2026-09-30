import disnake
from disnake.ext import commands, tasks
from functions.database import database as db
from functions.emoji import emoji
from typing import Optional, List, Dict
import asyncio


class DecorationModal(disnake.ui.Modal):
    def __init__(self, decoration_data: Optional[dict] = None, clientes_system=None):
        self.decoration_data = decoration_data
        self.clientes_system = clientes_system
        
        components = [
            disnake.ui.Label(
                text="Selecione o Cargo",
                component=disnake.ui.RoleSelect(
                    placeholder="Escolha um cargo para a condecoração",
                    custom_id="decoration_role_select",
                    min_values=1,
                    max_values=1,
                ),
                description="Cargo que será atribuído quando o cliente atingir o valor mínimo.",
            ),
            disnake.ui.TextInput(
                label="Valor Mínimo Gasto (R$)",
                custom_id="min_spent",
                placeholder="Ex: 100.00",
                value=str(decoration_data.get("min_spent", "")) if decoration_data else "",
                max_length=30,
                required=True
            ),
            disnake.ui.TextInput(
                label="Nome da Condecoração",
                custom_id="name",
                placeholder="Ex: Cliente VIP",
                value=decoration_data.get("name", "") if decoration_data else "",
                max_length=30,
                required=True
            ),
            disnake.ui.TextInput(
                label="Descrição",
                custom_id="description",
                placeholder="Ex: Para clientes que gastaram mais de R$ 100",
                value=decoration_data.get("description", "") if decoration_data else "",
                max_length=80,
                required=False,
                style=disnake.TextInputStyle.paragraph
            )
        ]
        
        title = "Editar Condecoração" if decoration_data else "Nova Condecoração"
        super().__init__(title=title, components=components, custom_id="decoration_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        try:
            mode = db.get_document("custom_mode").get("mode")
            from functions.message import message, embed_message
            
            valores = inter.resolved_values
            selected = valores.get("decoration_role_select")
            
            # Normalizar seleção para role ID
            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            if isinstance(selected, (str, int)):
                role_id = int(selected)
            elif hasattr(selected, "id"):
                role_id = int(selected.id)
            else:
                if mode == "embed":
                    await embed_message.error(inter, "Cargo inválido!", followup=True)
                else:
                    await message.error(inter, "Cargo inválido!", followup=True)
                return
            
            # Verificar se o cargo existe
            role = inter.guild.get_role(role_id)
            if not role:
                if mode == "embed":
                    await embed_message.error(inter, "Cargo não encontrado!", followup=True)
                else:
                    await message.error(inter, "Cargo não encontrado!", followup=True)
                return
            
            min_spent = float(inter.text_values["min_spent"])
            name = inter.text_values["name"]
            description = inter.text_values.get("description", "")
            
            # Carregar dados
            data = db.get_document("loja_customers")
            if not data:
                data = {"settings": {"auto_role": True}, "decorations": {"roles": []}, "customers": {}}
            if "decorations" not in data:
                data["decorations"] = {"roles": []}
            
            decorations = data["decorations"]["roles"]
            
            if self.decoration_data:
                # Editar existente - não precisa verificar limite
                decoration = {
                    "min_spent": min_spent,
                    "role_id": role_id,
                    "name": name,
                    "description": description
                }
                for i, dec in enumerate(decorations):
                    if dec.get("role_id") == self.decoration_data.get("role_id"):
                        decorations[i] = decoration
                        break
            else:
                # Adicionar nova - verificar limite de 5
                if len(decorations) >= 5:
                    if mode == "embed":
                        await embed_message.error(inter, "Você atingiu o limite máximo de 5 condecorações!", followup=True)
                    else:
                        await message.error(inter, "Você atingiu o limite máximo de 5 condecorações!", followup=True)
                    return
                
                decoration = {
                    "min_spent": min_spent,
                    "role_id": role_id,
                    "name": name,
                    "description": description
                }
                decorations.append(decoration)
            
            # Ordenar por valor mínimo
            decorations.sort(key=lambda x: x["min_spent"])
            data["decorations"]["roles"] = decorations
            
            db.save_document("loja_customers", data)
            
            # Voltar ao painel de condecorações após salvar (padrão tickets - usar edit_message diretamente)
            if self.clientes_system:
                panel_data = self.clientes_system.panel_decorations(inter)
                if isinstance(panel_data, tuple):
                    embed, components = panel_data
                    await inter.response.edit_message(content=None, embed=embed, components=components)
                else:
                    await inter.response.edit_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            
            # Enviar feedback ephemeral após atualizar o painel
            if mode == "embed":
                await embed_message.success(inter, f"Condecoração **{name}** salva com sucesso!", followup=True)
            else:
                await message.success(inter, f"Condecoração **{name}** salva com sucesso!", followup=True)
            
        except ValueError:
            if mode == "embed":
                await embed_message.error(inter, "Valores inválidos! Verifique os dados informados.", followup=True)
            else:
                await message.error(inter, "Valores inválidos! Verifique os dados informados.", followup=True)
        except Exception as e:
            if mode == "embed":
                await embed_message.error(inter, f"Erro: {str(e)}", followup=True)
            else:
                await message.error(inter, f"Erro: {str(e)}", followup=True)


class RemoveDecorationModal(disnake.ui.Modal):
    def __init__(self, clientes_system=None, guild: disnake.Guild = None):
        self.clientes_system = clientes_system
        self.guild = guild
        
        data = db.get_document("loja_customers")
        decorations = data.get("decorations", {}).get("roles", [])
        
        # Criar opções do seletor
        options = []
        for dec in decorations:
            role_id = dec.get("role_id")
            decoration_name = dec.get("name", "Sem nome")
            min_spent = dec.get("min_spent", 0)
            
            # Tentar buscar o role se guild foi fornecido
            role_name = None
            if guild and role_id:
                try:
                    role = guild.get_role(int(role_id))
                    if role:
                        role_name = role.name
                except (ValueError, TypeError):
                    pass
            
            # Criar descrição (limitada a 100 caracteres)
            if role_name:
                description = f"{role_name} • R$ {min_spent:.2f}"
            else:
                description = f"R$ {min_spent:.2f}"
            
            # Limitar tamanho da descrição
            if len(description) > 100:
                description = description[:97] + "..."
            
            options.append(
                disnake.SelectOption(
                    label=decoration_name[:100],  # Discord limita label a 100 caracteres
                    description=description[:100],  # Discord limita description a 100 caracteres
                    value=str(role_id),
                    emoji=emoji.delete
                )
            )
        
        components = [
            disnake.ui.Label(
                text="Selecione a Condecoração para Remover",
                component=disnake.ui.StringSelect(
                    placeholder="Escolha a condecoração que deseja remover",
                    custom_id="remove_decoration_select",
                    options=options,
                    min_values=1,
                    max_values=1,
                    required=True
                ),
                description="A condecoração selecionada será removida permanentemente.",
            ),
        ]
        
        super().__init__(title="Remover Condecoração", components=components, custom_id="remove_decoration_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        from functions.message import message, embed_message
        
        # Usar wait antes de processar (padrão tickets)
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        try:
            valores = inter.resolved_values
            selected = valores.get("remove_decoration_select")
            
            # Normalizar seleção
            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            
            if not selected:
                if mode == "embed":
                    await embed_message.error(inter, "Nenhuma condecoração selecionada!", followup=True)
                else:
                    await message.error(inter, "Nenhuma condecoração selecionada!", followup=True)
                return
            
            role_id_to_remove = int(selected)
            
            data = db.get_document("loja_customers")
            decorations = data.get("decorations", {}).get("roles", [])
            
            # Encontrar e remover a condecoração
            removed = False
            removed_name = None
            for i, dec in enumerate(decorations):
                if dec.get("role_id") == role_id_to_remove:
                    removed_name = dec.get("name", "Sem nome")
                    decorations.pop(i)
                    removed = True
                    break
            
            if removed:
                data["decorations"]["roles"] = decorations
                db.save_document("loja_customers", data)
                
                # Atualizar painel de condecorações
                if self.clientes_system:
                    panel_data = self.clientes_system.panel_decorations(inter)
                    if isinstance(panel_data, tuple):
                        embed, components = panel_data
                        await inter.edit_original_message(content=None, embed=embed, components=components)
                    else:
                        await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
                
                # Enviar feedback ephemeral
                if mode == "embed":
                    await embed_message.success(inter, f"Condecoração **{removed_name}** removida com sucesso!", followup=True)
                else:
                    await message.success(inter, f"Condecoração **{removed_name}** removida com sucesso!", followup=True)
            else:
                if mode == "embed":
                    await embed_message.error(inter, "Condecoração não encontrada!", followup=True)
                else:
                    await message.error(inter, "Condecoração não encontrada!", followup=True)
            
        except ValueError:
            if mode == "embed":
                await embed_message.error(inter, "Valor inválido!", followup=True)
            else:
                await message.error(inter, "Valor inválido!", followup=True)
        except Exception as e:
            if mode == "embed":
                await embed_message.error(inter, f"Erro: {str(e)}", followup=True)
            else:
                await message.error(inter, f"Erro: {str(e)}", followup=True)


class ClientesSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.check_customer_roles.is_running():
            self.check_customer_roles.start()
    
    def cog_unload(self):
        self.check_customer_roles.cancel()
    
    @tasks.loop(minutes=5)
    async def check_customer_roles(self):
        """Verifica e atualiza cargos de clientes periodicamente"""
        try:
            await self.sync_all_customers()
        except Exception as e:
            print(f"Erro ao sincronizar clientes: {e}")
    
    @check_customer_roles.before_loop
    async def before_check_customer_roles(self):
        await self.bot.wait_until_ready()
    
    async def sync_all_customers(self):
        """Sincroniza todos os clientes com seus cargos"""
        from modules.loja.cart.purchase_manager import PurchaseManager
        
        data = db.get_document("loja_customers")
        if not data:
            data = {"settings": {"auto_role": True}, "decorations": {"roles": []}, "customers": {}}
        if "settings" not in data:
            data["settings"] = {"auto_role": True}
        if "decorations" not in data:
            data["decorations"] = {"roles": []}
        if "customers" not in data:
            data["customers"] = {}
        
        if not data.get("settings", {}).get("auto_role", True):
            return
        
        # Obter ID do servidor
        config = db.get_document("config")
        server_id = config.get("bot", {}).get("server")
        if not server_id:
            return
        
        try:
            guild = self.bot.get_guild(int(server_id))
        except (ValueError, TypeError):
            return
        
        if not guild:
            return
        
        # Obter estatísticas de todos os usuários
        all_purchases = PurchaseManager.get_all_purchases()
        user_stats = {}
        
        for purchase in all_purchases:
            user_id = purchase.get("user_id")
            if user_id:
                if user_id not in user_stats:
                    user_stats[user_id] = 0
                user_stats[user_id] += purchase.get("pricing", {}).get("final_price", 0)
        
        # Atualizar cargos baseado no valor gasto
        decorations = data.get("decorations", {}).get("roles", [])
        
        # Buscar cargo de cliente do documento cargos
        cargos_data = db.get_document("cargos")
        cargo_cliente_id = cargos_data.get("cargo_cliente")
        
        for user_id_str, total_spent in user_stats.items():
            try:
                member = guild.get_member(int(user_id_str))
                if not member:
                    continue
                
                # Adicionar cargo de cliente se configurado
                if cargo_cliente_id:
                    try:
                        cargo_cliente = guild.get_role(int(cargo_cliente_id))
                        if cargo_cliente and cargo_cliente not in member.roles:
                            await member.add_roles(cargo_cliente, reason="Cliente da loja")
                    except (ValueError, TypeError):
                        pass
                
                # Adicionar condecorações baseadas no valor gasto
                for decoration in decorations:
                    role_id = decoration.get("role_id")
                    min_spent = decoration.get("min_spent", 0)
                    
                    if role_id and total_spent >= min_spent:
                        try:
                            role = guild.get_role(int(role_id))
                            if role and role not in member.roles:
                                await member.add_roles(role, reason=f"Condecoração: gastou R$ {total_spent:.2f}")
                        except (ValueError, TypeError):
                            pass
                
                # Salvar cliente no banco
                if user_id_str not in data.get("customers", {}):
                    data.setdefault("customers", {})[user_id_str] = {
                        "total_spent": total_spent,
                        "first_purchase": None,
                        "last_purchase": None
                    }
                else:
                    data["customers"][user_id_str]["total_spent"] = total_spent
                
            except Exception as e:
                print(f"Erro ao sincronizar cliente {user_id_str}: {e}")
        
        db.save_document("loja_customers", data)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        """Quando um membro entra no servidor, restaura seus cargos de cliente"""
        if member.bot:
            return
        
        data = db.get_document("loja_customers")
        if not data.get("settings", {}).get("auto_role"):
            return
        
        user_id_str = str(member.id)
        if user_id_str not in data.get("customers", {}):
            return
        
        # Restaurar cargo de cliente
        cargos_data = db.get_document("cargos")
        cargo_cliente_id = cargos_data.get("cargo_cliente")
        if cargo_cliente_id:
            try:
                cargo_cliente = member.guild.get_role(int(cargo_cliente_id))
                if cargo_cliente:
                    await member.add_roles(cargo_cliente, reason="Cliente retornou ao servidor")
            except (ValueError, TypeError):
                pass
        
        # Restaurar condecorações
        from modules.loja.cart.purchase_manager import PurchaseManager
        user_stats = PurchaseManager.get_user_statistics(member.id)
        total_spent = user_stats.get("total_spent", 0)
        
        decorations = data.get("decorations", {}).get("roles", [])
        for decoration in decorations:
            role_id = decoration.get("role_id")
            if role_id and total_spent >= decoration.get("min_spent", 0):
                try:
                    role = member.guild.get_role(int(role_id))
                    if role:
                        await member.add_roles(role, reason=f"Condecoração restaurada")
                except (ValueError, TypeError):
                    pass
    
    def panel_decorations(self, inter: disnake.Interaction, show_edit_select: bool = False) -> dict:
        """Painel de condecorações"""
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            return self._panel_decorations_components(inter, show_edit_select)
        return self._panel_decorations_embed(inter, show_edit_select)
    
    def panel_edit_decoration_select(self, inter: disnake.Interaction) -> dict:
        """Painel intermediário para selecionar condecoração para editar"""
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            return self._panel_edit_decoration_select_components(inter)
        return self._panel_edit_decoration_select_embed(inter)
    
    def _panel_edit_decoration_select_components(self, inter: disnake.Interaction) -> dict:
        data = db.get_document("loja_customers")
        decorations = data.get("decorations", {}).get("roles", [])
        
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        # Criar opções do select
        options = []
        for dec in decorations:
            role_id = dec.get("role_id")
            decoration_name = dec.get("name", "Sem nome")
            min_spent = dec.get("min_spent", 0)
            
            # Tentar buscar o role
            role_name = None
            if inter.guild and role_id:
                try:
                    role = inter.guild.get_role(int(role_id))
                    if role:
                        role_name = role.name
                except (ValueError, TypeError):
                    pass
            
            # Criar descrição
            if role_name:
                description = f"{role_name} • R$ {min_spent:.2f}"
            else:
                description = f"R$ {min_spent:.2f}"
            
            if len(description) > 100:
                description = description[:97] + "..."
            
            options.append(
                disnake.SelectOption(
                    label=decoration_name[:100],
                    description=description[:100],
                    value=str(role_id),
                    emoji=emoji.edit
                )
            )
        
        select = disnake.ui.StringSelect(
            placeholder="Selecione a condecoração para editar",
            options=options,
            custom_id="Loja_Clientes_EditDecoration_Select",
            min_values=1,
            max_values=1
        )
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Loja > Clientes > **Editar Condecoração**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Selecione a condecoração que deseja editar."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(select),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Clientes_Decorations"
                )
            )
        ]}
    
    def _panel_edit_decoration_select_embed(self, inter: disnake.Interaction):
        data = db.get_document("loja_customers")
        decorations = data.get("decorations", {}).get("roles", [])
        
        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Editar Condecoração",
            description="Selecione a condecoração que deseja editar.",
            color=disnake.Color.from_rgb(0, 202, 164)
        )
        
        # Criar opções do select
        options = []
        for dec in decorations:
            role_id = dec.get("role_id")
            decoration_name = dec.get("name", "Sem nome")
            min_spent = dec.get("min_spent", 0)
            
            role_name = None
            if inter.guild and role_id:
                try:
                    role = inter.guild.get_role(int(role_id))
                    if role:
                        role_name = role.name
                except (ValueError, TypeError):
                    pass
            
            description = f"{role_name} • R$ {min_spent:.2f}" if role_name else f"R$ {min_spent:.2f}"
            if len(description) > 100:
                description = description[:97] + "..."
            
            options.append(
                disnake.SelectOption(
                    label=decoration_name[:100],
                    description=description[:100],
                    value=str(role_id),
                    emoji=emoji.edit
                )
            )
        
        select = disnake.ui.StringSelect(
            placeholder="Selecione a condecoração para editar",
            options=options,
            custom_id="Loja_Clientes_EditDecoration_Select",
            min_values=1,
            max_values=1
        )
        
        components = [
            disnake.ui.ActionRow(select),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Clientes_Decorations"
                )
            )
        ]
        
        return embed, components
    
    def _panel_decorations_components(self, inter: disnake.Interaction, show_edit_select: bool = False) -> dict:
        data = db.get_document("loja_customers")
        decorations = data.get("decorations", {}).get("roles", [])
        
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        # Criar lista de condecorações
        decorations_text = ""
        if decorations:
            for dec in decorations:
                role_id = dec.get("role_id")
                role = None
                if role_id:
                    try:
                        role = inter.guild.get_role(int(role_id))
                    except (ValueError, TypeError):
                        pass
                role_mention = role.mention if role else "Cargo não encontrado"
                decorations_text += (
                    f"**{dec.get('name')}**\n"
                    f"-# Cargo: {role_mention}\n"
                    f"-# Valor mínimo: R$ {dec.get('min_spent', 0):.2f}\n"
                    f"-# Descrição: {dec.get('description', 'Sem descrição')}\n\n"
                )
        else:
            decorations_text = "Nenhuma condecoração configurada."
        
        # Criar opções do select de edição se necessário
        edit_select = None
        if show_edit_select and decorations:
            options = []
            for dec in decorations:
                role_id = dec.get("role_id")
                decoration_name = dec.get("name", "Sem nome")
                min_spent = dec.get("min_spent", 0)
                
                # Tentar buscar o role
                role_name = None
                if inter.guild and role_id:
                    try:
                        role = inter.guild.get_role(int(role_id))
                        if role:
                            role_name = role.name
                    except (ValueError, TypeError):
                        pass
                
                # Criar descrição
                if role_name:
                    description = f"{role_name} • R$ {min_spent:.2f}"
                else:
                    description = f"R$ {min_spent:.2f}"
                
                if len(description) > 100:
                    description = description[:97] + "..."
                
                options.append(
                    disnake.SelectOption(
                        label=decoration_name[:100],
                        description=description[:100],
                        value=str(role_id),
                        emoji=emoji.edit
                    )
                )
            
            if options:
                edit_select = disnake.ui.StringSelect(
                    placeholder="Selecione a condecoração para editar",
                    options=options,
                    custom_id="Loja_Clientes_EditDecoration_Select",
                    min_values=1,
                    max_values=1
                )
        
        components_list = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Loja > Clientes > **Condecorações**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure cargos que serão dados automaticamente baseado no valor gasto pelo cliente."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(decorations_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.plus,
                        custom_id="Loja_Clientes_AddDecoration",
                        disabled=len(decorations) >= 5
                    ),
                    disnake.ui.Button(
                        label="Editar",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.edit,
                        custom_id="Loja_Clientes_EditDecoration",
                        disabled=len(decorations) == 0 or show_edit_select
                    ),
                    disnake.ui.Button(
                        label="Remover",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="Loja_Clientes_RemoveDecoration",
                        disabled=len(decorations) == 0
                    )
                ),
                **container_kwargs
            ),
        ]
        
        # Adicionar select de edição se necessário
        if edit_select:
            components_list.insert(1, disnake.ui.ActionRow(edit_select))
        
        components_list.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Clientes"
                ),
                disnake.ui.Button(
                    label="Sincronizar",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.reload,
                    custom_id="Loja_Clientes_Sync"
                )
            )
        )
        
        return {"components": components_list}
    
    def _panel_decorations_embed(self, inter: disnake.Interaction, show_edit_select: bool = False):
        data = db.get_document("loja_customers")
        decorations = data.get("decorations", {}).get("roles", [])
        
        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Condecorações",
            description="Configure cargos baseados em valor gasto",
            color=disnake.Color.from_rgb(0, 202, 164)
        )
        
        if decorations:
            for dec in decorations:
                role_id = dec.get("role_id")
                role = None
                if role_id:
                    try:
                        role = inter.guild.get_role(int(role_id))
                    except (ValueError, TypeError):
                        pass
                embed.add_field(
                    name=dec.get("name"),
                    value=(
                        f"Cargo: {role.mention if role else 'Não encontrado'}\n"
                        f"Mínimo: R$ {dec.get('min_spent', 0):.2f}\n"
                        f"{dec.get('description', '')}"
                    ),
                    inline=False
                )
        else:
            embed.add_field(name="Status", value="Nenhuma condecoração configurada", inline=False)
        
        # Criar select de edição se necessário
        components = []
        if show_edit_select and decorations:
            options = []
            for dec in decorations:
                role_id = dec.get("role_id")
                decoration_name = dec.get("name", "Sem nome")
                min_spent = dec.get("min_spent", 0)
                
                role_name = None
                if inter.guild and role_id:
                    try:
                        role = inter.guild.get_role(int(role_id))
                        if role:
                            role_name = role.name
                    except (ValueError, TypeError):
                        pass
                
                description = f"{role_name} • R$ {min_spent:.2f}" if role_name else f"R$ {min_spent:.2f}"
                if len(description) > 100:
                    description = description[:97] + "..."
                
                options.append(
                    disnake.SelectOption(
                        label=decoration_name[:100],
                        description=description[:100],
                        value=str(role_id),
                        emoji=emoji.edit
                    )
                )
            
            if options:
                components.append(
                    disnake.ui.ActionRow(
                        disnake.ui.StringSelect(
                            placeholder="Selecione a condecoração para editar",
                            options=options,
                            custom_id="Loja_Clientes_EditDecoration_Select",
                            min_values=1,
                            max_values=1
                        )
                    )
                )
        
        components.extend([
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Adicionar",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.plus,
                    custom_id="Loja_Clientes_AddDecoration",
                    disabled=len(decorations) >= 5
                ),
                disnake.ui.Button(
                    label="Editar",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="Loja_Clientes_EditDecoration",
                    disabled=len(decorations) == 0 or show_edit_select
                ),
                disnake.ui.Button(
                    label="Remover",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id="Loja_Clientes_RemoveDecoration",
                    disabled=len(decorations) == 0
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Clientes"
                ),
                disnake.ui.Button(
                    label="Sincronizar",
                    style=disnake.ButtonStyle.green,
                    emoji=emoji.reload,
                    custom_id="Loja_Clientes_Sync"
                )
            )
        ])
        
        return embed, components
    
    def panel_clientes(self, inter: disnake.Interaction) -> dict:
        """Painel principal de clientes"""
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            return self._panel_clientes_components(inter)
        return self._panel_clientes_embed(inter)
    
    def _panel_clientes_components(self, inter: disnake.Interaction) -> dict:
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Loja > **Configurar Clientes**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure o sistema de clientes da sua loja.\n"
                    "Defina cargos automáticos e condecorações baseadas em gastos."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Condecorações",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.star,
                        custom_id="Loja_Clientes_Decorations"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Panel"
                )
            )
        ]}
    
    def _panel_clientes_embed(self, inter: disnake.Interaction):
        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Configurar Clientes",
            description="Configure o sistema de clientes da loja",
            color=disnake.Color.from_rgb(0, 202, 164)
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Condecorações",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.star,
                    custom_id="Loja_Clientes_Decorations"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Panel"
                )
            )
        ]
        
        return embed, components
    
    async def check_user_decorations(self, user_id: int, guild: disnake.Guild):
        """Verifica e atribui condecorações para um usuário específico após compra"""
        try:
            data = db.get_document("loja_customers")
            if not data:
                data = {"settings": {"auto_role": True}, "decorations": {"roles": []}, "customers": {}}
            if "settings" not in data:
                data["settings"] = {"auto_role": True}
            if "decorations" not in data:
                data["decorations"] = {"roles": []}
            if "customers" not in data:
                data["customers"] = {}
            
            if not data.get("settings", {}).get("auto_role", True):
                return
            
            from modules.loja.cart.purchase_manager import PurchaseManager
            user_stats = PurchaseManager.get_user_statistics(user_id)
            total_spent = user_stats.get("total_spent", 0)
            
            member = guild.get_member(user_id)
            if not member:
                return
            
            decorations = data.get("decorations", {}).get("roles", [])
            
            # Buscar cargo de cliente do documento cargos
            cargos_data = db.get_document("cargos")
            cargo_cliente_id = cargos_data.get("cargo_cliente")
            
            # Adicionar cargo de cliente se configurado
            if cargo_cliente_id:
                try:
                    cargo_cliente = guild.get_role(int(cargo_cliente_id))
                    if cargo_cliente and cargo_cliente not in member.roles:
                        await member.add_roles(cargo_cliente, reason="Cliente da loja")
                except (ValueError, TypeError):
                    pass
            
            # Verificar e atribuir condecorações baseadas no valor gasto
            for decoration in decorations:
                role_id = decoration.get("role_id")
                min_spent = decoration.get("min_spent", 0)
                
                if role_id and total_spent >= min_spent:
                    try:
                        role = guild.get_role(int(role_id))
                        if role and role not in member.roles:
                            await member.add_roles(role, reason=f"Condecoração: gastou R$ {total_spent:.2f}")
                    except (ValueError, TypeError):
                        pass
            
            # Atualizar dados do cliente
            user_id_str = str(user_id)
            if user_id_str not in data.get("customers", {}):
                data.setdefault("customers", {})[user_id_str] = {
                    "total_spent": total_spent,
                    "first_purchase": user_stats.get("first_purchase"),
                    "last_purchase": user_stats.get("last_purchase")
                }
            else:
                data["customers"][user_id_str]["total_spent"] = total_spent
                if user_stats.get("first_purchase"):
                    if not data["customers"][user_id_str].get("first_purchase"):
                        data["customers"][user_id_str]["first_purchase"] = user_stats.get("first_purchase")
                if user_stats.get("last_purchase"):
                    data["customers"][user_id_str]["last_purchase"] = user_stats.get("last_purchase")
            
            db.save_document("loja_customers", data)
            
        except Exception as e:
            print(f"Erro ao verificar condecorações do usuário {user_id}: {e}")
    
    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Clientes":
            mode = db.get_document("custom_mode").get("mode")
            from functions.message import message, embed_message
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            
            panel_data = self.panel_clientes(inter)
            if isinstance(panel_data, tuple):
                embed, components = panel_data
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_Clientes_Decorations":
            mode = db.get_document("custom_mode").get("mode")
            from functions.message import message, embed_message
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            
            panel_data = self.panel_decorations(inter)
            if isinstance(panel_data, tuple):
                embed, components = panel_data
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_Clientes_AddDecoration":
            # Verificar limite antes de abrir o modal
            data = db.get_document("loja_customers")
            decorations = data.get("decorations", {}).get("roles", [])
            
            if len(decorations) >= 5:
                mode = db.get_document("custom_mode").get("mode")
                from functions.message import message, embed_message
                if mode == "embed":
                    await embed_message.error(inter, "Você atingiu o limite máximo de 5 condecorações!", send=True)
                else:
                    await message.error(inter, "Você atingiu o limite máximo de 5 condecorações!", send=True)
                return
            
            await inter.response.send_modal(DecorationModal(clientes_system=self))
        
        elif inter.component.custom_id == "Loja_Clientes_EditDecoration":
            data = db.get_document("loja_customers")
            decorations = data.get("decorations", {}).get("roles", [])
            
            if not decorations:
                mode = db.get_document("custom_mode").get("mode")
                from functions.message import message, embed_message
                if mode == "embed":
                    await embed_message.error(inter, "Nenhuma condecoração para editar!", send=True)
                else:
                    await message.error(inter, "Nenhuma condecoração para editar!", send=True)
                return
            
            # Atualizar painel mostrando o select de edição
            mode = db.get_document("custom_mode").get("mode")
            from functions.message import message, embed_message
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            
            panel_data = self.panel_edit_decoration_select(inter)
            if isinstance(panel_data, tuple):
                embed, components = panel_data
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_Clientes_RemoveDecoration":
            data = db.get_document("loja_customers")
            decorations = data.get("decorations", {}).get("roles", [])
            
            if not decorations:
                mode = db.get_document("custom_mode").get("mode")
                from functions.message import message, embed_message
                if mode == "embed":
                    await embed_message.error(inter, "Nenhuma condecoração para remover!", send=True)
                else:
                    await message.error(inter, "Nenhuma condecoração para remover!", send=True)
                return
            
            await inter.response.send_modal(RemoveDecorationModal(clientes_system=self, guild=inter.guild))
        
        elif inter.component.custom_id == "Loja_Clientes_Sync":
            await inter.response.defer()
            
            try:
                config = db.get_document("config")
                server_id = config.get("bot", {}).get("server")
                
                if not server_id:
                    await inter.followup.send(
                        f"{emoji.wrong} Servidor não configurado!",
                        ephemeral=True
                    )
                    return
                
                guild = self.bot.get_guild(int(server_id))
                if not guild:
                    await inter.followup.send(
                        f"{emoji.wrong} Servidor não encontrado!",
                        ephemeral=True
                    )
                    return
                
                await self.sync_all_customers()
                await inter.followup.send(
                    f"{emoji.correct} Sincronização concluída com sucesso!",
                    ephemeral=True
                )
            except Exception as e:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao sincronizar: {str(e)}",
                    ephemeral=True
                )
    
    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Clientes_EditDecoration_Select":
            role_id = int(inter.values[0])
            
            # Buscar dados da condecoração
            data = db.get_document("loja_customers")
            decorations = data.get("decorations", {}).get("roles", [])
            
            decoration_data = None
            for dec in decorations:
                if dec.get("role_id") == role_id:
                    decoration_data = dec.copy()
                    break
            
            if not decoration_data:
                await inter.response.send_message(
                    f"{emoji.wrong} Condecoração não encontrada!",
                    ephemeral=True
                )
                return
            
            # Abrir modal de edição com os dados
            await inter.response.send_modal(DecorationModal(
                decoration_data=decoration_data, 
                clientes_system=self
            ))
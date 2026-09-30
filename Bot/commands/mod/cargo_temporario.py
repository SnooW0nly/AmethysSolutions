import disnake
from disnake.ext import commands
import time

from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms
from functions.utils import utils


# Modais de tempo (adicionar/sobrepor dias)
class CargoTempModal(disnake.ui.Modal):
    def __init__(self, action, membro, cargo_id):
        self.action = action
        self.membro = membro
        self.cargo_id = cargo_id

        titles = {"add": "Adicionar Tempo", "set": "Sobrepor Tempo", "sub": "Remover Dias"}
        labels = {"add": "Dias a adicionar", "set": "Novos dias de duração", "sub": "Dias a remover"}

        super().__init__(title=titles[action], components=[
            disnake.ui.TextInput(
                label=labels[action],
                placeholder="Ex: 7",
                custom_id="dias",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=3,
            )
        ])

    async def callback(self, inter: disnake.ModalInteraction):
        dias_str = inter.text_values["dias"]
        if not dias_str.isdigit():
            return await inter.response.send_message(f"{emoji.wrong} Digite um número válido!", ephemeral=True)

        dias = int(dias_str)
        data = db.get_document("cargos_temporarios")
        user_id = str(self.membro.id)
        agora = time.time()

        for entry in data["users"][user_id]:
            if entry["role_id"] == self.cargo_id:
                if self.action == "add":
                    entry["expiration"] = max(entry["expiration"], agora) + (dias * 86400)
                elif self.action == "set":
                    entry["expiration"] = agora + (dias * 86400)
                elif self.action == "sub":
                    entry["expiration"] = max(agora, entry["expiration"] - (dias * 86400))
                break

        db.save_document("cargos_temporarios", data)

        cog = inter.bot.get_cog("CargoTemporarioCommand")
        color = int(db.get_document("custom_colors").get("primary", "00caa4").replace("#", ""), 16)
        roles_data = data["users"][user_id]
        components = cog.montar_components(inter.guild, self.membro, roles_data, self.cargo_id, color)
        await inter.response.edit_message(components=components, content=None)


# Modal para trocar o cargo
class TrocarCargoModal(disnake.ui.Modal):
    def __init__(self, membro, cargo_id_atual):
        self.membro = membro
        self.cargo_id_atual = cargo_id_atual

        super().__init__(title="Trocar Cargo", components=[
            disnake.ui.TextInput(
                label="ID do novo cargo",
                placeholder="Ex: 123456789012345678",
                custom_id="cargo_id",
                style=disnake.TextInputStyle.short,
                min_length=17,
                max_length=20,
            )
        ])

    async def callback(self, inter: disnake.ModalInteraction):
        cargo_id_str = inter.text_values["cargo_id"]
        if not cargo_id_str.isdigit():
            return await inter.response.send_message(f"{emoji.wrong} ID inválido!", ephemeral=True)

        novo_cargo_id = int(cargo_id_str)
        novo_cargo = inter.guild.get_role(novo_cargo_id)
        if not novo_cargo:
            return await inter.response.send_message(f"{emoji.wrong} Cargo não encontrado neste servidor!", ephemeral=True)

        data = db.get_document("cargos_temporarios")
        user_id = str(self.membro.id)

        entry_atual = None
        for entry in data["users"][user_id]:
            if entry["role_id"] == self.cargo_id_atual:
                entry_atual = entry
                break

        if not entry_atual:
            return await inter.response.send_message(f"{emoji.wrong} Cargo não encontrado no banco.", ephemeral=True)

        # Verifica se o novo cargo já existe para o usuário
        for entry in data["users"][user_id]:
            if entry["role_id"] == novo_cargo_id:
                return await inter.response.send_message(f"{emoji.wrong} O usuário já possui esse cargo temporário!", ephemeral=True)

        # Troca o cargo no banco mantendo a expiração
        entry_atual["role_id"] = novo_cargo_id
        db.save_document("cargos_temporarios", data)

        # Remove o cargo antigo e adiciona o novo
        cargo_antigo = inter.guild.get_role(self.cargo_id_atual)
        try:
            if cargo_antigo:
                await self.membro.remove_roles(cargo_antigo)
            await self.membro.add_roles(novo_cargo)
        except Exception:
            pass

        cog = inter.bot.get_cog("CargoTemporarioCommand")
        color = int(db.get_document("custom_colors").get("primary", "00caa4").replace("#", ""), 16)
        roles_data = data["users"][user_id]
        components = cog.montar_components(inter.guild, self.membro, roles_data, novo_cargo_id, color)
        await inter.response.edit_message(components=components, content=None)


class CargoTemporarioCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def format_time(self, timestamp):
        remaining = timestamp - time.time()
        if remaining <= 0:
            return "Expirado"
        days = int(remaining // 86400)
        hours = int((remaining % 86400) // 3600)
        return f"{days}d {hours}h restantes"

    def montar_components(self, guild, membro, roles_data, selected_id, color):
        info_text = f"# {emoji.role} Gerenciar Cargos\n-# Membro: {membro.mention}\n\n"
        for r in roles_data:
            role_obj = guild.get_role(r["role_id"])
            role_name = role_obj.name if role_obj else "Cargo Desconhecido"
            status = self.format_time(r["expiration"])
            marker = " 🔘" if selected_id == r["role_id"] else ""
            info_text += f"{emoji.star} **{role_name}**{marker}\n└ {emoji.time} `{status}`\n"

        mid = membro.id
        sid = selected_id or 0

        row1 = disnake.ui.ActionRow(
            disnake.ui.Button(label="➕ Adicionar Dias", style=disnake.ButtonStyle.gray,
                              custom_id=f"ct_add_{mid}_{sid}", disabled=not selected_id),
            disnake.ui.Button(label="🔁 Sobrepor Tempo", style=disnake.ButtonStyle.gray,
                              custom_id=f"ct_set_{mid}_{sid}", disabled=not selected_id),
            disnake.ui.Button(label="➖ Remover Dias", style=disnake.ButtonStyle.gray,
                              custom_id=f"ct_sub_{mid}_{sid}", disabled=not selected_id),
        )
        row2 = disnake.ui.ActionRow(
            disnake.ui.Button(label="🔄 Trocar Cargo", style=disnake.ButtonStyle.blurple,
                              custom_id=f"ct_swp_{mid}_{sid}", disabled=not selected_id),
            disnake.ui.Button(label="🗑️ Remover Cargo", style=disnake.ButtonStyle.red,
                              custom_id=f"ct_del_{mid}_{sid}", disabled=not selected_id),
        )

        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(info_text),
                accent_colour=disnake.Colour(color),
            ),
            row1,
            row2,
        ]

        if len(roles_data) > 1:
            options = [
                disnake.SelectOption(
                    label=guild.get_role(r["role_id"]).name if guild.get_role(r["role_id"]) else "Desconhecido",
                    value=str(r["role_id"]),
                    default=(r["role_id"] == selected_id),
                )
                for r in roles_data
            ]
            components.append(disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Selecione o cargo para editar...",
                    options=options,
                    custom_id=f"ct_sel_{mid}",
                )
            ))

        return components

    @commands.Cog.listener("on_message_interaction")
    async def on_ct_interaction(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id

        if cid.startswith("ct_sel_"):
            parts = cid.split("_")
            membro_id = int(parts[2])
            selected_id = int(inter.values[0])

            membro = inter.guild.get_member(membro_id)
            if not membro:
                return await inter.response.send_message(f"{emoji.wrong} Membro não encontrado.", ephemeral=True)

            await inter.response.defer()
            data = db.get_document("cargos_temporarios")
            roles_data = data.get("users", {}).get(str(membro_id), [])
            color = int(db.get_document("custom_colors").get("primary", "00caa4").replace("#", ""), 16)
            components = self.montar_components(inter.guild, membro, roles_data, selected_id, color)
            await inter.edit_original_response(components=components, content=None)
            return

        actions = ("ct_add_", "ct_set_", "ct_sub_", "ct_del_", "ct_swp_")
        if not any(cid.startswith(a) for a in actions):
            return

        parts = cid.split("_")
        action = parts[1]       # add / set / sub / del / swp
        membro_id = int(parts[2])
        cargo_id = int(parts[3])

        membro = inter.guild.get_member(membro_id)
        if not membro:
            return await inter.response.send_message(f"{emoji.wrong} Membro não encontrado.", ephemeral=True)

        if action in ("add", "set", "sub"):
            return await inter.response.send_modal(CargoTempModal(action, membro, cargo_id))

        if action == "swp":
            return await inter.response.send_modal(TrocarCargoModal(membro, cargo_id))

        if action == "del":
            await inter.response.defer()
            data = db.get_document("cargos_temporarios")
            user_id = str(membro_id)

            data["users"][user_id] = [r for r in data["users"][user_id] if r["role_id"] != cargo_id]
            if not data["users"][user_id]:
                del data["users"][user_id]
            db.save_document("cargos_temporarios", data)

            role = inter.guild.get_role(cargo_id)
            if role:
                try:
                    await membro.remove_roles(role)
                except Exception:
                    pass

            color = int(db.get_document("custom_colors").get("primary", "00caa4").replace("#", ""), 16)
            roles_data = data.get("users", {}).get(user_id, [])

            if not roles_data:
                sem_cargo = [disnake.ui.Container(disnake.ui.TextDisplay(
                    f"{emoji.wrong} Este usuário não possui mais cargos temporários."
                ))]
                await inter.edit_original_response(components=sem_cargo, content=None)
            else:
                selected_id = roles_data[0]["role_id"] if len(roles_data) == 1 else None
                components = self.montar_components(inter.guild, membro, roles_data, selected_id, color)
                await inter.edit_original_response(components=components, content=None)

    @commands.slash_command(
        name="cargo_temporario",
        description="Gerencia cargos temporários",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(administrator=True),
    )
    async def cargo_temporario(self, inter):
        pass

    @cargo_temporario.sub_command(name="gerenciar", description="Abre o painel de edição de cargos de um membro")
    async def gerenciar(self, inter, membro: disnake.Member):
        if not await perms.check(inter.author.id):
            return await inter.response.send_message(f"{emoji.wrong} Sem permissão!", ephemeral=True)

        await inter.response.defer(ephemeral=True)

        data = db.get_document("cargos_temporarios")
        user_id = str(membro.id)

        if user_id not in data.get("users", {}):
            return await inter.edit_original_response(
                content=f"{emoji.wrong} Este usuário não possui cargos temporários."
            )

        roles_data = data["users"][user_id]
        color = int(db.get_document("custom_colors").get("primary", "00caa4").replace("#", ""), 16)
        selected_id = roles_data[0]["role_id"] if len(roles_data) == 1 else None
        components = self.montar_components(inter.guild, membro, roles_data, selected_id, color)
        await inter.edit_original_response(components=components, content=None)

    @cargo_temporario.sub_command(name="adicionar", description="Adiciona um cargo temporário a um usuário")
    async def adicionar(
        self,
        inter: disnake.ApplicationCommandInteraction,
        membro: disnake.Member = commands.Param(description="Membro para receber o cargo"),
        cargo: disnake.Role = commands.Param(description="Cargo a ser adicionado"),
        dias: int = commands.Param(description="Duração em dias", min_value=1, max_value=365),
    ):
        await inter.response.defer(ephemeral=True)

        if not await perms.check(inter.author.id):
            return await inter.followup.send(f"{emoji.wrong} Você não tem permissão!", ephemeral=True)

        expiration = time.time() + (dias * 86400)
        data = db.get_document("cargos_temporarios")
        if "users" not in data:
            data["users"] = {}

        user_id = str(membro.id)
        if user_id not in data["users"]:
            data["users"][user_id] = []

        for entry in data["users"][user_id]:
            if entry["role_id"] == cargo.id:
                entry["expiration"] = expiration
                db.save_document("cargos_temporarios", data)
                return await inter.followup.send(
                    f"{emoji.correct} Tempo do cargo {cargo.mention} atualizado para {dias} dias.", ephemeral=True
                )

        data["users"][user_id].append({"role_id": cargo.id, "expiration": expiration})
        db.save_document("cargos_temporarios", data)

        try:
            await membro.add_roles(cargo)
            await inter.followup.send(
                f"{emoji.correct} Cargo {cargo.mention} adicionado a {membro.mention} por {dias} dias.", ephemeral=True
            )
        except disnake.Forbidden:
            await inter.followup.send(f"{emoji.wrong} Sem permissão para adicionar o cargo.", ephemeral=True)
        except disnake.HTTPException:
            await inter.followup.send(f"{emoji.wrong} Erro ao adicionar o cargo.", ephemeral=True)

    @cargo_temporario.sub_command(name="remover", description="Remove cargos temporários de um usuário")
    async def remover(
        self,
        inter: disnake.ApplicationCommandInteraction,
        membro: disnake.Member = commands.Param(description="Membro para remover o cargo"),
        cargo: disnake.Role = commands.Param(default=None, description="Cargo a remover (se vazio, remove todos)"),
    ):
        await inter.response.defer(ephemeral=True)

        if not await perms.check(inter.author.id):
            return await inter.followup.send(f"{emoji.wrong} Você não tem permissão!", ephemeral=True)

        data = db.get_document("cargos_temporarios")
        if "users" not in data or str(membro.id) not in data["users"]:
            return await inter.followup.send(f"{emoji.wrong} O usuário não possui cargos temporários.", ephemeral=True)

        user_id = str(membro.id)
        roles_data = data["users"][user_id]

        if cargo:
            new_roles = [r for r in roles_data if r["role_id"] != cargo.id]
            if new_roles:
                data["users"][user_id] = new_roles
            else:
                del data["users"][user_id]
            db.save_document("cargos_temporarios", data)
            try:
                await membro.remove_roles(cargo)
                await inter.followup.send(f"{emoji.correct} Cargo {cargo.mention} removido de {membro.mention}.", ephemeral=True)
            except disnake.Forbidden:
                await inter.followup.send(f"{emoji.wrong} Sem permissão para remover o cargo.", ephemeral=True)
        else:
            roles_to_remove = [inter.guild.get_role(r["role_id"]) for r in roles_data if inter.guild.get_role(r["role_id"])]
            del data["users"][user_id]
            db.save_document("cargos_temporarios", data)
            try:
                if roles_to_remove:
                    await membro.remove_roles(*roles_to_remove)
                await inter.followup.send(f"{emoji.correct} Todos os cargos removidos de {membro.mention}.", ephemeral=True)
            except disnake.Forbidden:
                await inter.followup.send(f"{emoji.wrong} Sem permissão para remover alguns cargos.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(CargoTemporarioCommand(bot))
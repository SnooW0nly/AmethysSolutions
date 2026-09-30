import asyncio
import disnake
from disnake.ext import tasks
from functions.database import database as db
from modules.giveaways.preferences.requirements import check_giveaway_requirements
from .logger_giveaways import log_giveaway_event
from functions.emoji import emoji
from modules.giveaways.container_utils import ContainerUtils

@tasks.loop(minutes=5)
async def monitor_giveaways_task(bot: disnake.Client):
    await bot.wait_until_ready()
    
    try:
        config = db.obter("database/giveaways/giveaways_data.json")
    except Exception as e:
        print(f"Error reading giveaways data: {e}")
        return

    if not isinstance(config, dict):
        return

    monitored_giveaways = {gid: gdata for gid, gdata in config.items() if gdata.get("monitor_enabled")}

    for giveaway_id, giveaway_data in monitored_giveaways.items():
        if not giveaway_data.get("requirements"):
            continue

        for task in giveaway_data.get("tasks", []):
            if not task.get("participants") or not task.get("channel_id"):
                continue

            try:
                channel = bot.get_channel(task["channel_id"]) or await bot.fetch_channel(task["channel_id"])
                guild = channel.guild
            except (disnake.NotFound, disnake.Forbidden):
                continue
            
            if not guild:
                continue

            participants_to_remove = []
            current_participants = list(task["participants"])

            for member_id in current_participants:
                try:
                    member = guild.get_member(member_id) or await guild.fetch_member(member_id)
                except disnake.NotFound:
                    participants_to_remove.append(member_id)
                    continue
                
                success, reason = await check_giveaway_requirements(member, giveaway_id, bot)
                if not success:
                    participants_to_remove.append(member_id)
                    await log_giveaway_event(
                        bot=bot,
                        giveaway_id=giveaway_id,
                        title="Sorteios - Monitor",
                        lines=[
                            f"{emoji.giveaway} **Sorteio:** {giveaway_data.get('name')}",
                            f"{emoji.member} **Membro:** {member.mention} (`{member.id}`)",
                            f"{emoji.wrong} **Ação:** Removido pelo monitor",
                            f"{emoji.edit} **Motivo:** {reason}"
                        ]
                    )
                    
                    try:
                        dm_message = (
                            f"Olá! Você foi removido do sorteio **{giveaway_data.get('name')}** no servidor **{guild.name}**.\n\n"
                            f"**Motivo:** {reason.replace(f'{emoji.wrong} ', '')}\n\n"
                            "Você pode tentar entrar novamente assim que cumprir todos os requisitos."
                        )
                        await member.send(dm_message)
                    except disnake.Forbidden:
                        pass # DMs fechadas, ignora silenciosamente.
                    except Exception as e:
                        print(f"[Monitor] Erro inesperado ao enviar DM para {member.display_name} ({member.id}): {e}")

                await asyncio.sleep(1)

            if participants_to_remove:
                live_config = db.obter("database/giveaways/giveaways_data.json")
                live_giveaway = live_config.get(giveaway_id, {})
                live_task = next((t for t in live_giveaway.get("tasks", []) if t.get("id") == task.get("id")), None)
                
                if live_task and 'participants' in live_task:
                    live_task['participants'] = [p for p in live_task['participants'] if p not in participants_to_remove]
                    db.salvar("database/giveaways/giveaways_data.json", live_config)

                    try:
                        message_to_edit = await channel.fetch_message(live_task["message_id"])

                        button_data = live_giveaway.get("button", {})
                        base_label = button_data.get("label", "Participar")
                        participant_count = len(live_task.get("participants", []))
                        new_label = f"{base_label} ({participant_count})"

                        style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}

                        button_kwargs = {
                            "label": new_label,
                            "style": style_map.get(button_data.get("style", "green")),
                            "custom_id": f"Giveaway_Participate_{giveaway_id}_{task['id']}"
                        }
                        if button_data.get("emoji"):
                            button_kwargs["emoji"] = button_data.get("emoji")

                        updated_button = disnake.ui.Button(**button_kwargs)

                        style = live_giveaway.get("message_style", "embed")
                        if style == "container":
                            data = live_giveaway.get("container", {})
                            container = ContainerUtils.montar_container(
                                conteudo=data.get("content"),
                                imagem_url=data.get("image_url"),
                                cor_hex=data.get("color"),
                                thumbnail_url=data.get("thumbnail_url")
                            )
                            action_row = disnake.ui.ActionRow(updated_button)
                            await message_to_edit.edit(components=[container, action_row])
                        else:
                            view = disnake.ui.View(timeout=None)
                            view.add_item(updated_button)
                            await message_to_edit.edit(view=view)
                    except (disnake.NotFound, disnake.Forbidden, KeyError) as e:
                        pass # Se a mensagem não puder ser editada, ignora silenciosamente

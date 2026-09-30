import asyncio
import disnake
from disnake.ext import tasks
import datetime
import random
from functions.database import database as db
from functions.emoji import emoji
from .logger_giveaways import log_giveaway_event
from functions.utils import utils

async def select_winners(bot: disnake.Client, task: dict, giveaway_data: dict, all_previous_winners: list[int]) -> list[int]:
    winners = []
    guild = bot.get_guild(task.get("guild_id"))
    if not guild:
        return []

    if giveaway_data.get("mode") == "falso":
        user_ids = set(giveaway_data.get("winner_users", []))
        role_ids = giveaway_data.get("winner_roles", [])
        
        for role_id in role_ids:
            role = guild.get_role(role_id)
            if role:
                for member in role.members:
                    user_ids.add(member.id)
        
        winners = list(user_ids)

    elif giveaway_data.get("mode") == "real":
        min_participants = task.get("min_participants", 0)
        if len(task.get("participants", [])) < min_participants:
            return []

        eligible_participants_ids = [p for p in task.get("participants", []) if p not in all_previous_winners]
        
        if not eligible_participants_ids:
            return []

        bonus_roles = giveaway_data.get("bonus_roles", {})
        weighted_participants = []

        for user_id in eligible_participants_ids:
            member = guild.get_member(user_id)
            if not member:
                try:
                    member = await guild.fetch_member(user_id)
                except (disnake.NotFound, disnake.Forbidden):
                    member = None

            entries = 1
            if member and bonus_roles:
                member_role_ids = {str(r.id) for r in member.roles}
                for role_id, bonus_entries in bonus_roles.items():
                    if role_id in member_role_ids:
                        entries += int(bonus_entries)
            
            weighted_participants.extend([user_id] * entries)
        
        if not weighted_participants:
            return []

        max_winners = task.get("max_winners", 1)
        
        unique_participants_count = len(set(weighted_participants))
        if max_winners > unique_participants_count:
            max_winners = unique_participants_count

        drawn_winners = set()
        if not weighted_participants:
            return []
            
        while len(drawn_winners) < max_winners:
            winner = random.choice(weighted_participants)
            drawn_winners.add(winner)
            weighted_participants = [p for p in weighted_participants if p != winner]
            if not weighted_participants:
                break
            
        winners = list(drawn_winners)

    return winners

async def announce_winners(bot: disnake.Client, original_message: disnake.Message, task: dict, giveaway_data: dict, winners: list[int], is_reroll: bool = False):
    try:
        channel = bot.get_channel(task["channel_id"]) or await bot.fetch_channel(task["channel_id"])
        # original_message = await channel.fetch_message(task["message_id"]) # This line is now handled in process_giveaway_roll
    except (disnake.NotFound, disnake.Forbidden):
        return

    winner_mentions = [f"<@{winner_id}>" for winner_id in winners]
    
    if not winners:
        if giveaway_data.get("mode") == "real":
            if len(task.get("participants", [])) < task.get("min_participants", 0):
                announcement_content = f"O sorteio **{giveaway_data.get('name')}** foi cancelado por não atingir o mínimo de **{task.get('min_participants', 0)}** participantes."
            else:
                announcement_content = f"Não há mais participantes elegíveis para sortear em **{giveaway_data.get('name')}**."
        else: # falso
            announcement_content = f"Não foram definidos ganhadores para o sorteio falso **{giveaway_data.get('name')}**."
    else:
        if len(winners) == 1:
            pronoun = "você"
            verb = "ganhou"
        else:
            pronoun = "vocês"
            verb = "ganharam"
        
        announcement_content = f"Parabéns {', '.join(winner_mentions)}, {pronoun} {verb} o sorteio **{giveaway_data.get('name')}**!"

    # Send as a new message, replying to the original
    await original_message.reply(f"{announcement_content}")
    
    # Não remove os botões - o handler de participação verifica se task["rolled"] == True
    # e mostra mensagem de sorteio encerrado


async def deliver_prizes(bot: disnake.Client, giveaway_data: dict, winners: list[int], guild: disnake.Guild, message_url: str):
    prize_info = giveaway_data.get("prize", {})
    prize_type = prize_info.get("type", "none")
    dm_notify = prize_info.get("dm_notify", True)

    # Se o tipo é "none" e o aviso na DM está desativado, não envia nada
    if prize_type == "none" and not dm_notify:
        return

    for winner_id in winners:
        try:
            member = bot.get_user(winner_id) or await bot.fetch_user(winner_id)
            
            view = disnake.ui.View()
            view.add_item(disnake.ui.Button(label="Ir para o Sorteio", url=message_url))

            # Se o tipo é "content", sempre envia o conteúdo (independente de dm_notify)
            if prize_type == "content" and prize_info.get("content"):
                message = (
                    f"Parabéns por ganhar o sorteio **{giveaway_data.get('name')}** no servidor **{guild.name}**!\n\n"
                    f"**Seu prêmio:**\n```{prize_info.get('content')}```"
                )
                await member.send(message, view=view)
            # Se o tipo é "none" e dm_notify está ativado, envia apenas o aviso
            elif prize_type == "none" and dm_notify:
                message = f"Parabéns! Você ganhou o sorteio **{giveaway_data.get('name')}** no servidor **{guild.name}**."
                await member.send(message, view=view)
        except (disnake.NotFound, disnake.Forbidden):
            # User not found or DMs are closed
            pass
        except Exception as e:
            print(f"Error sending prize DM to {winner_id}: {e}")

async def process_giveaway_roll(bot: disnake.Client, giveaway_id: str, task_id: str, is_reroll: bool = False):
    config = db.obter("database/giveaways/giveaways_data.json")
    giveaway_data = config.get(giveaway_id, {})
    task = next((t for t in giveaway_data.get("tasks", []) if t.get("id") == task_id), None)

    if not giveaway_data or not task:
        return

    guild = None
    message_url = ""
    original_message = None
    
    try:
        channel = bot.get_channel(task['channel_id'])
        if not channel:
            raise ValueError(f"Channel {task['channel_id']} not found.")
        
        guild = channel.guild
        task['guild_id'] = guild.id

        if task.get("message_id"):
            message_url = f"https://discord.com/channels/{guild.id}/{channel.id}/{task['message_id']}"
            original_message = await channel.fetch_message(task['message_id'])
        else:
            raise ValueError("Message ID not found in task.")

    except (disnake.NotFound, disnake.Forbidden, ValueError) as e:
        await log_giveaway_event(
            bot=bot,
            giveaway_id=giveaway_id,
            title="Sorteios - ERRO AO SORTEAR",
            lines=[
                f"{emoji.giveaway} **Sorteio:** {giveaway_data.get('name')}",
                f"{emoji.settings} **Tarefa:** {task.get('name')}",
                f"{emoji.wrong} **Erro:** A mensagem original do sorteio não foi encontrada ou não tenho permissão para acessá-la no canal <#{task.get('channel_id')}>.",
                f"O sorteio não foi finalizado e a tarefa foi marcada com erro."
            ]
        )
        task['status'] = 'error'
        db.salvar("database/giveaways/giveaways_data.json", config)
        return

    if "draws" not in task:
        task["draws"] = []

    all_previous_winners = [winner for draw in task["draws"] for winner in draw["winners"]]
    
    winners = await select_winners(bot, task, giveaway_data, all_previous_winners)
    
    await announce_winners(bot, original_message, task, giveaway_data, winners, is_reroll)
    
    if winners:
        await deliver_prizes(bot, giveaway_data, winners, guild, message_url)

    new_draw = {
        "draw_id": utils.gerar_id(8),
        "winners": winners,
        "timestamp": datetime.datetime.now().timestamp()
    }
    task["draws"].append(new_draw)
    
    task["status"] = "finished"
    task["rolled"] = True  # Marca o sorteio como encerrado para bloquear novas participações
    db.salvar("database/giveaways/giveaways_data.json", config)

    await log_giveaway_event(
        bot=bot,
        giveaway_id=giveaway_id,
        title=f"Sorteios - {'Novo Sorteio' if is_reroll else 'Sorteio Finalizado'}",
        lines=[
            f"{emoji.giveaway} **Sorteio:** {giveaway_data.get('name')}",
            f"{emoji.settings} **Tarefa:** {task.get('name')}",
            f"{emoji.flag} **Ganhadores:** {f'`{len(winners)}`' if winners else '`Nenhum`'}",
            f"{emoji.textc} **ID do Sorteio:** `{new_draw['draw_id']}`"
        ]
    )
    
@tasks.loop(seconds=15)
async def roll_giveaways_task(bot: disnake.Client):
    await bot.wait_until_ready()
    config = db.obter("database/giveaways/giveaways_data.json")
    if not isinstance(config, dict):
        return

    current_time = datetime.datetime.now().timestamp()
    
    for giveaway_id, giveaway_data in config.items():
        for task in giveaway_data.get("tasks", []):
            if task.get("status") == "running" and task.get("end_time") and current_time >= task["end_time"]:
                await process_giveaway_roll(bot, giveaway_id, task["id"], is_reroll=False)
                await asyncio.sleep(2)

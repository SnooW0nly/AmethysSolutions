import disnake
from disnake.ext import commands, tasks
import datetime
import time
import traceback

from functions.database import database as db
from modules.tickets.functions.setup_functions.close_ticket import close_ticket

class CloseTicketsTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.check_inactive_tickets.is_running():
            self.check_inactive_tickets.start()
        if not self.check_time_close_tickets.is_running():
            self.check_time_close_tickets.start()

    def cog_unload(self):
        self.check_inactive_tickets.cancel()
        self.check_time_close_tickets.cancel()

    @tasks.loop(minutes=5)
    async def check_inactive_tickets(self):
        tickets_data = db.obter("database/tickets/tickets_data.json")
        config = db.obter("database/tickets/tickets_config.json")
        if not tickets_data or not config:
            return

        now = int(time.time())

        for panel_id, users in tickets_data.get("panels", {}).items():
            panel_data = config.get("panels", {}).get(panel_id, {})
            inactive_pref = panel_data.get("preferences", {}).get("auto_close", {}).get("inactive", {})
            
            if not inactive_pref.get("enabled", False) or inactive_pref.get("minutes", 0) == 0:
                continue
            
            minutes = inactive_pref["minutes"]
            
            for user_id, tickets in users.items():
                for ticket in list(tickets):
                    if ticket.get("status") == "open" and "last_activity_timestamp" in ticket:
                        if (now - ticket["last_activity_timestamp"]) > (minutes * 60):
                            channel = self.bot.get_channel(ticket.get("ticket_id"))
                            if channel:
                                try:
                                    log_reason = "Fechado por inatividade."
                                    await close_ticket(
                                        bot=self.bot,
                                        channel=channel,
                                        closed_by=channel.guild.me,
                                        reason=log_reason,
                                        inter=None
                                    )
                                except Exception:
                                    traceback.print_exc()
    
    @tasks.loop(minutes=1)
    async def check_time_close_tickets(self):
        config = db.obter("database/tickets/tickets_config.json")
        tickets_data = db.obter("database/tickets/tickets_data.json")
        if not config or not tickets_data:
            return

        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")

        config_changed = False
        for panel_id, panel_data in config.get("panels", {}).items():
            at_time_pref = panel_data.get("preferences", {}).get("auto_close", {}).get("at_time", {})

            if (at_time_pref.get("enabled", False) and 
                at_time_pref.get("time") == current_time and
                at_time_pref.get("last_run") != today_str):

                at_time_pref["last_run"] = today_str
                config_changed = True

                if not tickets_data.get("panels", {}).get(panel_id):
                    continue

                for user_id, tickets in tickets_data.get("panels", {}).get(panel_id, {}).items():
                    for ticket in list(tickets):
                        if ticket.get("status") == "open":
                            channel = self.bot.get_channel(ticket.get("ticket_id"))
                            if channel:
                                try:
                                    reason = "Fechamento automático por horário."
                                    await close_ticket(
                                        bot=self.bot,
                                        channel=channel,
                                        closed_by=channel.guild.me,
                                        reason=reason,
                                        inter=None
                                    )
                                except Exception:
                                    traceback.print_exc()
        if config_changed:
            db.salvar("database/tickets/tickets_config.json", config)

    @check_inactive_tickets.before_loop
    @check_time_close_tickets.before_loop
    async def before_tasks(self):
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(CloseTicketsTasks(bot))

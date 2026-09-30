import time
from functions.database import database as db

def log_ticket_event(channel_id: int, event_type: str, author_id: int, details: dict = None):
    tickets_data = db.get_document("tickets_data") or {}
    ticket_found = False

    def find_and_log(panels_dict):
        nonlocal ticket_found
        for panel_id, users in panels_dict.items():
            if not isinstance(users, dict):
                continue
            if ticket_found: break
            for user_id, tickets in users.items():
                if ticket_found: break
                for ticket in tickets:
                    if ticket.get("ticket_id") == channel_id:
                        if "history" not in ticket:
                            ticket["history"] = []
                        
                        event = {
                            "type": event_type,
                            "author_id": author_id,
                            "timestamp": int(time.time()),
                            "details": details or {}
                        }
                        ticket["history"].append(event)
                        ticket_found = True
                        break
    
    find_and_log(tickets_data.get("panels", {}))
    
    if not ticket_found:
        top_level_panels = {
            k: v for k, v in tickets_data.items()
            if k not in ["panels", "ai_silenced"]
        }
        find_and_log(top_level_panels)

    if ticket_found:
        db.save_document("tickets_data", tickets_data)
        return True
    
    return False
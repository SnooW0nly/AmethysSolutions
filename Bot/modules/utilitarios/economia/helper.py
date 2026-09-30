"""
modules/utilitarios/economia/helper.py
Sistema de economia completo — helper central.
"""

from datetime import datetime
from functions.database import database as db

ECONOMY_DB_FILE   = "database/utilitarios/economia/coins.json"
BANK_DB_FILE      = "database/utilitarios/economia/bank.json"
SOCIAL_DB_FILE    = "database/utilitarios/economia/social.json"
INVENTORY_DB_FILE = "database/utilitarios/economia/inventory.json"
COOLDOWNS_DB_FILE = "database/utilitarios/economia/cooldowns.json"
STREAKS_DB_FILE   = "database/utilitarios/economia/streaks.json"
JOBS_DB_FILE      = "database/utilitarios/economia/jobs.json"

DEFAULT_JOBS = {
    "gari":        {"name": "Gari",        "emoji": "🧹", "description": "Varre as ruas da cidade.",                    "accept_chance": 95, "min_pay": 40,   "max_pay": 80,   "level_required": 0},
    "entregador":  {"name": "Entregador",  "emoji": "🛵", "description": "Faz entregas pelo bairro.",                   "accept_chance": 88, "min_pay": 60,   "max_pay": 120,  "level_required": 0},
    "garcom":      {"name": "Garçom",      "emoji": "🍽️", "description": "Atende mesas num restaurante movimentado.",   "accept_chance": 78, "min_pay": 90,   "max_pay": 180,  "level_required": 0},
    "mecanico":    {"name": "Mecânico",    "emoji": "🔧", "description": "Conserta veículos na oficina.",                "accept_chance": 62, "min_pay": 160,  "max_pay": 280,  "level_required": 0},
    "professor":   {"name": "Professor",   "emoji": "📚", "description": "Dá aulas em escola pública.",                  "accept_chance": 55, "min_pay": 200,  "max_pay": 350,  "level_required": 0},
    "programador": {"name": "Programador", "emoji": "💻", "description": "Desenvolve software para empresas.",           "accept_chance": 40, "min_pay": 320,  "max_pay": 650,  "level_required": 0},
    "medico":      {"name": "Médico",      "emoji": "🩺", "description": "Atende pacientes no hospital.",                "accept_chance": 25, "min_pay": 500,  "max_pay": 1000, "level_required": 0},
    "ceo":         {"name": "CEO",         "emoji": "💼", "description": "Gerencia uma empresa de grande porte.",        "accept_chance": 8,  "min_pay": 1200, "max_pay": 3000, "level_required": 0},
}

DEFAULT_SETTINGS = {
    "enabled": False,
    "currency_name": "Coin",
    "currency_emoji": "🪙",
    "reset_time": 0,
    "multiplier": 1.0,
    "role_multipliers": {},
    "logs_enabled": False,
    "log_channel": None,
    "commands": {},
    "events": [],
    "daily":   {"min_reward": 100,  "max_reward": 500,   "cooldown": 86400,   "streak_bonus": True, "streak_multiplier": 0.1, "max_streak_days": 30},
    "weekly":  {"min_reward": 1000, "max_reward": 3000,  "cooldown": 604800},
    "monthly": {"min_reward": 5000, "max_reward": 15000, "cooldown": 2592000},
    "work":    {"cooldown": 3600, "use_jobs": True},
    "crime":   {"min_reward": 200,  "max_reward": 1000, "success_chance": 60, "fine_min": 100, "fine_max": 400, "cooldown": 7200,
                "success_messages": ["Você assaltou uma loja abandonada","Você hackeou uma conta bancária","Você furtou uma carteira","Você vendeu produtos ilegais","Você invadiu um armazém"],
                "fail_messages":    ["A polícia te pegou em flagrante","Você escorregou e foi preso","Uma câmera te flagrou","A vítima gritou e você foi detido","Você foi reconhecido por uma testemunha"]},
    "rob":     {"success_chance": 40, "min_steal_percent": 10, "max_steal_percent": 40, "fine_percent": 25, "cooldown": 14400, "min_target_balance": 200},
    "fish":    {"min_reward": 20,  "max_reward": 150, "cooldown": 1800,
                "items": [{"name":"Peixinho Pequeno","min":10,"max":30,"chance":40},{"name":"Peixe Médio","min":40,"max":80,"chance":35},{"name":"Peixão","min":100,"max":150,"chance":20},{"name":"Tesouro Submerso","min":300,"max":600,"chance":5}]},
    "mine":    {"min_reward": 30,  "max_reward": 200, "cooldown": 3600,
                "items": [{"name":"Pedra Comum","min":10,"max":30,"chance":40},{"name":"Carvão","min":30,"max":70,"chance":30},{"name":"Ferro","min":70,"max":120,"chance":20},{"name":"Diamante","min":200,"max":400,"chance":8},{"name":"Cristal Raro","min":500,"max":1000,"chance":2}]},
    "hunt":    {"min_reward": 25,  "max_reward": 175, "cooldown": 2700,
                "items": [{"name":"Coelho","min":15,"max":40,"chance":40},{"name":"Veado","min":50,"max":100,"chance":30},{"name":"Javali","min":80,"max":150,"chance":20},{"name":"Lobo Raro","min":200,"max":350,"chance":8},{"name":"Dragão Lendário","min":500,"max":900,"chance":2}]},
    "slots":    {"min_bet": 10, "max_bet": 5000,  "jackpot_multiplier": 15.0, "three_match_multiplier": 5.0, "two_match_multiplier": 1.5},
    "coinflip": {"min_bet": 10, "max_bet": 10000},
    "pay":      {"tax_percent": 0, "max_per_day": 0, "min_transfer": 1},
    "shop":     {"items": []},
    "hourly":    {"min_reward": 30,   "max_reward": 120,  "cooldown": 3600},
    "vote":      {"min_reward": 300,  "max_reward": 800,  "cooldown": 43200},
    "trivia":    {"reward": 150, "timeout": 30},
    "dice":      {"min_bet": 10, "max_bet": 5000},
    "rps":       {"min_bet": 10, "max_bet": 5000},
    "blackjack": {"min_bet": 50, "max_bet": 10000},
    "lottery":   {"ticket_price": 100, "jackpot_seed": 5000, "min_participants": 2},
    "adventure": {"min_bet": 50, "max_bet": 2000},
    "gift":      {"min": 1, "max": 0},
    "wordle":    {},
    "missions":  {},
    "profile":   {},
    "sell":      {},
}


class EconomyHelper:

    # ── COINS ─────────────────────────────────────────────────────────────────

    @staticmethod
    def get_user_coins(user_id: int) -> int:
        return db.obter(ECONOMY_DB_FILE).get(str(user_id), 0)

    @staticmethod
    def set_user_coins(user_id: int, amount: int):
        data = db.obter(ECONOMY_DB_FILE)
        data[str(user_id)] = max(0, int(amount))
        db.salvar(ECONOMY_DB_FILE, data)

    @staticmethod
    def get_user_bank(user_id: int) -> int:
        return db.obter(BANK_DB_FILE).get(str(user_id), 0)

    @staticmethod
    def set_user_bank(user_id: int, amount: int):
        data = db.obter(BANK_DB_FILE)
        data[str(user_id)] = max(0, int(amount))
        db.salvar(BANK_DB_FILE, data)

    @staticmethod
    def deposit_coins(user_id: int, amount: int) -> bool:
        if amount <= 0: return False
        if not EconomyHelper.remove_user_coins(user_id, amount, "Depósito no banco"):
            return False
        current_bank = EconomyHelper.get_user_bank(user_id)
        EconomyHelper.set_user_bank(user_id, current_bank + amount)
        return True

    @staticmethod
    def withdraw_coins(user_id: int, amount: int) -> bool:
        if amount <= 0: return False
        current_bank = EconomyHelper.get_user_bank(user_id)
        if current_bank < amount:
            return False
        EconomyHelper.set_user_bank(user_id, current_bank - amount)
        EconomyHelper.add_user_coins(user_id, amount, "Saque do banco")
        return True

    @staticmethod
    def add_user_coins(user_id: int, amount: int, reason: str = None, member=None) -> int:
        mult = EconomyHelper.get_effective_multiplier(user_id, member)
        final = max(1, int(amount * mult))
        EconomyHelper.set_user_coins(user_id, EconomyHelper.get_user_coins(user_id) + final)
        if reason:
            EconomyHelper.log_transaction(user_id, final, "add", reason)
        return final

    @staticmethod
    def remove_user_coins(user_id: int, amount: int, reason: str = None) -> bool:
        current = EconomyHelper.get_user_coins(user_id)
        if current < amount:
            return False
        EconomyHelper.set_user_coins(user_id, current - amount)
        if reason:
            EconomyHelper.log_transaction(user_id, amount, "remove", reason)
        return True

    @staticmethod
    def transfer_coins(from_id: int, to_id: int, amount: int) -> tuple[bool, int]:
        tax_pct = EconomyHelper.get_economy_settings().get("pay", {}).get("tax_percent", 0)
        tax = int(amount * tax_pct / 100)
        net = amount - tax
        if not EconomyHelper.remove_user_coins(from_id, amount, "Transferência"):
            return False, 0
        EconomyHelper.set_user_coins(to_id, EconomyHelper.get_user_coins(to_id) + net)
        return True, net

    @staticmethod
    def get_leaderboard(limit: int = 10) -> list:
        data = db.obter(ECONOMY_DB_FILE)
        return sorted(data.items(), key=lambda x: x[1], reverse=True)[:limit]

    @staticmethod
    def reset_all_coins():
        db.salvar(ECONOMY_DB_FILE, {})
        db.salvar(BANK_DB_FILE, {})
        db.salvar(SOCIAL_DB_FILE, {})

    # ── SOCIAL ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_social_data(user_id: int) -> dict:
        data = db.obter(SOCIAL_DB_FILE).get(str(user_id), {})
        # Garantir campos padrão
        defaults = {
            "partner": None, "married_at": None,
            "reps": 0, "last_rep_at": None,
            "children": [], "parent": None,
            "interactions": {}, # {type: count}
            "bffs": {}, # {user_id: {percent: X, date: Y}}
            "daily_ships": {} # {target_id: {percent: X, date: Y}}
        }
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data

    @staticmethod
    def set_social_data(user_id: int, data: dict):
        all_data = db.obter(SOCIAL_DB_FILE)
        all_data[str(user_id)] = data
        db.salvar(SOCIAL_DB_FILE, all_data)

    @staticmethod
    def get_partner(user_id: int) -> int | None:
        return EconomyHelper.get_social_data(user_id).get("partner")

    @staticmethod
    def set_marriage(user1_id: int, user2_id: int):
        d1 = EconomyHelper.get_social_data(user1_id)
        d2 = EconomyHelper.get_social_data(user2_id)
        d1["partner"] = user2_id
        d1["married_at"] = datetime.now().isoformat()
        d2["partner"] = user1_id
        d2["married_at"] = datetime.now().isoformat()
        EconomyHelper.set_social_data(user1_id, d1)
        EconomyHelper.set_social_data(user2_id, d2)

    @staticmethod
    def divorce(user_id: int):
        d1 = EconomyHelper.get_social_data(user_id)
        partner_id = d1.get("partner")
        if partner_id:
            d2 = EconomyHelper.get_social_data(partner_id)
            d2["partner"] = None
            d2["married_at"] = None
            EconomyHelper.set_social_data(partner_id, d2)
        d1["partner"] = None
        d1["married_at"] = None
        EconomyHelper.set_social_data(user_id, d1)

    @staticmethod
    def add_rep(user_id: int):
        data = EconomyHelper.get_social_data(user_id)
        data["reps"] = data.get("reps", 0) + 1
        EconomyHelper.set_social_data(user_id, data)

    @staticmethod
    def add_interaction(user_id: int, interaction_type: str):
        data = EconomyHelper.get_social_data(user_id)
        if "interactions" not in data: data["interactions"] = {}
        data["interactions"][interaction_type] = data["interactions"].get(interaction_type, 0) + 1
        EconomyHelper.set_social_data(user_id, data)

    @staticmethod
    def set_bff(user1_id: int, user2_id: int, percent: int):
        d1 = EconomyHelper.get_social_data(user1_id)
        d2 = EconomyHelper.get_social_data(user2_id)
        now = datetime.now().isoformat()
        d1["bffs"][str(user2_id)] = {"percent": percent, "date": now}
        d2["bffs"][str(user1_id)] = {"percent": percent, "date": now}
        EconomyHelper.set_social_data(user1_id, d1)
        EconomyHelper.set_social_data(user2_id, d2)

    @staticmethod
    def adopt(parent_id: int, child_id: int):
        dp = EconomyHelper.get_social_data(parent_id)
        dc = EconomyHelper.get_social_data(child_id)
        if child_id not in dp["children"]:
            dp["children"].append(child_id)
        dc["parent"] = parent_id
        EconomyHelper.set_social_data(parent_id, dp)
        EconomyHelper.set_social_data(child_id, dc)

    @staticmethod
    def abandon(parent_id: int, child_id: int):
        dp = EconomyHelper.get_social_data(parent_id)
        dc = EconomyHelper.get_social_data(child_id)
        if child_id in dp["children"]:
            dp["children"].remove(child_id)
        if dc["parent"] == parent_id:
            dc["parent"] = None
        EconomyHelper.set_social_data(parent_id, dp)
        EconomyHelper.set_social_data(child_id, dc)

    # ── MULTIPLICADORES ───────────────────────────────────────────────────────

    @staticmethod
    def get_effective_multiplier(user_id: int, member=None, target: str = "global") -> float:
        s = EconomyHelper.get_economy_settings()
        base = float(s.get("multiplier", 1.0))
        role_mult = 1.0
        if member:
            for role in member.roles:
                rm = s.get("role_multipliers", {}).get(str(role.id))
                if rm and float(rm) > role_mult:
                    role_mult = float(rm)
        event_mult = EconomyHelper.get_active_event_multiplier(target)
        return round(base * role_mult * event_mult, 4)

    @staticmethod
    def set_global_multiplier(value: float):
        s = EconomyHelper.get_economy_settings()
        s["multiplier"] = value
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def set_role_multiplier(role_id: int, value: float):
        s = EconomyHelper.get_economy_settings()
        if "role_multipliers" not in s:
            s["role_multipliers"] = {}
        if value == 1.0:
            s["role_multipliers"].pop(str(role_id), None)
        else:
            s["role_multipliers"][str(role_id)] = value
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def remove_role_multiplier(role_id: int):
        s = EconomyHelper.get_economy_settings()
        s.get("role_multipliers", {}).pop(str(role_id), None)
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def get_role_multipliers() -> dict:
        return EconomyHelper.get_economy_settings().get("role_multipliers", {})

    # ── EVENTOS ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_events() -> list:
        return EconomyHelper.get_economy_settings().get("events", [])

    @staticmethod
    def get_active_events() -> list:
        now = datetime.now()
        active = []
        for ev in EconomyHelper.get_events():
            end_str = ev.get("ends_at")
            if not end_str:
                active.append(ev); continue
            try:
                if datetime.fromisoformat(end_str) > now:
                    active.append(ev)
            except Exception:
                pass
        return active

    @staticmethod
    def get_active_event_multiplier(target: str = "global") -> float:
        mult = 1.0
        for ev in EconomyHelper.get_active_events():
            ev_target = ev.get("target", "global")
            if ev_target in ("global", target):
                mult *= float(ev.get("multiplier", 1.0))
        return mult

    @staticmethod
    def add_event(name: str, target: str, multiplier: float,
                  duration_hours: float = 0, description: str = "") -> dict:
        import uuid
        from datetime import timedelta
        s = EconomyHelper.get_economy_settings()
        if "events" not in s:
            s["events"] = []
        event = {
            "id":          str(uuid.uuid4())[:8],
            "name":        name,
            "description": description,
            "target":      target,
            "multiplier":  multiplier,
            "created_at":  datetime.now().isoformat(),
            "ends_at":     (datetime.now() + timedelta(hours=duration_hours)).isoformat() if duration_hours > 0 else None,
        }
        s["events"].append(event)
        EconomyHelper.save_economy_settings(s)
        return event

    @staticmethod
    def remove_event(event_id: str) -> bool:
        s = EconomyHelper.get_economy_settings()
        events = s.get("events", [])
        new = [e for e in events if e["id"] != event_id]
        if len(new) == len(events):
            return False
        s["events"] = new
        EconomyHelper.save_economy_settings(s)
        return True

    @staticmethod
    def clear_expired_events():
        s = EconomyHelper.get_economy_settings()
        now = datetime.now()
        s["events"] = [e for e in s.get("events", [])
                       if not e.get("ends_at") or datetime.fromisoformat(e["ends_at"]) > now]
        EconomyHelper.save_economy_settings(s)

    # ── EMPREGOS ──────────────────────────────────────────────────────────────

    @staticmethod
    def get_all_jobs() -> dict:
        custom = EconomyHelper.get_economy_settings().get("custom_jobs", {})
        return {**DEFAULT_JOBS, **custom}

    @staticmethod
    def get_job(job_id: str) -> dict | None:
        return EconomyHelper.get_all_jobs().get(job_id)

    @staticmethod
    def add_custom_job(job_id: str, name: str, emoji_str: str, description: str,
                       accept_chance: int, min_pay: int, max_pay: int):
        s = EconomyHelper.get_economy_settings()
        if "custom_jobs" not in s:
            s["custom_jobs"] = {}
        s["custom_jobs"][job_id] = {
            "name": name, "emoji": emoji_str, "description": description,
            "accept_chance": accept_chance, "min_pay": min_pay, "max_pay": max_pay,
            "level_required": 0,
        }
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def remove_custom_job(job_id: str) -> bool:
        s = EconomyHelper.get_economy_settings()
        if job_id in s.get("custom_jobs", {}):
            del s["custom_jobs"][job_id]
            EconomyHelper.save_economy_settings(s)
            return True
        return False

    @staticmethod
    def edit_job(job_id: str, **kwargs):
        """
        Edita campos de um emprego (padrão ou custom).
        Empregos padrão editados são promovidos para custom_jobs com as alterações.
        Campos editáveis: name, emoji, description, accept_chance, min_pay, max_pay, level_required.
        """
        s        = EconomyHelper.get_economy_settings()
        all_jobs = {**DEFAULT_JOBS, **s.get("custom_jobs", {})}
        base     = dict(all_jobs.get(job_id, {}))
        if not base:
            return False
        for k, v in kwargs.items():
            if k in ("name","emoji","description","accept_chance","min_pay","max_pay","level_required"):
                base[k] = v
        if "custom_jobs" not in s:
            s["custom_jobs"] = {}
        s["custom_jobs"][job_id] = base
        EconomyHelper.save_economy_settings(s)
        return True

    @staticmethod
    def reset_default_jobs():
        """
        Remove todos os empregos padrão de custom_jobs,
        fazendo-os voltarem ao estado original do DEFAULT_JOBS.
        Empregos totalmente custom (não em DEFAULT_JOBS) não são afetados.
        """
        s      = EconomyHelper.get_economy_settings()
        custom = s.get("custom_jobs", {})
        for jid in list(DEFAULT_JOBS.keys()):
            custom.pop(jid, None)
        s["custom_jobs"] = custom
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def get_user_job(user_id: int) -> dict | None:
        job_id = db.obter(JOBS_DB_FILE).get(str(user_id))
        if not job_id:
            return None
        job = EconomyHelper.get_job(job_id)
        return {"id": job_id, **job} if job else None

    @staticmethod
    def set_user_job(user_id: int, job_id: str):
        data = db.obter(JOBS_DB_FILE)
        data[str(user_id)] = job_id
        db.salvar(JOBS_DB_FILE, data)

    @staticmethod
    def remove_user_job(user_id: int):
        data = db.obter(JOBS_DB_FILE)
        data.pop(str(user_id), None)
        db.salvar(JOBS_DB_FILE, data)

    # ── PERFIL (admin) ────────────────────────────────────────────────────────

    @staticmethod
    def get_user_profile(user_id: int) -> dict:
        return {
            "coins":     EconomyHelper.get_user_coins(user_id),
            "job":       EconomyHelper.get_user_job(user_id),
            "streak":    EconomyHelper.get_streak(user_id, "daily"),
            "inventory": EconomyHelper.get_inventory(user_id),
            "cooldowns": db.obter(COOLDOWNS_DB_FILE).get(str(user_id), {}),
        }

    # ── INVENTÁRIO ────────────────────────────────────────────────────────────

    @staticmethod
    def get_inventory(user_id: int) -> dict:
        return db.obter(INVENTORY_DB_FILE).get(str(user_id), {})

    @staticmethod
    def add_to_inventory(user_id: int, item_id: str, quantity: int = 1):
        data = db.obter(INVENTORY_DB_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = {}
        data[str(user_id)][item_id] = data[str(user_id)].get(item_id, 0) + quantity
        db.salvar(INVENTORY_DB_FILE, data)

    @staticmethod
    def remove_from_inventory(user_id: int, item_id: str, quantity: int = 1) -> bool:
        data = db.obter(INVENTORY_DB_FILE)
        inv = data.get(str(user_id), {})
        if inv.get(item_id, 0) < quantity:
            return False
        inv[item_id] -= quantity
        if inv[item_id] <= 0:
            del inv[item_id]
        data[str(user_id)] = inv
        db.salvar(INVENTORY_DB_FILE, data)
        return True

    # ── COOLDOWNS ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_cooldown(user_id: int, command: str) -> datetime | None:
        ts = db.obter(COOLDOWNS_DB_FILE).get(str(user_id), {}).get(command)
        return datetime.fromisoformat(ts) if ts else None

    @staticmethod
    def set_cooldown(user_id: int, command: str):
        data = db.obter(COOLDOWNS_DB_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = {}
        data[str(user_id)][command] = datetime.now().isoformat()
        db.salvar(COOLDOWNS_DB_FILE, data)

    @staticmethod
    def reset_cooldown(user_id: int, command: str):
        data = db.obter(COOLDOWNS_DB_FILE)
        if str(user_id) in data:
            data[str(user_id)].pop(command, None)
            db.salvar(COOLDOWNS_DB_FILE, data)

    @staticmethod
    def check_cooldown(user_id: int, command: str) -> int:
        s = EconomyHelper.get_economy_settings()
        cd = s.get(command, {}).get("cooldown", 86400)
        last = EconomyHelper.get_cooldown(user_id, command)
        if not last:
            return 0
        return max(0, int(cd - (datetime.now() - last).total_seconds()))

    # ── STREAKS ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_streak(user_id: int, command: str) -> dict:
        return db.obter(STREAKS_DB_FILE).get(str(user_id), {}).get(command, {"count": 0, "last_date": None})

    @staticmethod
    def update_streak(user_id: int, command: str) -> int:
        from datetime import date, timedelta
        data = db.obter(STREAKS_DB_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = {}
        sd = data[str(user_id)].get(command, {"count": 0, "last_date": None})
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if sd["last_date"] == yesterday:
            sd["count"] += 1
        elif sd["last_date"] != today:
            sd["count"] = 1
        sd["last_date"] = today
        data[str(user_id)][command] = sd
        db.salvar(STREAKS_DB_FILE, data)
        return sd["count"]

    @staticmethod
    def reset_streak(user_id: int, command: str):
        data = db.obter(STREAKS_DB_FILE)
        if str(user_id) in data:
            data[str(user_id)][command] = {"count": 0, "last_date": None}
            db.salvar(STREAKS_DB_FILE, data)

    # ── SETTINGS ──────────────────────────────────────────────────────────────

    @staticmethod
    def get_economy_settings() -> dict:
        saved = db.get_document("economy_settings_global") or {}
        merged = {}
        for k, v in DEFAULT_SETTINGS.items():
            if isinstance(v, dict) and k in saved:
                merged[k] = {**v, **saved[k]}
            else:
                merged[k] = saved.get(k, v)
        for k, v in saved.items():
            if k not in merged:
                merged[k] = v
        return merged

    @staticmethod
    def save_economy_settings(settings: dict):
        db.save_document("economy_settings_global", settings)

    @staticmethod
    def get_cmd_setting(command: str, key: str):
        s = EconomyHelper.get_economy_settings()
        return s.get(command, {}).get(key, DEFAULT_SETTINGS.get(command, {}).get(key))

    @staticmethod
    def set_cmd_setting(command: str, key: str, value):
        s = EconomyHelper.get_economy_settings()
        if command not in s:
            s[command] = {}
        s[command][key] = value
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def is_economy_enabled() -> bool:
        return EconomyHelper.get_economy_settings().get("enabled", False)

    @staticmethod
    def toggle_economy():
        s = EconomyHelper.get_economy_settings()
        s["enabled"] = not s.get("enabled", False)
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def get_currency_name() -> str:
        return EconomyHelper.get_economy_settings().get("currency_name", "Coin")

    @staticmethod
    def get_currency_emoji() -> str:
        return EconomyHelper.get_economy_settings().get("currency_emoji", "🪙")

    @staticmethod
    def get_currency_display() -> str:
        s = EconomyHelper.get_economy_settings()
        return f"{s.get('currency_emoji','🪙')} {s.get('currency_name','Coin')}"

    @staticmethod
    def set_currency_name(name: str):
        s = EconomyHelper.get_economy_settings()
        s["currency_name"] = name
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def set_currency_emoji(emoji_str: str):
        s = EconomyHelper.get_economy_settings()
        s["currency_emoji"] = emoji_str
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def get_reset_time() -> int:
        return EconomyHelper.get_economy_settings().get("reset_time", 0)

    @staticmethod
    def set_reset_time(seconds: int):
        s = EconomyHelper.get_economy_settings()
        s["reset_time"] = seconds
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def get_multiplier() -> float:
        return EconomyHelper.get_economy_settings().get("multiplier", 1.0)

    @staticmethod
    def get_command_status(command_name: str) -> bool:
        return EconomyHelper.get_economy_settings().get("commands", {}).get(command_name, True)

    @staticmethod
    def toggle_command_status(command_name: str):
        s = EconomyHelper.get_economy_settings()
        if "commands" not in s:
            s["commands"] = {}
        s["commands"][command_name] = not s["commands"].get(command_name, True)
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def toggle_logs():
        s = EconomyHelper.get_economy_settings()
        s["logs_enabled"] = not s.get("logs_enabled", False)
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def set_log_channel(channel_id: int):
        s = EconomyHelper.get_economy_settings()
        s["log_channel"] = channel_id
        EconomyHelper.save_economy_settings(s)

    # ── LOJA ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_shop_items() -> list:
        return EconomyHelper.get_economy_settings().get("shop", {}).get("items", [])

    @staticmethod
    def add_shop_item(item_id: str, name: str, price: int, description: str,
                      emoji_str: str = "📦", role_id: int = None):
        s = EconomyHelper.get_economy_settings()
        if "shop" not in s:
            s["shop"] = {"items": []}
        s["shop"]["items"].append({"id": item_id, "name": name, "price": price,
                                   "description": description, "emoji": emoji_str, "role_id": role_id})
        EconomyHelper.save_economy_settings(s)

    @staticmethod
    def remove_shop_item(item_id: str) -> bool:
        s = EconomyHelper.get_economy_settings()
        items = s.get("shop", {}).get("items", [])
        new = [i for i in items if i["id"] != item_id]
        if len(new) == len(items):
            return False
        s["shop"]["items"] = new
        EconomyHelper.save_economy_settings(s)
        return True

    @staticmethod
    def get_shop_item(item_id: str) -> dict | None:
        return next((i for i in EconomyHelper.get_shop_items() if i["id"] == item_id), None)

    # ── UTILS ─────────────────────────────────────────────────────────────────

    @staticmethod
    def format_cooldown(seconds: int) -> str:
        if seconds <= 0:
            return "agora"
        h, r = divmod(int(seconds), 3600)
        m, s = divmod(r, 60)
        parts = []
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}m")
        if s or not parts: parts.append(f"{s}s")
        return " ".join(parts)

    @staticmethod
    def format_coins(amount: int) -> str:
        s = EconomyHelper.get_economy_settings()
        return f"**{amount:,}** {s.get('currency_emoji','🪙')} {s.get('currency_name','Coin')}"

    @staticmethod
    def log_transaction(user_id: int, amount: int, type: str, reason: str):
        if not EconomyHelper.get_economy_settings().get("logs_enabled"):
            return
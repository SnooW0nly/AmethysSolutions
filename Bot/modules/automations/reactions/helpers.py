import disnake
import json
from functions.database import database as db

class ReacoesDB:
    def __init__(self):
        self.collection_name = "automations_reactions"
        self.db_data = self._load()
        self._migrate()

    def _load(self):
        return db.get_document(self.collection_name) or {"status": False, "reactions": []}

    def _save(self):
        db.save_document(self.collection_name, {}, self.db_data)

    def _migrate(self):
        reactions = self.db_data.get("reactions")
        migrated = False
        if reactions and isinstance(reactions, list) and reactions and "channel_id" in reactions[0]:
            self.db_data["reactions"] = [
                {"type": "channel", "value": r["channel_id"], "emoji": r["emoji"]} for r in reactions
            ]
            migrated = True
        
        if migrated:
            self._save()

    def get_status(self):
        # Reload data to get latest status
        self.db_data = self._load()
        return self.db_data.get("status", False)

    def set_status(self, status: bool):
        self.db_data["status"] = status
        self._save()

    def add_reaction(self, reaction_type: str, value, emoji: str):
        if "reactions" not in self.db_data:
            self.db_data["reactions"] = []
        
        self.db_data["reactions"].append({"type": reaction_type, "value": value, "emoji": emoji})
        self._save()

    def remove_reaction(self, reaction_type: str, value, emoji: str):
        if "reactions" not in self.db_data:
            return

        self.db_data["reactions"] = [
            r for r in self.db_data["reactions"]
            if not (r.get("type") == reaction_type and str(r.get("value")) == str(value) and r.get("emoji") == emoji)
        ]
        self._save()

    def get_reactions(self):
        # Reload data to get latest reactions
        self.db_data = self._load()
        return self.db_data.get("reactions", [])

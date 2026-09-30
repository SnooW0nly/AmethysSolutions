"""
Índice em memória para lookup O(1) de canal → ticket.
Elimina os loops O(n³) que causavam travamentos com muitos tickets abertos.
"""
import threading
from typing import Optional

# Estrutura: {channel_id: {"panel_id": str, "user_id": str, "ticket": dict_ref}}
_index: dict[int, dict] = {}
_lock = threading.Lock()


def rebuild_index(tickets_data: dict) -> None:
    """Reconstrói o índice completo a partir do tickets_data. Chamar no startup."""
    new_index = {}
    for panel_id, users in tickets_data.get("panels", {}).items():
        if not isinstance(users, dict):
            continue
        for user_id, tickets in users.items():
            for ticket in tickets:
                if ticket.get("status") == "open":
                    ch_id = ticket.get("ticket_id")
                    if ch_id:
                        new_index[ch_id] = {
                            "panel_id": panel_id,
                            "user_id": user_id,
                            "ticket": ticket,
                        }
    with _lock:
        _index.clear()
        _index.update(new_index)


def register(channel_id: int, panel_id: str, user_id: str, ticket: dict) -> None:
    """Registra um ticket recém-criado no índice."""
    with _lock:
        _index[channel_id] = {
            "panel_id": panel_id,
            "user_id": user_id,
            "ticket": ticket,
        }


def unregister(channel_id: int) -> None:
    """Remove um ticket do índice (ao fechar)."""
    with _lock:
        _index.pop(channel_id, None)


def find(channel_id: int) -> Optional[dict]:
    """
    Retorna {"panel_id", "user_id", "ticket"} ou None.
    Complexidade O(1).
    """
    with _lock:
        return _index.get(channel_id)


def find_panel_and_config(channel_id: int):
    """
    Compatível com o padrão antigo _find_panel_by_channel.
    Retorna (panel_id, panel_data, ticket) sem tocar no MongoDB.
    panel_data é buscado apenas se necessário — caller deve passar tickets_config.
    """
    entry = find(channel_id)
    if entry:
        return entry["panel_id"], entry["user_id"], entry["ticket"]
    return None, None, None
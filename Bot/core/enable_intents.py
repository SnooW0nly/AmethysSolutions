import requests
from functions.database import database as db


def get_application_id(token: str) -> str:
    """
    Obtém o ID da aplicação a partir do token do bot.
    """
    response = requests.get(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bot {token}"}
    )
    if response.status_code == 200:
        return response.json().get("id")
    raise Exception(f"Erro ao obter ID da aplicação: {response.status_code}")


def enable_intents(token: str, app_id: str = None) -> bool:
    """
    Ativa as intents privilegiadas do bot.
    flags 11051008 = GATEWAY_PRESENCE | GATEWAY_GUILD_MEMBERS | GATEWAY_MESSAGE_CONTENT
    """
    if app_id is None:
        app_id = get_application_id(token)
    
    response = requests.patch(
        f"https://discord.com/api/v10/applications/{app_id}",
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        },
        json={
            "bot_public": False,
            "bot_require_code_grant": False,
            "flags": 11051008
        }
    )
    
    if response.status_code == 200:
        print("[Intents] Intents privilegiadas ativadas com sucesso!")
        return True
    else:
        print(f"[Intents] Erro ao ativar intents: {response.status_code} - {response.text}")
        return False

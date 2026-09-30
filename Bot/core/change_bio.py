# core/change_bio.py
from functions.database import database as db
import requests

DEFAULT_USERNAME     = "AmySallers"
DEFAULT_BIO_FALLBACK = "https://amethys.solutions/"

# Limite oficial do Discord para bio de aplicação
_DISCORD_BIO_LIMIT = 400
_BIO_SEPARATOR     = "\n~~                                                                                                                 ~~\n"


def _fetch_bio_from_api(token: str, api_url: str, bot_token: str) -> str | None:
    """Busca a bio obrigatória da Amethys na API central."""
    try:
        response = requests.get(
            f"{api_url}/bot/bio",
            headers={
                "authorization": bot_token,
                "content-type": "application/json",
            },
            timeout=10,
        )
        if response.status_code == 200:
            bio = response.json().get("bio", "")
            if bio:
                return bio
    except Exception as e:
        print(f"[change_bio] Erro ao buscar bio da API: {e}")
    return None


def _get_user_bio() -> str:
    """Retorna a bio personalizada salva pelo dono do bot (pode ser vazia)."""
    return (db.get_document("custom_bio") or {}).get("user_bio", "")


def _build_final_bio(amethys_bio: str, user_bio: str) -> str:
    """
    Combina a bio da Amethys (imutável, sempre primeiro) com a bio do usuário.

    - A bio da Amethys NUNCA é truncada nem removida.
    - Se a bio do usuário ultrapassar o espaço disponível, ela é cortada pelo
      final com "…" para que a bio da Amethys caiba integralmente.
    - Se a bio da Amethys já ocupar todo o limite, o texto do usuário é omitido.
    """
    if not user_bio:
        return amethys_bio

    base      = amethys_bio + _BIO_SEPARATOR
    available = _DISCORD_BIO_LIMIT - len(base)

    if available <= 0:
        return amethys_bio

    if len(user_bio) <= available:
        return base + user_bio

    # Trunca o texto do usuário preservando a bio da Amethys integralmente
    return base + user_bio[: available - 1] + "…"


def change_bio() -> None:
    database  = db.obter("config.json")
    token     = database["bot"]["token"]
    app_id    = database["bot"]["id"]
    api_url   = database.get("apiURL", "")
    bot_token = database.get("botToken", "")

    # 1. Bio da Amethys (obrigatória)
    amethys_bio = _fetch_bio_from_api(token, api_url, bot_token) or DEFAULT_BIO_FALLBACK

    # 2. Bio personalizada do usuário
    user_bio = _get_user_bio()

    # 3. Composição final
    final_bio = _build_final_bio(amethys_bio, user_bio)

    # 4. Aplica no Discord
    requests.patch(
        f"https://discord.com/api/v9/applications/{app_id}",
        headers={"authorization": f"Bot {token}", "content-type": "application/json"},
        json={"description": final_bio},
    )

    # 5. Atualiza username se mudou
    bot_info = db.get_document("custom_bot_info") or {}
    username = bot_info.get("username", DEFAULT_USERNAME)

    if bot_info.get("username_applied") != username:
        response = requests.patch(
            "https://discord.com/api/v9/users/@me",
            headers={"authorization": f"Bot {token}", "content-type": "application/json"},
            json={"username": username},
        )
        if response.status_code == 200:
            bot_info["username_applied"] = username
            db.save_document("custom_bot_info", {}, bot_info)
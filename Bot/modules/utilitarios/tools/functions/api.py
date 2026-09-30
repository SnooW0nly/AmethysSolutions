import json
import aiohttp

with open("configs/config_api.json", "r", encoding="utf-8") as _f:
    _API_CFG = json.load(_f)

_API_BASE = _API_CFG.get("tools", "http://localhost:22222")


async def _api(method: str, endpoint: str, data: dict = None, params: dict = None):
    url = f"{_API_BASE}{endpoint}"
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, json=data, params=params, headers=headers) as resp:
            if resp.status == 404:
                return None
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"API error {resp.status}: {text}")
            return await resp.json()


async def check_blacklist(user_id: str) -> bool:
    try:
        result = await _api("GET", f"/api/storage/check-blacklist/{user_id}")
        return bool(result and result.get("blacklisted", False))
    except Exception:
        return False


async def login(user_id: str, token: str, plan: str):
    return await _api("POST", "/auth/login", data={"userId": user_id, "token": token, "plan": plan})


async def logout(user_id: str):
    return await _api("POST", "/auth/logout", data={"userId": user_id})


async def get_status_config(user_id: str):
    return await _api("GET", "/api/animated-status/config", params={"userId": user_id})


async def start_status(user_id: str):
    return await _api("POST", "/api/animated-status/start", data={"userId": user_id})


async def stop_status(user_id: str):
    return await _api("POST", "/api/animated-status/stop", data={"userId": user_id})


async def add_status(user_id: str, text: str, emoji_val: str, delay: int):
    return await _api("POST", "/api/animated-status/config/add", data={"userId": user_id, "text": text, "emoji": emoji_val, "delay": delay})


async def remove_status_by_index(user_id: str, index: int):
    return await _api("POST", "/api/animated-status/config/remove-by-index", data={"userId": user_id, "index": index})


async def edit_status_by_index(user_id: str, index: int, text: str, emoji_val: str, delay: int):
    return await _api("POST", "/api/animated-status/config/edit-by-index", data={"userId": user_id, "index": index, "text": text, "emoji": emoji_val, "delay": delay})


async def clear_status(user_id: str):
    return await _api("POST", "/api/animated-status/config/clear", data={"userId": user_id})


# ── Usuário / Rich Presence ────────────────────────────────────────────────────

async def get_user_info(user_id: str):
    return await _api("POST", "/api/user/getUserInfo", data={"userId": user_id})


async def set_activity(user_id: str, activity: dict):
    return await _api("POST", "/api/user/setActivity", data={"userId": user_id, "activity": activity})


async def update_activity(user_id: str, activity: dict):
    return await _api("POST", "/api/user/updateActivity", data={"userId": user_id, "activity": activity})


async def set_default_activity(user_id: str):
    return await _api("POST", "/api/user/setDefaultActivity", data={"userId": user_id})


# ── DMs ────────────────────────────────────────────────────────────────────────

async def clear_dm(user_id: str, target_id: str = None, channel_id: str = None):
    data = {"userId": user_id}
    if target_id:
        data["targetId"] = target_id
    if channel_id:
        data["channelId"] = channel_id
    return await _api("POST", "/api/dm/clearDm", data=data)


async def clear_dm_media(user_id: str, target_id: str = None, channel_id: str = None):
    data = {"userId": user_id}
    if target_id:
        data["targetId"] = target_id
    if channel_id:
        data["channelId"] = channel_id
    return await _api("POST", "/api/dm/clearDmMedia", data=data)


async def close_dms(user_id: str):
    return await _api("POST", "/api/dm/closeDms", data={"userId": user_id})


async def clear_all_dms(user_id: str):
    return await _api("POST", "/api/dm/clearAllDms", data={"userId": user_id})


async def open_dms(user_id: str):
    return await _api("POST", "/api/dm/openDms", data={"userId": user_id})


async def leave_group_dms(user_id: str):
    return await _api("POST", "/api/dm/leaveGroupDms", data={"userId": user_id})


async def open_all_history_dms(user_id: str):
    return await _api("POST", "/api/dm/openAllHistoryDms", data={"userId": user_id})


async def nuke_all_dms(user_id: str):
    return await _api("POST", "/api/dm/nukeAllDms", data={"userId": user_id})


async def clear_voice_msgs(user_id: str):
    return await _api("POST", "/api/dm/clearVoiceChannelsMessages", data={"userId": user_id})


async def dm_status(user_id: str):
    return await _api("POST", "/api/dm/status", data={"userId": user_id})


async def remove_friends(user_id: str):
    return await _api("POST", "/api/removeFriends", data={"userId": user_id})


async def clear_messages(user_id: str, channel_id: str):
    return await _api("POST", "/api/clearMessages", data={"userId": user_id, "channelId": channel_id})


# ── Servidores ─────────────────────────────────────────────────────────────────

async def leave_servers(user_id: str):
    return await _api("POST", "/api/server/leaveServers", data={"userId": user_id})


async def delete_owned_servers(user_id: str):
    return await _api("POST", "/api/server/deleteOwnedServers", data={"userId": user_id})


async def kick_all(user_id: str, guild_id: str):
    return await _api("POST", "/api/server/kickAllMembers", data={"userId": user_id, "guildId": guild_id})


async def ban_all(user_id: str, guild_id: str):
    return await _api("POST", "/api/server/banAllMembers", data={"userId": user_id, "guildId": guild_id})


async def clear_server(user_id: str, guild_id: str):
    return await _api("POST", "/api/server/clearServer", data={"userId": user_id, "guildId": guild_id})


async def send_dm_all(user_id: str, guild_id: str, msg: str):
    return await _api("POST", "/api/server/sendDmToAll", data={"userId": user_id, "guildId": guild_id, "message": msg})


async def solve_captcha(user_id: str, guild_id: str):
    return await _api("POST", "/api/server/solveCaptcha", data={"userId": user_id, "guildId": guild_id})


# ── Voz ────────────────────────────────────────────────────────────────────────

async def connect_voice(user_id: str, guild_id: str, channel_id: str):
    return await _api("POST", "/api/voice/connectToVoice", data={"userId": user_id, "guildId": guild_id, "channelId": channel_id})


async def disconnect_voice(user_id: str):
    return await _api("POST", "/api/voice/disconnectFromVoice", data={"userId": user_id})


async def reconnect_voice(user_id: str):
    return await _api("POST", "/api/voice/reconnectToVoice", data={"userId": user_id})


async def voice_status(user_id: str):
    return await _api("POST", "/api/voice/voiceStatus", data={"userId": user_id})


async def start_spam_call(user_id: str, guild_id: str):
    return await _api("POST", "/api/voice/startSpamCall", data={"userId": user_id, "guildId": guild_id})


async def stop_spam_call(user_id: str):
    return await _api("POST", "/api/voice/stopSpamCall", data={"userId": user_id})


async def play_audio(user_id: str, audio: str):
    return await _api("POST", "/api/voice/playAudio", data={"userId": user_id, "audio": audio})


async def list_audios(user_id: str):
    return await _api("POST", "/api/voice/listAudios", data={"userId": user_id})


async def move_voice_users(user_id: str, guild_id: str, from_channel_id: str, to_channel_id: str):
    return await _api("POST", "/api/voice/moveVoiceUsers", data={"userId": user_id, "guildId": guild_id, "fromChannelId": from_channel_id, "toChannelId": to_channel_id})


async def disconnect_voice_users(user_id: str, guild_id: str, channel_id: str):
    return await _api("POST", "/api/voice/disconnectVoiceUsers", data={"userId": user_id, "guildId": guild_id, "channelId": channel_id})


# ── Farms ──────────────────────────────────────────────────────────────────────

async def start_kosame(user_id: str, guild_id: str, channel_id: str):
    return await _api("POST", "/api/kosame/start", data={"userId": user_id, "guildId": guild_id, "channelId": channel_id})


async def stop_kosame(user_id: str):
    return await _api("POST", "/api/kosame/stop", data={"userId": user_id})


async def start_zany(user_id: str, guild_id: str, channel_id: str):
    return await _api("POST", "/api/zany/start", data={"userId": user_id, "guildId": guild_id, "channelId": channel_id})


async def stop_zany(user_id: str):
    return await _api("POST", "/api/zany/stop", data={"userId": user_id})


async def bump(user_id: str, guild_id: str):
    return await _api("POST", "/api/bump", data={"userId": user_id, "guildId": guild_id})


# ── Orbes e Missões ────────────────────────────────────────────────────────────

async def get_orb_available(token: str):
    return await _api("GET", f"/api/orb/available/{token}")


async def complete_orb(token: str, orb_id: str):
    return await _api("POST", f"/api/orb/complete/{token}", data={"orbId": orb_id})


async def get_quests_available(user_id: str):
    return await _api("POST", "/api/quest/available", data={"userId": user_id})


async def complete_all_quests(user_id: str):
    return await _api("POST", "/api/quest/completeAll", data={"userId": user_id})
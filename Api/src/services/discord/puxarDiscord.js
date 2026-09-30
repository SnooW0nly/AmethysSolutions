export const DISCORD_API = "https://discord.com/api";

export function getBotAuthHeader() {
  const token = process.env.DISCORD_BOT_TOKEN;
  if (!token) throw new Error("DISCORD_BOT_TOKEN não configurado");
  return { Authorization: `Bot ${token}` };
}

export async function addUserToGuild({ userId, accessToken, guildId, nickname }) {
  if (!userId) throw new Error("userId ausente");
  const finalGuildId = guildId || process.env.DISCORD_GUILD_ID;
  if (!finalGuildId) throw new Error("DISCORD_GUILD_ID não configurado");
  if (!accessToken) throw new Error("accessToken ausente");

  const url = `${DISCORD_API}/guilds/${finalGuildId}/members/${userId}`;
  const body = { access_token: accessToken };
  if (nickname) body.nick = nickname;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  const resp = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getBotAuthHeader(),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  });
  clearTimeout(timeoutId);

  if (!resp.ok && resp.status !== 201 && resp.status !== 204) {
    const t = await resp.text();
    throw new Error(`Falha ao adicionar ao servidor: ${resp.status} ${t}`);
  }
  return true;
}

export async function fetchGuildMember({ userId, guildId }) {
  if (!userId) throw new Error("userId ausente");
  const finalGuildId = guildId || process.env.DISCORD_GUILD_ID;
  if (!finalGuildId) throw new Error("DISCORD_GUILD_ID não configurado");

  const url = `${DISCORD_API}/guilds/${finalGuildId}/members/${userId}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  const resp = await fetch(url, {
    headers: {
      ...getBotAuthHeader(),
    },
    signal: controller.signal,
  });
  clearTimeout(timeoutId);
  if (!resp.ok) return null;
  return resp.json();
}
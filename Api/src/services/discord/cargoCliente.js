import { DISCORD_API, getBotAuthHeader } from "./puxarDiscord.js";

export async function addRoleToMember({ userId, roleId, guildId }) {
  if (!userId) throw new Error("userId ausente");
  if (!roleId) throw new Error("roleId ausente");
  const finalGuildId = guildId || process.env.DISCORD_GUILD_ID;
  if (!finalGuildId) throw new Error("DISCORD_GUILD_ID não configurado");

  const url = `${DISCORD_API}/guilds/${finalGuildId}/members/${userId}/roles/${roleId}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  const resp = await fetch(url, {
    method: "PUT",
    headers: {
      ...getBotAuthHeader(),
    },
    signal: controller.signal,
  });
  clearTimeout(timeoutId);
  if (!resp.ok && resp.status !== 204) {
    const t = await resp.text();
    throw new Error(`Falha ao adicionar cargo: ${resp.status} ${t}`);
  }
  return true;
}

export async function removeRoleFromMember({ userId, roleId, guildId }) {
  if (!userId) throw new Error("userId ausente");
  if (!roleId) throw new Error("roleId ausente");
  const finalGuildId = guildId || process.env.DISCORD_GUILD_ID;
  if (!finalGuildId) throw new Error("DISCORD_GUILD_ID não configurado");

  const url = `${DISCORD_API}/guilds/${finalGuildId}/members/${userId}/roles/${roleId}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);
  const resp = await fetch(url, {
    method: "DELETE",
    headers: {
      ...getBotAuthHeader(),
    },
    signal: controller.signal,
  });
  clearTimeout(timeoutId);
  if (!resp.ok && resp.status !== 204) {
    const t = await resp.text();
    throw new Error(`Falha ao remover cargo: ${resp.status} ${t}`);
  }
  return true;
}
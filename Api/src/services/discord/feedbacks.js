/**
 * src/services/discord/feedbacks.js
 * Busca feedbacks do canal Discord.
 * Canal e token agora são lidos do MongoDB (GlobalConfig) com fallback para .env.
 */

let cache = null;
let cacheTime = 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutos

async function resolveConfig() {
  try {
    const { getDiscordConfig } = await import(
      "../../routes/admin/discord/discord-config.js"
    );
    const [channelId, botToken] = await Promise.all([
      getDiscordConfig("discord_feedback_channel_id"),
      getDiscordConfig("discord_bot_token"),
    ]);
    return { channelId, botToken };
  } catch {
    return {
      channelId: process.env.DISCORD_FEEDBACK_CHANNEL_ID || null,
      botToken: process.env.DISCORD_BOT_TOKEN || null,
    };
  }
}

function resolveAvatar(author) {
  if (author.avatar) {
    const ext = author.avatar.startsWith("a_") ? "gif" : "png";
    return `https://cdn.discordapp.com/avatars/${author.id}/${author.avatar}.${ext}?size=64`;
  }
  const index = (BigInt(author.id) >> 22n) % 6n;
  return `https://cdn.discordapp.com/embed/avatars/${index}.png`;
}

function cleanContent(content) {
  return content
    .replace(/<@!?\d+>/g, "")
    .replace(/<#\d+>/g, "")
    .replace(/<@&\d+>/g, "")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export async function getFeedbacks() {
  if (cache && Date.now() - cacheTime < CACHE_TTL) {
    return cache;
  }

  const { channelId, botToken } = await resolveConfig();

  if (!channelId) {
    console.warn("[FEEDBACKS] discord_feedback_channel_id não configurado");
    return [];
  }

  if (!botToken) {
    console.error("[FEEDBACKS] discord_bot_token não configurado");
    return [];
  }

  try {
    const response = await fetch(
      `https://discord.com/api/v10/channels/${channelId}/messages?limit=50`,
      {
        headers: {
          Authorization: `Bot ${botToken}`,
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      const err = await response.text();
      console.error("[FEEDBACKS] Erro na API do Discord:", response.status, err);
      return cache || [];
    }

    const messages = await response.json();

    const feedbacks = messages
      .filter(
        (m) =>
          !m.author.bot &&
          m.content &&
          cleanContent(m.content).length >= 15
      )
      .slice(0, 30)
      .map((m) => ({
        id: m.id,
        content: cleanContent(m.content),
        username: m.author.global_name || m.author.username,
        avatar: resolveAvatar(m.author),
        timestamp: m.timestamp,
      }));

    cache = feedbacks;
    cacheTime = Date.now();

    console.log(`[FEEDBACKS] ${feedbacks.length} feedbacks carregados`);
    return feedbacks;
  } catch (error) {
    console.error("[FEEDBACKS] Erro ao buscar feedbacks:", error.message);
    return cache || [];
  }
}

export function invalidateFeedbackCache() {
  cache = null;
  cacheTime = 0;
}
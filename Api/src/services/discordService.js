import fetch from "node-fetch";

/**
 * Busca informações do bot via Discord API
 * @param {string} token - Token do bot Discord
 * @returns {Promise<{id: string, username: string, discriminator: string, avatar: string}>}
 */
export async function getBotInfo(token) {
  try {
    const response = await fetch("https://discord.com/api/v10/users/@me", {
      headers: {
        Authorization: `Bot ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error("Token inválido ou bot não encontrado");
    }

    const data = await response.json();
    
    return {
      id: data.id,
      username: data.username,
      discriminator: data.discriminator,
      avatar: data.avatar,
      bot: data.bot === true,
    };
  } catch (err) {
    console.error("[DISCORD SERVICE]", err);
    throw new Error("Erro ao buscar informações do bot no Discord");
  }
}

/**
 * Busca informações de um usuário Discord
 * @param {string} token - Token do bot
 * @param {string} userId - ID do usuário
 * @returns {Promise<{id: string, username: string, discriminator: string, avatar: string, global_name: string}>}
 */
export async function getUserInfo(token, userId) {
  try {
    const response = await fetch(`https://discord.com/api/v10/users/${userId}`, {
      headers: {
        Authorization: `Bot ${token}`,
      },
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    
    return {
      id: data.id,
      username: data.username,
      discriminator: data.discriminator,
      avatar: data.avatar,
      global_name: data.global_name || data.username,
    };
  } catch (err) {
    console.error("[DISCORD SERVICE - GET USER]", err);
    return null;
  }
}

/**
 * Busca informações de um servidor Discord
 * @param {string} token - Token do bot
 * @param {string} guildId - ID do servidor
 * @returns {Promise<{id: string, name: string, icon: string, member_count: number}>}
 */
export async function getGuildInfo(token, guildId) {
  try {
    const response = await fetch(`https://discord.com/api/v10/guilds/${guildId}?with_counts=true`, {
      headers: {
        Authorization: `Bot ${token}`,
      },
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    
    return {
      id: data.id,
      name: data.name,
      icon: data.icon,
      member_count: data.approximate_member_count || 0,
      owner_id: data.owner_id,
    };
  } catch (err) {
    console.error("[DISCORD SERVICE - GET GUILD]", err);
    return null;
  }
}

/**
 * Gera URL do avatar do Discord
 * @param {string} userId - ID do usuário
 * @param {string} avatar - Hash do avatar
 * @returns {string} URL do avatar
 */
export function getAvatarUrl(userId, avatar) {
  if (!avatar) {
    return `https://cdn.discordapp.com/embed/avatars/${parseInt(userId) % 5}.png`;
  }
  return `https://cdn.discordapp.com/avatars/${userId}/${avatar}.png?size=128`;
}

/**
 * Gera URL do ícone do servidor
 * @param {string} guildId - ID do servidor
 * @param {string} icon - Hash do ícone
 * @returns {string} URL do ícone
 */
export function getGuildIconUrl(guildId, icon) {
  if (!icon) {
    return null;
  }
  return `https://cdn.discordapp.com/icons/${guildId}/${icon}.png?size=128`;
}

/**
 * Gera URL de convite do bot
 * @param {string} botId - ID do bot Discord
 * @param {string} permissions - Permissões (padrão: admin + commands)
 * @returns {string} URL de convite
 */
export function generateInviteUrl(botId, permissions = "8") {
  // Permissão 8 = Administrator
  // scope: bot + applications.commands
  return `https://discord.com/api/oauth2/authorize?client_id=${botId}&permissions=${permissions}&scope=bot%20applications.commands`;
}

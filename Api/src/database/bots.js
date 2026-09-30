/**
 * Utilitários para conexão com bots do Discord
 */

import { Client, GatewayIntentBits, Partials } from "discord.js";

/**
 * Conecta a um bot do Discord usando o token
 * @param {string} botToken - Token do bot
 * @param {number} timeout - Timeout em ms (padrão: 10000)
 * @returns {Promise<Client|null>} Cliente conectado ou null se falhar
 */
export async function connectToUserBot(botToken, timeout = 10000) {
  return new Promise(async (resolve) => {
    const client = new Client({
      intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages],
      partials: [Partials.Channel],
    });

    let timeoutId;

    try {
      // Faz login com o token do bot
      await client.login(botToken);

      // Espera o bot estar pronto
      await new Promise((res, rej) => {
        timeoutId = setTimeout(() => {
          rej(new Error("Timeout ao conectar bot"));
        }, timeout);

        client.once("ready", () => {
          clearTimeout(timeoutId);
          res();
        });

        client.once("error", (err) => {
          clearTimeout(timeoutId);
          rej(err);
        });
      });

      resolve(client);
    } catch (error) {
      console.error("[BOTS] Erro ao conectar bot:", error.message);
      if (timeoutId) clearTimeout(timeoutId);
      
      // Tenta destruir o cliente se houver erro
      try {
        await client.destroy();
      } catch (e) {
        // Ignora erro ao destruir
      }
      
      resolve(null);
    }
  });
}

/**
 * Busca o ID do bot usando o token
 * @param {string} token - Token do bot
 * @returns {Promise<string|null>} ID do bot ou null se falhar
 */
export async function fetchDiscordBotId(token) {
  try {
    const response = await fetch("https://discord.com/api/v10/users/@me", {
      headers: { Authorization: `Bot ${token}` },
    });
    
    if (!response.ok) return null;
    
    const data = await response.json();
    return data.id;
  } catch (error) {
    console.error("[BOTS] Erro ao buscar ID do bot:", error.message);
    return null;
  }
}

/**
 * Valida se um token de bot é válido
 * @param {string} token - Token do bot
 * @returns {Promise<boolean>} True se válido, false caso contrário
 */
export async function validateBotToken(token) {
  const botId = await fetchDiscordBotId(token);
  return botId !== null;
}

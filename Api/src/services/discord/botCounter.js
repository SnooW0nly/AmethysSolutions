/**
 * src/services/discord/botCounter.js
 * Serviço de contador de aplicações no Discord.
 * As configurações são lidas do MongoDB (GlobalConfig) com fallback para .env.
 *
 * Além de atualizar o canal de voz com a contagem de aplicações,
 * este serviço também seta o status/RPC nos user accounts cujos tokens
 * estejam cadastrados no model Divulgacao (isActive: true, isValid: true).
 */

import { GatewayIntentBits } from "discord.js";
import Application from "../../database/models/Application.js";
import Divulgacao from "../../database/models/Divulgacao.js";
import { WebSocket } from "ws";
// Client compartilhado com o shop — evita dois logins com o mesmo token (op 9)
import sharedClient from "./shop/client.js";

// ─── Estado do bot principal (canal de voz) ───────────────────────────────────

let client = sharedClient;
let isRunning = false;
let _cachedToken = null;

// ─── User accounts (tokens do .env) ──────────────────────────────────────────

/**
 * Mapa de clientes de user account ativos.
 * Chave: token (string) → valor: objeto do client do Gateway
 */
const userClients = new Map();

// ─── Invalidação de cache ─────────────────────────────────────────────────────

export function invalidateCounterCache() {
  _cachedToken = null;
  console.log("[BOT COUNTER] Cache invalidado — próximo ciclo usará nova config");
}

// ─── Resolução de config ──────────────────────────────────────────────────────

/**
 * Resolve config: tenta MongoDB, cai para .env
 */
async function resolveConfig() {
  try {
    const { getDiscordConfig } = await import(
      "../../routes/admin/discord/discord-config.js"
    );
    const [token, guildId, channelId] = await Promise.all([
      getDiscordConfig("discord_bot_token"),
      getDiscordConfig("discord_guild_id"),
      getDiscordConfig("discord_counter_channel_id"),
    ]);
    return { token, guildId, channelId };
  } catch {
    return {
      token: process.env.DISCORD_BOT_TOKEN || null,
      guildId: process.env.DISCORD_GUILD_ID || null,
      channelId: process.env.DISCORD_COUNTER_CHANNEL_ID || null,
    };
  }
}

/**
 * Retorna a lista de tokens de user accounts a partir do model Divulgacao.
 * Considera apenas tokens com isActive: true e isValid: true.
 */
async function resolveUserTokens() {
  try {
    const divulgacao = await Divulgacao.findOne().lean();
    if (!divulgacao?.tokens?.length) return [];
    return divulgacao.tokens
      .filter((t) => t.isActive && t.isValid && t.token)
      .map((t) => t.token.trim())
      .filter(Boolean);
  } catch (err) {
    console.warn("[BOT COUNTER][USER] Falha ao buscar tokens do Divulgacao:", err.message);
    return [];
  }
}

// ─── Ícone do servidor ────────────────────────────────────────────────────────

/**
 * Busca a URL do ícone da guild via API REST do Discord (sem cache local).
 * Usa o token do bot principal para autenticação.
 *
 * @param {string} guildId
 * @param {string} botToken
 * @returns {Promise<string|null>}
 */
async function fetchGuildIconUrl(guildId, botToken) {
  try {
    const res = await fetch(`https://discord.com/api/v10/guilds/${guildId}`, {
      headers: { Authorization: `Bot ${botToken}` },
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.icon) return null;
    const ext = data.icon.startsWith("a_") ? "gif" : "png";
    return `https://cdn.discordapp.com/icons/${guildId}/${data.icon}.${ext}?size=512`;
  } catch {
    return null;
  }
}

// ─── Construção da presença (RPC) ─────────────────────────────────────────────

/**
 * Monta o payload de presença (op 3) para os user accounts.
 *
 * @param {number}      totalApps    - Total de aplicações cadastradas
 * @param {number}      botsOnline   - Quantidade de user accounts online
 * @param {string|null} guildIconUrl - URL do ícone do servidor (ou fallback)
 * @param {string}      inviteUrl    - Link do servidor/convite
 */
function buildAmethysPresence(totalApps, botsOnline, guildIconUrl, inviteUrl) {
  // O Gateway de user account exige "mp:external/<url_encodada>" para imagens
  // externas — URLs brutas são ignoradas silenciosamente pelo cliente.
  const rawUrl = guildIconUrl || "https://cdn.discordapp.com/embed/avatars/0.png";
  const largeImage = rawUrl.startsWith("https://cdn.discordapp.com/")
    ? rawUrl.replace("https://cdn.discordapp.com/", "mp:")
    : rawUrl;

  return {
    op: 3, // PRESENCE_UPDATE opcode
    d: {
      since: null,
      status: "online",
      afk: false,
      activities: [
        {
          application_id: "936929561302675456",
          type: 0, // Playing
          name: "Amethys Solutions",
          details: "Amethys Solutions a melhor do momento",
          state: `Por apenas R$6.99`,
          assets: {
            large_image: largeImage,
            large_text: "Amethys — Acesse agora",
          },
          buttons: ["Amethys Solutions"],
          metadata: {
            button_urls: [inviteUrl],
          },
          timestamps: {
            start: Date.now(),
          },
        },
      ],
    },
  };
}

// ─── User account WebSocket client ───────────────────────────────────────────

const GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json";

/**
 * Conecta um user account via WebSocket ao Discord Gateway.
 * Mantém heartbeat e identifica automaticamente.
 *
 * @param {string} token - Token de user account
 * @returns {Promise<object|null>} - Objeto do client ou null em caso de falha
 */
function connectUserClient(token) {
  return new Promise((resolve) => {
    let ws;
    let heartbeatInterval = null;
    let sequence = null;
    let resolved = false;
    let identified = false;

    const safeResolve = (val) => {
      if (!resolved) {
        resolved = true;
        resolve(val);
      }
    };

    const cleanup = () => {
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
      }
    };

    ws = new WebSocket(GATEWAY_URL);

    /** Objeto exposto para uso interno */
    const clientRef = {
      isReady: () => ws.readyState === WebSocket.OPEN && identified,
      setPresence: (payload) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(payload));
        }
      },
      destroy: () => {
        cleanup();
        try { ws.close(); } catch {}
        userClients.delete(token);
      },
      token,
    };

    const timeout = setTimeout(() => {
      console.warn("[BOT COUNTER][USER] Timeout ao conectar user account");
      cleanup();
      try { ws.close(); } catch {}
      safeResolve(null);
    }, 30_000);

    ws.onmessage = (event) => {
      let msg;
      try { msg = JSON.parse(event.data); } catch { return; }

      if (msg.s) sequence = msg.s;

      switch (msg.op) {
        // Hello — inicia heartbeat e envia Identify
        case 10: {
          const interval = msg.d.heartbeat_interval;
          heartbeatInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ op: 1, d: sequence }));
            }
          }, interval);

          ws.send(
            JSON.stringify({
              op: 2,
              d: {
                token,
                capabilities: 16381,
                properties: {
                  os: "Windows",
                  browser: "Discord Client",
                  device: "",
                  system_locale: "pt-BR",
                  browser_user_agent:
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9163 Chrome/124.0.6367.243 Electron/30.4.0 Safari/537.36",
                  browser_version: "30.4.0",
                  os_version: "10",
                  referrer: "",
                  referring_domain: "",
                  referrer_current: "",
                  referring_domain_current: "",
                  release_channel: "stable",
                  client_build_number: 339213,
                  client_event_source: null,
                },
                presence: {
                  status: "online",
                  since: 0,
                  activities: [],
                  afk: false,
                },
                compress: false,
                client_state: {
                  guild_versions: {},
                  highest_last_message_id: "0",
                  read_state_version: 0,
                  user_guild_settings_version: -1,
                  user_settings_version: -1,
                  private_channels_version: "0",
                  api_code_version: 0,
                },
              },
            })
          );
          break;
        }

        // Dispatch
        case 0: {
          if (msg.t === "READY") {
            identified = true;
            clearTimeout(timeout);
            const u = msg.d?.user;
            console.log(
              `[BOT COUNTER][USER] Conectado: ${u?.username ?? "desconhecido"}${u?.discriminator && u.discriminator !== "0" ? `#${u.discriminator}` : ""}`
            );
            // força presença inicial após conexão
            setTimeout(() => {
              try {
                clientRef.setPresence(
                  buildAmethysPresence(0, 0, null, "https://discord.gg/amethys")
                );
              } catch {}
            }, 2000);
            safeResolve(clientRef);
          }
          break;
        }

        // Invalid session
        case 9: {
          console.warn("[BOT COUNTER][USER] Sessão inválida — token pode estar incorreto");
          cleanup();
          clearTimeout(timeout);
          try { ws.close(); } catch {}
          safeResolve(null);
          break;
        }
      }
    };

    ws.onerror = (err) => {
      console.error("[BOT COUNTER][USER] Erro no WebSocket:", err?.message ?? err);
      cleanup();
      clearTimeout(timeout);
      safeResolve(null);
    };

    ws.onclose = () => {
      cleanup();
      identified = false;
      userClients.delete(token);
      console.log("[BOT COUNTER][USER] Conexão encerrada para um token");
    };
  });
}

/**
 * Garante que todos os user tokens do .env estão conectados ao Gateway.
 */
async function ensureUserClientsConnected() {
  const tokens = await resolveUserTokens();
  if (tokens.length === 0) return;

  for (const token of tokens) {
    const existing = userClients.get(token);
    if (existing?.isReady()) continue;

    if (existing) {
      // Client existente mas não pronto — limpa antes de reconectar
      try { existing.destroy(); } catch {}
      userClients.delete(token);
    }

    const uc = await connectUserClient(token);
    if (uc) {
      userClients.set(token, uc);
    } else {
      console.warn("[BOT COUNTER][USER] Falha ao conectar um token — ignorando");
    }
  }
}

/**
 * Envia o payload de presença para todos os user accounts conectados.
 *
 * @param {number}      totalApps
 * @param {number}      botsOnline
 * @param {string|null} guildIconUrl
 * @param {string}      inviteUrl
 */
function updateUserPresences(totalApps, botsOnline, guildIconUrl, inviteUrl) {
  const presence = buildAmethysPresence(totalApps, botsOnline, guildIconUrl, inviteUrl);
  let updated = 0;

  for (const [, uc] of userClients) {
    if (uc.isReady()) {
      uc.setPresence(presence);
      updated++;
    }
  }

  if (updated > 0) {
    console.log(`[BOT COUNTER][USER] Presença atualizada em ${updated} conta(s)`);
  }
}

// ─── Atualização principal ────────────────────────────────────────────────────

/**
 * Atualiza o nome do canal de voz e os status dos user accounts.
 */
async function updateBotCounter() {
  try {
    const { token, guildId, channelId } = await resolveConfig();

    if (!channelId) {
      console.warn("[BOT COUNTER] discord_counter_channel_id não configurado");
      return;
    }
    if (!guildId) {
      console.warn("[BOT COUNTER] discord_guild_id não configurado");
      return;
    }
    if (!token) {
      console.warn("[BOT COUNTER] discord_bot_token não configurado");
      return;
    }

    // Se o token mudou, reconecta o cliente principal
    if (_cachedToken && _cachedToken !== token) {
      console.log("[BOT COUNTER] Token mudou — reconectando cliente");
      await stopBotCounter();
    }

    if (!client || !isRunning) {
      await connectClient(token);
    }
    if (!client) return;

    // ── Contagem de aplicações hospedadas ───────────────────────────────────
    // Conta apenas apps que estão efetivamente hospedadas na Discloud:
    // não deletadas, não bloqueadas e com hosting.appId preenchido
    const totalApps = await Application.countDocuments({
      isDeleted: false,
      isBlocked: false,
      "hosting.appId": { $exists: true, $ne: null, $ne: "" },
    });

    // ── Atualiza canal de voz ───────────────────────────────────────────────
    const guild = await client.guilds.fetch(guildId).catch(() => null);
    if (!guild) {
      console.error("[BOT COUNTER] Servidor Discord não encontrado");
      return;
    }

    const channel = await guild.channels.fetch(channelId).catch(() => null);
    if (!channel) {
      console.error("[BOT COUNTER] Canal não encontrado");
      return;
    }

    if (channel.type !== 2) {
      console.error("[BOT COUNTER] O canal especificado não é um canal de voz");
      return;
    }

    const newName = `Aplicações: ${totalApps}`;
    if (channel.name !== newName) {
      await channel.setName(newName);
      console.log(`[BOT COUNTER] Canal atualizado: ${newName}`);
    }

    // ── User accounts: presença / RPC ───────────────────────────────────────
    const userTokens = await resolveUserTokens();
    if (userTokens.length > 0) {
      const botsOnline = [...userClients.values()].filter((uc) => uc.isReady()).length;
      const guildIconUrl = await fetchGuildIconUrl(guildId, token);
      const inviteUrl =
        process.env.DISCORD_INVITE_URL ||
        `https://discord.gg/${process.env.DISCORD_INVITE_CODE || "amethys"}`;

      updateUserPresences(totalApps, botsOnline, guildIconUrl, inviteUrl);
    }
  } catch (error) {
    console.error("[BOT COUNTER] Erro ao atualizar contador:", error.message);
  }
}

// ─── Conexão do bot principal ─────────────────────────────────────────────────

async function connectClient(token) {
  try {
    // Reutiliza o sharedClient — não cria novo Client (evita segundo login com mesmo token)
    client = sharedClient;

    await new Promise((resolve, reject) => {
      // Se já está pronto (ex: shop já conectou antes), resolve imediatamente
      if (client.isReady()) {
        console.log(`[BOT COUNTER] Reaproveitando client já conectado como ${client.user.tag}`);
        return resolve();
      }

      const timeout = setTimeout(
        () => reject(new Error("Timeout ao conectar no Discord")),
        30000
      );
      client.once("ready", () => {
        clearTimeout(timeout);
        console.log(`[BOT COUNTER] Bot conectado como ${client.user.tag}`);
        resolve();
      });
      client.once("error", (err) => {
        clearTimeout(timeout);
        reject(err);
      });
      client.login(token);
    });

    _cachedToken = token;
    isRunning = true;
  } catch (error) {
    console.error("[BOT COUNTER] Erro ao conectar cliente:", error.message);
    isRunning = false;
  }
}

// ─── API pública ──────────────────────────────────────────────────────────────

let _intervalId = null;

/**
 * Inicia o serviço de contador (canal de voz + RPC dos user accounts).
 */
export async function startBotCounter() {
  if (isRunning) {
    console.warn("[BOT COUNTER] Serviço já está rodando");
    return;
  }

  const { token } = await resolveConfig();
  if (!token) {
    console.error("[BOT COUNTER] Token não configurado — serviço não iniciado");
    return;
  }

  try {
    await connectClient(token);
    if (!isRunning) return;

    // Conecta user accounts em paralelo com o primeiro ciclo
    await ensureUserClientsConnected();

    await updateBotCounter();

    if (_intervalId) clearInterval(_intervalId);
    _intervalId = setInterval(async () => {
      await ensureUserClientsConnected(); // reconecta caídos
      await updateBotCounter();
    }, 5 * 60 * 1000);

    console.log("[BOT COUNTER] Serviço de contador iniciado");
  } catch (error) {
    console.error("[BOT COUNTER] Erro ao iniciar serviço:", error.message);
    isRunning = false;
  }
}

/**
 * Para o serviço de contador e desconecta todos os clients.
 */
export async function stopBotCounter() {
  if (_intervalId) {
    clearInterval(_intervalId);
    _intervalId = null;
  }

  // Destrói user clients
  for (const [, uc] of userClients) {
    try { uc.destroy(); } catch {}
  }
  userClients.clear();

  // Não destrói o sharedClient aqui — ele é compartilhado com o shop
  // O client será destruído apenas quando o processo encerrar
  client = null;

  isRunning = false;
  _cachedToken = null;
  console.log("[BOT COUNTER] Serviço de contador parado");
}

/**
 * Força atualização imediata do contador e dos status.
 */
export async function forceUpdateCounter() {
  await ensureUserClientsConnected();
  await updateBotCounter();
}
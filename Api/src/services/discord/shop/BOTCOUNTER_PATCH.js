/**
 * PATCH: src/services/discord/botCounter.js
 *
 * Alteração necessária para unificar o Client discord.js com o shop.
 * Sem isso, dois logins com o mesmo token causam op 9 (Discord derruba o mais antigo).
 *
 * ANTES (linha ~12 e função connectClient):
 * ─────────────────────────────────────────
 *   import { Client, GatewayIntentBits } from "discord.js";
 *   ...
 *   let client = null;
 *   ...
 *   async function connectClient(token) {
 *     client = new Client({
 *       intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates],
 *     });
 *     ...
 *   }
 *
 * DEPOIS (3 mudanças):
 * ─────────────────────────────────────────
 *   // 1. Importa o client compartilhado (remove o import de Client/GatewayIntentBits se não usado em outro lugar)
 *   import sharedClient from "./shop/client.js";
 *
 *   // 2. Inicializa let client apontando para o compartilhado
 *   let client = sharedClient;
 *
 *   // 3. Na função connectClient, usa o client compartilhado em vez de instanciar novo:
 *   async function connectClient(token) {
 *     try {
 *       // NÃO cria new Client() — usa o sharedClient já importado
 *       client = sharedClient;
 *
 *       await new Promise((resolve, reject) => {
 *         const timeout = setTimeout(
 *           () => reject(new Error("Timeout ao conectar no Discord")),
 *           30000
 *         );
 *         client.once("ready", () => {
 *           clearTimeout(timeout);
 *           console.log(`[BOT COUNTER] Bot conectado como ${client.user.tag}`);
 *           resolve();
 *         });
 *         client.once("error", (err) => {
 *           clearTimeout(timeout);
 *           reject(err);
 *         });
 *         // Só faz login se ainda não estiver pronto
 *         if (!client.isReady()) {
 *           client.login(token);
 *         } else {
 *           resolve();
 *         }
 *       });
 *
 *       _cachedToken = token;
 *       isRunning = true;
 *     } catch (error) {
 *       console.error("[BOT COUNTER] Erro ao conectar cliente:", error.message);
 *       isRunning = false;
 *     }
 *   }
 */

// Este arquivo é apenas documentação do patch.
// Aplique as mudanças acima manualmente no botCounter.js.

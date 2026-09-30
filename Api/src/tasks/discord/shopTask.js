/**
 * src/tasks/discord/shopTask.js
 *
 * Inicializa o sistema de loja/gerenciamento do Discord:
 *  1. Registra o handler de interações no client
 *  2. Aguarda o client estar pronto (reutiliza a conexão do botCounter)
 *  3. Publica (ou re-publica) as embeds nos canais configurados
 *
 * Lock de cluster: evita que múltiplos workers PM2 publiquem ao mesmo tempo.
 *
 * Adicionar no server.js:
 *   import { startShopTask } from "./src/tasks/discord/shopTask.js";
 *   // dentro do app.listen, após startBotCounter():
 *   await startShopTask();
 */

import client from "../../services/discord/shop/client.js";
import { publishShopMessage } from "../../services/discord/shop/shopMessage.js";
import { publishManagerMessage } from "../../services/discord/shop/managerMessage.js";
import { handleInteraction } from "../../services/discord/shop/interactions.js";
import GlobalConfig from "../../database/models/GlobalConfig.js";

let _handlersRegistered = false;

/**
 * Tenta adquirir lock de publicação para evitar race condition em clusters PM2.
 * Retorna true se este worker pode publicar, false caso contrário.
 */
async function acquirePublishLock() {
  try {
    const lock = await GlobalConfig.findOneAndUpdate(
      { key: "shop_publish_lock", value: { $ne: true } },
      { $set: { value: true, lockedAt: new Date() } },
      { upsert: false, new: true }
    );
    if (!lock) {
      // Garante que o documento existe para futuros upserts
      await GlobalConfig.findOneAndUpdate(
        { key: "shop_publish_lock" },
        { $setOnInsert: { value: false } },
        { upsert: true }
      ).catch(() => null);
    }
    return !!lock;
  } catch {
    // Em caso de erro no lock, deixa publicar (evita travar a inicialização)
    return true;
  }
}

async function releasePublishLock() {
  try {
    await GlobalConfig.updateOne(
      { key: "shop_publish_lock" },
      { $set: { value: false } }
    );
  } catch {
    // silencioso
  }
}

export async function startShopTask() {
  // Registra handler de interações apenas uma vez
  if (!_handlersRegistered) {
    client.on("interactionCreate", handleInteraction);
    _handlersRegistered = true;
  }

  // Aguarda o botCounter fazer login — shop nunca chama client.login()
  if (!client.isReady()) {
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error("[SHOP TASK] Timeout aguardando client ficar pronto")),
        60_000
      );
      client.once("ready", () => {
        clearTimeout(timeout);
        resolve();
      });
    });
  }

  const canPublish = await acquirePublishLock();

  if (!canPublish) {
    console.log("[SHOP TASK] Outro worker já está publicando as embeds — aguardando");
    return;
  }

  try {
    await publishShopMessage();
    await publishManagerMessage();
    console.log("[SHOP TASK] ✅ Embeds publicadas e interações registradas");
  } catch (err) {
    console.error("[SHOP TASK] Erro ao publicar embeds:", err.message);
  } finally {
    await releasePublishLock();
  }
}

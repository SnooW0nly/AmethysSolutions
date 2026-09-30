/**
 * setRestartFlag.js
 *
 * Grava {"pending": true} na coleção "restart_flag" do banco MongoDB do bot
 * SOMENTE quando há um update em massa originado pelo painel admin.
 *
 * A IA (aiMonitorService) NÃO chama isso — reinicios da IA são silenciosos.
 *
 * O bot Python lê essa flag no on_ready → log_restart e, se existir,
 * menciona @everyone no canal de logs. Após ler, o bot apaga a flag.
 */

import { getBotDatabase } from "../services/botDatabaseService.js";

/**
 * Grava a flag de reinicio por atualização no banco do bot.
 * @param {string} botID - O botID (igual ao db_name no MongoDB dos bots)
 */
export async function setRestartFlag(botID) {
  if (!botID) return;

  try {
    const db = await getBotDatabase(botID);
    const col = db.collection("restart_flag");

    await col.updateOne(
      {},
      { $set: { pending: true, setAt: new Date().toISOString() } },
      { upsert: true }
    );

    console.log(`[SET_RESTART_FLAG] Flag de update gravada para botID: ${botID}`);
  } catch (err) {
    console.error(`[SET_RESTART_FLAG] Erro ao gravar flag para ${botID}:`, err.message);
  }
}
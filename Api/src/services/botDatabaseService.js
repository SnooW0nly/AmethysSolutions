import { MongoClient } from "mongodb";

const MONGO_BOTS_URI = process.env.MONGO_BOTS_URI || "mongodb://localhost:27017";

let client = null;

/**
 * Conecta ao MongoDB dos bots
 */
async function connectBotDatabase() {
  if (client) return client;
  
  try {
    client = new MongoClient(MONGO_BOTS_URI);
    await client.connect();
    console.log("[BOT DATABASE] Conectado ao MongoDB dos bots");
    return client;
  } catch (err) {
    console.error("[BOT DATABASE] Erro ao conectar:", err);
    throw err;
  }
}

/**
 * Obtém database do bot pelo ID
 * @param {string} botId - ID do bot Discord
 * @returns {Promise<Db>}
 */
export async function getBotDatabase(botId) {
  const mongoClient = await connectBotDatabase();
  return mongoClient.db(botId);
}

/**
 * Obtém um documento de uma coleção do bot
 * @param {string} botId - ID do bot
 * @param {string} collectionName - Nome da coleção
 * @param {object} query - Query de busca
 * @returns {Promise<object|null>}
 */
export async function getBotDocument(botId, collectionName, query = {}) {
  try {
    const db = await getBotDatabase(botId);
    const collection = db.collection(collectionName);
    return await collection.findOne(query);
  } catch (err) {
    console.error(`[BOT DATABASE] Erro ao buscar documento:`, err);
    return null;
  }
}

/**
 * Salva/atualiza um documento na coleção do bot
 * @param {string} botId - ID do bot
 * @param {string} collectionName - Nome da coleção
 * @param {object} query - Query de busca
 * @param {object} data - Dados para salvar
 * @returns {Promise<boolean>}
 */
export async function saveBotDocument(botId, collectionName, query, data) {
  try {
    const db = await getBotDatabase(botId);
    const collection = db.collection(collectionName);
    
    // Remove _id se existir para evitar conflitos
    if (data._id) {
      delete data._id;
    }
    
    await collection.updateOne(
      query,
      { $set: data },
      { upsert: true }
    );
    
    return true;
  } catch (err) {
    console.error(`[BOT DATABASE] Erro ao salvar documento:`, err);
    return false;
  }
}

/**
 * Fecha conexão com MongoDB dos bots
 */
export async function closeBotDatabase() {
  if (client) {
    await client.close();
    client = null;
    console.log("[BOT DATABASE] Conexão fechada");
  }
}

// Fecha conexão ao encerrar processo
process.on("SIGINT", async () => {
  await closeBotDatabase();
  process.exit(0);
});

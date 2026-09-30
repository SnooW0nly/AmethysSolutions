/**
 * Cliente Redis compartilhado para rate limiters
 * Usa Redis se REDIS_URL estiver configurado, caso contrário usa Map em memória (fallback)
 *
 * INSTALAR: npm install ioredis
 */

let redisClient = null;
let usingRedis = false;

// Map em memória como fallback
const memoryStore = new Map();

async function getRedisClient() {
  if (redisClient) return redisClient;

  const REDIS_URL = process.env.REDIS_URL;
  if (!REDIS_URL) {
    if (process.env.NODE_ENV === 'production') {
      console.warn('[REDIS] ⚠️ REDIS_URL não configurado — rate limiters usando memória local (ineficaz em cluster)');
    }
    return null;
  }

  try {
    const { default: Redis } = await import('ioredis');
    redisClient = new Redis(REDIS_URL, {
      maxRetriesPerRequest: 1,
      enableReadyCheck: false,
      lazyConnect: true,
    });

    redisClient.on('error', (err) => {
      console.error('[REDIS] Erro de conexão:', err.message);
    });

    await redisClient.connect();
    usingRedis = true;
    console.log('[REDIS] ✅ Conectado ao Redis para rate limiting distribuído');
    return redisClient;
  } catch (err) {
    console.error('[REDIS] Falha ao conectar, usando fallback em memória:', err.message);
    redisClient = null;
    return null;
  }
}

/**
 * Incrementa contador e define expiração.
 * Retorna { count, resetTime } para o identificador dado.
 */
export async function incrementCounter(key, windowMs) {
  const redis = await getRedisClient();

  if (redis) {
    try {
      const now = Date.now();
      const windowKey = `rl:${key}:${Math.floor(now / windowMs)}`;
      const ttlSeconds = Math.ceil(windowMs / 1000) + 1;

      const count = await redis.incr(windowKey);
      if (count === 1) {
        await redis.expire(windowKey, ttlSeconds);
      }

      const resetTime = Math.floor(now / windowMs) * windowMs;
      return { count, resetTime };
    } catch (err) {
      console.error('[REDIS] Erro ao incrementar contador, usando memória:', err.message);
      // Fallthrough para memória
    }
  }

  // Fallback em memória
  const now = Date.now();
  let data = memoryStore.get(key);
  if (!data || now - data.resetTime >= windowMs) {
    data = { count: 0, resetTime: now };
    memoryStore.set(key, data);
  }
  data.count++;
  return { count: data.count, resetTime: data.resetTime };
}

/**
 * Limpa entradas expiradas do store em memória periodicamente
 */
setInterval(() => {
  const now = Date.now();
  for (const [k, v] of memoryStore.entries()) {
    if (now - v.resetTime > 15 * 60 * 1000) {
      memoryStore.delete(k);
    }
  }
}, 60000);

export { usingRedis };
export default getRedisClient;
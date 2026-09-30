/**
 * Sistema de cache em memória para rotas públicas
 */

// Armazena cache em memória
const cacheStore = new Map();

/**
 * Limpa cache expirado periodicamente
 */
setInterval(() => {
  const now = Date.now();
  for (const [key, data] of cacheStore.entries()) {
    if (data.expiresAt && now > data.expiresAt) {
      cacheStore.delete(key);
    }
  }
}, 60000); // Limpa a cada 1 minuto

/**
 * Gera chave de cache baseada na URL e query params
 */
function generateCacheKey(req) {
  const url = req.originalUrl || req.url;
  const query = req.query ? JSON.stringify(req.query) : '';
  return `${req.method}:${url}:${query}`;
}

/**
 * Middleware de cache para rotas públicas
 * @param {number} ttlSeconds - Tempo de vida do cache em segundos (padrão: 60)
 */
export function cacheMiddleware(ttlSeconds = 60) {
  return (req, res, next) => {
    // Apenas cache para GET requests
    if (req.method !== 'GET') {
      return next();
    }

    const cacheKey = generateCacheKey(req);
    const cached = cacheStore.get(cacheKey);

    // Se existe cache válido, retornar
    if (cached && (!cached.expiresAt || Date.now() < cached.expiresAt)) {
      res.setHeader('X-Cache', 'HIT');
      res.setHeader('X-Cache-Key', cacheKey);
      return res.json(cached.data);
    }

    // Interceptar res.json para cachear resposta
    const originalJson = res.json.bind(res);
    res.json = function(data) {
      // Cachear apenas respostas de sucesso
      if (res.statusCode >= 200 && res.statusCode < 300) {
        cacheStore.set(cacheKey, {
          data,
          expiresAt: Date.now() + (ttlSeconds * 1000),
          createdAt: Date.now()
        });
        res.setHeader('X-Cache', 'MISS');
        res.setHeader('X-Cache-Key', cacheKey);
      }
      return originalJson(data);
    };

    next();
  };
}

/**
 * Limpa cache específico ou todo o cache
 */
export function clearCache(pattern = null) {
  if (!pattern) {
    cacheStore.clear();
    return { cleared: 'all' };
  }

  let cleared = 0;
  for (const key of cacheStore.keys()) {
    if (key.includes(pattern)) {
      cacheStore.delete(key);
      cleared++;
    }
  }

  return { cleared, pattern };
}

/**
 * Obtém estatísticas do cache
 */
export function getCacheStats() {
  const now = Date.now();
  let valid = 0;
  let expired = 0;
  let totalSize = 0;

  for (const [key, data] of cacheStore.entries()) {
    totalSize += JSON.stringify(data).length;
    if (data.expiresAt && now > data.expiresAt) {
      expired++;
    } else {
      valid++;
    }
  }

  return {
    total: cacheStore.size,
    valid,
    expired,
    totalSize: `${(totalSize / 1024).toFixed(2)} KB`
  };
}

export default cacheMiddleware;


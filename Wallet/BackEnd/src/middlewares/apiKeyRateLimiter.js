/**
 * Rate Limiter específico para autenticação via API Key
 * Limita requisições por API Key (principal ou secundária)
 * Usa Redis se REDIS_URL estiver configurado (distribuído), caso contrário usa Map em memória.
 */

import { incrementCounter } from '../utils/redisClient.js';

// Fallback em memória
const apiKeyRequestCounts = new Map();

setInterval(() => {
  const now = Date.now();
  for (const [apiKey, data] of apiKeyRequestCounts.entries()) {
    if (now - data.resetTime > data.windowMs) {
      apiKeyRequestCounts.delete(apiKey);
    }
  }
}, 60000);

/**
 * Extrai a API Key do request
 */
function getApiKeyFromRequest(req) {
  // Tentar obter do header X-API-Key (apenas se for API Key de usuário vp_)
  const apiKeyHeader = req.headers['x-api-key'];
  if (apiKeyHeader && apiKeyHeader.startsWith('vp_')) {
    return apiKeyHeader;
  }

  // Tentar obter do header Authorization (Bearer token)
  const authHeader = req.headers['authorization'];
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.replace('Bearer ', '');
    // Se é API Key de usuário (começa com vp_)
    if (token.startsWith('vp_')) {
      return token;
    }
  }

  return null;
}

/**
 * Rate limiter para requisições autenticadas via API Key
 * Identifica pela API Key usada na requisição
 * 
 * @param {Object} options - Opções de configuração
 * @param {number} options.windowMs - Janela de tempo em milissegundos (padrão: 60000 = 1 minuto)
 * @param {number} options.max - Número máximo de requisições por janela (padrão: 100)
 * @param {string} options.message - Mensagem de erro personalizada
 */
export function apiKeyRateLimiter(options = {}) {
  const config = {
    windowMs: options.windowMs || 60 * 1000, // 1 minuto padrão
    max: options.max || 1500, // 1500 requisições por minuto padrão (25 req/s por API Key)
    message: options.message || 'Muitas requisições com esta API Key. Tente novamente em alguns instantes.',
  };

  return async (req, res, next) => {
    try {
      const apiKey = getApiKeyFromRequest(req);
      if (!apiKey) return next();

      // Usar os últimos 20 caracteres como identificador (não armazenar chave completa)
      const identifier = `apikey:${apiKey.slice(-20)}`;
      const { count, resetTime } = await incrementCounter(identifier, config.windowMs);

      if (count > config.max) {
        const retryAfter = Math.ceil((resetTime + config.windowMs - Date.now()) / 1000);

        console.warn(`[RATE LIMIT] API Key bloqueada temporariamente: ${identifier} (${count}/${config.max} requisições)`);

        (async () => {
          try {
            const { notifyRateLimit } = await import('../services/discordNotifier.js');
            const Register = (await import('../database/models/Register.js')).default;
            const user = await Register.getByApiKey(apiKey);
            await notifyRateLimit({
              apiKey,
              email: user?.email || 'Desconhecido',
              endpoint: req.originalUrl || req.url,
              limit: config.max,
              windowMs: config.windowMs,
              ip: req.ip || req.headers['x-forwarded-for'] || 'N/A'
            });
          } catch (e) {
            console.error('[DISCORD] Erro ao notificar rate limit:', e.message);
          }
        })();

        const resetTimestamp = Math.floor((resetTime + config.windowMs) / 1000);
        res.setHeader('X-RateLimit-Limit', config.max);
        res.setHeader('X-RateLimit-Remaining', 0);
        res.setHeader('X-RateLimit-Reset', resetTimestamp);
        res.setHeader('X-RateLimit-Type', 'api-key');

        return res.status(429).json({
          success: false,
          error: 'Too Many Requests',
          message: config.message,
          retryAfter
        });
      }

      const resetTimestamp = Math.floor((resetTime + config.windowMs) / 1000);
      res.setHeader('X-RateLimit-Limit', config.max);
      res.setHeader('X-RateLimit-Remaining', Math.max(0, config.max - count));
      res.setHeader('X-RateLimit-Reset', resetTimestamp);
      res.setHeader('X-RateLimit-Type', 'api-key');

      next();
    } catch (error) {
      console.error('[RATE LIMIT] Erro no API Key rate limiter:', error);
      next();
    }
  };
}

/**
 * Rate limiter padrão para API Key (100 req/min)
 */
export const defaultApiKeyRateLimiter = apiKeyRateLimiter();

/**
 * Rate limiter mais restritivo para operações críticas via API Key (50 req/min)
 */
export const strictApiKeyRateLimiter = apiKeyRateLimiter({
  windowMs: 60 * 1000,
  max: 150, // Aumentado de 50 para 150
  message: 'Muitas requisições com esta API Key. Aguarde um momento antes de tentar novamente.'
});

/**
 * Rate limiter para criação de pagamentos via API Key (30 req/min)
 */
export const paymentApiKeyRateLimiter = apiKeyRateLimiter({
  windowMs: 60 * 1000,
  max: 100, // Aumentado de 30 para 100
  message: 'Muitas tentativas de criação de pagamento com esta API Key. Aguarde um momento antes de tentar novamente.'
});

/**
 * Rate limiter para criação de API Keys via API Key (30 req/min)
 */
export const apiKeyCreationApiKeyRateLimiter = apiKeyRateLimiter({
  windowMs: 60 * 1000,
  max: 30, // Aumentado de 3 para 30
  message: 'Muitas tentativas de criação de API Key. Aguarde 1 minuto antes de tentar novamente.'
});

export default apiKeyRateLimiter;

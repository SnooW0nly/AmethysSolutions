/**
 * Rate Limiter específico para autenticação via JWT Token
 * Limita requisições por userId extraído do token JWT
 */

import { verifyToken } from '../services/authService.js';

// Armazena contadores de requisições por userId
const jwtRequestCounts = new Map();

/**
 * Limpa contadores expirados periodicamente
 */
setInterval(() => {
  const now = Date.now();
  for (const [userId, data] of jwtRequestCounts.entries()) {
    if (now - data.resetTime > data.windowMs) {
      jwtRequestCounts.delete(userId);
    }
  }
}, 60000); // Limpa a cada 1 minuto

/**
 * Rate limiter para requisições autenticadas via JWT Token
 * Identifica o usuário pelo userId do token decodificado
 * 
 * @param {Object} options - Opções de configuração
 * @param {number} options.windowMs - Janela de tempo em milissegundos (padrão: 60000 = 1 minuto)
 * @param {number} options.max - Número máximo de requisições por janela (padrão: 60)
 * @param {string} options.message - Mensagem de erro personalizada
 */
export function jwtRateLimiter(options = {}) {
  const config = {
    windowMs: options.windowMs || 60 * 1000, // 1 minuto padrão
    max: options.max || 60, // 60 requisições por minuto padrão
    message: options.message || 'Muitas requisições. Tente novamente em alguns instantes.',
  };

  return async (req, res, next) => {
    try {
      // Tentar extrair userId do token JWT
      const authHeader = req.headers['authorization'];
      let userId = null;

      if (authHeader && authHeader.startsWith('Bearer ')) {
        const token = authHeader.replace('Bearer ', '');

        // Verificar se é um token JWT (tem pontos)
        if (token.includes('.')) {
          try {
            const decoded = await verifyToken(token);
            if (decoded && decoded.userId) {
              userId = decoded.userId;
            }
          } catch (error) {
            // Token inválido, não aplicar rate limit (deixar outros middlewares tratarem)
            return next();
          }
        }
      }

      // Se não conseguiu extrair userId, não aplicar rate limit
      // (pode ser API Key ou requisição não autenticada)
      if (!userId) {
        return next();
      }

      const identifier = `jwt:${userId}`;
      const now = Date.now();

      // Inicializa ou obtém dados do userId
      let data = jwtRequestCounts.get(identifier);

      if (!data || now - data.resetTime > config.windowMs) {
        // Cria novo contador
        data = {
          count: 0,
          resetTime: now,
          windowMs: config.windowMs
        };
        jwtRequestCounts.set(identifier, data);
      }

      // Verifica ANTES de incrementar para bloquear imediatamente quando atingir o limite
      if (data.count >= config.max) {
        const retryAfter = Math.ceil((data.resetTime + config.windowMs - now) / 1000);

        console.warn(`[RATE LIMIT] JWT Token bloqueado temporariamente para userId: ${userId} (${data.count}/${config.max} requisições)`);

        // Define headers informativos mesmo quando bloqueado
        const resetTimestamp = Math.floor((data.resetTime + config.windowMs) / 1000);
        res.setHeader('X-RateLimit-Limit', config.max);
        res.setHeader('X-RateLimit-Remaining', 0);
        res.setHeader('X-RateLimit-Reset', resetTimestamp);
        res.setHeader('X-RateLimit-Type', 'jwt');

        return res.status(429).json({
          success: false,
          error: 'Too Many Requests',
          message: config.message,
          retryAfter
        });
      }

      // Incrementa contador apenas se não excedeu o limite
      data.count++;

      // Define headers informativos
      const resetTimestamp = Math.floor((data.resetTime + config.windowMs) / 1000);
      res.setHeader('X-RateLimit-Limit', config.max);
      res.setHeader('X-RateLimit-Remaining', Math.max(0, config.max - data.count));
      res.setHeader('X-RateLimit-Reset', resetTimestamp);
      res.setHeader('X-RateLimit-Type', 'jwt');

      next();
    } catch (error) {
      // Em caso de erro, continuar sem aplicar rate limit
      console.error('[RATE LIMIT] Erro no JWT rate limiter:', error);
      next();
    }
  };
}

/**
 * Rate limiter padrão para JWT (60 req/min)
 */
export const defaultJwtRateLimiter = jwtRateLimiter();

/**
 * Rate limiter mais restritivo para operações críticas via JWT (30 req/min)
 */
export const strictJwtRateLimiter = jwtRateLimiter({
  windowMs: 60 * 1000,
  max: 30,
  message: 'Muitas requisições. Aguarde um momento antes de tentar novamente.'
});

/**
 * Rate limiter para criação de pagamentos via JWT (20 req/min)
 */
export const paymentJwtRateLimiter = jwtRateLimiter({
  windowMs: 60 * 1000,
  max: 20,
  message: 'Muitas tentativas de criação de pagamento. Aguarde um momento antes de tentar novamente.'
});

/**
 * Rate limiter para criação de API Keys via JWT (30 req/min)
 */
export const apiKeyCreationJwtRateLimiter = jwtRateLimiter({
  windowMs: 60 * 1000,
  max: 30, // Aumentado de 3 para 30
  message: 'Muitas tentativas de criação de API Key. Aguarde 1 minuto antes de tentar novamente.'
});

export default jwtRateLimiter;


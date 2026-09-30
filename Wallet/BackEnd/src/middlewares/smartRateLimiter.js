/**
 * Rate Limiter Inteligente
 * Detecta automaticamente o tipo de autenticação (JWT ou API Key) e aplica o rate limiter apropriado
 */

import { jwtRateLimiter, paymentJwtRateLimiter, strictJwtRateLimiter, apiKeyCreationJwtRateLimiter } from './tokenRateLimiter.js';
import { apiKeyRateLimiter, paymentApiKeyRateLimiter, strictApiKeyRateLimiter, apiKeyCreationApiKeyRateLimiter } from './apiKeyRateLimiter.js';

/**
 * Rate limiter inteligente que detecta o tipo de autenticação
 * Aplica rate limiting baseado em JWT (userId) ou API Key conforme o tipo de autenticação
 * 
 * @param {Object} options - Opções de configuração
 * @param {number} options.jwtWindowMs - Janela de tempo para JWT em milissegundos
 * @param {number} options.jwtMax - Máximo de requisições JWT por janela
 * @param {number} options.apiKeyWindowMs - Janela de tempo para API Key em milissegundos
 * @param {number} options.apiKeyMax - Máximo de requisições API Key por janela
 */
export function smartRateLimiter(options = {}) {
  const jwtLimiter = jwtRateLimiter({
    windowMs: options.jwtWindowMs || 60 * 1000,
    max: options.jwtMax || 60,
    message: options.jwtMessage || 'Muitas requisições. Tente novamente em alguns instantes.'
  });

  const apiKeyLimiter = apiKeyRateLimiter({
    windowMs: options.apiKeyWindowMs || 60 * 1000,
    max: options.apiKeyMax || 1500, // 1500 req/min = 25 req/s
    message: options.apiKeyMessage || 'Muitas requisições com esta API Key. Tente novamente em alguns instantes.'
  });

  return (req, res, next) => {
    // Aplicar ambos os rate limiters
    // Cada um só aplica se detectar seu tipo de autenticação
    jwtLimiter(req, res, (err) => {
      if (err) return next(err);
      apiKeyLimiter(req, res, next);
    });
  };
}

/**
 * Rate limiter padrão inteligente
 * JWT: 60 req/min | API Key: 1500 req/min (25 req/s)
 */
export const defaultSmartRateLimiter = smartRateLimiter();

/**
 * Rate limiter restritivo inteligente
 * JWT: 30 req/min | API Key: 50 req/min
 */
export const strictSmartRateLimiter = smartRateLimiter({
  jwtMax: 30,
  apiKeyMax: 50,
  jwtMessage: 'Muitas requisições. Aguarde um momento antes de tentar novamente.',
  apiKeyMessage: 'Muitas requisições com esta API Key. Aguarde um momento antes de tentar novamente.'
});

/**
 * Rate limiter para criação de pagamentos
 * JWT: 20 req/min | API Key: 30 req/min
 */
export const paymentSmartRateLimiter = (req, res, next) => {
  // Aplicar rate limiter de pagamento para JWT
  paymentJwtRateLimiter(req, res, (err) => {
    if (err) return next(err);
    // Aplicar rate limiter de pagamento para API Key
    paymentApiKeyRateLimiter(req, res, next);
  });
};

/**
 * Rate limiter ultra-restritivo para criação de API Keys
 * JWT: 3 req/min | API Key: 3 req/min
 * Operação muito sensível que precisa de proteção máxima contra spam
 */
export const apiKeyCreationSmartRateLimiter = (req, res, next) => {
  // Aplicar rate limiter ultra-restritivo para JWT
  apiKeyCreationJwtRateLimiter(req, res, (err) => {
    if (err) return next(err);
    // Aplicar rate limiter ultra-restritivo para API Key
    apiKeyCreationApiKeyRateLimiter(req, res, next);
  });
};

export default smartRateLimiter;


/**
 * Rate Limiter para proteger contra ataques de força bruta e DDoS
 * Usa Redis se REDIS_URL estiver configurado (distribuído), caso contrário usa Map em memória.
 */

import { securityConfig } from '../config/security.js';
import { getClientIP } from '../utils/getClientIP.js';
import { incrementCounter } from '../utils/redisClient.js';

// Fallback em memória (usado quando Redis não está disponível)
const requestCounts = new Map();

setInterval(() => {
  const now = Date.now();
  for (const [ip, data] of requestCounts.entries()) {
    if (now - data.resetTime > securityConfig.rateLimit.windowMs) {
      requestCounts.delete(ip);
    }
  }
}, 60000);

/**
 * Middleware de rate limiting genérico
 */
export function rateLimiter(options = {}) {
  const config = {
    windowMs: options.windowMs || securityConfig.rateLimit.windowMs,
    max: options.max || securityConfig.rateLimit.max,
    message: options.message || securityConfig.rateLimit.message,
  };

  return async (req, res, next) => {
    // Obtém IP real do cliente considerando proxies reversos
    const ip = getClientIP(req);
    
    // Verifica se o IP está na whitelist
    const whitelist = securityConfig.rateLimit.whitelist || [];
    if (whitelist.includes(ip)) {
      return next();
    }
    
    const { count, resetTime } = await incrementCounter(`ip:${ip}`, config.windowMs);

    // Define headers informativos
    res.setHeader('X-RateLimit-Limit', config.max);
    res.setHeader('X-RateLimit-Remaining', Math.max(0, config.max - count));
    res.setHeader('X-RateLimit-Reset', new Date(resetTime + config.windowMs).toISOString());

    if (count > config.max) {
      console.warn(`[RATE LIMIT] IP bloqueado temporariamente: ${ip}`);
      return res.status(429).json({
        success: false,
        error: config.message,
        retryAfter: Math.ceil((resetTime + config.windowMs - Date.now()) / 1000),
      });
    }

    next();
  };
}

/**
 * Rate limiter específico para rotas de autenticação baseado em EMAIL (usuário)
 * Usa o email do body da requisição ao invés do IP
 */
const authRequestCounts = new Map();

setInterval(() => {
  const now = Date.now();
  for (const [email, data] of authRequestCounts.entries()) {
    if (now - data.resetTime > securityConfig.rateLimit.auth.windowMs) {
      authRequestCounts.delete(email);
    }
  }
}, 60000);

export const authRateLimiter = async (req, res, next) => {
  const email = req.body?.email;
  if (!email) return next();

  const identifier = email.toLowerCase();
  const config = {
    windowMs: securityConfig.rateLimit.auth.windowMs,
    max: securityConfig.rateLimit.auth.max,
    message: 'Muitas tentativas de login. Tente novamente em 15 minutos.',
  };

  const { count, resetTime } = await incrementCounter(`auth:${identifier}`, config.windowMs);

  res.setHeader('X-RateLimit-Limit', config.max);
  res.setHeader('X-RateLimit-Remaining', Math.max(0, config.max - count));
  res.setHeader('X-RateLimit-Reset', new Date(resetTime + config.windowMs).toISOString());

  if (count > config.max) {
    console.warn(`[RATE LIMIT] Email bloqueado temporariamente: ${identifier}`);
    return res.status(429).json({
      success: false,
      error: config.message,
      retryAfter: Math.ceil((resetTime + config.windowMs - Date.now()) / 1000),
    });
  }

  next();
};

/**
 * Rate limiter para rotas de API gerais
 */
export const apiRateLimiter = rateLimiter();

export default rateLimiter;

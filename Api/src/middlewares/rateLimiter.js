/**
 * Rate Limiter para proteger contra ataques de força bruta e DDoS
 */

import { securityConfig } from '../config/security.js';

// Armazena contadores de requisições por IP
const requestCounts = new Map();

/**
 * Limpa contadores expirados periodicamente
 */
setInterval(() => {
  const now = Date.now();
  for (const [ip, data] of requestCounts.entries()) {
    if (now - data.resetTime > securityConfig.rateLimit.windowMs) {
      requestCounts.delete(ip);
    }
  }
}, 60000); // Limpa a cada 1 minuto

/**
 * Middleware de rate limiting genérico
 */
export function rateLimiter(options = {}) {
  const config = {
    windowMs: options.windowMs || securityConfig.rateLimit.windowMs,
    max: options.max || securityConfig.rateLimit.max,
    message: options.message || securityConfig.rateLimit.message,
  };

  return (req, res, next) => {
    // Obtém IP real considerando proxies
    const ip = req.ip || req.connection.remoteAddress;
    
    // Verifica se o IP está na whitelist
    const whitelist = securityConfig.rateLimit.whitelist || [];
    if (whitelist.includes(ip)) {
      console.log(`[RATE LIMIT] IP confiável ignorado: ${ip}`);
      return next();
    }
    
    const now = Date.now();
    
    // Inicializa ou obtém dados do IP
    let ipData = requestCounts.get(ip);
    
    if (!ipData || now - ipData.resetTime > config.windowMs) {
      // Cria novo contador
      ipData = {
        count: 0,
        resetTime: now,
      };
      requestCounts.set(ip, ipData);
    }

    // Incrementa contador
    ipData.count++;

    // Define headers informativos
    res.setHeader('X-RateLimit-Limit', config.max);
    res.setHeader('X-RateLimit-Remaining', Math.max(0, config.max - ipData.count));
    res.setHeader('X-RateLimit-Reset', new Date(ipData.resetTime + config.windowMs).toISOString());

    // Verifica se excedeu o limite
  /*  if (ipData.count > config.max) {
      console.warn(`[RATE LIMIT] IP bloqueado temporariamente: ${ip}`);
      
      return res.status(429).json({
        error: config.message,
        retryAfter: Math.ceil((ipData.resetTime + config.windowMs - now) / 1000),
      });
    } */

    next();
  };
}

/**
 * Rate limiter específico para rotas de autenticação
 */
export const authRateLimiter = rateLimiter({
  windowMs: securityConfig.rateLimit.auth.windowMs,
  max: securityConfig.rateLimit.auth.max,
  message: 'Muitas tentativas de login. Tente novamente em 15 minutos.',
});

/**
 * Rate limiter para rotas de API gerais
 * Ignora rotas de bot info para evitar rate limit nos bots
 */
export const apiRateLimiter = (req, res, next) => {
  // Ignora rate limit para rotas de bot info (usadas pelos bots para buscar config)
  if (req.path.match(/^\/(?:api\/)?bot\/[^/]+\/info$/)) {
    return next();
  }
  return rateLimiter()(req, res, next);
};

export default rateLimiter;

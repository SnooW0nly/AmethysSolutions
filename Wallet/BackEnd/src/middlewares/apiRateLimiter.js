/**
 * Rate Limiter específico para rotas da API Amethys Wallet
 * Baseado na documentação: 60 req/min para rotas gerais, 30s cooldown para register
 */

import { securityConfig } from '../config/security.js';
import { getClientIP } from '../utils/getClientIP.js';

// Armazena contadores de requisições por API Key ou IP
const requestCounts = new Map();

/**
 * Limpa contadores expirados periodicamente
 */
setInterval(() => {
  const now = Date.now();
  for (const [key, data] of requestCounts.entries()) {
    if (now - data.resetTime > data.windowMs) {
      requestCounts.delete(key);
    }
  }
}, 60000); // Limpa a cada 1 minuto

/**
 * Obtém identificador único para rate limiting
 */
function getIdentifier(req) {
  // Priorizar API Key do usuário (começa com 'vp_') se disponível
  // NÃO usar o X-API-Key do frontend (validação de origem)
  const headerApiKey = req.headers['x-api-key'];
  const authToken = req.headers['authorization']?.replace('Bearer ', '');
  const apiKey = (headerApiKey && headerApiKey.startsWith('vp_'))
    ? headerApiKey
    : (authToken && authToken.startsWith('vp_') ? authToken : null);
  if (apiKey) {
    return `apiKey:${apiKey}`;
  }

  // Fallback para IP real do cliente
  return `ip:${getClientIP(req)}`;
}

/**
 * Rate limiter para rotas gerais da API (10 req/s = 600 req/min)
 */
export function apiRateLimiter(req, res, next) {
  const identifier = getIdentifier(req);
  const windowMs = 1000; // 1 segundo
  const max = 10; // 10 requisições por segundo

  const now = Date.now();

  // Inicializa ou obtém dados do identificador
  let data = requestCounts.get(identifier);

  if (!data || now - data.resetTime > windowMs) {
    data = {
      count: 0,
      resetTime: now,
      windowMs
    };
    requestCounts.set(identifier, data);
  }

  // Incrementa contador
  data.count++;

  // Define headers informativos
  const resetTimestamp = Math.floor((data.resetTime + windowMs) / 1000);
  res.setHeader('X-RateLimit-Limit', max);
  res.setHeader('X-RateLimit-Remaining', Math.max(0, max - data.count));
  res.setHeader('X-RateLimit-Reset', resetTimestamp);

  // Verifica se excedeu o limite
  if (data.count > max) {
    const retryAfter = Math.ceil((data.resetTime + windowMs - now) / 1000);

    return res.status(429).json({
      success: false,
      error: 'Too Many Requests',
      message: `Rate limit exceeded. Please try again in ${retryAfter} seconds`,
      retryAfter
    });
  }

  next();
}

/**
 * Rate limiter para endpoint de registro (30 segundos entre requisições)
 */
const registerLastRequest = new Map();

export function registerRateLimiter(req, res, next) {
  const identifier = getIdentifier(req);
  const cooldownMs = 30 * 1000; // 30 segundos
  const now = Date.now();

  const lastRequest = registerLastRequest.get(identifier);

  if (lastRequest && (now - lastRequest) < cooldownMs) {
    const waitTime = Math.ceil((cooldownMs - (now - lastRequest)) / 1000);

    return res.status(429).json({
      success: false,
      error: 'Too Many Requests',
      message: `Aguarde ${waitTime} segundos antes de atualizar novamente`,
      retryAfter: waitTime
    });
  }

  // Atualiza timestamp da última requisição
  registerLastRequest.set(identifier, now);

  // Headers informativos
  res.setHeader('X-RateLimit-Limit', '1 per 30s');
  res.setHeader('X-RateLimit-Remaining', '0');
  res.setHeader('X-RateLimit-Reset', Math.floor((now + cooldownMs) / 1000));

  next();
}

/**
 * Rate limiter para rotas admin (mais restritivo)
 */
export function adminRateLimiter(req, res, next) {
  const identifier = getIdentifier(req);
  const windowMs = 60 * 1000; // 1 minuto
  const max = 30; // 30 requisições por minuto para admin

  const now = Date.now();

  let data = requestCounts.get(`admin:${identifier}`);

  if (!data || now - data.resetTime > windowMs) {
    data = {
      count: 0,
      resetTime: now,
      windowMs
    };
    requestCounts.set(`admin:${identifier}`, data);
  }

  data.count++;

  const resetTimestamp = Math.floor((data.resetTime + windowMs) / 1000);
  res.setHeader('X-RateLimit-Limit', max);
  res.setHeader('X-RateLimit-Remaining', Math.max(0, max - data.count));
  res.setHeader('X-RateLimit-Reset', resetTimestamp);

  if (data.count > max) {
    const retryAfter = Math.ceil((data.resetTime + windowMs - now) / 1000);

    return res.status(429).json({
      success: false,
      error: 'Too Many Requests',
      message: `Rate limit exceeded. Please try again in ${retryAfter} seconds`,
      retryAfter
    });
  }

  next();
}

/**
 * Rate limiter para rotas públicas (mais permissivo)
 */
export function publicRateLimiter(req, res, next) {
  const ip = getClientIP(req);
  const windowMs = 60 * 1000; // 1 minuto
  const max = 120; // 120 requisições por minuto para rotas públicas

  const now = Date.now();

  let data = requestCounts.get(`public:${ip}`);

  if (!data || now - data.resetTime > windowMs) {
    data = {
      count: 0,
      resetTime: now,
      windowMs
    };
    requestCounts.set(`public:${ip}`, data);
  }

  data.count++;

  const resetTimestamp = Math.floor((data.resetTime + windowMs) / 1000);
  res.setHeader('X-RateLimit-Limit', max);
  res.setHeader('X-RateLimit-Remaining', Math.max(0, max - data.count));
  res.setHeader('X-RateLimit-Reset', resetTimestamp);

  if (data.count > max) {
    const retryAfter = Math.ceil((data.resetTime + windowMs - now) / 1000);

    return res.status(429).json({
      success: false,
      error: 'Too Many Requests',
      message: `Rate limit exceeded. Please try again in ${retryAfter} seconds`,
      retryAfter
    });
  }

  next();
}


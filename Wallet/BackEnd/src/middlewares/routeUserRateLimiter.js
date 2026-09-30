import { securityConfig } from '../config/security.js';
import { getClientIP } from '../utils/getClientIP.js';
import { incrementCounter } from '../utils/redisClient.js';

// Fallback em memória para controle de bloqueios temporários
const routeUserCounts = new Map();

setInterval(() => {
    const now = Date.now();
    for (const [key, data] of routeUserCounts.entries()) {
        if (now > data.resetTime && (!data.blockedUntil || now > data.blockedUntil)) {
            routeUserCounts.delete(key);
        }
    }
}, 60000);

/**
 * Middleware to limit specific routes per user.
 * If a user hits the same route > limit times in windowMs, they get blocked for 5 seconds.
 * 
 * @param {Object} options
 * @param {number} options.windowMs - Window size in ms (default: 1000ms)
 * @param {number} options.max - Max requests per window (default: 5)
 * @param {number} options.blockDurationMs - Block duration in ms (default: 5000ms)
 */
export function routeUserRateLimiter(options = {}) {
    const windowMs = options.windowMs || 1000; // 1 second default window
    const max = options.max || 5; // 5 requests per second default
    const blockDurationMs = options.blockDurationMs || 5000; // 5 seconds block

    return async (req, res, next) => {
        const clientIP = getClientIP(req);
        const routePath = req.originalUrl || req.path || '';

        const whitelist = securityConfig.rateLimit?.whitelist || [];
        if (whitelist.includes(clientIP) || clientIP === '15.204.233.46') return next();

        if (
            routePath === '/health' ||
            routePath.startsWith('/api/health') ||
            routePath === '/api/healthz' ||
            routePath === '/healthz'
        ) return next();

        const userId = req.user?.id || clientIP;
        const key = `${userId}:${routePath}`;
        const now = Date.now();

        // Verificar bloqueio ativo (mantido em memória local para velocidade)
        const localData = routeUserCounts.get(key);
        if (localData?.blockedUntil && now < localData.blockedUntil) {
            const retryAfter = Math.ceil((localData.blockedUntil - now) / 1000);
            return res.status(429).json({
                success: false,
                error: `Muitas requisições para esta rota. Aguarde ${retryAfter} segundos.`,
                retryAfter
            });
        }

        const { count } = await incrementCounter(`route:${key}`, windowMs);

        if (count > max) {
            const blockedUntil = now + blockDurationMs;
            routeUserCounts.set(key, { blockedUntil, resetTime: now + windowMs });
            console.warn(`[RATE LIMIT] User ${userId} blocked on ${routePath} for ${blockDurationMs}ms`);
            return res.status(429).json({
                success: false,
                error: `Muitas requisições. Aguarde ${blockDurationMs / 1000} segundos.`,
                retryAfter: blockDurationMs / 1000
            });
        }

        next();
    };
}

export default routeUserRateLimiter;
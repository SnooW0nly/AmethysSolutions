import rateLimit from 'express-rate-limit';
import { getClientIP } from '../utils/getClientIP.js';

const AUTH_TOKEN = process.env.DEFENSE_AUTH_TOKEN || 'LOOP_FIREWALL';
let rateLimitEnabled = false;
let aggressiveCacheEnabled = false;
let maintenanceMode = false;
let blockedIPs = new Set();

// Middleware de autenticação para endpoints admin
export const authMiddleware = (req, res, next) => {
  if (req.headers['authorization'] !== AUTH_TOKEN) {
    return res.status(401).json({
      success: false,
      error: 'Unauthorized'
    });
  }
  next();
};

// Configuração do rate limiter dinâmico
const configureRateLimiter = (maxRequests = 10, windowMs = 60000) => {
  return rateLimit({
    windowMs,
    max: maxRequests,
    message: {
      success: false,
      error: 'Too many requests'
    },
    skip: (req) => !rateLimitEnabled,
    // Usar função customizada para obter IP ao invés de confiar no trust proxy
    keyGenerator: (req) => {
      return getClientIP(req);
    }
  });
};

export const dynamicRateLimiter = configureRateLimiter();

// Middleware de bloqueio de IP
export const ipBlockMiddleware = (req, res, next) => {
  const clientIP = getClientIP(req);
  if (blockedIPs.has(clientIP)) {
    return res.status(403).json({
      success: false,
      error: 'IP blocked'
    });
  }
  next();
};

// Middleware de modo de manutenção
export const maintenanceMiddleware = (req, res, next) => {
  if (maintenanceMode && !req.path.startsWith('/admin/') && !req.path.startsWith('/health') && !req.path.startsWith('/api/health')) {
    return res.status(503).json({
      success: false,
      error: 'Service temporarily unavailable'
    });
  }
  next();
};

// Middleware de cache agressivo
export const cacheMiddleware = (req, res, next) => {
  if (aggressiveCacheEnabled && req.method === 'GET') {
    res.set({
      'Cache-Control': 'public, max-age=300',
      'Expires': new Date(Date.now() + 300000).toUTCString()
    });
  }
  next();
};

// Rotas de administração do sistema de defesa
export const setupDefenseRoutes = (app) => {
  // Health check público - MINIMAL INFO ONLY
  app.get('/health', (req, res) => {
    res.json({
      success: true,
      status: 'ok',
      timestamp: Date.now()
    });
  });

  // Ativar rate limiting
  app.post('/admin/rate-limit/enable', authMiddleware, (req, res) => {
    const { maxRequests = 10, windowMs = 60000 } = req.body;
    rateLimitEnabled = true;
    res.json({
      success: true,
      message: 'Rate limiting enabled',
      config: { maxRequests, windowMs }
    });
  });

  // Desativar rate limiting
  app.post('/admin/rate-limit/disable', authMiddleware, (req, res) => {
    rateLimitEnabled = false;
    res.json({
      success: true,
      message: 'Rate limiting disabled'
    });
  });

  // Bloquear IP
  app.post('/admin/block-ip', authMiddleware, (req, res) => {
    const { ip } = req.body;
    if (!ip) return res.status(400).json({
      success: false,
      error: 'IP is required'
    });
    blockedIPs.add(ip);
    res.json({
      success: true,
      message: `IP ${ip} blocked`,
      totalBlocked: blockedIPs.size
    });
  });

  // Desbloquear IP
  app.post('/admin/unblock-ip', authMiddleware, (req, res) => {
    const { ip } = req.body;
    blockedIPs.delete(ip);
    res.json({
      success: true,
      message: `IP ${ip} unblocked`
    });
  });

  // Gerenciar cache
  app.post('/admin/clear-cache', authMiddleware, (req, res) => {
    const { action } = req.body;
    aggressiveCacheEnabled = action === 'aggressive_cache';
    res.json({
      success: true,
      message: aggressiveCacheEnabled ? 'Aggressive cache enabled' : 'Cache cleared'
    });
  });

  // Modo de manutenção
  app.post('/admin/maintenance', authMiddleware, (req, res) => {
    const { mode, duration } = req.body;
    if (mode === 'partial') {
      maintenanceMode = true;
      if (duration) {
        setTimeout(() => { maintenanceMode = false; }, duration * 1000);
      }
      res.json({
        success: true,
        message: 'Maintenance mode enabled',
        duration
      });
    } else {
      maintenanceMode = false;
      res.json({
        success: true,
        message: 'Maintenance mode disabled'
      });
    }
  });

  // Status do sistema de defesa
  app.get('/admin/defense-status', authMiddleware, (req, res) => {
    res.json({
      success: true,
      rateLimitEnabled,
      aggressiveCacheEnabled,
      maintenanceMode,
      blockedIPs: Array.from(blockedIPs),
      totalBlockedIPs: blockedIPs.size
    });
  });
};


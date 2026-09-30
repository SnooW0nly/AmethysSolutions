/**
 * Middleware para configurar headers de segurança HTTP
 * Protege contra vulnerabilidades comuns (XSS, clickjacking, etc.)
 */

import { securityConfig } from '../config/security.js';

/**
 * Aplica headers de segurança em todas as respostas
 */
export default function securityHeaders(req, res, next) {
  // Remove header que expõe tecnologia usada
  res.removeHeader('X-Powered-By');

  // Previne clickjacking
  res.setHeader('X-Frame-Options', 'DENY');

  // Previne MIME sniffing
  res.setHeader('X-Content-Type-Options', 'nosniff');

  // Ativa proteção XSS do navegador
  res.setHeader('X-XSS-Protection', '1; mode=block');

  // Força HTTPS em produção
  if (process.env.NODE_ENV === 'production') {
    res.setHeader(
      'Strict-Transport-Security',
      `max-age=${securityConfig.headers.hsts.maxAge}; includeSubDomains; preload`
    );
  }

  // Content Security Policy
  const csp = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');

  res.setHeader('Content-Security-Policy', csp);

  // Previne que o navegador envie o Referer para outros domínios
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');

  // Controla quais features do navegador podem ser usadas
  res.setHeader(
    'Permissions-Policy',
    'geolocation=(), microphone=(), camera=(), payment=()'
  );

  // Adiciona ID único para rastreamento de requisições
  const requestId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  res.setHeader('X-Request-ID', requestId);
  req.requestId = requestId;

  next();
}

/**
 * Middleware para logging de requisições suspeitas
 */
export function suspiciousActivityLogger(req, res, next) {
  const suspiciousPatterns = [
    // Path traversal
    /(\.\.\/)|(\.\.\\)|(\/etc\/)|(\/proc\/)|(\/sys\/)|(%2e%2e)|(%252e)/i,
    // SQL injection
    /(union.*select|insert.*into|drop.*table|delete.*from|update.*set|'.*or.*'|".*or.*")/i,
    // XSS - Only in URL and body, not query params or headers
    /(<script|javascript:|onerror=|onload=|onclick=|onmouseover=|onfocus=|<iframe|<img.*onerror)/i,
    // Code injection - must be in URL/body context
    /(eval\(|exec\(|system\(|spawn\(|child_process)/i,
    // Null byte injection
    /(%00|\\x00)/i,
  ];

  // Only check URL and body - NOT User-Agent (has semicolons normally) or query params (too many false positives)
  const urlToCheck = `${req.url || ''} ${req.originalUrl || ''}`;
  const bodyToCheck = JSON.stringify(req.body || {});

  for (const pattern of suspiciousPatterns) {
    if (pattern.test(urlToCheck) || pattern.test(bodyToCheck)) {
      const clientIP = req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown';
      console.error('[SECURITY] ⚠️ ATIVIDADE SUSPEITA DETECTADA!');
      console.error(`[SECURITY] IP: ${clientIP}`);
      console.error(`[SECURITY] URL: ${req.originalUrl || req.url}`);
      console.error(`[SECURITY] Method: ${req.method}`);
      console.error(`[SECURITY] Pattern matched: ${pattern}`);
      console.error(`[SECURITY] Timestamp: ${new Date().toISOString()}`);

      return res.status(403).json({
        success: false,
        error: 'Requisição bloqueada por motivos de segurança',
      });
    }
  }

  next();
}


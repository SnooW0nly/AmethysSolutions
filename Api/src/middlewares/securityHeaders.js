import { securityConfig } from '../config/security.js';

const ALLOWED_FRAME_ANCESTORS = [
  "https://amethys.solutions",
  "https://*.amethys.solutions",
  "https://amethysapp.vercel.app",
  "https://amethysapplications.com.br",
  "http://localhost:3000",
  "http://localhost:3001",
];

export default function securityHeaders(req, res, next) {
  res.removeHeader('X-Powered-By');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-XSS-Protection', '1; mode=block');

  if (process.env.NODE_ENV === 'production') {
    res.setHeader(
      'Strict-Transport-Security',
      `max-age=${securityConfig.headers.hsts.maxAge}; includeSubDomains; preload`
    );
  }

  const isTranscriptHtml = req.path.match(/\/api\/v1\/transcript\/[^/]+\/html$/);

  if (isTranscriptHtml) {
    const frameAncestors = ALLOWED_FRAME_ANCESTORS.join(' ');

    const csp = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https: http:",
      "font-src 'self' data: https:",
      "connect-src 'self'",
      `frame-ancestors ${frameAncestors}`,
      "base-uri 'self'",
    ].join('; ');

    res.setHeader('Content-Security-Policy', csp);

  } else {
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
    res.setHeader('X-Frame-Options', 'DENY');
  }

  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader(
    'Permissions-Policy',
    'geolocation=(), microphone=(), camera=(), payment=()'
  );

  const requestId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  res.setHeader('X-Request-ID', requestId);
  req.requestId = requestId;

  next();
}

export function suspiciousActivityLogger(req, res, next) {
  const suspiciousPatterns = [
    /(\.\.|\/etc\/|\/proc\/|\/sys\/)/i,
    /(union.*select|insert.*into|drop.*table)/i,
    /(<script|javascript:|onerror=|onload=)/i,
    /(eval\(|exec\(|system\()/i,
  ];

  const checkString = `${req.url} ${JSON.stringify(req.query)} ${JSON.stringify(req.body)}`;

  for (const pattern of suspiciousPatterns) {
    if (pattern.test(checkString)) {
      console.error('[SECURITY] Atividade suspeita detectada!');
      console.error(`[SECURITY] IP: ${req.ip}`);
      console.error(`[SECURITY] URL: ${req.url}`);
      console.error(`[SECURITY] User-Agent: ${req.headers['user-agent']}`);
      console.error(`[SECURITY] Pattern: ${pattern}`);

      return res.status(403).json({
        error: 'Requisição bloqueada por motivos de segurança',
      });
    }
  }

  next();
}
import "./config/env.js";
import { FRONTEND_URL, FRONTEND_URL_SECONDARY } from "./config/env.js";

import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

import dbConnect from "./database/db.js";
import routes from "./routes/index.js";
import errorHandler from "./middlewares/errorHandler.js";
import corsOptions, { corsLogger } from "./config/cors.js";
import { validateEnvironment, securityConfig } from "./config/security.js";
import securityHeaders, { suspiciousActivityLogger } from "./middlewares/securityHeaders.js";
import {
  ipBlockMiddleware,
  maintenanceMiddleware,
  setupDefenseRoutes
} from "./middlewares/defense.js";
import routeUserRateLimiter from "./middlewares/routeUserRateLimiter.js";
import { getClientIP } from "./utils/getClientIP.js";
import { validateFrontendApiKey } from "./middlewares/frontendApiKey.js";

// ========================= SECURITY CONFIGURATION =========================
validateEnvironment();

// ========================= DATABASE CONNECTION =========================
await dbConnect();

const app = express();

// ========================= TRUST PROXY =========================
// Confiar em todos os proxies (útil para Cloudflare, nginx, etc.)
// Isso permite que req.ip e req.connection.remoteAddress retornem o IP real do cliente
app.set("trust proxy", true);

// ========================= CORS (DEVE VIR PRIMEIRO) =========================
// CORS deve ser processado ANTES de qualquer middleware que possa retornar erro
// Caso contrário, erros de outros middlewares serão interpretados como erro de CORS
app.use(corsLogger);
app.use(cors(corsOptions));

// ========================= DEFENSE SYSTEM =========================
app.use(ipBlockMiddleware);
app.use(maintenanceMiddleware);
// app.use(cacheMiddleware); // Removed
app.use(routeUserRateLimiter({ windowMs: 2000, max: 30, blockDurationMs: 5000 }));

// ========================= SECURITY HEADERS =========================
app.use(securityHeaders);
app.use(suspiciousActivityLogger);

// ========================= FILE ACCESS BLOCKER =========================
// CRITICAL: Block access to source files, sensitive extensions AND path traversal
app.use((req, res, next) => {
  const reqPath = (req.path || '').toLowerCase();
  const originalUrl = (req.originalUrl || '').toLowerCase();

  // ==> CRITICAL: Block path traversal attempts FIRST <==
  const pathTraversalPatterns = [
    /\.\./,           // Basic path traversal
    /%2e%2e/i,        // URL encoded ..
    /%252e%252e/i,    // Double URL encoded ..
    /\.%2e/i,         // Mixed encoding
    /%2e\./i,         // Mixed encoding
    /\.\.\\/,         // Windows path traversal
    /\.\.\//,         // Unix path traversal
  ];

  const hasPathTraversal = pathTraversalPatterns.some(pattern =>
    pattern.test(reqPath) || pattern.test(originalUrl) || pattern.test(decodeURIComponent(originalUrl))
  );

  if (hasPathTraversal) {
    const clientIP = getClientIP(req);
    console.error(`[SECURITY] 🚨 PATH TRAVERSAL BLOQUEADO!`);
    console.error(`[SECURITY] IP: ${clientIP}`);
    console.error(`[SECURITY] Path: ${req.originalUrl}`);
    console.error(`[SECURITY] User-Agent: ${req.headers['user-agent']}`);
    console.error(`[SECURITY] Timestamp: ${new Date().toISOString()}`);

    return res.status(403).json({
      success: false,
      error: 'Acesso negado'
    });
  }

  const blockedExtensions = ['.env', '.git', '.config', '.md', '.lock', '.js', '.json', '.ts'];
  const blockedPaths = [
    '/.env', '/src/', '/node_modules/', '/scripts/', '/.git/',
    '/package.json', '/package-lock.json', '/server.js', '/discloud.config',
    '/.gitignore', '/docs/', '/config.json', '/database/'
  ];

  // Block sensitive file extensions (except uploads and API routes)
  const isSensitiveExtension = blockedExtensions.some(ext =>
    reqPath.endsWith(ext) || originalUrl.endsWith(ext)
  );

  // Block access to source paths
  const isSensitivePath = blockedPaths.some(blocked =>
    reqPath.includes(blocked) || originalUrl.includes(blocked)
  );

  // Allow only specific routes
  const isAllowedRoute = reqPath.startsWith('/uploads') ||
    reqPath.startsWith('/api') ||
    reqPath.startsWith('/health') ||
    reqPath.startsWith('/admin') ||
    reqPath.startsWith('/auth') ||
    reqPath.startsWith('/profile') ||
    reqPath.startsWith('/affiliates') ||
    reqPath.startsWith('/tickets') ||
    reqPath.startsWith('/v1');

  if ((isSensitiveExtension || isSensitivePath) && !isAllowedRoute) {
    const clientIP = getClientIP(req);
    console.error(`[SECURITY BLOCK] Tentativa de acesso a arquivo sensível bloqueada!`);
    console.error(`[SECURITY BLOCK] IP: ${clientIP}`);
    console.error(`[SECURITY BLOCK] Path: ${req.originalUrl}`);
    console.error(`[SECURITY BLOCK] User-Agent: ${req.headers['user-agent']}`);
    console.error(`[SECURITY BLOCK] Timestamp: ${new Date().toISOString()}`);

    return res.status(403).json({
      success: false,
      error: 'Acesso negado'
    });
  }

  next();
});

// ========================= BODY PARSER =========================
app.use('/api/v1/goatpay-webhook', express.raw({ type: 'application/json', limit: '1mb' }));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// ========================= FRONTEND API KEY VALIDATION =========================
// Validates X-API-Key header to ensure requests come from authorized frontend
app.use(validateFrontendApiKey);

// ========================= REQUEST SIGNING VALIDATION =========================
// Validates HMAC signature on sensitive operations (withdrawals, transfers)
// to prevent intercept/modification attacks
import { validateRequestSignature } from './middlewares/requestSigning.js';
app.use(validateRequestSignature);

// ========================= DASHBOARD-ONLY GUARD FOR AUTH ME =========================
// Drop external /api/auth/me requests before logging to avoid log flooding
// Permite IPs confiáveis do backend mesmo que a origem não esteja autorizada
app.use((req, res, next) => {
  const path = req.path || req.originalUrl || '';
  if (path === '/api/auth/me') {
    const origin = req.headers['origin'];
    const referer = req.headers['referer'];
    const clientIP = getClientIP(req);
    const nodeEnv = process.env.NODE_ENV || 'development';

    // IPs confiáveis do backend que devem ter acesso permitido
    const TRUSTED_BACKEND_IPS = [
      '15.204.233.46', // IP do backend
      ...(process.env.TRUSTED_BACKEND_IPS
        ? process.env.TRUSTED_BACKEND_IPS.split(',').map(ip => ip.trim())
        : []
      ),
    ];

    // Se for um IP confiável do backend, permite o acesso
    if (TRUSTED_BACKEND_IPS.includes(clientIP)) {
      return next();
    }

    if (nodeEnv === 'idk' /* placeholder to keep formatting */) { /* no-op */ }
    if ((process.env.NODE_ENV || 'development') === 'production') {
      const allowedOrigins = [FRONTEND_URL, FRONTEND_URL_SECONDARY].filter(Boolean);
      const fromAllowedOrigin =
        (typeof origin === 'string' && allowedOrigins.includes(origin)) ||
        (typeof referer === 'string' && allowedOrigins.some(o => referer.startsWith(o)));
      if (!fromAllowedOrigin) {
        return res.status(403).json({
          success: false,
          error: 'Acesso negado. Requisições devem ser feitas através da dashboard.',
        });
      }
    }
  }
  return next();
});

// ========================= REQUEST LOGGER =========================
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();

  // Não logar informações sensíveis
  // Remover query params e IDs sensíveis da URL
  let sanitizedUrl = req.originalUrl;

  // Não logar rotas de webhook/adquirente (monitoramento externo)
  if (sanitizedUrl.includes('/goatpay-webhook') || sanitizedUrl.includes('/goatpay/')) {
    return next();
  }

  // Remover query params que podem conter informações sensíveis
  if (sanitizedUrl.includes('?')) {
    sanitizedUrl = sanitizedUrl.split('?')[0];
  }

  // Ofuscar IDs longos (provavelmente são UIDs ou tokens)
  sanitizedUrl = sanitizedUrl.replace(/\/[a-f0-9]{32,}/gi, '/[ID]');

  // Não logar rotas de pagamento/depósito com detalhes
  if (sanitizedUrl.includes('/payment') || sanitizedUrl.includes('/deposit')) {
    sanitizedUrl = sanitizedUrl.replace(/\/payment\/.*/, '/payment/[ID]');
  }

  console.log(`[${timestamp}] ${req.method} ${sanitizedUrl}`);
  next();
});

// ========================= DEFENSE ROUTES =========================
setupDefenseRoutes(app);

// ========================= STATIC FILES =========================
// Secured static file serving with explicit options
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

app.use("/uploads", express.static(join(__dirname, '../database/uploads'), {
  dotfiles: 'deny',        // Block dotfiles (.env, .git, etc)
  index: false,            // Disable directory indexing
  redirect: false,         // Disable redirect for directories
  fallthrough: false,      // Return 404 immediately if file not found
}));

// ========================= ROTAS =========================
app.use("/", routes);
app.use("/api", routes);

// ========================= 404 HANDLER =========================
app.use((req, res, next) => {
  console.warn(`[404] Rota não encontrada: ${req.method} ${req.originalUrl}`);
  res.status(404).json({
    success: false,
    error: "Rota não encontrada",
    path: req.originalUrl
  });
});

// ========================= ERROR HANDLER =========================
app.use(errorHandler);

export default app;


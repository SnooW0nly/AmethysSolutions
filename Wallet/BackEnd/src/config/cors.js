/**
 * Configuração avançada de CORS para produção
 * Garante que apenas domínios autorizados possam acessar a API
 */

import { getClientIP } from '../utils/getClientIP.js';

// IPs confiáveis do backend que devem ter acesso permitido independentemente da origem
const TRUSTED_BACKEND_IPS = [
  '15.204.233.46', // IP do backend
  ...(process.env.TRUSTED_BACKEND_IPS
    ? process.env.TRUSTED_BACKEND_IPS.split(',').map(ip => ip.trim())
    : []
  ),
];

// Map temporário para armazenar informações de requisições confiáveis
// Usa um identificador único baseado em timestamp + IP para evitar colisões
const trustedRequests = new Map();

// Limpa requisições antigas a cada 5 segundos
setInterval(() => {
  const now = Date.now();
  for (const [key, data] of trustedRequests.entries()) {
    if (now - data.timestamp > 5000) {
      trustedRequests.delete(key);
    }
  }
}, 5000);

const ALLOWED_ORIGINS = [
  process.env.FRONTEND_URL, // URL do frontend em produção
  process.env.FRONTEND_URL_SECONDARY, // URL secundária (opcional)
  // Suporte para múltiplas URLs via FRONTEND_URLS (separadas por vírgula)
  ...(process.env.FRONTEND_URLS
    ? process.env.FRONTEND_URLS.split(',').map(url => url.trim())
    : []
  ),
].filter(Boolean); // Remove valores undefined/null

/**
 * Valida se a origem da requisição está autorizada
 * @param {string} origin - Origem da requisição
 * @param {object} req - Objeto de requisição Express (opcional, para verificação de IP)
 */
function isOriginAllowed(origin, req = null) {
  const nodeEnv = process.env.NODE_ENV || 'development';

  // Verifica se o IP do cliente está na lista de IPs confiáveis do backend
  // Se for um IP confiável, permite independentemente da origem
  if (req) {
    const clientIP = getClientIP(req);
    if (TRUSTED_BACKEND_IPS.includes(clientIP)) {
      console.log(`[CORS] ✅ Acesso permitido para IP confiável do backend: ${clientIP}`);
      return true;
    }
  }

  // Requisições sem origin são same-origin requests (mesmo domínio)
  // Isso é comum quando o frontend e backend estão no mesmo domínio
  if (!origin) {
    // Em produção, só permite se não houver origem (same-origin)
    // Isso é seguro porque requisições same-origin não passam por CORS
    if (nodeEnv === 'production') {
      return true;
    }
    // Em desenvolvimento, permite apenas se houver FRONTEND_URL configurado
    // Caso contrário, bloqueia para forçar uso de origem explícita
    return false;
  }

  // Permitir todas as URLs de preview da Vercel do projeto
  // Padrão: https://vision-wallet-XXXX-carlos-projects-4555788f.vercel.app
  const vercelPreviewPattern = /^https:\/\/vision-wallet-[a-z0-9]+-carlos-projects-4555788f\.vercel\.app$/;
  if (vercelPreviewPattern.test(origin)) {
    console.log(`[CORS] ✅ Vercel preview URL permitida: ${origin}`);
    return true;
  }

  // Em desenvolvimento, permite apenas localhost/127.0.0.1 E se estiver na lista de origens permitidas
  if (nodeEnv === 'development') {
    const isLocalhost = origin.includes('localhost') ||
      origin.includes('127.0.0.1') ||
      origin.includes('0.0.0.0');

    // Se for localhost E estiver na lista de origens permitidas, permite
    if (isLocalhost && ALLOWED_ORIGINS.length > 0) {
      return ALLOWED_ORIGINS.some(allowed => origin.includes(allowed) || allowed.includes(origin));
    }

    // Se não houver origens configuradas em dev, permite localhost (fallback)
    if (isLocalhost && ALLOWED_ORIGINS.length === 0) {
      return true;
    }

    return false;
  }

  // Em produção, SEMPRE valida contra lista de origens permitidas
  if (ALLOWED_ORIGINS.length === 0) {
    console.error('[CORS] ❌ ERRO CRÍTICO: Nenhuma origem permitida configurada em produção. Bloqueando todas as requisições.');
    return false; // BLOQUEIA se não houver configuração
  }

  return ALLOWED_ORIGINS.includes(origin);
}

/**
 * Configuração CORS otimizada
 */
export const corsOptions = {
  // Validação dinâmica de origem (RESTRITIVA)
  origin: function (origin, callback) {
    const nodeEnv = process.env.NODE_ENV || 'development';

    // Verifica se há uma requisição confiável pendente para esta origem
    // O corsLogger define isso antes do CORS ser processado
    let isTrustedRequest = false;
    let matchedKey = null;

    for (const [key, data] of trustedRequests.entries()) {
      // Verifica se a origem corresponde ou se ambas são null/undefined
      if ((data.origin === origin) || (!origin && !data.origin)) {
        isTrustedRequest = true;
        matchedKey = key;
        break;
      }
    }

    // Remove a entrada se encontrou correspondência
    if (matchedKey) {
      trustedRequests.delete(matchedKey);
    }

    // Se for uma requisição de IP confiável, permite independentemente da origem
    if (isTrustedRequest) {
      callback(null, true);
      return;
    }

    // Log para debug (apenas em desenvolvimento)
    if (nodeEnv === 'development') {
      console.log(`[CORS] Requisição recebida - Origin: ${origin || '(sem origin)'}, NODE_ENV: ${nodeEnv}`);
    }

    // Verificação padrão de origem
    if (isOriginAllowed(origin)) {
      callback(null, true);
    } else {
      // Log de segurança para tentativas bloqueadas
      console.warn(`[CORS] 🚫 Origem bloqueada: ${origin || '(sem origin)'}`);
      console.warn(`[CORS] Origens permitidas: ${ALLOWED_ORIGINS.length > 0 ? ALLOWED_ORIGINS.join(', ') : 'Nenhuma configurada'}`);
      callback(new Error('Acesso negado por política CORS. Apenas requisições da dashboard são permitidas.'));
    }
  },

  // Permite envio de cookies e headers de autenticação
  credentials: true,

  // Métodos HTTP permitidos
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],

  // Headers permitidos nas requisições
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'Accept',
    'Origin',
    'X-API-Key',
    'X-Request-Timestamp',
    'X-Request-Signature',
  ],

  // Headers expostos nas respostas
  exposedHeaders: [
    'Content-Length',
    'Content-Type',
    'X-Request-ID',
  ],

  // Cache de preflight (OPTIONS) por 24 horas
  maxAge: 86400,

  // Não permite credenciais para requisições sem origem específica
  optionsSuccessStatus: 204,
};

/**
 * Middleware adicional para logging de CORS e verificação de IP confiável
 * Este middleware verifica se o IP é confiável e permite o acesso mesmo que a origem não esteja autorizada
 * Deve ser executado ANTES do middleware cors()
 * 
 * Para IPs confiáveis, define os headers CORS manualmente e marca a requisição para pular a validação CORS padrão
 */
export function corsLogger(req, res, next) {
  const origin = req.headers.origin;
  const clientIP = getClientIP(req);

  // Verifica se o IP está na lista de IPs confiáveis do backend
  if (TRUSTED_BACKEND_IPS.includes(clientIP)) {
    // Se for um IP confiável, define os headers CORS manualmente
    // e marca a requisição para que o CORS não bloqueie
    if (origin) {
      res.setHeader('Access-Control-Allow-Origin', origin);
      res.setHeader('Access-Control-Allow-Credentials', 'true');
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept, Origin, X-API-Key, X-Request-Timestamp, X-Request-Signature');
      res.setHeader('Access-Control-Max-Age', '86400');
    }

    // Marca a requisição como confiável para que a função origin do CORS permita
    const requestId = `${Date.now()}-${clientIP}-${Math.random()}`;
    trustedRequests.set(requestId, {
      origin: origin || null,
      ip: clientIP,
      timestamp: Date.now()
    });

    // Armazena o requestId no req para uso posterior
    req._trustedRequestId = requestId;

    console.log(`[CORS] ✅ IP confiável do backend detectado: ${clientIP} (Origin: ${origin || '(sem origin)'})`);

    // Para requisições OPTIONS (preflight), responde imediatamente
    if (req.method === 'OPTIONS') {
      return res.status(204).end();
    }
  }

  // Para outros IPs, verifica a origem normalmente
  if (!TRUSTED_BACKEND_IPS.includes(clientIP) && origin && !isOriginAllowed(origin, req)) {
    console.warn(`[SECURITY] Tentativa de acesso de origem não autorizada: ${origin}`);
    console.warn(`[SECURITY] IP: ${clientIP}, User-Agent: ${req.headers['user-agent']}`);
  }

  next();
}

export default corsOptions;


const ALLOWED_ORIGINS = [
  process.env.FRONTEND_URL,
  process.env.FRONTEND_URL_SECONDARY,
].filter(Boolean);

function isOriginAllowed(origin) {
  const nodeEnv = process.env.NODE_ENV || 'development';

  if (!origin) return true;

  if (nodeEnv === 'development') {
    return (
      origin.includes('localhost') ||
      origin.includes('127.0.0.1') ||
      origin.includes('0.0.0.0')
    );
  }

  if (ALLOWED_ORIGINS.length === 0) {
    console.warn('[CORS] ⚠ Nenhuma origem permitida configurada. Permitindo todas em modo permissivo.');
    return true;
  }

  return ALLOWED_ORIGINS.some(allowed => {
    if (origin === allowed) return true;
    try {
      const allowedHost = new URL(allowed).hostname;
      const originHost  = new URL(origin).hostname;
      return originHost === allowedHost || originHost.endsWith('.' + allowedHost);
    } catch { return false; }
  });
}

export const corsOptions = {
  origin: function (origin, callback) {
    const nodeEnv = process.env.NODE_ENV || 'development';

    if (nodeEnv === 'development') {
      console.log(`[CORS] Requisição recebida - Origin: ${origin || '(same-origin)'}, NODE_ENV: ${nodeEnv}`);
    }

    if (isOriginAllowed(origin)) {
      callback(null, true);
    } else {
      console.warn(`[CORS] Origem bloqueada: ${origin || '(same-origin)'}`);
      console.warn(`[CORS] Origens permitidas: ${ALLOWED_ORIGINS.length > 0 ? ALLOWED_ORIGINS.join(', ') : 'Nenhuma configurada'}`);
      callback(new Error('Acesso negado por política CORS'));
    }
  },

  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],

  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'Accept',
    'Origin',
  ],

  exposedHeaders: [
    'Content-Length',
    'Content-Type',
    'X-Request-ID',
  ],

  maxAge: 86400,
  optionsSuccessStatus: 204,
};

export function corsLogger(req, res, next) {
  const origin = req.headers.origin;

  if (origin && !isOriginAllowed(origin)) {
    console.warn(`[SECURITY] Tentativa de acesso de origem não autorizada: ${origin}`);
    console.warn(`[SECURITY] IP: ${req.ip}, User-Agent: ${req.headers['user-agent']}`);
  }

  next();
}

export default corsOptions;
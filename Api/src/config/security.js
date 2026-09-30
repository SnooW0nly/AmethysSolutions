/**
 * Configurações de segurança centralizadas
 */

export const securityConfig = {
  jwt: {
    // Tempo de expiração do token (7 dias)
    accessTokenExpiry: '7d',
    
    // Tempo de expiração do refresh token (30 dias)
    refreshTokenExpiry: '30d',
    
    // Algoritmo de criptografia
    algorithm: 'HS256',
    
    // Issuer e Audience para validação adicional
    issuer: process.env.JWT_ISSUER || 'vision-backend',
    audience: process.env.JWT_AUDIENCE || 'vision-frontend',
  },

  cookies: {
    // Configurações de cookies seguros
    httpOnly: true, // Não acessível via JavaScript
    secure: process.env.NODE_ENV === 'production', // HTTPS apenas em produção
    sameSite: process.env.NODE_ENV === 'production' ? 'strict' : 'lax',
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 dias em milissegundos
    domain: process.env.COOKIE_DOMAIN, // Define o domínio do cookie
    path: '/',
  },

  rateLimit: {
    // Limite de requisições por IP
    windowMs: 15 * 60 * 1000, // 15 minutos
    max: 1000, // Máximo de 1000 requisições por janela (aumentado para produção)
    message: 'Muitas requisições deste IP, tente novamente mais tarde',
    
    // IPs confiáveis que não sofrem rate limiting (frontend, servidores próprios, etc)
    whitelist: process.env.TRUSTED_IPS 
      ? process.env.TRUSTED_IPS.split(',').map(ip => ip.trim())
      : [],
    
    // Limite mais restritivo para rotas de autenticação
    auth: {
      windowMs: 15 * 60 * 1000,
      max: 5, // Apenas 5 tentativas de login em 15 minutos
    },
  },

  headers: {
    // Headers de segurança HTTP
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        scriptSrc: ["'self'"],
        imgSrc: ["'self'", 'data:', 'https:'],
      },
    },
    
    // Previne clickjacking
    frameguard: { action: 'deny' },
    
    // Força HTTPS
    hsts: {
      maxAge: 31536000, // 1 ano
      includeSubDomains: true,
      preload: true,
    },
    
    // Previne MIME sniffing
    noSniff: true,
    
    // Remove header X-Powered-By
    hidePoweredBy: true,
  },

  validation: {
    // Tamanho máximo do body (10MB)
    maxBodySize: '10mb',
    
    // Timeout de requisições (30 segundos)
    requestTimeout: 30000,
  },
};

/**
 * Valida se o ambiente está configurado corretamente
 */
export function validateEnvironment() {
  const required = [
    'JWT_SECRET',
    'MONGODB_URI',
    'FRONTEND_URL',
  ];

  const missing = required.filter(key => !process.env[key]);

  if (missing.length > 0) {
    throw new Error(
      `Variáveis de ambiente obrigatórias não definidas: ${missing.join(', ')}`
    );
  }

  // Valida força do JWT_SECRET em produção
  if (process.env.NODE_ENV === 'production') {
    const secret = process.env.JWT_SECRET;
    
    if (secret.length < 32) {
      throw new Error('JWT_SECRET deve ter no mínimo 32 caracteres em produção');
    }
  }

  console.log('[SECURITY] ✓ Validação de ambiente concluída');
}

export default securityConfig;
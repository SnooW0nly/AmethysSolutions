/**
 * Middleware para validar requisições do frontend
 * 
 * Adiciona uma camada extra de segurança verificando se a requisição
 * contém o header X-API-Key com o token secreto compartilhado entre
 * frontend e backend.
 * 
 * Isso previne que atacantes façam requisições diretas à API mesmo
 * que consigam tokens JWT válidos.
 * 
 * Para DESABILITAR: configure FRONTEND_API_KEY_ENABLED=false no .env
 */

import { getClientIP } from '../utils/getClientIP.js';
import crypto from 'crypto';

// Toggle para habilitar/desabilitar validação (default: true se tiver key configurada)
const API_KEY_ENABLED = process.env.FRONTEND_API_KEY_ENABLED !== 'false';

// Token secreto compartilhado (definido no .env)
const FRONTEND_API_KEY = process.env.FRONTEND_API_KEY;

// Rotas que NÃO precisam do API key (públicas ou de webhook)
const PUBLIC_ROUTES = [
    '/health',
    '/api/health',
    '/v1/public-stats',
    '/api/v1/public-stats',
    // Webhooks externos (geralmente usam sua própria autenticação)
    '/api/v1/webhook',
    '/v1/webhook',
];

// Prefixos de rotas que NÃO precisam do API key do frontend
// (mas ainda podem requerer autenticação do usuário via JWT ou API Key vp_*)
const PUBLIC_PREFIXES = [
    '/uploads/',      // Arquivos estáticos
    '/admin/',        // Admin usa auth própria
    // Rotas da API v1 - públicas para acesso via API Key do usuário (vp_*)
    '/v1/payment/',
    '/api/v1/payment/',
    '/v1/withdraw/',
    '/api/v1/withdraw/',
    '/v1/transfer/',
    '/api/v1/transfer/',
    '/v1/user/',
    '/api/v1/user/',
    '/v1/mistic',
    '/api/v1/mistic',
];

/**
 * Verifica se a rota é pública (não precisa de API key)
 */
function isPublicRoute(path) {
    // Verificar rotas exatas
    if (PUBLIC_ROUTES.includes(path)) {
        return true;
    }

    // Verificar prefixos
    for (const prefix of PUBLIC_PREFIXES) {
        if (path.startsWith(prefix)) {
            return true;
        }
    }

    return false;
}

/**
 * Middleware que valida o X-API-Key header
 */
export function validateFrontendApiKey(req, res, next) {
    const path = req.path || req.originalUrl || '';

    // Pular validação para rotas públicas
    if (isPublicRoute(path)) {
        return next();
    }

    // Pular validação se desabilitado via .env
    if (!API_KEY_ENABLED) {
        return next();
    }

    // Pular validação se não houver FRONTEND_API_KEY configurada
    // (para não quebrar em desenvolvimento)
    if (!FRONTEND_API_KEY) {
        if (process.env.NODE_ENV === 'production') {
            console.warn('[SECURITY] ⚠️ FRONTEND_API_KEY não configurada em produção!');
        }
        return next();
    }

    // Verificar o header X-API-Key
    const apiKey = req.headers['x-api-key'];

    if (!apiKey) {
        const clientIP = getClientIP(req);
        console.error(`[SECURITY] ❌ Requisição sem X-API-Key bloqueada`);
        console.error(`[SECURITY] IP: ${clientIP}`);
        console.error(`[SECURITY] Path: ${path}`);
        console.error(`[SECURITY] User-Agent: ${req.headers['user-agent']}`);

        return res.status(401).json({
            success: false,
            error: 'Não autorizado'
        });
    }

    // Validar o token usando timing-safe comparison para prevenir timing attacks
    let isValid = false;
    try {
        const padLen = Math.max(apiKey.length, FRONTEND_API_KEY.length, 64);
        isValid = apiKey.length === FRONTEND_API_KEY.length &&
            crypto.timingSafeEqual(
                Buffer.from(apiKey.padEnd(padLen)),
                Buffer.from(FRONTEND_API_KEY.padEnd(padLen))
            );
    } catch {
        isValid = false;
    }

    if (!isValid) {
        const clientIP = getClientIP(req);
        console.error(`[SECURITY] ❌ X-API-Key inválida`);
        console.error(`[SECURITY] IP: ${clientIP}`);
        console.error(`[SECURITY] Path: ${path}`);
        console.error(`[SECURITY] User-Agent: ${req.headers['user-agent']}`);

        return res.status(401).json({
            success: false,
            error: 'Não autorizado'
        });
    }

    next();
}

export default validateFrontendApiKey;

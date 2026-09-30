/**
 * Middleware de Assinatura de Requisições (Request Signing)
 * 
 * Previne ataques de interceptação e modificação de requests sensíveis
 * usando HMAC-SHA256 para assinar o payload da requisição.
 * 
 * Headers obrigatórios:
 * - X-Request-Timestamp: Unix timestamp em milissegundos
 * - X-Request-Signature: HMAC-SHA256(secret, timestamp + method + path + body)
 * 
 * A assinatura expira após 5 minutos para prevenir replay attacks.
 */

import crypto from 'crypto';
import { getClientIP } from '../utils/getClientIP.js';

// Secret compartilhado entre frontend e backend (deve ser diferente do FRONTEND_API_KEY)
const REQUEST_SIGNING_SECRET = process.env.REQUEST_SIGNING_SECRET;

// Toggle para habilitar/desabilitar (default: true se tiver secret configurado)
const SIGNING_ENABLED = process.env.REQUEST_SIGNING_ENABLED !== 'false';

// Tempo máximo de validade da assinatura (5 minutos)
const SIGNATURE_MAX_AGE_MS = 5 * 60 * 1000;

// Rotas que REQUEREM assinatura (operações sensíveis)
const SIGNED_ROUTES = [
    // Saques
    '/v1/withdraw/create',
    '/api/v1/withdraw/create',
    '/v1/withdraw/crypto',
    '/api/v1/withdraw/crypto',
    // Transferências internas
    '/v1/transfer/internal',
    '/api/v1/transfer/internal',
    // Pagamentos externos (send)
    '/v1/payment/send',
    '/api/v1/payment/send',
];

// Cache de assinaturas usadas (para prevenir replay attacks)
const usedSignatures = new Map();

// Limpa assinaturas antigas periodicamente (a cada 10 minutos)
setInterval(() => {
    const now = Date.now();
    for (const [sig, timestamp] of usedSignatures.entries()) {
        if (now - timestamp > SIGNATURE_MAX_AGE_MS * 2) {
            usedSignatures.delete(sig);
        }
    }
}, 10 * 60 * 1000);

/**
 * Verifica se a rota requer assinatura
 */
function requiresSignature(path, method) {
    // Apenas POST/PUT/DELETE em rotas sensíveis
    if (!['POST', 'PUT', 'DELETE'].includes(method.toUpperCase())) {
        return false;
    }

    // Verificar se é uma rota que requer assinatura
    return SIGNED_ROUTES.some(route => path.startsWith(route));
}

/**
 * Gera a assinatura esperada para validação
 */
function generateExpectedSignature(secret, timestamp, method, path, body) {
    const payload = `${timestamp}:${method.toUpperCase()}:${path}:${JSON.stringify(body || {})}`;
    return crypto.createHmac('sha256', secret).update(payload).digest('hex');
}

/**
 * Middleware que valida assinatura de requisições sensíveis
 */
export function validateRequestSignature(req, res, next) {
    const path = req.path || req.originalUrl || '';
    const method = req.method;

    // Verificar se a rota requer assinatura
    if (!requiresSignature(path, method)) {
        return next();
    }

    // Pular validação se desabilitado
    if (!SIGNING_ENABLED) {
        return next();
    }

    // Pular validação se não houver secret configurado (dev mode)
    if (!REQUEST_SIGNING_SECRET) {
        if (process.env.NODE_ENV === 'production') {
            console.warn('[SECURITY] ⚠️ REQUEST_SIGNING_SECRET não configurado em produção!');
        }
        return next();
    }

    // ====== IMPORTANTE: Pular validação para API pública ======
    // Requisições usando API Key do usuário (vp_*) são da API pública
    // e não requerem assinatura HMAC (usam autenticação via API Key)
    const authHeader = req.headers['authorization'] || '';
    const apiKeyHeader = req.headers['x-api-key'] || '';

    // Se está usando API Key do usuário (formato vp_*), pular assinatura
    if (apiKeyHeader.startsWith('vp_') || authHeader.startsWith('vp_')) {
        return next();
    }

    // Se não tem Authorization Bearer (JWT), é API pública, pular
    if (!authHeader.startsWith('Bearer ')) {
        return next();
    }

    // Obter headers de assinatura
    const timestamp = req.headers['x-request-timestamp'];
    const signature = req.headers['x-request-signature'];

    if (!timestamp || !signature) {
        const clientIP = getClientIP(req);
        console.error(`[SECURITY] ❌ Requisição sem assinatura bloqueada`);
        console.error(`[SECURITY] IP: ${clientIP}`);
        console.error(`[SECURITY] Path: ${path}`);
        console.error(`[SECURITY] User-Agent: ${req.headers['user-agent']}`);

        return res.status(400).json({
            success: false,
            error: 'Requisição inválida',
            code: 'MISSING_SIGNATURE'
        });
    }

    // Validar timestamp (previne replay attacks)
    const requestTime = parseInt(timestamp, 10);
    const now = Date.now();

    if (isNaN(requestTime) || Math.abs(now - requestTime) > SIGNATURE_MAX_AGE_MS) {
        const clientIP = getClientIP(req);
        console.error(`[SECURITY] ❌ Requisição com timestamp expirado ou inválido`);
        console.error(`[SECURITY] IP: ${clientIP}`);
        console.error(`[SECURITY] Path: ${path}`);
        console.error(`[SECURITY] Timestamp: ${timestamp}, Now: ${now}, Diff: ${now - requestTime}ms`);

        return res.status(400).json({
            success: false,
            error: 'Requisição expirada',
            code: 'EXPIRED_REQUEST'
        });
    }

    // Verificar se assinatura já foi usada (replay attack)
    if (usedSignatures.has(signature)) {
        const clientIP = getClientIP(req);
        console.error(`[SECURITY] ❌ Assinatura duplicada detectada (possível replay attack)`);
        console.error(`[SECURITY] IP: ${clientIP}`);
        console.error(`[SECURITY] Path: ${path}`);

        return res.status(400).json({
            success: false,
            error: 'Requisição inválida',
            code: 'DUPLICATE_REQUEST'
        });
    }

    // Gerar e comparar assinatura esperada
    const expectedSignature = generateExpectedSignature(
        REQUEST_SIGNING_SECRET,
        timestamp,
        method,
        path,
        req.body
    );

    // Usar timing-safe comparison para prevenir timing attacks
    const isValid = crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
    );

    if (!isValid) {
        const clientIP = getClientIP(req);
        console.error(`[SECURITY] ❌ Assinatura inválida - POSSÍVEL TENTATIVA DE MANIPULAÇÃO`);
        console.error(`[SECURITY] IP: ${clientIP}`);
        console.error(`[SECURITY] Path: ${path}`);
        console.error(`[SECURITY] User-Agent: ${req.headers['user-agent']}`);
        console.error(`[SECURITY] Body: ${JSON.stringify(req.body)}`);

        return res.status(400).json({
            success: false,
            error: 'Requisição inválida',
            code: 'INVALID_SIGNATURE'
        });
    }

    // Registrar assinatura como usada
    usedSignatures.set(signature, now);

    // Log de sucesso (remover em produção se muito verbose)
    if (process.env.NODE_ENV !== 'production') {
        console.log(`[SECURITY] ✅ Assinatura válida para ${method} ${path}`);
    }

    next();
}

/**
 * Função utilitária para gerar assinatura (para testes)
 */
export function generateSignature(timestamp, method, path, body) {
    if (!REQUEST_SIGNING_SECRET) {
        throw new Error('REQUEST_SIGNING_SECRET não configurado');
    }
    return generateExpectedSignature(REQUEST_SIGNING_SECRET, timestamp, method, path, body);
}

export default validateRequestSignature;

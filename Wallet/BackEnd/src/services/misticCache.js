/**
 * Cache e Rate Limiting para Mistic API (OTIMIZADO)
 * 
 * - Cache de respostas: 5 segundos de TTL (reduzido para detecção mais rápida)
 * - Rate limiter: máximo 20 requisições por segundo (aumentado)
 * - Backoff exponencial em caso de 429
 */

// Cache em memória para respostas de checkTransaction
const transactionCache = new Map();

// Configurações OTIMIZADAS
const CACHE_TTL_MS = 5000; // 5 segundos (reduzido de 15s para detecção mais rápida)
const MAX_REQUESTS_PER_SECOND = 20; // Aumentado de 10 para maior throughput
const BACKOFF_INITIAL_MS = 1000; // 1 segundo inicial (reduzido de 2s)
const BACKOFF_MAX_MS = 30000; // 30 segundos máximo (reduzido de 60s)

// Estado do rate limiter
let requestTimestamps = [];
let currentBackoff = 0;
let backoffUntil = 0;

/**
 * Limpa entradas expiradas do cache
 */
function cleanupCache() {
    const now = Date.now();
    for (const [key, value] of transactionCache.entries()) {
        if (now > value.expiresAt) {
            transactionCache.delete(key);
        }
    }
}

// Limpar cache a cada 30 segundos
setInterval(cleanupCache, 30000);

/**
 * Obtém resposta do cache se válida
 */
export function getCachedTransaction(transactionId) {
    const cached = transactionCache.get(transactionId);
    if (cached && Date.now() < cached.expiresAt) {
        return cached.data;
    }
    return null;
}

/**
 * Salva resposta no cache
 */
export function cacheTransaction(transactionId, data) {
    transactionCache.set(transactionId, {
        data,
        expiresAt: Date.now() + CACHE_TTL_MS
    });
}

/**
 * Verifica se podemos fazer uma requisição (rate limiting)
 * @returns {boolean} true se pode fazer requisição
 */
export function canMakeRequest() {
    const now = Date.now();

    // Se está em backoff, verificar se já passou
    if (now < backoffUntil) {
        return false;
    }

    // Limpar timestamps antigos (mais de 1 segundo)
    requestTimestamps = requestTimestamps.filter(ts => now - ts < 1000);

    // Verificar se não excede o limite
    return requestTimestamps.length < MAX_REQUESTS_PER_SECOND;
}

/**
 * Registra uma requisição feita
 */
export function recordRequest() {
    requestTimestamps.push(Date.now());
}

/**
 * Registra um erro 429 e aplica backoff exponencial
 */
export function recordRateLimit() {
    const now = Date.now();

    // Backoff exponencial
    if (currentBackoff === 0) {
        currentBackoff = BACKOFF_INITIAL_MS;
    } else {
        currentBackoff = Math.min(currentBackoff * 2, BACKOFF_MAX_MS);
    }

    backoffUntil = now + currentBackoff;
    console.log(`⏳ Rate limit da Mistic detectado. Aguardando ${currentBackoff / 1000}s antes de continuar...`);
}

/**
 * Reseta o backoff (quando requisição é bem-sucedida)
 */
export function resetBackoff() {
    if (currentBackoff > 0) {
        currentBackoff = 0;
        backoffUntil = 0;
    }
}

/**
 * Retorna o tempo restante de backoff em ms
 */
export function getBackoffRemaining() {
    const remaining = backoffUntil - Date.now();
    return remaining > 0 ? remaining : 0;
}

/**
 * Retorna estatísticas do cache
 */
export function getCacheStats() {
    return {
        cacheSize: transactionCache.size,
        requestsLastSecond: requestTimestamps.filter(ts => Date.now() - ts < 1000).length,
        currentBackoff,
        backoffRemaining: getBackoffRemaining()
    };
}

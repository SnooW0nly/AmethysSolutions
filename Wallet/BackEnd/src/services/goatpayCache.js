/**
 * Cache e rate limiting para a API GoatPay (mintlify-docs).
 */

const transactionCache = new Map();

const CACHE_TTL_MS = 5000;
const MAX_REQUESTS_PER_SECOND = 20;
const BACKOFF_INITIAL_MS = 1000;
const BACKOFF_MAX_MS = 30000;

let requestTimestamps = [];
let currentBackoff = 0;
let backoffUntil = 0;

function cleanupCache() {
  const now = Date.now();
  for (const [key, value] of transactionCache.entries()) {
    if (now > value.expiresAt) {
      transactionCache.delete(key);
    }
  }
}

setInterval(cleanupCache, 30000);

export function getCachedTransaction(cacheKey) {
  const cached = transactionCache.get(cacheKey);
  if (cached && Date.now() < cached.expiresAt) {
    return cached.data;
  }
  return null;
}

export function cacheTransaction(cacheKey, data) {
  transactionCache.set(cacheKey, {
    data,
    expiresAt: Date.now() + CACHE_TTL_MS,
  });
}

export function canMakeRequest() {
  const now = Date.now();
  if (now < backoffUntil) return false;
  requestTimestamps = requestTimestamps.filter((ts) => now - ts < 1000);
  return requestTimestamps.length < MAX_REQUESTS_PER_SECOND;
}

export function recordRequest() {
  requestTimestamps.push(Date.now());
}

export function recordRateLimit() {
  const now = Date.now();
  currentBackoff = currentBackoff === 0
    ? BACKOFF_INITIAL_MS
    : Math.min(currentBackoff * 2, BACKOFF_MAX_MS);
  backoffUntil = now + currentBackoff;
  console.log(`⏳ Rate limit GoatPay. Aguardando ${currentBackoff / 1000}s...`);
}

export function resetBackoff() {
  currentBackoff = 0;
  backoffUntil = 0;
}

export function getBackoffRemaining() {
  const remaining = backoffUntil - Date.now();
  return remaining > 0 ? remaining : 0;
}

export function getCacheStats() {
  return {
    cacheSize: transactionCache.size,
    requestsLastSecond: requestTimestamps.filter((ts) => Date.now() - ts < 1000).length,
    currentBackoff,
    backoffRemaining: getBackoffRemaining(),
  };
}

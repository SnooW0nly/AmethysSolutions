/**
 * src/services/discord/shop/sessions.js
 *
 * Estado temporário em memória para fluxos multi-passo.
 * Atualmente não é necessário — Modals resolvem tudo em um único round-trip.
 * Mantido para extensibilidade futura.
 */

/** @type {Map<string, any>} userId → dados de sessão */
const sessions = new Map();

export function setSession(userId, data) {
  sessions.set(userId, { ...data, createdAt: Date.now() });
}

export function getSession(userId) {
  return sessions.get(userId) ?? null;
}

export function deleteSession(userId) {
  sessions.delete(userId);
}

// Limpa sessões com mais de 15 minutos automaticamente
setInterval(() => {
  const cutoff = Date.now() - 15 * 60 * 1000;
  for (const [key, val] of sessions) {
    if (val.createdAt < cutoff) sessions.delete(key);
  }
}, 5 * 60 * 1000);

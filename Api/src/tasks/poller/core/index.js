// src/tasks/poller/core/index.js
import { updatePendingPayments }  from "../jobs/updatePendingPayments.js";
import { cleanupOldPayments }     from "../jobs/cleanupOldPayments.js";
import { refreshExpiringTokens }  from "../jobs/refreshDiscordTokens.js";

export function startPoller({ intervalMs = 10000 } = {}) {
  setInterval(async () => {
    try {
      await updatePendingPayments();
      await cleanupOldPayments();
    } catch (err) {
      console.error("[poller] Erro geral:", err?.message || err);
    }
  }, intervalMs);

  // Roda a cada 6 horas (independente do intervalo do poller principal)
  const SIX_HOURS = 6 * 60 * 60 * 1000;
  setInterval(async () => {
    try {
      await refreshExpiringTokens();
    } catch (err) {
      console.error("[refreshTokens] Erro geral:", err?.message || err);
    }
  }, SIX_HOURS);

  // Roda imediatamente na primeira vez que o servidor sobe
  refreshExpiringTokens().catch(err =>
    console.error("[refreshTokens] Erro na inicialização:", err?.message || err)
  );
}
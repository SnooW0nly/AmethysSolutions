import { PORT, NODE_ENV } from "./src/config/env.js";
import app from "./src/app.js";
import { startPaymentPoller } from "./src/services/paymentPoller.js";
import { startWithdrawPoller } from "./src/services/withdrawPoller.js";
import { startWebhookScheduler } from "./src/services/webhookService.js";

const envLabel = NODE_ENV === "production" ? "production" : "development";

app.listen(PORT, async () => {
  const timestamp = new Date().toISOString();

  console.log(`\n============================================`);
  console.log(`[${timestamp}] 🚀 Amethys Wallet API iniciada`);
  console.log(`[${timestamp}] 🌎 Ambiente: ${envLabel}`);
  console.log(`[${timestamp}] 📡 Porta: ${PORT}`);
  console.log(`============================================\n`);

  // Iniciar schedulers após conexão com banco
  try {
    const POLLER_INTERVAL = parseInt(process.env.PAYMENT_POLLER_INTERVAL || '5000'); // 5 segundos (ultra otimizado)

    startPaymentPoller(POLLER_INTERVAL);
    startWithdrawPoller(parseInt(process.env.WITHDRAW_POLLER_INTERVAL || '10000')); // 10 segundos (otimizado)

    // Iniciar scheduler de webhooks
    const WEBHOOK_INTERVAL = parseInt(process.env.WEBHOOK_INTERVAL || '60000'); // 60 segundos padrão
    startWebhookScheduler(WEBHOOK_INTERVAL);

    console.log('\n✅ Todos os schedulers iniciados com sucesso!\n');
  } catch (error) {
    console.error('❌ Erro ao iniciar schedulers:', error);
  }
});
// ========================= GLOBAL ERROR HANDLERS =========================
process.on("unhandledRejection", (reason) => {
  console.error("💥 Unhandled Rejection:", reason);
});

process.on("uncaughtException", (err) => {
  console.error("💥 Uncaught Exception:", err);
  process.exit(1);
});

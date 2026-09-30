import { PORT, NODE_ENV } from "./src/config/env.js";
import app from "./src/app.js";
import { startPoller } from "./src/tasks/poller/core/index.js";
import { startChargeService } from "./src/services/billing/chargeService.js";
import { startBlockService } from "./src/services/billing/blockService.js";
import { startBotCounter } from "./src/services/discord/botCounter.js";
import { cleanExpiredCodes } from "./src/services/emailVerification.js";
import { initService as initDivulgacao } from "./src/services/divulgacaoService.js";
import { startRoleSync } from "./src/tasks/discord/roleSync.js";
import { startDiscloudSync } from "./src/tasks/discloud/discloudSync.js";
import { startShopTask } from "./src/tasks/discord/shopTask.js";

console.clear();

const envLabel = NODE_ENV === "production" ? "production" : "development";

app.listen(PORT, async () => {
  const timestamp = new Date().toISOString();

  console.log(`\n============================================`);
  console.log(`[${timestamp}] 🚀 Amethys API iniciada`);
  console.log(`[${timestamp}] 🌎 Ambiente: ${envLabel}`);
  console.log(`[${timestamp}] 📡 Porta: ${PORT}`);
  console.log(`============================================\n`);

  startPoller({ intervalMs: 10000 });
  console.log(`[${timestamp}] 🔄 Poller iniciado (10s)`);

  startChargeService();
  console.log(`[${timestamp}] 💰 Serviço de cobrança iniciado`);

  startBlockService();
  console.log(`[${timestamp}] ⛔ Serviço de bloqueio iniciado`);

  startBotCounter();
  console.log(`[${timestamp}] 🤖 Serviço de contador iniciado`);

  await startShopTask();
  console.log(`[${timestamp}] 🛒 Shop Discord iniciado`);

  setInterval(cleanExpiredCodes, 30 * 60 * 1000);
  console.log(`[${timestamp}] ✉️ Limpeza de códigos agendada (30min)`);

  await initDivulgacao();
  console.log(`[${timestamp}] 📢 Serviço de divulgação inicializado`);

  startRoleSync();
  console.log(`[${timestamp}] 🎭 Sincronização de cargos iniciada (10min)`);

  startDiscloudSync();
  console.log(`[${timestamp}] ☁️ Sincronização Discloud iniciada (15min)`);
});

process.on("unhandledRejection", (reason) => {
  console.error("💥 Unhandled Rejection:", reason);
});

process.on("uncaughtException", (err) => {
  console.error("💥 Uncaught Exception:", err);
});
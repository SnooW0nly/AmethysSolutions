/**
 * POST /admin/updates/github-webhook
 *
 * Recebe o webhook de push do GitHub e dispara a atualização automática
 * em todos os bots com apenas os arquivos que foram alterados no push.
 *
 * ⚠️  Esta rota NÃO usa authMiddleware nem requireAdmin — a autenticação
 *     é feita pela assinatura HMAC do GitHub (X-Hub-Signature-256).
 *     Por isso ela deve ser registrada FORA do router que aplica esses middlewares.
 *
 * Configuração necessária no .env:
 *   GITHUB_WEBHOOK_SECRET=<secret que você define no GitHub>
 *   GITHUB_TOKEN=<Personal Access Token com permissão de leitura no repo>
 *   GITHUB_REPO=owner/nome-do-repo
 *   GITHUB_BRANCH=main          (opcional, padrão: main)
 *   GITHUB_ADMIN_ID=<ObjectId de um usuário admin no MongoDB>  (opcional)
 */

import express from "express";
import {
  validateGithubSignature,
  processGithubPush,
} from "../../../services/githubUpdateService.js";

const router = express.Router();

/**
 * Middleware para capturar o body cru (Buffer) antes do express.json() o parsear.
 * Necessário para validar a assinatura HMAC do GitHub, que é calculada sobre o body bruto.
 * Registrado apenas nesta rota.
 */
router.use(
  express.raw({ type: "application/json", limit: "10mb" })
);

router.post("/", async (req, res) => {
  // ── 1. Validar assinatura ──────────────────────────────────────────────────
  const secret    = process.env.GITHUB_WEBHOOK_SECRET;
  const signature = req.headers["x-hub-signature-256"];
  const event     = req.headers["x-github-event"];

  if (!secret) {
    console.error("[GITHUB WEBHOOK] GITHUB_WEBHOOK_SECRET não configurado");
    return res.status(500).json({ success: false, message: "Webhook não configurado no servidor" });
  }

  if (!validateGithubSignature(secret, signature, req.body)) {
    console.warn("[GITHUB WEBHOOK] Assinatura inválida — requisição rejeitada");
    return res.status(401).json({ success: false, message: "Assinatura inválida" });
  }

  // ── 2. Ignorar eventos que não são push ────────────────────────────────────
  if (event !== "push") {
    console.log(`[GITHUB WEBHOOK] Evento '${event}' ignorado (somente 'push' é processado)`);
    return res.status(200).json({ success: true, message: `Evento '${event}' ignorado` });
  }

  // ── 3. Parsear o body (veio como Buffer do express.raw) ────────────────────
  let payload;
  try {
    payload = JSON.parse(req.body.toString("utf8"));
  } catch (err) {
    console.error("[GITHUB WEBHOOK] Erro ao parsear payload:", err.message);
    return res.status(400).json({ success: false, message: "Payload inválido" });
  }

  // ── 4. Responder imediatamente ao GitHub (evita timeout de 10s) ────────────
  // O GitHub espera resposta rápida — o processamento real acontece em background.
  res.status(202).json({ success: true, message: "Webhook recebido — processando atualização" });

  // ── 5. Processar em background ─────────────────────────────────────────────
  const adminUserId = process.env.GITHUB_ADMIN_ID || null;

  try {
    const result = await processGithubPush(payload, adminUserId);

    if (!result) {
      // Push ignorado (branch errada, sem mudanças, etc.) — já logado internamente
      return;
    }

    console.log(
      `[GITHUB WEBHOOK] ✅ Atualização disparada — updateId: ${result.updateId} | ` +
      `${result.toUpdate.length} arquivo(s) atualizados | ` +
      `${result.toDelete.length} arquivo(s) removidos | ` +
      `ZIP: ${result.zipSizeKB} KB`
    );
  } catch (err) {
    console.error("[GITHUB WEBHOOK] ❌ Erro ao processar push:", err.message);
    // Não há como responder ao GitHub aqui (já respondemos 202 acima)
  }
});

export default router;
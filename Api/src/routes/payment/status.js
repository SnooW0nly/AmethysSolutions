import express from "express";
import Payment from "../../database/models/Payment.js";
import { checkPixPayment } from "../../services/payment/index.js";
import Application from "../../database/models/Application.js";
import { handleApprovedPayment } from "../../tasks/poller/processPayment.js";

const router = express.Router();

/**
 * Retorna todas as informações de um pagamento
 * Atualiza o status buscando da Woovi se o provedor for woovi
 */
router.get("/:id/status", async (req, res, next) => {
  try {
    const { id } = req.params;
    let payment = await Payment.findById(id);

    if (!payment) return res.status(404).json({ error: "Pagamento não encontrado" });

    // Ownership check: the payment must belong to the authenticated user
    if (String(payment.userId) !== String(req.user._id)) {
      return res.status(403).json({ error: "Você não tem permissão para acessar este pagamento" });
    }

    // Se o pagamento está pendente, busca status atualizado do provedor
    const isPendingMistic = payment.provider === "mistic" && payment.status === "pending" && payment.misticId;
    const isPendingWoovi = payment.provider === "woovi" && payment.status === "pending" && payment.wooviId;

    if (isPendingMistic || isPendingWoovi) {
      const paymentIdToCheck = isPendingMistic ? payment.misticId : payment.wooviId;
      const providerName = isPendingMistic ? "mistic" : "woovi";

      try {
        const { status: updatedStatus, raw } = await checkPixPayment({
          payment_id: paymentIdToCheck,
          provider: providerName,
        });

        // Se o status mudou, atualiza o pagamento
        const wasPending = payment.status === "pending";
        if (updatedStatus !== payment.status) {
          payment.status = updatedStatus;
          if (isPendingMistic) {
            payment.misticRaw = raw;
          } else {
            payment.wooviRaw = raw;
          }
          await payment.save();
          console.log(`[PAYMENT STATUS] Pagamento ${id} atualizado: ${payment.status} -> ${updatedStatus}`);

          // Se foi aprovado, processa o pagamento
          if (updatedStatus === "approved") {
            const existingApp = await Application.findOne({ paymentId: payment._id }).lean();
            if (!existingApp) {
              try {
                console.log(`[PAYMENT STATUS] Pagamento ${id} aprovado mas sem Application. Processando...`);
                await handleApprovedPayment(payment);
                console.log(`[PAYMENT STATUS] Pagamento ${id} processado com sucesso`);
              } catch (error) {
                console.error(`[PAYMENT STATUS] Erro ao processar pagamento aprovado:`, error);
              }
            }
          }
        } else if (updatedStatus === "approved") {
          // Se já estava aprovado, verifica se precisa processar
          const existingApp = await Application.findOne({ paymentId: payment._id }).lean();
          if (!existingApp) {
            try {
              console.log(`[PAYMENT STATUS] Pagamento ${id} já estava aprovado mas sem Application. Processando...`);
              await handleApprovedPayment(payment);
              console.log(`[PAYMENT STATUS] Pagamento ${id} processado com sucesso`);
            } catch (error) {
              console.error(`[PAYMENT STATUS] Erro ao processar pagamento aprovado:`, error);
            }
          }
        }
      } catch (error) {
        console.warn(`[PAYMENT STATUS] Erro ao buscar status atualizado de ${providerName}:`, error.message);
        // Continua com o status local se não conseguir buscar do provedor
      }
    }

    // Derive a safe createdAt in case old records don't have it populated
    const createdAt = payment.createdAt || (payment._id && typeof payment._id.getTimestamp === "function" ? payment._id.getTimestamp() : undefined);

    // Busca aplicação vinculada a este pagamento (se existir)
    let applicationId = null;
    try {
      const app = await Application.findOne({ paymentId: payment._id }).select({ _id: 1 }).lean();
      applicationId = app?._id || null;
    } catch { }
    // Fallback: para faturas de renovação usamos metadata.applicationId (já é o _id da aplicação)
    if (!applicationId && payment?.metadata?.applicationId) {
      applicationId = String(payment.metadata.applicationId);
    }

    res.json({
      id: payment._id,
      plan: payment.plan,
      coupon: payment.coupon,
      priceFinal: payment.priceFinal,
      status: payment.status,
      qr_code_base64: payment.qrCodeBase64,
      qr_code_text: payment.qrCodeText,
      expiresAt: payment.expiresAt,
      createdAt,
      applicationId,
    });
  } catch (e) {
    next(e);
  }
});

export default router;

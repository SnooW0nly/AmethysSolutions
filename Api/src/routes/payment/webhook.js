import express from "express";
import Payment from "../../database/models/Payment.js";
import Application from "../../database/models/Application.js";
import { handleApprovedPayment } from "../../tasks/poller/processPayment.js";
import { mapStatus } from "../../services/mistic/pix.js";

const router = express.Router();

/**
 * Webhook da Woovi para receber notificações de pagamento
 * POST /payment/webhook
 * 
 * A Woovi envia eventos quando o status de uma cobrança muda.
 * Documentação: https://developers.woovi.com/docs/api-reference/webhook
 */
router.post("/", async (req, res, next) => {
  try {
    const event = req.body;

    // Validação básica do evento
    if (!event || !event.type) {
      return res.status(400).json({ error: "Evento inválido" });
    }

    console.log(`[WOOVI WEBHOOK] Evento recebido: ${event.type}`);

    // Processa apenas eventos relacionados a cobranças
    if (event.type === "charge.finished" || event.type === "charge.paid") {
      const charge = event.data;

      // O charge pode ter id ou correlationID
      const chargeId = charge?.correlationID || charge?.id;

      if (!chargeId) {
        console.warn("[WOOVI WEBHOOK] Charge sem ID ou correlationID");
        return res.status(400).json({ error: "Charge ID ausente" });
      }

      // Busca o pagamento pelo misticId ou wooviId
      const payment = await Payment.findOne({ 
        $or: [
          { misticId: chargeId },
          { wooviId: chargeId }
        ]
      });

      if (!payment) {
        console.warn(`[WOOVI WEBHOOK] Pagamento não encontrado para charge ${chargeId}`);
        return res.status(404).json({ error: "Pagamento não encontrado" });
      }

      // Mapeia o status da Woovi para o status interno
      const status = mapStatus(charge.status || charge.state);

      // Atualiza o pagamento
      const wasPending = payment.status === "pending";
      const statusChanged = payment.status !== status;

      if (statusChanged) {
        payment.status = status;
        if (payment.provider === "mistic") {
          payment.misticRaw = charge;
        } else {
          payment.wooviRaw = charge;
        }
        await payment.save();

        console.log(`[WOOVI WEBHOOK] Pagamento ${payment._id} atualizado para status: ${status}`);
      }

      // Se foi aprovado, processa o pagamento (mesmo que o status não tenha mudado agora)
      // Verifica se já existe Application para evitar reprocessamento
      if (status === "approved") {
        const existingApp = await Application.findOne({ paymentId: payment._id }).lean();

        if (!existingApp) {
          try {
            console.log(`[WOOVI WEBHOOK] Pagamento ${payment._id} aprovado mas sem Application. Processando...`);
            await handleApprovedPayment(payment);
            console.log(`[WOOVI WEBHOOK] Pagamento ${payment._id} processado com sucesso`);
          } catch (error) {
            console.error(`[WOOVI WEBHOOK] Erro ao processar pagamento aprovado:`, error);
            // Não retorna erro para não fazer a Woovi reenviar o webhook
          }
        } else if (statusChanged && wasPending) {
          // Se mudou agora e estava pendente, também processa (pode ser atualização)
          try {
            console.log(`[WOOVI WEBHOOK] Pagamento ${payment._id} mudou para approved. Processando...`);
            await handleApprovedPayment(payment);
            console.log(`[WOOVI WEBHOOK] Pagamento ${payment._id} processado com sucesso`);
          } catch (error) {
            console.error(`[WOOVI WEBHOOK] Erro ao processar pagamento aprovado:`, error);
            // Não retorna erro para não fazer a Woovi reenviar o webhook
          }
        }
      }

      return res.status(200).json({ success: true, message: "Webhook processado" });
    }

    // Outros tipos de eventos são apenas logados
    console.log(`[WOOVI WEBHOOK] Evento ${event.type} recebido mas não processado`);
    return res.status(200).json({ success: true, message: "Evento recebido" });
  } catch (error) {
    console.error("[WOOVI WEBHOOK] Erro ao processar webhook:", error);
    // Retorna 200 para evitar que a Woovi reenvie o webhook
    return res.status(200).json({ success: false, error: "Erro interno" });
  }
});

export default router;


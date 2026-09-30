import express from "express";
import Payment from "../../../database/models/Payment.js";
import { handleApprovedPayment } from "../../../tasks/poller/processPayment.js";

const router = express.Router();

/**
 * POST /admin/payments/:id/approve
 * Marca pagamento como approved e dispara o mesmo fluxo do poller
 */
router.post("/:id/approve", async (req, res) => {
  try {
    const { id } = req.params;
    const payment = await Payment.findById(id);
    if (!payment) return res.status(404).json({ error: "Pagamento não encontrado" });

    // Marca como aprovado e dispara fluxo específico (sem consultar Efi)
    payment.status = "approved";
    await payment.save();
    await handleApprovedPayment(payment);

    return res.json({ ok: true, id: payment._id, status: payment.status });
  } catch (e) {
    console.error(e);
    return res.status(400).json({ error: "Não foi possível aprovar o pagamento" });
  }
});

export default router;



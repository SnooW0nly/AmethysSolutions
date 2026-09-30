import Payment from "../../../database/models/Payment.js";
import { processPayment } from "../processPayment.js";

export async function updatePendingPayments() {
  // Só processa pagamentos que já têm PIX gerado (provider definido).
  // Carrinhos com status "cart" são ignorados — eles não têm misticId/wooviId/efiId ainda.
  const pendings = await Payment.find({
    status: "pending",
    provider: { $in: ["mistic", "woovi", "efi"] },
  });

  for (const p of pendings) {
    try {
      await processPayment(p);
    } catch (err) {
      const paymentId = p.misticId || p.wooviId || p.efiId || p._id;
      console.error(`[poller] Erro verificando ${paymentId} (${p.provider}):`, err?.message || err);
    }
  }
}

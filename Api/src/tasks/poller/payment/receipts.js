import User from "../../../database/models/User.js";
import { sendReceiptEmail } from "../../../services/mail/receipt.js";

export async function sendReceiptForPayment(payment) {
  try {
    const user = await User.findById(payment.userId).lean();
    const to = user?.email;
    if (!to) {
      console.warn(
        `[poller] Usuário ${payment.userId} sem email. Recibo não enviado.`
      );
      return;
    }

    const subtotal = Number(payment.plan?.price ?? payment.priceFinal ?? 0);
    const total = Number(payment.priceFinal ?? subtotal);
    const discount = Math.max(subtotal - total, 0);

    await sendReceiptEmail({
      to,
      subject: "Pagamento aprovado — Recibo Sync",
      invoiceNumber: payment.invoiceNumber || String(payment._id),
      invoiceDate: new Date().toLocaleDateString("pt-BR"),
      invoiceSubTotal: subtotal,
      invoiceDiscount: discount,
      invoiceTotal: total,
      userName: user?.globalName || user?.username || "Cliente Sync",
      userEmail: to,
      planName: payment.plan?.name || "Plano Sync",
      months: payment.plan?.months || 1,
    });
  } catch (err) {
    const paymentId = payment.wooviId || payment.efiId || payment._id;
    console.error(
      `[poller] Falha ao enviar recibo do pagamento ${paymentId} (${payment.provider || 'woovi'}):`,
      err?.message || err
    );
  }
}



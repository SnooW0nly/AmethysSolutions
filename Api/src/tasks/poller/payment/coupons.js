import Coupon from "../../../database/models/Coupon.js";
import AuditLog from "../../../database/models/AuditLog.js";

export async function redeemCouponUsage(payment) {
  if (!payment?.coupon?.code) return;
  try {
    await Coupon.findOneAndUpdate(
      { name: payment.coupon.code },
      { $inc: { usedCount: +1 } }
    );
    await AuditLog.create({
      entity: "coupon",
      action: "redeem",
      actorId: String(payment.userId || ""),
      targetId: payment.coupon.code,
      metadata: { paymentId: String(payment._id) },
    });
  } catch (err) {
    console.error(
      `[poller] Falha ao atualizar uso do cupom ${payment.coupon.code}:`,
      err?.message || err
    );
  }
}



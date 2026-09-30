export function isPaymentExpired(payment) {
  return payment.expiresAt < new Date();
}

export async function markPaymentExpired(payment) {
  payment.status = "cancelled";
  await payment.save();
  const paymentId = payment.wooviId || payment.efiId || payment._id;
  console.log(`[poller] Pagamento ${paymentId} (${payment.provider || 'woovi'}) expirou`);
}

export async function updatePaymentStatus(payment, status) {
  if (status === payment.status) return false;
  payment.status = status;
  await payment.save();
  const paymentId = payment.wooviId || payment.efiId || payment._id;
  console.log(`[poller] Pagamento ${paymentId} (${payment.provider || 'woovi'}) atualizado -> ${status}`);
  return true;
}



import Payment from "../../../database/models/Payment.js";

export async function cleanupOldPayments() {
  const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);
  const result = await Payment.deleteMany({
    status: { $ne: "approved" },
    createdAt: { $lt: tenMinutesAgo },
  });
  if (result.deletedCount > 0) {
    console.log(
      `[poller] Limpou ${result.deletedCount} pagamentos não aprovados com >10min`
    );
  }
}



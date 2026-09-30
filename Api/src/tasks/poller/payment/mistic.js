import { checkPixPayment } from "../../../services/payment/index.js";

/**
 * Busca o status de um pagamento usando Mistic
 * @param {string} paymentId - ID do pagamento (misticId)
 * @param {string} provider - Provedor usado ('mistic' ou 'efi')
 * @returns {Promise<string>} - Status do pagamento
 */
export async function fetchPixStatus(paymentId, provider = "mistic") {
  try {
    const { status } = await checkPixPayment({
      payment_id: paymentId,
      provider,
    });
    return status;
  } catch (error) {
    console.error(`[mistic] Erro ao buscar status do pagamento ${paymentId}:`, error);
    throw error;
  }
}


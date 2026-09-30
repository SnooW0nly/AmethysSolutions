import { checkPixPayment } from "../../../services/payment/index.js";

/**
 * Busca o status de um pagamento usando Woovi
 * @param {string} paymentId - ID do pagamento (wooviId)
 * @param {string} provider - Provedor usado ('woovi' ou 'efi')
 * @returns {Promise<string>} - Status do pagamento
 */
export async function fetchPixStatus(paymentId, provider = "woovi") {
  try {
    const { status } = await checkPixPayment({
      payment_id: paymentId,
      provider,
    });
    return status;
  } catch (error) {
    console.error(`[woovi] Erro ao buscar status do pagamento ${paymentId}:`, error);
    throw error;
  }
}


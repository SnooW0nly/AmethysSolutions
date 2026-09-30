/**
 * Serviço unificado de pagamentos
 * Escolhe automaticamente entre Efi Bank e Mistic baseado na configuração
 */

import { createPixPayment as createEfiPayment, checkPixPayment as checkEfiPayment } from "../efi-bank/index.js";
import { createPixPayment as createMisticPayment, checkPixPayment as checkMisticPayment } from "../mistic/index.js";

/**
 * Determina qual provedor usar baseado nas variáveis de ambiente
 * @returns {'efi' | 'mistic'}
 */
function getPaymentProvider() {
  // Força uso de Mistic (Woovi foi substituído)
  // Apenas permite EFI se explicitamente configurado via variável de ambiente
  if (process.env.PAYMENT_PROVIDER === "efi") {
    console.warn("[PAYMENT] EFI está sendo usado por configuração explícita. Considere migrar para Mistic.");
    return "efi";
  }

  // Sempre usa Mistic por padrão
  return "mistic";
}

/**
 * Cria um pagamento PIX usando o provedor configurado
 * @param {object} params
 * @param {number} params.price - Valor do pagamento
 * @param {string} params.description - Descrição do pagamento
 * @param {string} params.payerName - Nome do pagador (opcional)
 * @param {string} params.payerDocument - CPF do pagador (opcional)
 * @returns {Promise<{provider: string, paymentId: string, emv: string, qrBase64: string, raw: object}>}
 */
export async function createPixPayment({ price, description, payerName, payerDocument }) {
  const provider = getPaymentProvider();

  if (provider === "mistic") {
    const { misticId, emv, qrBase64, raw } = await createMisticPayment({
      price,
      description,
      payerName,
      payerDocument,
    });
    return {
      provider: "mistic",
      paymentId: misticId,
      emv,
      qrBase64,
      raw,
    };
  } else {
    const { efiId, emv, qrBase64, raw } = await createEfiPayment({ price, description });
    return {
      provider: "efi",
      paymentId: efiId,
      emv,
      qrBase64,
      raw,
    };
  }
}

/**
 * Verifica o status de um pagamento usando o provedor correto
 * @param {object} params
 * @param {string} params.payment_id - ID do pagamento
 * @param {string} params.provider - Provedor usado ('efi' ou 'mistic')
 * @returns {Promise<{status: string, raw: object}>}
 */
export async function checkPixPayment({ payment_id, provider }) {
  if (provider === "mistic" || !provider) {
    // Se não especificado, tenta Mistic primeiro
    try {
      return await checkMisticPayment({ payment_id });
    } catch (error) {
      // Se falhar e não tiver provider especificado, tenta Efi
      if (!provider) {
        try {
          return await checkEfiPayment({ payment_id });
        } catch (e) {
          throw error; // Lança o erro original do Mistic
        }
      }
      throw error;
    }
  } else {
    return await checkEfiPayment({ payment_id });
  }
}

/**
 * Obtém o provedor padrão configurado
 */
export function getDefaultProvider() {
  return getPaymentProvider();
}


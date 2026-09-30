/**
 * Serviços PIX da Woovi usando o SDK oficial
 */

/**
 * Cria uma cobrança PIX via Woovi
 * @param {object} params
 * @param {object} params.client - Cliente Woovi inicializado
 * @param {number} params.amount - Valor em centavos (ex: 10000 = R$ 100,00)
 * @param {string} params.description - Descrição da cobrança
 * @param {number} params.expirationSeconds - Tempo de expiração em segundos (padrão: 600 = 10 minutos)
 * @returns {Promise<{charge: object, qrCode: object, raw: object}>}
 */
export async function createCharge({
  client,
  amount,
  description = "Pagamento via Woovi",
  expirationSeconds = 600,
}) {
  try {
    // Converte valor para centavos (Woovi trabalha com centavos)
    const amountInCents = Math.round(Number(amount) * 100);

    // Cria a cobrança usando o SDK Woovi
    // O SDK espera o valor em centavos e correlationID único
    const correlationID = `payment-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    const charge = await client.charge.create({
      value: amountInCents,
      correlationID,
      comment: description,
      // Opcional: tempo de expiração em segundos
      ...(expirationSeconds && expirationSeconds !== 600 && { expirationSeconds }),
    });

    // Log da resposta completa da cobrança
    console.log("[WOOVI] Resposta completa da criação de cobrança:");
    console.log(JSON.stringify(charge, null, 2));

    // A resposta da Woovi já vem com o brCode (EMV) na própria charge
    // Não precisamos buscar separadamente
    // O brCode pode estar em charge.brCode ou charge.charge.brCode
    const brCode = charge?.brCode || charge?.charge?.brCode || null;

    return {
      charge,
      brCode,
      correlationID,
      raw: charge,
    };
  } catch (error) {
    console.error("[woovi] Erro ao criar cobrança:", error);
    throw error;
  }
}

/**
 * Obtém QR Code de uma cobrança existente
 * @param {object} params
 * @param {object} params.client - Cliente Woovi inicializado
 * @param {string} params.chargeId - ID da cobrança
 * @returns {Promise<object>}
 */
export async function getQRCodeByCharge({ client, chargeId }) {
  try {
    const qrCode = await client.charge.getQrCode(chargeId);
    return qrCode;
  } catch (error) {
    console.error("[woovi] Erro ao buscar QR Code:", error);
    throw error;
  }
}

/**
 * Obtém o status de uma cobrança
 * @param {object} params
 * @param {object} params.client - Cliente Woovi inicializado
 * @param {string} params.chargeId - ID da cobrança
 * @returns {Promise<object>}
 */
export async function getChargeStatus({ client, chargeId }) {
  try {
    // A Woovi permite buscar por correlationID ou identifier
    // O SDK espera um objeto com 'id' ao invés de string direta
    const charge = await client.charge.get({ id: chargeId });
    console.log(`[WOOVI] Resposta ao buscar charge ${chargeId}:`, JSON.stringify(charge, null, 2));
    
    // A resposta pode vir como charge.charge ou diretamente
    const chargeData = charge?.charge || charge;
    return chargeData || charge;
  } catch (error) {
    console.error("[woovi] Erro ao buscar status da cobrança:", error);
    throw error;
  }
}

/**
 * Mapeia o status da Woovi para o status interno
 * @param {string} wooviStatus - Status retornado pela Woovi
 * @returns {string} - Status interno: 'pending', 'approved', 'cancelled'
 */
export function mapStatus(wooviStatus) {
  if (!wooviStatus) return "pending";

  const statusUpper = String(wooviStatus).toUpperCase();

  // Status aprovado/pago
  // Woovi usa: COMPLETED, PAID (em maiúsculas)
  if (
    statusUpper === "PAID" ||
    statusUpper === "COMPLETED" ||
    statusUpper === "APPROVED"
  ) {
    return "approved";
  }

  // Status cancelado/expirado
  // Woovi usa: EXPIRED, CANCELLED, FAILED, REFUNDED
  if (
    statusUpper === "CANCELLED" ||
    statusUpper === "CANCELED" ||
    statusUpper === "EXPIRED" ||
    statusUpper === "FAILED" ||
    statusUpper === "REFUNDED"
  ) {
    return "cancelled";
  }

  // Status pendente/ativo
  // Woovi usa: ACTIVE, PENDING, WAITING
  // ACTIVE significa que a cobrança está ativa e aguardando pagamento
  if (
    statusUpper === "ACTIVE" ||
    statusUpper === "PENDING" ||
    statusUpper === "WAITING"
  ) {
    return "pending";
  }

  // Default: pendente
  return "pending";
}


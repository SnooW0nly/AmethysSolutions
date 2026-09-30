import { createClient } from "@woovi/node-sdk";
import { createCharge, getQRCodeByCharge, getChargeStatus, mapStatus } from "./pix.js";
import qrcode from "qrcode";
import Payment from "../../database/models/Payment.js";

// Inicializa o cliente Woovi
let wooviClient = null;

/**
 * Inicializa o cliente Woovi
 */
function getWooviClient() {
  if (!wooviClient) {
    const appId = process.env.WOOVI_APP_ID || process.env.WOOVI_API_KEY;
    
    if (!appId) {
      console.warn("[woovi] WOOVI_APP_ID ou WOOVI_API_KEY não configurado");
      return null;
    }

    wooviClient = createClient({ appId });
  }

  return wooviClient;
}

/**
 * Cria um pagamento PIX via Woovi
 * @param {object} params - Parâmetros do pagamento
 * @param {number} params.price - Valor do pagamento
 * @param {string} params.description - Descrição do pagamento
 * @returns {Promise<{wooviId: string, emv: string, qrBase64: string, raw: object}>}
 */
export async function createPixPayment({ price, description }) {
  // Modo mock para desenvolvimento/local quando credenciais não existem
  const shouldMock =
    process.env.WOOVI_MOCK === "true" ||
    (!process.env.WOOVI_APP_ID && !process.env.WOOVI_API_KEY);

  if (shouldMock) {
    if (process.env.WOOVI_MOCK !== "true") {
      console.warn("[woovi] Mock ativado por falta de env:", {
        hasAppId: Boolean(process.env.WOOVI_APP_ID),
        hasApiKey: Boolean(process.env.WOOVI_API_KEY),
      });
    }
    const wooviId = `MOCK-${Date.now()}`;
    const emv = `000201MOCKTXID${wooviId}`;
    const qrBase64 = await qrcode.toDataURL(emv, { width: 300 });
    const raw = { mock: true, description, price };
    return { wooviId, emv, qrBase64, raw };
  }

  const client = getWooviClient();
  if (!client) {
    throw new Error("Cliente Woovi não inicializado");
  }

  try {
    // Criar cobrança usando o SDK Woovi
    console.log("[WOOVI] Criando cobrança com valor:", price, "descrição:", description);
    const { charge, brCode, correlationID, raw } = await createCharge({
      client,
      amount: price,
      description,
    });

    console.log("[WOOVI] Dados retornados após criar cobrança:");
    console.log("- charge:", JSON.stringify(charge, null, 2));
    console.log("- brCode:", brCode);
    console.log("- correlationID:", correlationID);

    // O EMV (brCode) já vem na resposta da criação da cobrança
    // Pode estar em charge.brCode ou charge.charge.brCode
    const emv = brCode || charge?.brCode || charge?.charge?.brCode || null;

    // Gera QR em base64 a partir do brCode
    let qrBase64 = null;
    if (emv) {
      qrBase64 = await qrcode.toDataURL(emv, { width: 300 });
      console.log("[WOOVI] QR Code gerado em base64:", qrBase64.substring(0, 50) + "...");
    } else {
      console.warn("[WOOVI] EMV (brCode) não encontrado! Não foi possível gerar QR Code.");
    }

    // O wooviId deve ser o correlationID (usado para identificar o pagamento)
    // A Woovi usa correlationID para identificar cobranças
    const wooviId = correlationID || charge?.correlationID || charge?.charge?.correlationID || null;
    
    console.log("[WOOVI] wooviId final:", wooviId);
    console.log("[WOOVI] EMV final:", emv ? emv.substring(0, 50) + "..." : null);
    
    return {
      wooviId,
      emv,
      qrBase64,
      raw: raw || charge,
    };
  } catch (error) {
    console.error("[woovi] Erro ao criar pagamento:", error);
    throw error;
  }
}

/**
 * Verifica o status de um pagamento PIX via Woovi
 * @param {object} params - Parâmetros
 * @param {string} params.payment_id - ID do pagamento (wooviId)
 * @returns {Promise<{status: string, raw: object}>}
 */
export async function checkPixPayment({ payment_id }) {
  const client = getWooviClient();
  if (!client) {
    throw new Error("Cliente Woovi não inicializado");
  }

  try {
    // A Woovi permite buscar por correlationID ou identifier/transactionID
    // Tentamos buscar usando o payment_id (que é o correlationID)
    let raw = null;
    let wooviStatus = null;
    
    try {
      // Tenta buscar usando o correlationID diretamente
      // O SDK espera { id: chargeId } ao invés de string direta
      raw = await getChargeStatus({ client, chargeId: payment_id });
      
      // A resposta pode ter status em charge.status ou status direto
      wooviStatus = raw?.status || raw?.charge?.status || raw?.state || null;
      
    } catch (error) {
      console.warn(`[woovi] Erro ao buscar charge por correlationID ${payment_id}:`, error);
      throw error;
    }
    
    const status = mapStatus(wooviStatus);

    console.log(`[WOOVI] Status do pagamento ${payment_id}: ${wooviStatus} -> ${status}`);

    // Atualiza o pagamento no banco (busca por wooviId que é o correlationID)
    await Payment.findOneAndUpdate(
      { wooviId: payment_id },
      { status, wooviRaw: raw }
    );

    return { status, raw };
  } catch (error) {
    console.error("[woovi] Erro ao verificar pagamento:", error);
    throw error;
  }
}

/**
 * Obtém o cliente Woovi (para uso externo se necessário)
 */
export function getClient() {
  return getWooviClient();
}


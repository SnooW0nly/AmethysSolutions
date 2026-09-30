/**
 * Serviço Mistic Pay - API de pagamentos PIX
 * Documentação: https://api.misticpay.com
 */

import axios from "axios";
import qrcode from "qrcode";
import Payment from "../../database/models/Payment.js";
import { mapStatus } from "./pix.js";

const MISTIC_BASE_URL = "https://api.misticpay.com/api";

/**
 * Obtém os headers de autenticação da Mistic
 */
function getAuthHeaders() {
    const clientId = process.env.MISTIC_CLIENT;
    const clientSecret = process.env.MISTIC_SECRET;

    if (!clientId || !clientSecret) {
        console.warn("[mistic] MISTIC_CLIENT ou MISTIC_SECRET não configurado");
        return null;
    }

    return {
        ci: clientId,
        cs: clientSecret,
        "Content-Type": "application/json",
    };
}

/**
 * Cria um pagamento PIX via Mistic
 * @param {object} params - Parâmetros do pagamento
 * @param {number} params.price - Valor do pagamento em reais (ex: 4.55)
 * @param {string} params.description - Descrição do pagamento
 * @param {string} params.payerName - Nome do pagador (opcional, usa default)
 * @param {string} params.payerDocument - CPF do pagador (opcional, usa default)
 * @param {string} params.transactionId - ID da transação na sua aplicação (opcional)
 * @returns {Promise<{misticId: string, emv: string, qrBase64: string, raw: object}>}
 */
export async function createPixPayment({
    price,
    description,
    payerName = "Cliente Amethys",
    payerDocument = "00000000000",
    transactionId = null
}) {
    const headers = getAuthHeaders();

    // Modo mock para desenvolvimento quando credenciais não existem
    if (!headers) {
        console.warn("[mistic] Mock ativado por falta de credenciais");
        const mockId = `MOCK-${Date.now()}`;
        const emv = `000201MOCKTXID${mockId}`;
        const qrBase64 = await qrcode.toDataURL(emv, { width: 300 });
        return { misticId: mockId, emv, qrBase64, raw: { mock: true, description, price } };
    }

    try {
        // Gera um transactionId único se não fornecido
        const txId = transactionId || `vision-${Date.now()}-${Math.random().toString(36).substring(7)}`;

        console.log("[MISTIC] Criando transação:", { price, description, payerName, txId });

        const response = await axios.post(
            `${MISTIC_BASE_URL}/transactions/create`,
            {
                amount: Number(price),
                payerName,
                payerDocument: payerDocument.replace(/\D/g, ""), // Remove formatação
                transactionId: txId,
                description,
            },
            { headers }
        );

        const data = response.data;
        console.log("[MISTIC] Resposta da criação:", JSON.stringify(data, null, 2));

        if (!data || !data.data) {
            throw new Error("Resposta inválida da Mistic");
        }

        const result = data.data;

        // O misticId é o transactionId retornado pela Mistic
        const misticId = result.transactionId;

        // O EMV é o código copia-e-cola (copyPaste)
        const emv = result.copyPaste;

        // Gera QR Code a partir do EMV ou usa o qrCodeBase64 da resposta
        let qrBase64 = result.qrCodeBase64;
        if (!qrBase64 && emv) {
            qrBase64 = await qrcode.toDataURL(emv, { width: 300 });
        }

        console.log("[MISTIC] Transação criada com sucesso:", {
            misticId,
            emv: emv ? emv.substring(0, 50) + "..." : null,
            hasQrCode: !!qrBase64,
        });

        return {
            misticId,
            emv,
            qrBase64,
            raw: result,
        };
    } catch (error) {
        console.error("[mistic] Erro ao criar pagamento:", error.response?.data || error.message);
        throw error;
    }
}

/**
 * Verifica o status de um pagamento PIX via Mistic
 * @param {object} params - Parâmetros
 * @param {string} params.payment_id - ID da transação (misticId)
 * @returns {Promise<{status: string, raw: object}>}
 */
export async function checkPixPayment({ payment_id }) {
    const headers = getAuthHeaders();

    if (!headers) {
        throw new Error("Credenciais Mistic não configuradas");
    }

    try {
        console.log(`[MISTIC] Verificando transação ${payment_id}`);

        const response = await axios.post(
            `${MISTIC_BASE_URL}/transactions/check`,
            { transactionId: payment_id },
            { headers }
        );

        const data = response.data;
        console.log(`[MISTIC] Status da transação ${payment_id}:`, JSON.stringify(data, null, 2));

        if (!data || !data.transaction) {
            throw new Error("Resposta inválida da Mistic");
        }

        const transaction = data.transaction;
        const misticStatus = transaction.transactionState;
        const status = mapStatus(misticStatus);

        console.log(`[MISTIC] Status mapeado: ${misticStatus} -> ${status}`);

        // Atualiza o pagamento no banco (busca por misticId)
        await Payment.findOneAndUpdate(
            { $or: [{ misticId: payment_id }, { wooviId: payment_id }] },
            { status, misticRaw: transaction }
        );

        return { status, raw: transaction };
    } catch (error) {
        console.error("[mistic] Erro ao verificar pagamento:", error.response?.data || error.message);
        throw error;
    }
}

/**
 * Re-exporta mapStatus para uso externo
 */
export { mapStatus } from "./pix.js";

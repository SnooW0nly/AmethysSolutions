/**
 * Saque automático — Mistic Pay
 * Endpoint: POST /api/transactions/withdraw
 * Documentação: https://docs.misticpay.com/#create-withdrawal
 *
 * Após cada pagamento aprovado, saca o valor daquele pagamento
 * especificamente para o PIX configurado em WITHDRAW_PIX_KEY.
 */

import axios from "axios";

const MISTIC_BASE_URL  = "https://api.misticpay.com";
const WITHDRAW_PIX_KEY = process.env.WITHDRAW_PIX_KEY  || "a4892f02-41cc-45f8-8e22-083ebb8f5a8e";
const WITHDRAW_WEBHOOK = process.env.WITHDRAW_WEBHOOK_URL || null; // opcional

/**
 * Retorna os headers de autenticação da Mistic
 */
function getAuthHeaders() {
  const clientId     = process.env.MISTIC_CLIENT;
  const clientSecret = process.env.MISTIC_SECRET;

  if (!clientId || !clientSecret) {
    throw new Error("[mistic/withdraw] MISTIC_CLIENT ou MISTIC_SECRET não configurado");
  }

  return {
    ci: clientId,
    cs: clientSecret,
    "Content-Type": "application/json",
  };
}

/**
 * Realiza o saque do valor exato de um pagamento aprovado para o PIX configurado.
 *
 * @param {object}  params
 * @param {string}  params.transactionId   - misticId da cobrança (apenas para log/descrição)
 * @param {number}  params.amount          - Valor a sacar em reais  (ex: 4.55 = R$ 4,55)
 * @param {string}  [params.pixKey]        - Chave PIX destino (default: WITHDRAW_PIX_KEY)
 * @param {string}  [params.pixKeyType]    - Tipo da chave: "EMAIL" | "CPF" | "CNPJ" | "TELEFONE" | "CHAVE_ALEATORIA"
 * @param {string}  [params.description]   - Descrição do saque
 *
 * @returns {Promise<{ success: boolean, jobId?: string, withdrawTxId?: number, error?: string }>}
 */
export async function withdrawPayment({
  transactionId,
  amount,
  pixKey     = WITHDRAW_PIX_KEY,
  pixKeyType = "CHAVE_ALEATORIA",
  description,
}) {
  try {
    const headers = getAuthHeaders();

    const amountFloat = Number(Number(amount).toFixed(2));

    if (!amountFloat || amountFloat <= 0) {
      throw new Error(`Valor de saque inválido: ${amount}`);
    }

    if (!pixKey) {
      throw new Error("Chave PIX de destino não configurada (WITHDRAW_PIX_KEY)");
    }

    const desc = description || `Saque automático — pagamento ${transactionId}`;

    console.log(
      `[mistic/withdraw] ▶ Iniciando saque — valor: R$ ${amountFloat} | ` +
      `chave: ${pixKey} (${pixKeyType}) | pagamento: ${transactionId}`
    );

    // Payload conforme documentação oficial da Mistic
    const payload = {
      amount:      amountFloat,  // valor em reais (ex: 10.50)
      pixKey,                    // chave PIX do destinatário
      pixKeyType,                // "EMAIL", "CPF", "CNPJ", "TELEFONE" ou "CHAVE_ALEATORIA"
      description: desc,
      ...(WITHDRAW_WEBHOOK ? { projectWebhook: WITHDRAW_WEBHOOK } : {}),
    };

    const response = await axios.post(
      `${MISTIC_BASE_URL}/api/transactions/withdraw`,
      payload,
      { headers }
    );

    const data = response.data;

    // Resposta esperada: { message, data: { jobId, transactionId, status, message } }
    // De acordo com a documentação, os dados podem estar diretamente no corpo ou em data
    const resultData   = data?.data || data;
    const jobId        = resultData?.jobId         || null;
    const withdrawTxId = resultData?.transactionId || null;
    const status       = resultData?.status        || null;

    console.log(
      `[mistic/withdraw] ✅ Saque enfileirado — jobId: ${jobId} | ` +
      `withdrawTxId: ${withdrawTxId} | status: ${status}`
    );

    return { success: true, jobId, withdrawTxId, status };
  } catch (error) {
    const detail = error.response?.data || error.message;

    console.error(
      `[mistic/withdraw] ❌ Erro ao sacar pagamento ${transactionId}:`,
      typeof detail === "object" ? JSON.stringify(detail) : detail
    );

    // Falha no saque NUNCA interrompe o fluxo — o cliente já recebeu o bot
    return { success: false, error: String(typeof detail === "object" ? JSON.stringify(detail) : detail) };
  }
}
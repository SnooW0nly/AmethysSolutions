/**
 * feeService.js
 *
 * Ponto único de acesso às taxas globais do sistema.
 * Sempre usa FeeConfig do banco; fallback para os defaults
 * caso a collection esteja vazia ou o banco esteja offline.
 *
 * Defaults:
 *   transactionFee = 55 centavos  (R$ 0,55)
 *   withdrawFee    = 30 centavos  (R$ 0,30)
 */

import FeeConfig from '../database/models/FeeConfig.js';

// Defaults hardcoded — usados se o banco falhar completamente
export const DEFAULT_TRANSACTION_FEE = 55; // centavos
export const DEFAULT_WITHDRAW_FEE    = 30; // centavos

/**
 * Retorna as taxas globais atuais.
 * @returns {Promise<{ transactionFee: number, withdrawFee: number, _fromDefault: boolean }>}
 */
export async function getFees() {
  try {
    const config = await FeeConfig.getSingleton();
    return {
      transactionFee: config.transactionFee ?? DEFAULT_TRANSACTION_FEE,
      withdrawFee:    config.withdrawFee    ?? DEFAULT_WITHDRAW_FEE,
      _fromDefault:   config._fromDefault   ?? false,
    };
  } catch (err) {
    console.warn('[feeService] Falha ao buscar FeeConfig, usando defaults:', err.message);
    return {
      transactionFee: DEFAULT_TRANSACTION_FEE,
      withdrawFee:    DEFAULT_WITHDRAW_FEE,
      _fromDefault:   true,
    };
  }
}

/**
 * Retorna apenas a taxa de transação/envio (centavos).
 */
export async function getTransactionFee() {
  const { transactionFee } = await getFees();
  return transactionFee;
}

/**
 * Retorna apenas a taxa de saque PIX (centavos).
 */
export async function getWithdrawFee() {
  const { withdrawFee } = await getFees();
  return withdrawFee;
}

export default { getFees, getTransactionFee, getWithdrawFee };

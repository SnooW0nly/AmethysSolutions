/**
 * Serviço de categorização WHITE/BLACK
 *
 * Taxas de TRANSAÇÃO configuráveis via admin panel (PUT /api/v1/admin/plans/:id)
 * armazenadas no MongoDB na collection `plans`.
 *
 * Taxa de SAQUE (withdrawFee) configurável via PUT /api/v1/admin/fees
 * armazenada no MongoDB na collection `fee_config`.
 *
 * Planos esperados no banco:
 *   WHITE_1 … WHITE_5  → transactionFee (centavos), splitFee (centavos)
 *   BLACK              → transactionFeePercent (%), transactionFeeFixed (centavos), splitFee (centavos)
 */

import Plan from '../database/models/Plan.js';
import { getWithdrawFee, getTransactionFee, DEFAULT_TRANSACTION_FEE, DEFAULT_WITHDRAW_FEE } from './feeService.js';

// Custo fixo estimado do adquirente GoatPay (centavos) — ajuste via GOATPAY_PROVIDER_FEE_CENTS
export const GOATPAY_PROVIDER_FEE = parseInt(process.env.GOATPAY_PROVIDER_FEE_CENTS || '0', 10);
export const MISTIC_BASE_FEE = GOATPAY_PROVIDER_FEE; // alias legado

// ─── Defaults (fallback se o plano não existir no banco) ──────────────────────
// Taxa de transação: usa DEFAULT_TRANSACTION_FEE do feeService (55c)
// Cada tier WHITE pode ter um offset, mas o base vem do FeeConfig agora.
// Para manter compatibilidade com tiers, os offsets são calculados sobre o base.

const DEFAULT_BLACK = {
  percentFee: 6,   // 6%
  fixedFee: 200,   // R$ 2,00
  splitPercent: 1, // 1%
  splitFixed: 100, // R$ 1,00
};

// Exportados apenas para compatibilidade com imports legados
export const BLACK_CONFIG = DEFAULT_BLACK;

// WHITE_TIERS agora é dinâmico via FeeConfig — mantido como referência de offset por tier
// O fee real de cada tier = FeeConfig.transactionFee (base) + offset abaixo
const WHITE_TIER_OFFSETS = {
  1: 0,
  2: 0,
  3: 0,
  4: 0,
  5: 0,
};

// Alias legado (valores estáticos para código que não usa await)
export const WHITE_TIERS = {
  1: { fee: DEFAULT_TRANSACTION_FEE },
  2: { fee: DEFAULT_TRANSACTION_FEE },
  3: { fee: DEFAULT_TRANSACTION_FEE },
  4: { fee: DEFAULT_TRANSACTION_FEE },
  5: { fee: DEFAULT_TRANSACTION_FEE },
};

// ─── Helpers de leitura do banco ──────────────────────────────────────────────

async function fetchWhitePlan(tier = 1) {
  try {
    return await Plan.findOne({ id: `WHITE_${tier}`, active: true });
  } catch (_) {
    return null;
  }
}

async function fetchBlackPlan() {
  try {
    return await Plan.findOne({ id: 'BLACK', active: true });
  } catch (_) {
    return null;
  }
}

// ─── API pública ──────────────────────────────────────────────────────────────

/**
 * Retorna a taxa fixa WHITE para o tier (em centavos).
 * Prioridade: Plan.transactionFee → FeeConfig.transactionFee → DEFAULT (55c)
 */
export async function getWhiteFeeTier(tier = 1) {
  const plan = await fetchWhitePlan(tier);
  if (plan?.transactionFee != null) return plan.transactionFee;
  // Fallback para FeeConfig global
  return await getTransactionFee();
}

/**
 * Versão síncrona de getWhiteFeeTier para compatibilidade com código legado.
 * Retorna o default hardcoded (55c). Para valor real do banco, use getWhiteFeeTier().
 */
export function getWhiteFee(tier = 1) {
  return DEFAULT_TRANSACTION_FEE;
}

/**
 * Calcula a taxa para uma transação.
 * @param {string} category - 'WHITE' ou 'BLACK'
 * @param {number} tier     - Tier WHITE (1-5), ignorado para BLACK
 * @param {number} valueInCents
 * @returns {Promise<number>} Taxa em centavos
 */
export async function calculateFee(category, tier, valueInCents) {
  if (category === 'BLACK') {
    const plan = await fetchBlackPlan();
    const pct  = plan?.transactionFeePercent ?? DEFAULT_BLACK.percentFee;
    const fix  = plan?.transactionFeeFixed   ?? DEFAULT_BLACK.fixedFee;
    return Math.ceil((valueInCents * pct) / 100) + fix;
  }

  // WHITE: prioridade Plan.transactionFee → FeeConfig → default
  const plan = await fetchWhitePlan(tier);
  if (plan?.transactionFee != null) return plan.transactionFee;
  return await getTransactionFee();
}

/**
 * Calcula a taxa de saque PIX (centavos).
 * Usa FeeConfig.withdrawFee → fallback 30c.
 * @returns {Promise<number>} Taxa de saque em centavos
 */
export async function calculateWithdrawFee() {
  return await getWithdrawFee();
}

/**
 * Calcula o split (parte da Amethys) repassado via GoatPay splitUser/splitTax.
 * @returns {Promise<number>} Split em centavos
 */
export async function calculateSplit(category, tier, valueInCents = 0) {
  if (category === 'BLACK') {
    const plan = await fetchBlackPlan();
    if (plan?.splitFee != null) {
      return plan.splitFee;
    }
    const pctSplit = Math.ceil((valueInCents * DEFAULT_BLACK.splitPercent) / 100);
    return pctSplit + DEFAULT_BLACK.splitFixed;
  }

  // WHITE
  const plan = await fetchWhitePlan(tier);
  if (plan?.splitFee != null) return plan.splitFee;
  const fee = plan?.transactionFee ?? await getTransactionFee();
  return Math.max(0, fee - GOATPAY_PROVIDER_FEE);
}

/**
 * Retorna string de exibição da taxa de transação.
 */
export async function getFeeDisplay(category, tier) {
  if (category === 'BLACK') {
    const plan = await fetchBlackPlan();
    const pct = plan?.transactionFeePercent ?? DEFAULT_BLACK.percentFee;
    const fix = plan?.transactionFeeFixed   ?? DEFAULT_BLACK.fixedFee;
    return `${pct}% + R$ ${(fix / 100).toFixed(2).replace('.', ',')}`;
  }
  const plan = await fetchWhitePlan(tier);
  const fee = plan?.transactionFee ?? await getTransactionFee();
  return `R$ ${(fee / 100).toFixed(2).replace('.', ',')}`;
}

/**
 * Retorna string de exibição da taxa de saque.
 */
export async function getWithdrawFeeDisplay() {
  const fee = await getWithdrawFee();
  return `R$ ${(fee / 100).toFixed(2).replace('.', ',')}`;
}

export function getCategoryDisplay(category, tier) {
  return category === 'BLACK' ? 'BLACK' : `WHITE ${tier}`;
}

export function determineCategory(formData) {
  const { description, medFrequency } = formData;
  const blackKeywords = [
    'casino','cassino','aposta','apostas','bet','betting',
    'red','golpe','esquema','pirâmide','piramide',
    'forex','trading','investimento garantido',
  ];
  const descLower = (description || '').toLowerCase();
  const hasBlackKeyword = blackKeywords.some(k => descLower.includes(k));
  const hasFrequentMeds = medFrequency === 'FREQUENTLY' || medFrequency === 'ALWAYS';
  return (hasBlackKeyword || hasFrequentMeds) ? 'BLACK' : 'WHITE';
}

export function usesSeparateMisticAccount(category) {
  return category === 'BLACK';
}

export function usesSeparateGoatPayKey(category) {
  return category === 'BLACK';
}

export default {
  WHITE_TIERS, BLACK_CONFIG, MISTIC_BASE_FEE,
  getWhiteFee, getWhiteFeeTier,
  calculateFee, calculateSplit, calculateWithdrawFee,
  getFeeDisplay, getWithdrawFeeDisplay, getCategoryDisplay,
  determineCategory, usesSeparateMisticAccount,
};

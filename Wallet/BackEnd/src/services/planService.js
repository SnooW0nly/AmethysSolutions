/**
 * Serviço de gerenciamento de planos (AGORA VIA DATABASE)
 * 
 * Busca os planos diretamente do MongoDB (Model Plan).
 * Mantém fallback para LEGACY_ADAPTER apenas em caso de erro ou DB vazio.
 */

import Plan from '../database/models/Plan.js';
import {
  WHITE_TIERS,
  BLACK_CONFIG,
  getWhiteFee,
  getFeeDisplay,
  calculateFee,
  calculateSplit
} from './categoryService.js';

// Fallback apenas para quando o banco estiver vazio ou der erro
const LEGACY_ADAPTER = {
  FREE: {
    id: 'FREE',
    name: 'WHITE',
    transactionFeePercent: 0,
    transactionFeeFixed: getWhiteFee(1),
    transactionFee: getWhiteFee(1),
    splitFee: 0,
    useSeparateMistic: false,
    monthlyFee: 0,
    minTransactions: 0,
    maxTransactions: null,
    downgradeTo: null,
    order: 0,
  },
  BLACK: {
    id: 'BLACK',
    name: 'BLACK',
    transactionFeePercent: BLACK_CONFIG.percentFee,
    transactionFeeFixed: BLACK_CONFIG.fixedFee,
    transactionFee: BLACK_CONFIG.fixedFee,
    splitFee: BLACK_CONFIG.splitFixed,
    useSeparateMistic: true,
    monthlyFee: 0,
    minTransactions: 0,
    maxTransactions: null,
    downgradeTo: null,
    order: -1,
  },
};

let plansCache = null;
let cacheTimestamp = null;
const CACHE_TTL = 60000; // 1 minuto

/**
 * Carrega todos os planos ativos do banco de dados
 */
async function loadPlansFromDB() {
  const now = Date.now();
  if (plansCache && cacheTimestamp && (now - cacheTimestamp) < CACHE_TTL) {
    return plansCache;
  }

  try {
    const plansFromDB = await Plan.find({ active: true }).lean();
    const plansMap = {};
    for (const plan of plansFromDB) {
      plansMap[plan.id] = {
        id: plan.id,
        name: plan.name,
        description: plan.description || '',
        transactionFeePercent: plan.transactionFeePercent ?? 0,
        transactionFeeFixed: plan.transactionFeeFixed ?? 0,
        transactionFee: plan.transactionFee ?? 0,
        splitFee: plan.splitFee ?? 0,
        useSeparateMistic: plan.useSeparateMistic ?? false,
        monthlyFee: plan.monthlyFee ?? 0,
        minTransactions: plan.minTransactions ?? 0,
        maxTransactions: plan.maxTransactions ?? null,
        downgradeTo: plan.downgradeTo ?? null,
        order: plan.order ?? 0,
      };
    }
    plansCache = plansMap;
    cacheTimestamp = now;
    return plansCache;
  } catch (error) {
    console.error('[planService] Erro ao buscar planos do DB, usando fallback:', error);
    return LEGACY_ADAPTER;
  }
}

/**
 * Obtém planos (com cache)
 */
export async function getPlans() {
  return await loadPlansFromDB();
}

/**
 * Limpa cache de planos
 */
export function clearPlanCache() {
  plansCache = null;
  cacheTimestamp = null;
}

/**
 * Obtém configuração de um plano específico
 * @param {string} planName - ID do plano (ex: 'FREE', 'BLACK1')
 */
export async function getPlan(planName) {
  const key = planName?.toUpperCase();
  if (!key) return (await getPlans())['FREE'] || LEGACY_ADAPTER.FREE;

  const plans = await getPlans();
  if (plans[key]) return plans[key];

  // Fallback: se não encontrar no DB, tenta o LEGACY_ADAPTER
  if (LEGACY_ADAPTER[key]) return LEGACY_ADAPTER[key];

  // Último fallback: plano FREE genérico
  return plans['FREE'] || LEGACY_ADAPTER.FREE;
}

/**
 * Obtém ordem dos planos (baseado no campo order do DB)
 */
export async function getPlanOrder() {
  const plans = await getPlans();
  const order = Object.values(plans)
    .sort((a, b) => (a.order || 0) - (b.order || 0))
    .map(p => p.id);
  return order.length ? order : ['FREE', 'BLACK'];
}

/**
 * Obtém o próximo plano (upgrade) com base na ordem
 * @param {string} currentPlan
 */
export async function getNextPlan(currentPlan) {
  const order = await getPlanOrder();
  const idx = order.indexOf(currentPlan?.toUpperCase());
  if (idx === -1 || idx === order.length - 1) return null;
  const nextId = order[idx + 1];
  return await getPlan(nextId);
}

/**
 * Obtém o plano anterior (downgrade) com base na ordem
 * @param {string} currentPlan
 */
export async function getPreviousPlan(currentPlan) {
  const order = await getPlanOrder();
  const idx = order.indexOf(currentPlan?.toUpperCase());
  if (idx <= 0) return null;
  const prevId = order[idx - 1];
  return await getPlan(prevId);
}

/**
 * Verifica se o usuário deve fazer upgrade baseado nas transações
 * (utiliza os limites do plano)
 */
export async function shouldUpgrade(currentPlan, transactionCount) {
  const plan = await getPlan(currentPlan);
  if (!plan) return false;
  const maxTx = plan.maxTransactions;
  if (maxTx !== null && transactionCount > maxTx) {
    const next = await getNextPlan(currentPlan);
    if (next) return next.id;
  }
  return false;
}

/**
 * Verifica se o usuário deve fazer downgrade baseado nas transações
 */
export async function shouldDowngrade(currentPlan, transactionCount) {
  const plan = await getPlan(currentPlan);
  if (!plan) return false;
  const minTx = plan.minTransactions;
  if (minTx > 0 && transactionCount < minTx) {
    const prev = await getPreviousPlan(currentPlan);
    if (prev) return prev.id;
    if (plan.downgradeTo) return plan.downgradeTo;
  }
  return false;
}

/**
 * Obtém todos os planos disponíveis (array)
 */
export async function getAllPlans() {
  const plans = await getPlans();
  return Object.values(plans);
}

/**
 * Verifica se uma data é dia útil (segunda a sexta)
 */
export function isBusinessDay(date) {
  const day = date.getDay();
  return day >= 1 && day <= 5;
}

/**
 * Calcula o próximo dia útil a partir de uma data
 */
export function getNextBusinessDay(date) {
  const nextDay = new Date(date);
  nextDay.setDate(nextDay.getDate() + 1);

  while (!isBusinessDay(nextDay)) {
    nextDay.setDate(nextDay.getDate() + 1);
  }
  return nextDay;
}

/**
 * Calcula o dia útil anterior a partir de uma data
 */
export function getPreviousBusinessDay(date) {
  const prevDay = new Date(date);
  prevDay.setDate(prevDay.getDate() - 1);

  while (!isBusinessDay(prevDay)) {
    prevDay.setDate(prevDay.getDate() - 1);
  }
  return prevDay;
}

/**
 * Inicializa datas de plano (30 dias a partir de hoje)
 */
export function initializePlanDates() {
  const now = new Date();
  const startDate = new Date(now);
  startDate.setHours(0, 0, 0, 0);

  const endDate = new Date(startDate);
  endDate.setDate(endDate.getDate() + 30);

  const renewalDate = getPreviousBusinessDay(endDate);

  return {
    planStartDate: startDate.toISOString(),
    planEndDate: endDate.toISOString(),
    planRenewalDate: renewalDate.toISOString()
  };
}

/**
 * Calcula conversão proporcional de planos (mantido, mas sem efeito prático)
 */
export async function calculatePlanConversion(oldPlan, newPlan, planEndDate) {
  const now = new Date();
  return {
    creditAmount: 0,
    daysRemaining: 0,
    daysFromCredit: 0,
    newEndDate: now.toISOString(),
    planRenewalDate: now.toISOString(),
    oldPlanValue: 0,
    newPlanValue: 0,
    oldPlanDailyValue: 0,
    newPlanDailyValue: 0
  };
}

/**
 * Renova um plano (cria novas datas)
 */
export function renewPlanDates() {
  return initializePlanDates();
}

/**
 * Calcula taxa de transação baseado no plano (wrapper para categoryService)
 */
export async function calculateTransactionFee(planName, valueInCents) {
  const plan = await getPlan(planName);
  // Se o plano tiver percentual, usa; senão usa taxa fixa
  if (plan.transactionFeePercent && plan.transactionFeePercent > 0) {
    const percent = Math.ceil((valueInCents * plan.transactionFeePercent) / 100);
    const fixed = plan.transactionFeeFixed || 0;
    return percent + fixed;
  } else {
    return plan.transactionFee || 0;
  }
}

/**
 * Obtém o splitFee baseado no plano (parte da taxa que fica para o sistema)
 */
export async function getSplitFee(planName, valueInCents = 0) {
  const plan = await getPlan(planName);
  if (plan.splitFee !== undefined && plan.splitFee !== null) {
    // Se splitFee for percentual (futuro) ou fixo
    return plan.splitFee;
  }
  // Fallback: calcula baseado na taxa de transação - custo do gateway (50 centavos)
  const txFee = await calculateTransactionFee(planName, valueInCents);
  return Math.max(0, txFee - 50);
}

// Exportar fallback para compatibilidade (mas não usar diretamente)
export const PLANS = LEGACY_ADAPTER;
export const PLAN_ORDER = ['FREE', 'BLACK'];
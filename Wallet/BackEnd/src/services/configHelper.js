import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CONFIG_FILE = path.join(process.cwd(), 'config.json');

/**
 * Lê o arquivo config.json
 */
export function getConfig() {
  try {
    const configData = fs.readFileSync(CONFIG_FILE, 'utf8');
    return JSON.parse(configData);
  } catch (error) {
    console.warn('⚠️ Erro ao ler config.json:', error.message);
    return {};
  }
}

/**
 * Obtém a taxa de pagamento em centavos
 */
export function getPaymentFee() {
  const config = getConfig();
  return config.taxa_pagamento !== undefined ? config.taxa_pagamento : 0; // Padrão agora: R$ 0,00
}

/**
 * Obtém a taxa de saque em centavos
 */
export function getWithdrawFee() {
  const config = getConfig();
  return config.taxa_saque !== undefined ? config.taxa_saque : 65; // Padrão agora: R$ 0,65
}

/**
 * Verifica se saques automáticos estão ativados
 */
export function isAutoWithdrawEnabled() {
  const config = getConfig();
  return config.saques_auto === 'true' || config.saques_auto === true;
}

/**
 * Verifica se bloqueio automático de saldo em MEDs está ativado
 */
export function isAutoBlockBalanceEnabled() {
  const config = getConfig();
  // Por padrão, se não estiver configurado, assume true (ativado)
  if (config.bloqueio_med === undefined) {
    return true;
  }
  return config.bloqueio_med === 'true' || config.bloqueio_med === true;
}


/**
 * Funções de API para Segurança de Transferências
 */

import { apiGet, apiPost } from './api';

export interface SecurityStatus {
  transferSecurityEnabled: boolean;
}

export interface SecurityStatusResponse {
  success: boolean;
  data: SecurityStatus;
}

/**
 * Obter status da segurança de transferências
 */
export async function getSecurityStatus(): Promise<SecurityStatusResponse> {
  return apiGet('/v1/user/security');
}

/**
 * Ativar segurança de transferências
 */
export async function enableTransferSecurity(): Promise<{ success: boolean; message: string; data: SecurityStatus }> {
  return apiPost('/v1/user/security/enable', {});
}

/**
 * Solicitar código para desativar segurança
 */
export async function requestDisableSecurityCode(): Promise<{ success: boolean; message: string }> {
  return apiPost('/v1/user/security/request-disable-code', {});
}

/**
 * Desativar segurança de transferências (requer código)
 */
export async function disableTransferSecurity(code: string): Promise<{ success: boolean; message: string; data: SecurityStatus }> {
  return apiPost('/v1/user/security/disable', { code });
}

/**
 * Solicitar código de verificação para transferência
 */
export async function requestTransferCode(amount: number | string): Promise<{ success: boolean; message: string }> {
  return apiPost('/v1/user/security/request-transfer-code', { amount });
}

/**
 * Verificar código de transferência
 */
export async function verifyTransferCode(code: string, amount: number | string): Promise<{ success: boolean; message: string; verified: boolean }> {
  return apiPost('/v1/user/security/verify-transfer-code', { code, amount });
}


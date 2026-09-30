/**
 * Funções de API para gerenciar API Keys
 */

import { apiGet, apiPost, apiPut, apiDelete } from './api';

export interface ApiKeyPermission {
  permission: string;
  description: string;
}

export interface ApiKey {
  type: 'main' | 'secondary';
  id?: number;
  name?: string;
  key?: string; // Só retornado na criação/reset
  permissions: string[];
  permissionsDescription?: ApiKeyPermission[];
  createdAt: string;
  lastUsedAt?: string | null;
  active: boolean;
  webhookUrl?: string;
}

export interface ApiKeyListResponse {
  success: boolean;
  data: {
    apiKeys: ApiKey[];
    total: number;
  };
}

export interface ApiKeyPermissionsResponse {
  success: boolean;
  data: {
    permissions: Record<string, string>;
    description: string;
  };
}

export interface CreateApiKeyData {
  name: string;
  permissions: string[];
  webhookUrl?: string;
}

export interface CreateApiKeyResponse {
  success: boolean;
  message: string;
  data: {
    apiKey: string;
    name: string;
    permissions: string[];
    permissionsDescription: ApiKeyPermission[];
    warning: string;
  };
}

export interface ResetApiKeyResponse {
  success: boolean;
  message: string;
  data: {
    apiKey: string;
    keyType: 'main' | 'secondary';
    keyName: string;
    warning: string;
  };
}

export interface UpdateApiKeyData {
  name?: string;
  permissions?: string[];
  active?: boolean;
  webhookUrl?: string;
}

/**
 * Listar todas as API Keys do usuário
 */
export async function listApiKeys(): Promise<ApiKeyListResponse> {
  return apiGet('/v1/user/api-key/list');
}

/**
 * Obter permissões disponíveis
 */
export async function getApiKeyPermissions(): Promise<ApiKeyPermissionsResponse> {
  return apiGet('/v1/user/api-key/permissions');
}

/**
 * Criar nova API Key secundária
 */
export async function createApiKey(data: CreateApiKeyData): Promise<CreateApiKeyResponse> {
  return apiPost('/v1/user/api-key/create', data);
}

/**
 * Resetar API Key (principal ou secundária)
 */
export async function resetApiKey(): Promise<ResetApiKeyResponse> {
  return apiPost('/v1/user/api-key/reset');
}

/**
 * Resetar API Key secundária específica
 */
export async function resetSecondaryApiKey(index: number): Promise<ResetApiKeyResponse> {
  return apiPost(`/v1/user/api-key/${index}/reset`);
}

/**
 * Atualizar API Key secundária
 */
export async function updateApiKey(index: number, data: UpdateApiKeyData): Promise<{ success: boolean; message: string; data: ApiKey }> {
  return apiPut(`/v1/user/api-key/${index}`, data);
}

/**
 * Deletar API Key secundária
 */
export async function deleteApiKey(index: number): Promise<{ success: boolean; message: string }> {
  return apiDelete(`/v1/user/api-key/${index}`);
}

/**
 * Obter API Key principal (com a chave para copiar)
 */
export async function getMainApiKey(): Promise<{ success: boolean; data: { apiKey: string; webhookUrl: string | null } }> {
  return apiGet('/v1/user/api-key/main');
}

/**
 * Atualizar API Key principal (webhook)
 */
export async function updateMainApiKey(data: { webhookUrl?: string }): Promise<{ success: boolean; message: string; data: { webhookUrl: string | null } }> {
  return apiPut('/v1/user/api-key/main', data);
}

export interface AuthorizedIP {
  ip: string;
  active: boolean;
  createdAt: string;
}

export interface AuthorizedIPsResponse {
  success: boolean;
  data: {
    authorizedIPs: AuthorizedIP[];
    total: number;
    hasRestriction: boolean;
  };
}

/**
 * Listar IPs autorizados
 */
export async function listAuthorizedIPs(): Promise<AuthorizedIPsResponse> {
  return apiGet('/v1/user/api-key/ips');
}

/**
 * Adicionar IP autorizado
 */
export async function addAuthorizedIP(ip: string): Promise<{ success: boolean; message: string; data: AuthorizedIP }> {
  return apiPost('/v1/user/api-key/ips', { ip });
}

/**
 * Remover IP autorizado
 */
export async function removeAuthorizedIP(ip: string): Promise<{ success: boolean; message: string }> {
  return apiDelete('/v1/user/api-key/ips', { ip });
}

/**
 * Limpar todos os IPs autorizados
 */
export async function clearAuthorizedIPs(): Promise<{ success: boolean; message: string; data: { removedCount: number } }> {
  return apiPost('/v1/user/api-key/ips/clear');
}


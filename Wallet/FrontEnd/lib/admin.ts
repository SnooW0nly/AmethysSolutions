/**
 * Serviços para API Admin
 */

import { apiGet, apiPost, apiPut, apiDelete, apiRequest } from './api';

// Tipos
export interface AdminUser {
  id: string;
  name: string;
  email: string;
  taxID: string;
  phone?: string;
  balance: number;
  saldo_split: number;
  blocked: boolean;
  status: string;
  limits?: {
    daily?: number;
    monthly?: number;
    perTransaction?: number;
  };
  dailyUsed?: number;
  monthlyUsed?: number;
  plan: string;
  pixKey?: string;
  pixKeyType?: string;
  apiKey?: string;
  createdAt: string;
  updatedAt: string;
}

export interface AdminUserDetails extends AdminUser {
  admin?: boolean;
  planStartDate?: string;
  planEndDate?: string;
  planRenewalDate?: string;
  planAutoRenew?: boolean;
  paymentFee?: number;
  splitFee?: number;
  webhookUrl?: string;
  isAffiliate?: boolean;
  referredBy?: string;
  statistics: {
    totalPayments: number;
    completedPayments: number;
    totalReceived: number;
    totalFees: number;
    totalWithdraws: number;
    totalWithdrawn: number;
  };
}

export interface AdminTransaction {
  id: string;
  type: 'payment' | 'withdraw';
  value: number;
  netValue?: number;
  fee?: number;
  status: string;
  description?: string;
  createdAt: string;
  paidAt?: string;
  completedAt?: string;
}

export interface AdminUsersResponse {
  success: boolean;
  data: {
    users: AdminUser[];
    pagination: {
      total: number;
      limit: number;
      offset: number;
      hasMore: boolean;
    };
    statistics: {
      total: number;
      active: number;
      blocked: number;
      deleted: number;
      totalBalance: number;
      totalSplit: number;
    };
  };
}

export interface AdminStatsResponse {
  success: boolean;
  data: {
    users: {
      total: number;
      active: number;
      blocked: number;
      deleted: number;
      totalBalance: number;
      totalSplit: number;
    };
    payments: {
      total: number;
      active: number;
      completed: number;
      pending: number;
      cancelled: number;
      totalValue: number;
      totalNetValue: number;
      totalFees: number;
    };
    withdraws: {
      total: number;
      completed: number;
      failed: number;
      processing: number;
      totalAmount: number;
    };
    transfers?: {
      total: number;
      completed: number;
      totalAmount: number;
    };
    registrations?: {
      total: number;
      last24h: number;
      last7d: number;
      last30d: number;
    };
    financial: {
      totalReceived: number;
      totalWithdrawn: number;
      totalTransferred?: number;
      totalMoneyMoved?: number;
      totalFeesCollected: number;
      systemBalance: number;
      pendingPayments: number;
    };
    split: {
      totalSplit: number;
    };
    generatedAt: string;
  };
}

export interface Plan {
  id: string;
  name: string;
  description?: string;
  transactionFee: number;
  transactionFeeInReais: string;
  monthlyFee: number;
  monthlyFeeInReais: string;
  minTransactions: number;
  maxTransactions: number | null;
  downgradeTo: string | null;
  order: number;
  // campos avançados (plano BLACK / taxa dinâmica)
  transactionFeePercent?: number | null;
  transactionFeeFixed?: number | null;
  splitFee?: number | null;
  useSeparateMistic?: boolean;
  active: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface PlanCreateRequest {
  id: string;
  name: string;
  description?: string;
  transactionFee: number;
  monthlyFee: number;
  minTransactions: number;
  maxTransactions?: number | null;
  downgradeTo?: string | null;
  order?: number;
  transactionFeePercent?: number | null;
  transactionFeeFixed?: number | null;
  splitFee?: number | null;
  useSeparateMistic?: boolean;
}

export interface PlanUpdateRequest {
  name?: string;
  description?: string;
  transactionFee?: number;
  monthlyFee?: number;
  minTransactions?: number;
  maxTransactions?: number | null;
  downgradeTo?: string | null;
  order?: number;
  active?: boolean;
  transactionFeePercent?: number | null;
  transactionFeeFixed?: number | null;
  splitFee?: number | null;
  useSeparateMistic?: boolean;
}

export interface PlanUpdateUserRequest {
  userId: string;
  plan?: string;
  autoUpgrade?: boolean;
}

export interface PlanUpdateResponse {
  success: boolean;
  message: string;
  data: {
    plan: {
      name: string;
      transactionFee: number;
      transactionFeeInReais: string;
      monthlyFee: number;
      monthlyFeeInReais: string;
    };
    autoUpgrade: boolean;
    balance: number;
    balanceInReais: string;
    updatedAt: string;
  };
}

/**
 * Listar usuários (Admin)
 */
export async function getAdminUsers(params?: {
  status?: string;
  blocked?: boolean;
  limit?: number;
  offset?: number;
  search?: string;
}): Promise<AdminUsersResponse> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.blocked !== undefined) queryParams.append('blocked', String(params.blocked));
  if (params?.limit !== undefined) queryParams.append('limit', String(params.limit));
  if (params?.search) queryParams.append('search', params.search);
  if (params?.offset !== undefined) queryParams.append('offset', String(params.offset));

  const query = queryParams.toString();
  return apiGet<AdminUsersResponse>(`/v1/admin/users${query ? `?${query}` : ''}`);
}

/**
 * Buscar detalhes de um usuário (Admin)
 */
export async function getAdminUser(userId: string): Promise<{ success: boolean; data: { user: AdminUserDetails; statistics: any } }> {
  return apiGet(`/v1/admin/users/${userId}`);
}

/**
 * Bloquear/Desbloquear usuário (Admin)
 */
export async function blockUser(userId: string, blocked: boolean): Promise<{ success: boolean; message: string }> {
  return apiPost('/v1/user/block', { userId, blocked });
}

/**
 * Obter estatísticas do sistema (Admin)
 */
export async function getAdminStats(): Promise<AdminStatsResponse> {
  return apiGet<AdminStatsResponse>('/v1/admin/stats');
}

/**
 * Obter logs de auditoria (Admin)
 */
export async function getAuditLogs(params?: {
  action?: string;
  entity?: string;
  userId?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
}): Promise<{
  success: boolean;
  data: {
    logs: any[];
    pagination: {
      total: number;
      limit: number;
      offset: number;
      hasMore: boolean;
    };
  };
}> {
  const queryParams = new URLSearchParams();
  if (params?.action) queryParams.append('action', params.action);
  if (params?.entity) queryParams.append('entity', params.entity);
  if (params?.userId) queryParams.append('userId', params.userId);
  if (params?.startDate) queryParams.append('startDate', params.startDate);
  if (params?.endDate) queryParams.append('endDate', params.endDate);
  if (params?.limit) queryParams.append('limit', String(params.limit));
  if (params?.offset) queryParams.append('offset', String(params.offset));

  const query = queryParams.toString();
  return apiGet(`/v1/admin/audit${query ? `?${query}` : ''}`);
}

/**
 * Atualizar plano do usuário (Admin)
 */
export async function updateUserPlan(data: PlanUpdateUserRequest): Promise<PlanUpdateResponse> {
  return apiPut<PlanUpdateResponse>('/v1/user/plan', data);
}

/**
 * Definir plano do usuário com dias específicos (Admin)
 */
export async function updateUserPlanAdmin(userId: string, plan: string, days: number): Promise<{ success: boolean; data: any }> {
  return apiPut(`/v1/admin/users/${userId}/plan`, { plan, days });
}

/**
 * Listar transações do usuário (Admin)
 */
export async function getAdminUserTransactions(userId: string, params?: {
  limit?: number;
  offset?: number;
  type?: 'payment' | 'withdraw' | 'all';
}): Promise<{
  success: boolean;
  data: {
    transactions: AdminTransaction[];
    pagination: {
      total: number;
      limit: number;
      offset: number;
      hasMore: boolean;
    };
  };
}> {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.append('limit', String(params.limit));
  if (params?.offset) queryParams.append('offset', String(params.offset));
  if (params?.type) queryParams.append('type', params.type);

  const query = queryParams.toString();
  return apiGet(`/v1/admin/users/${userId}/transactions${query ? `?${query}` : ''}`);
}

/**
 * Listar planos disponíveis (usuário)
 */
export async function getPlans(): Promise<{ success: boolean; data: { plans: Plan[] } }> {
  return apiGet('/v1/user/plan/list');
}

/**
 * Obter informações do plano de um usuário
 */
export async function getUserPlan(userId: string): Promise<{
  success: boolean;
  data: {
    currentPlan: Plan;
    planDates: {
      startDate: string | null;
      endDate: string | null;
      renewalDate: string | null;
      daysRemaining: number | null;
      autoRenew: boolean;
    };
    monthlyTransactions: number;
    autoUpgrade: boolean;
    lastPlanCheck: string | null;
    planChangedAt: string | null;
    upgradeEligibility: any;
  };
}> {
  return apiGet(`/v1/user/plan?userId=${userId}`);
}

/**
 * Listar todos os planos (Admin) — suporta includeInactive
 */
export async function getAdminPlans(
  params?: { includeInactive?: boolean }
): Promise<{ success: boolean; data: { plans: Plan[] } }> {
  const q = params?.includeInactive ? '?includeInactive=true' : '';
  return apiGet(`/v1/admin/plans${q}`);
}

/**
 * Buscar um plano específico (Admin)
 */
export async function getAdminPlan(planId: string): Promise<{ success: boolean; data: { plan: Plan } }> {
  return apiGet(`/v1/admin/plans/${planId}`);
}

/**
 * Criar um novo plano (Admin)
 */
export async function createPlan(data: PlanCreateRequest): Promise<{ success: boolean; message: string; data: { plan: Plan } }> {
  return apiPost('/v1/admin/plans', data);
}

/**
 * Atualizar um plano (Admin)
 */
export async function updatePlan(planId: string, data: PlanUpdateRequest): Promise<{ success: boolean; message: string; data: { plan: Plan } }> {
  return apiPut(`/v1/admin/plans/${planId}`, data);
}

/**
 * Desativar um plano — soft delete (Admin)
 */
export async function deletePlan(planId: string): Promise<{ success: boolean; message: string }> {
  return apiDelete(`/v1/admin/plans/${planId}`);
}

/**
 * Definir ou remover admin de um usuário (Admin)
 */
export async function setUserAdmin(userId: string, admin: boolean): Promise<{ success: boolean; message: string; data: { id: string; name: string; email: string; admin: boolean } }> {
  return apiPut(`/v1/admin/users/${userId}/set-admin`, { admin });
}

/**
 * Reativar um plano desativado (Admin)
 */
export async function restorePlan(
  planId: string
): Promise<{ success: boolean; message: string; data: { plan: Plan } }> {
  return apiRequest(`/v1/admin/plans/${planId}/restore`, { method: 'PATCH' });
}

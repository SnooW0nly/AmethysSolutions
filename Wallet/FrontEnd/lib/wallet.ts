/**
 * Funções de API para Wallet (saldo, transações, saques, pagamentos)
 */

import { apiGet, apiPost, apiPut, apiDelete } from './api';

export interface BalanceData {
  balance: {
    total: number;
    pendingPayments: number;
    totalWithPending: number;
    isNegative: boolean;
  };
  disputes: {
    total: number;
    pending: number;
    totalDisputedAmount: number;
    totalBlockedAmount: number;
  };
  statistics: {
    totalReceived: number;
    totalFees: number;
    completedPayments: number;
    pendingPayments: number;
    totalPayments: number;
    totalCompletedTransactions?: number;
  };
  limits: {
    daily: number;
    dailyUsed: number;
    dailyRemaining: number;
    monthly: number;
    monthlyUsed: number;
    monthlyRemaining: number;
    perTransaction: number;
  };
  plan?: {
    name: string;
    transactionFee: number;
    transactionFeeInReais: string;
  };
}

export interface UserData {
  id: string;
  name: string;
  email: string;
  taxID: string;
  phone?: string;
  balance: number;
  blocked: boolean;
  status: string;
  limits: {
    daily: number;
    monthly: number;
    perTransaction: number;
  };
  dailyUsed: number;
  monthlyUsed: number;
  pixKey?: string;
  pixKeyType?: string;
  pixKeyValidated: boolean;
  plan: {
    name: string;
    transactionFee: number;
    transactionFeeInReais: string;
    monthlyFee: number;
    monthlyFeeInReais: string;
  };
  planDates: {
    startDate: string | null;
    endDate: string | null;
    renewalDate: string | null;
    daysRemaining: number | null;
    autoRenew: boolean;
  };
  paymentFee: number;
  splitFee: number;
  autoUpgrade: boolean;
  monthlyTransactions: number;
  transferSecurityEnabled: boolean;
  aiEnabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Payment {
  id: string;
  correlationID?: string;
  value: number;
  netValue?: number;
  fee?: number;
  status: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  metadata?: any;
}

export interface PaymentListResponse {
  success: boolean;
  data: {
    payments: Payment[];
    pagination: {
      total: number;
      limit: number;
      offset: number;
      hasMore: boolean;
    };
    statistics: {
      total: number;
      completed: number;
      pending: number;
      totalValue: number;
      totalNetValue: number;
    };
  };
}

export interface Withdraw {
  id: string;
  correlationID?: string;
  value: number;
  status: string;
  pixKey?: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  metadata?: {
    fee?: number;
    sent?: number;
    [key: string]: any;
  };
}

export interface WithdrawListResponse {
  success: boolean;
  data: {
    withdraws: Withdraw[];
    pagination: {
      total: number;
      limit: number;
      offset: number;
      hasMore: boolean;
    };
    statistics: {
      total: number;
      completed: number;
      pending: number;
      failed: number;
      totalValue: number;
    };
  };
}

export interface CreatePaymentData {
  value: number | string;
  description?: string;
  coverFee?: boolean;
}

export interface CreatePaymentResponse {
  success: boolean;
  message: string;
  data: {
    id: string;
    transactionId: string;
    value: number;
    valueInReais: number;
    netValue: number;
    fee: number;
    status: string;
    qrcodeUrl?: string;
    copyPaste?: string;
    createdAt: string;
  };
}

export interface CreateWithdrawData {
  amount: number | string;
  pixKey?: string;
  pixKeyType?: 'CPF' | 'CNPJ' | 'EMAIL' | 'PHONE' | 'RANDOM';
  description?: string;
  coverFee?: boolean; // Se true, o valor digitado é o valor enviado, e a taxa é adicionada ao total
  verificationCode?: string; // Código de verificação quando segurança está ativada
}

export interface CreateWithdrawResponse {
  success: boolean;
  message: string;
  data: {
    id: string;
    value: number;
    fee: number;
    sent: number;
    status: string;
    pixKey: string;
    createdAt: string;
  };
}

/**
 * Obter saldo e estatísticas do usuário
 */
export async function getBalance(): Promise<{ success: boolean; data: BalanceData }> {
  return apiGet('/v1/user/balance');
}

/**
 * Listar pagamentos do usuário
 */
export async function listPayments(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<PaymentListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());

  const query = queryParams.toString();
  return apiGet(`/v1/payment/list${query ? `?${query}` : ''}`);
}

/**
 * Listar saques do usuário
 */
export async function listWithdraws(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<WithdrawListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());

  const query = queryParams.toString();
  return apiGet(`/v1/withdraw/list${query ? `?${query}` : ''}`);
}

export interface Transaction {
  id: string;
  type: 'income' | 'expense';
  transactionType: 'payment' | 'withdraw' | 'internal_transfer_sent' | 'internal_transfer_received' | 'commission';
  date: string;
  amount: number;
  status: string;
  description: string;
  originalData?: any;
}

export interface TransactionListResponse {
  success: boolean;
  data: {
    transactions: Transaction[];
    pagination: {
      total: number;
      page: number;
      limit: number;
      totalPages: number;
      hasMore: boolean;
    };
  };
}

/**
 * Listar todas as transações (pagamentos e saques)
 */
export async function listTransactions(params?: {
  page?: number;
  limit?: number;
  startDate?: string;
  endDate?: string;
  type?: string;
  status?: string;
}): Promise<TransactionListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.startDate) queryParams.append('startDate', params.startDate);
  if (params?.endDate) queryParams.append('endDate', params.endDate);
  if (params?.type) queryParams.append('type', params.type);
  if (params?.status) queryParams.append('status', params.status);

  const query = queryParams.toString();
  return apiGet(`/v1/user/transactions${query ? `?${query}` : ''}`);
}

/**
 * Criar pagamento (depositar)
 */
export async function createPayment(data: CreatePaymentData): Promise<CreatePaymentResponse> {
  return apiPost('/v1/payment/create', data);
}

/**
 * Criar saque (transferir)
 */
export async function createWithdraw(data: CreateWithdrawData): Promise<CreateWithdrawResponse> {
  return apiPost('/v1/withdraw/create', data);
}

/**
 * Dados para transferência interna
 */
export interface InternalTransferData {
  email: string;
  amount: number | string;
  description?: string;
}

/**
 * Resposta da transferência interna
 */
export interface InternalTransferResponse {
  success: boolean;
  message: string;
  data: {
    id: string;
    amount: number;
    amountInReais: number;
    recipient: {
      email: string;
      name: string;
    };
    description: string;
    fee: number;
    createdAt: string;
  };
}

/**
 * Criar transferência interna (sem taxa, sem limite)
 */
export async function createInternalTransfer(data: InternalTransferData): Promise<InternalTransferResponse> {
  return apiPost('/v1/transfer/internal', data);
}

/**
 * Buscar detalhes de um pagamento específico
 */
export async function getPaymentById(id: string): Promise<{ success: boolean; data: Payment & { netValue?: number; qrCode?: string } }> {
  return apiGet(`/v1/payment/get/${id}`);
}

/**
 * Buscar detalhes de um saque específico
 */
export async function getWithdrawById(id: string): Promise<{ success: boolean; data: Withdraw & { correlationID?: string; pixKeyType?: string; transactionId?: string; completedAt?: string; failedAt?: string; failureReason?: string } }> {
  return apiGet(`/v1/withdraw/get/${id}`);
}

/**
 * Obter dados do usuário (incluindo aiEnabled)
 */
export async function getUserData(): Promise<{ success: boolean; data: UserData }> {
  return apiGet('/v1/user/get');
}

// ========== AFILIADOS ==========

export interface AffiliateData {
  id: string;
  code: string;
  link: string;
  totalReferrals: number;
  totalEarnings: number;
  totalEarningsInReais: string;
  // Taxa de comissão
  commissionRate: number;
  commissionRateInReais: string;
  stats: {
    clicks: number;
    referrals: number;
    earnings: number;
    conversion: string;
  };
  recentReferrals: {
    name: string;
    email: string;
    plan: string;
    date: string;
  }[];
  status: string;
  createdAt: string;
}

export interface AffiliateReferral {
  id: string;
  email: string;
  name: string;
  plan: string;
  createdAt: string;
  transactions: number;
  earnings: number;
}

export interface AffiliateStatsData {
  affiliate: {
    id: string;
    code: string;
    link: string;
    status: string;
    createdAt: string;
  };
  stats: {
    totalReferrals: number;
    totalEarnings: number;
    totalEarningsInReais: string;
    totalTransactionsFromReferrals: number;
    commissionPerTransaction: number;
    commissionPerTransactionInReais: string;
    referralsLast7Days: number;
    referralsLast30Days: number;
  };
  referrals: AffiliateReferral[];
  generatedAt: string;
}

/**
 * Registrar como afiliado
 */
export async function registerAsAffiliate(code?: string): Promise<{ success: boolean; message: string; data: AffiliateData }> {
  return apiPost('/v1/affiliate/register', code ? { code } : {});
}

/**
 * Obter dados do afiliado
 */
export async function getAffiliateData(): Promise<{ success: boolean; isAffiliate: boolean; data?: AffiliateData; error?: string }> {
  return apiGet('/v1/affiliate/me');
}

/**
 * Atualizar código do afiliado
 */
export async function updateAffiliateCode(code: string): Promise<{ success: boolean; message: string; data: { code: string; link: string } }> {
  return apiPut('/v1/affiliate/code', { code });
}

/**
 * Obter estatísticas detalhadas do afiliado
 */
export async function getAffiliateStats(): Promise<{ success: boolean; data: AffiliateStatsData }> {
  return apiGet('/v1/affiliate/stats');
}

export async function trackAffiliateClick(_code: string): Promise<void> {
  // Rastreamento silencioso — sem endpoint disponível na API atual
}

/**
 * Validar código de afiliado (pública)
 */
export async function validateAffiliateCode(code: string): Promise<{ valid: boolean; data?: { code: string; name: string }; error?: string }> {
  try {
    const response = await apiGet<{ valid: boolean; data?: { code: string; name: string } }>(`/v1/affiliate/validate/${code}`);
    return response;
  } catch {
    return { valid: false, error: 'Erro ao validar código' };
  }
}

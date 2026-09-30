export interface Gift {
  _id: string;
  code: string;
  planId: string;
  planName: string;
  months: number;
  isUsed: boolean;
  usedBy?: {
    _id: string;
    username: string;
    globalName: string;
    discordId: string;
  };
  usedAt?: string;
  expiresAt?: string;
  createdBy: {
    _id: string;
    username: string;
    globalName: string;
    discordId: string;
  };
  description: string;
  batchId?: string;
  applicationId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface GiftStats {
  total: number;
  used: number;
  available: number;
  expired: number;
}

export interface GiftPlanStats {
  _id: string;
  planName: string;
  total: number;
  used: number;
  available: number;
}

export interface GiftActivity {
  _id: string;
  count: number;
}

export interface GiftBatch {
  _id: string;
  planName: string;
  total: number;
  used: number;
  createdAt: string;
}

export interface GiftStatsResponse {
  general: GiftStats;
  byPlan: GiftPlanStats[];
  recentActivity: GiftActivity[];
  recentBatches: GiftBatch[];
}

export interface CreateGiftRequest {
  planId: string;
  months: number;
  quantity?: number;
  expiresAt?: string;
  description?: string;
}

export interface CreateGiftResponse {
  batchId: string;
  quantity: number;
  gifts: {
    id: string;
    code: string;
    planName: string;
    months: number;
    expiresAt?: string;
  }[];
}

export interface RedeemGiftRequest {
  code: string;
}

export interface RedeemGiftResponse {
  application: {
    id: string;
    name: string;
    planName: string;
    months: number;
    expiresAt: string;
  };
}

export interface ValidateGiftRequest {
  code: string;
}

export interface ValidateGiftResponse {
  valid: boolean;
  message: string;
  data?: {
    planName?: string;
    months?: number;
    description?: string;
    expiresAt?: string;
    isUsed?: boolean;
    usedAt?: string;
    expired?: boolean;
  };
}

export interface GiftListFilters {
  page?: number;
  limit?: number;
  planId?: string;
  isUsed?: boolean;
  batchId?: string;
  search?: string;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

export interface GiftListResponse {
  gifts: Gift[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
  stats: GiftStats;
}

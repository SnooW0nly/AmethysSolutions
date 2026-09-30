export type AppPlan = {
  id: string;
  name?: string;
  months?: number;
  preco?: number | null; // new
  paymentId?: string | null; // new
};

export type AppHosting = {
  utilizedRam: number | null;
  status: string | null;
  startedAt?: string | null;
};

export type App = {
  _id: string;
  name?: string;
  plan: AppPlan;
  hosting: AppHosting;
  bot?: { configured?: boolean };
  expiresAt?: string;
};

// Detailed sanitized info for single application views
// Simplified hosting info for single application view (aligned with API)
export type AppHostingInfo = AppHosting;

export type AppBotInfo = {
  id: string | null;
  owner: string | null;
  server: string | null;
  perms: string[];
  configured?: boolean;
};

export type AppInfo = {
  _id: string;
  name?: string;
  plan: AppPlan;
  hosting: AppHostingInfo; // { utilizedRam, status }
  bot: AppBotInfo;
  info: {
    name: string;
    imageUrl: string | null;
  };
  permissions?: {
    canAccessRestricted: boolean;
    canChangeServer: boolean;
    canManagePerms: boolean;
    canChangeToken: boolean;
  };
  expiresAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};
export type Coupon = {
  name: string;
  percent: number;
  archived?: boolean;
  maxUses?: number;
  usedCount?: number;
  availableDays?: number;
  minCart?: number;
  createdAt?: string;
  updatedAt?: string;
};

export type CouponForm = {
  name: string;
  percent: string;
  maxUses: string;
  availableDays: string;
  minCart: string;
  archived: boolean;
};



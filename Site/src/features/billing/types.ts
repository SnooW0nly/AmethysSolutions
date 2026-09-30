import type { UserMinimal } from "@/types/user";
export type AdminUser = UserMinimal;

export type AdminPayment = {
  _id: string;
  id?: string;
  userId: string;
  plan: { id: string; name: string; price: number; months?: number | null };
  coupon?: { code: string; discountPercent: number } | null;
  priceFinal: number;
  status: string;
  createdAt?: string;
  user?: Partial<AdminUser> | null;
};



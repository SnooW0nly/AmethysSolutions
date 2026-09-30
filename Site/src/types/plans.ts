export type Feature = { title: string };

export type PlanOption = {
  id: string;
  name: string;
  value: number;
  discount?: number;
  months: number;
  description?: string;
};

export type Plan = {
  id: string;
  name: string;
  description?: string;
  primary?: boolean;
  features: Feature[];
  plans: PlanOption[];
  zipFilename?: string;
  purchasedCount?: number;
};

export type PlanFormState = {
  id: string;
  name: string;
  description: string;
  primary: boolean;
  featuresText: string;
  monthlyPrice: string;
  monthlyDiscount: string;
  quarterlyPrice: string;
  quarterlyDiscount: string;
  annualPrice: string;
  annualDiscount: string;
  zipFile: File | null;
};



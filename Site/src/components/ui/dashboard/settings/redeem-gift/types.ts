export interface GiftPlanData {
  planName: string;
  months: number;
  days: number;
  expiresAt?: string | null;
}

export interface GiftValidationResponse {
  valid: boolean;
  message: string;
  data?: GiftPlanData | null;
}

export interface GiftMessage {
  type: "success" | "error";
  text: string;
}

export interface ExistingApp {
  _id: string;
  name: string;
  expiresAt?: string | null;
}

export interface RedeemSuccessData {
  months: number;
  days: number;
  planName: string;
}

export interface RedeemResponse {
  success: boolean;
  message?: string;
  data?: RedeemSuccessData;
}



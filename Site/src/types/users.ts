export type ApiUser = {
  _id: string;
  discordId: string;
  username: string;
  globalName: string;
  email?: string;
  avatar?: string;
  admin?: boolean;
  createdAt?: string;
  ipHistory?: { ip: string; dates: string[] }[];
  applications?: string[];
  invoices?: string[];
};



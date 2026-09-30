export interface Application {
  _id: string;
  userId: {
    _id?: string;
    username?: string;
    email?: string;
    discordId?: string;
    avatar?: string;
  };
  paymentId?: string;
  name: string;
  botID?: string;
  
  plan?: {
    id: string;
    name?: string;
    months?: number;
    price?: number;
    paymentId?: string;
  };

  hosting?: {
    provider?: string;
    appId?: string;
    name?: string;
    ram?: number;
    version?: string;
    main?: string;
    status?: string;
    url?: string;
    createdAt?: string;
    updatedAt?: string;
    lastDeployAt?: string;
  };

  bot?: {
    token?: string;
    owner?: string;
    id?: string;
    perms?: string[];
    server?: string;
  };

  info?: {
    name?: string;
    imageUrl?: string;
    id?: string;
  };

  botConfig?: {
    botID: string;
    botToken: string;
    apiURL: string;
    version: string;
    syncEmojis?: boolean;
    saveConfig?: boolean;
    startOnBackup?: boolean;
  };

  starckrStatus?: {
    container?: string;
    cpu?: string;
    memory?: string;
    ssd?: string;
    netIO?: string;
    last_restart?: string;
  };

  starckrInfo?: {
    id?: string;
    name?: string;
    avatar?: string;
    ram?: number;
    lang?: string;
    online?: boolean;
  };

  expiresAt?: string;
  lastChargeSent?: string;
  
  lastUpdate?: string;
  lastUpdateBy?: string;
  updateVersion?: string;
  
  isBlocked?: boolean;
  blockedAt?: string;
  isDeleted?: boolean;
  deletedAt?: string;
  canRecover?: boolean;

  createdAt: string;
  updatedAt: string;
}

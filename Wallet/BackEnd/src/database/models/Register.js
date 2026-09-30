import mongoose from "mongoose";

const RegisterSchema = new mongoose.Schema(
  {
    // Identificação
    id: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    apiKey: {
      type: String,
      required: true,
      unique: true,
    },

    // Dados pessoais
    name: {
      type: String,
      required: true,
      trim: true,
    },
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
      index: true,
    },
    taxID: {
      type: String,
      required: false,
      index: true,
    },
    phone: {
      type: String,
      trim: true,
    },

    // Chave PIX
    pixKey: {
      type: String,
      trim: true,
    },
    pixKeyType: {
      type: String,
      enum: ['CPF', 'CNPJ', 'EMAIL', 'PHONE', 'RANDOM'],
    },
    pixKeyValidated: {
      type: Boolean,
      default: false,
    },

    // Subconta GoatPay (criada automaticamente no registro)
    goatpaySubaccountId: {
      type: String,
      index: true,
    },

    // Saldos (todos em centavos)
    balance: {
      type: Number,
      default: 0,
    },
    saldo_split: {
      type: Number,
      default: 0,
    },

    // Categorização WHITE/BLACK
    category: {
      type: String,
      enum: ['WHITE', 'BLACK'],
      default: 'WHITE',
    },
    tier: {
      type: Number,
      default: 1,
      min: 1,
      max: 5,
    },
    businessProfileId: {
      type: String,
      index: true,
    },
    businessProfileCompleted: {
      type: Boolean,
      default: false,
      index: true,
    },

    // Controle de categoria por admin
    categoryLockedByAdmin: {
      type: Boolean,
      default: false,
    },

    // Status e limites
    blocked: {
      type: Boolean,
      default: false,
    },
    status: {
      type: String,
      enum: ['active', 'inactive', 'deleted'],
      default: 'active',
    },
    admin: {
      type: Boolean,
      default: false,
      index: true,
    },
    limits: {
      daily: {
        type: Number,
        default: 999999999, // R$ 9.999.999,99 (praticamente sem limite)
      },
      monthly: {
        type: Number,
        default: 999999999, // R$ 9.999.999,99 (praticamente sem limite)
      },
      perTransaction: {
        type: Number,
        default: 500000, // R$ 5.000,00
      },
    },
    dailyUsed: {
      type: Number,
      default: 0,
    },
    monthlyUsed: {
      type: Number,
      default: 0,
    },

    // Webhook
    webhookUrl: {
      type: String,
      trim: true,
    },

    // Segurança de transferências
    transferSecurityEnabled: {
      type: Boolean,
      default: false,
    },

    // Assistente de IA
    aiEnabled: {
      type: Boolean,
      default: true,
    },

    // Sistema de Afiliados
    referredBy: {
      type: String, // ID do afiliado que indicou
      index: true,
    },
    referredByCode: {
      type: String, // Código usado na indicação
    },
    referralDate: {
      type: String, // Data da indicação (ISO string)
    },
    isAffiliate: {
      type: Boolean,
      default: false,
    },

    // IPs autorizados para API Keys
    authorizedIPs: [{
      ip: {
        type: String,
        required: true,
        trim: true,
      },
      active: {
        type: Boolean,
        default: true,
      },
      createdAt: {
        type: String, // ISO string
      },
    }],

    // API Keys secundárias
    apiKeys: [
      {
        key: {
          type: String,
          required: true,
        },
        name: {
          type: String,
        },
        plan: {
          type: String,
          enum: ['WHITE', 'BLACK'],
          default: 'WHITE',
        },
        permissions: [{
          type: String,
        }],
        active: {
          type: Boolean,
          default: true,
        },
        webhookUrl: {
          type: String,
          trim: true,
        },
        createdAt: {
          type: String, // ISO string
        },
        lastUsedAt: {
          type: String, // ISO string
        },
        updatedAt: {
          type: String, // ISO string
        },
      },
    ],

    // Timestamps
    deletedAt: {
      type: String, // ISO string
    },
  },
  {
    timestamps: true,
    collection: 'registers'
  }
);

// Índices compostos
RegisterSchema.index({ email: 1, taxID: 1 });
// apiKey já tem índice único criado automaticamente pelo unique: true
RegisterSchema.index({ 'apiKeys.key': 1 });

// Métodos estáticos
RegisterSchema.statics.getById = async function (id) {
  return await this.findOne({ id, status: { $ne: 'deleted' } });
};

RegisterSchema.statics.getByApiKey = async function (apiKey) {
  // Buscar pela API Key principal
  let user = await this.findOne({ apiKey, status: 'active' });

  if (user) {
    user.usedApiKey = {
      type: 'main',
      permissions: ['admin:all']
    };
    return user;
  }

  // Buscar por API Keys secundárias
  user = await this.findOne({
    'apiKeys.key': apiKey,
    status: 'active'
  });

  if (user && user.apiKeys) {
    const keyIndex = user.apiKeys.findIndex(k => k.key === apiKey);

    if (keyIndex !== -1) {
      const secondaryKey = user.apiKeys[keyIndex];

      if (secondaryKey.active === false) {
        return null;
      }

      // Atualizar lastUsedAt
      secondaryKey.lastUsedAt = new Date().toISOString();
      await this.updateOne(
        { id: user.id, 'apiKeys.key': apiKey },
        { $set: { 'apiKeys.$.lastUsedAt': new Date().toISOString() } }
      );

      user.usedApiKey = {
        type: 'secondary',
        index: keyIndex,
        permissions: secondaryKey.permissions || [],
        plan: secondaryKey.plan || 'WHITE'
      };

      return user;
    }
  }

  return null;
};

RegisterSchema.statics.getByEmailOrTaxID = async function (email, taxID) {
  return await this.findOne({
    $or: [{ email }, { taxID }],
    status: { $ne: 'deleted' }
  });
};

RegisterSchema.statics.updateBalance = async function (userId, amount, type = 'add', allowNegative = false) {
  const user = await this.findOne({ id: userId });
  if (!user) {
    throw new Error(`Usuário não encontrado com ID: ${userId}`);
  }

  const currentBalance = user.balance || 0;

  if (type === 'add') {
    // Usar findOneAndUpdate para garantir atomicidade
    const updated = await this.findOneAndUpdate(
      { id: userId },
      { $inc: { balance: amount } },
      { new: true }
    );
    return updated;
  } else if (type === 'subtract') {
    if (!allowNegative && currentBalance < amount) {
      throw new Error('Saldo insuficiente');
    }
    // Usar findOneAndUpdate para garantir atomicidade
    const updated = await this.findOneAndUpdate(
      { id: userId },
      { $inc: { balance: -amount } },
      { new: true }
    );
    return updated;
  }

  return user;
};

RegisterSchema.statics.getUsersWithExpiringPlans = async function () {
  const now = new Date().toISOString();
  return await this.find({
    status: 'active',
    blocked: { $ne: true },
    planRenewalDate: { $lte: now },
    planEndDate: { $gt: now },
    plan: { $ne: 'FREE' }
  });
};

RegisterSchema.statics.getUsersWithExpiredPlans = async function () {
  const now = new Date().toISOString();
  return await this.find({
    status: 'active',
    planEndDate: { $lte: now },
    plan: { $ne: 'FREE' }
  });
};

RegisterSchema.statics.getUsersBeforeRenewal = async function () {
  const now = new Date();
  const nowISO = now.toISOString();

  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(23, 59, 59, 999);
  const tomorrowISO = tomorrow.toISOString();

  return await this.find({
    status: 'active',
    blocked: { $ne: true },
    planRenewalDate: {
      $gte: nowISO,
      $lte: tomorrowISO,
      $exists: true,
      $ne: null
    },
    planEndDate: { $gt: nowISO }
  });
};

export default mongoose.models.Register || mongoose.model("Register", RegisterSchema);
import mongoose from "mongoose";

// Tipos de ações de auditoria
export const AUDIT_ACTIONS = {
  // Usuários
  USER_CREATED: 'USER_CREATED',
  USER_UPDATED: 'USER_UPDATED',
  USER_DELETED: 'USER_DELETED',
  USER_BLOCKED: 'USER_BLOCKED',
  USER_UNBLOCKED: 'USER_UNBLOCKED',
  USER_LIMITS_UPDATED: 'USER_LIMITS_UPDATED',

  // Planos
  PLAN_CHANGED: 'PLAN_CHANGED',
  PLAN_UPGRADED: 'PLAN_UPGRADED',
  PLAN_DOWNGRADED: 'PLAN_DOWNGRADED',
  PLAN_RENEWED: 'PLAN_RENEWED',
  PLAN_EXPIRED: 'PLAN_EXPIRED',
  PLAN_AUTO_UPGRADE_TOGGLED: 'PLAN_AUTO_UPGRADE_TOGGLED',

  // Pagamentos
  PAYMENT_CREATED: 'PAYMENT_CREATED',
  PAYMENT_UPDATED: 'PAYMENT_UPDATED',
  PAYMENT_COMPLETED: 'PAYMENT_COMPLETED',
  PAYMENT_SENT: 'PAYMENT_SENT',
  SPLIT_PROCESSED: 'SPLIT_PROCESSED',

  // Saques
  WITHDRAW_CREATED: 'WITHDRAW_CREATED',
  WITHDRAW_UPDATED: 'WITHDRAW_UPDATED',
  WITHDRAW_COMPLETED: 'WITHDRAW_COMPLETED',
  WITHDRAW_FAILED: 'WITHDRAW_FAILED',

  // Saldo
  BALANCE_CREDITED: 'BALANCE_CREDITED',
  BALANCE_DEBITED: 'BALANCE_DEBITED',
  BALANCE_BLOCKED: 'BALANCE_BLOCKED',
  BALANCE_UNBLOCKED: 'BALANCE_BLOCKED',

  // Configurações
  CONFIG_UPDATED: 'CONFIG_UPDATED',

  // Sistema
  PLAN_ANALYSIS_EXECUTED: 'PLAN_ANALYSIS_EXECUTED',
  PLAN_RENEWAL_EXECUTED: 'PLAN_RENEWAL_EXECUTED'
};

// Entidades do sistema
export const AUDIT_ENTITIES = {
  USER: 'USER',
  PAYMENT: 'PAYMENT',
  WITHDRAW: 'WITHDRAW',
  PLAN: 'PLAN',
  BALANCE: 'BALANCE',
  CONFIG: 'CONFIG',
  SYSTEM: 'SYSTEM'
};

const AuditSchema = new mongoose.Schema(
  {
    id: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    action: {
      type: String,
      required: true,
      enum: Object.values(AUDIT_ACTIONS),
      index: true,
    },
    entity: {
      type: String,
      required: true,
      enum: Object.values(AUDIT_ENTITIES),
      index: true,
    },
    entityId: {
      type: String,
      required: true,
      index: true,
    },
    userId: {
      type: String,
      index: true,
    },
    userEmail: {
      type: String,
    },
    dataBefore: {
      type: mongoose.Schema.Types.Mixed,
    },
    dataAfter: {
      type: mongoose.Schema.Types.Mixed,
    },
    metadata: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },
    ipAddress: {
      type: String,
    },
    userAgent: {
      type: String,
    },
    description: {
      type: String,
    },
  },
  {
    timestamps: true,
    collection: 'audit'
  }
);

// Índices compostos
AuditSchema.index({ entity: 1, entityId: 1 });
AuditSchema.index({ userId: 1, createdAt: -1 });
AuditSchema.index({ action: 1, createdAt: -1 });

// Métodos estáticos
AuditSchema.statics.saveLog = async function (auditData) {
  try {
    const {
      action,
      entity,
      entityId,
      userId,
      userEmail,
      dataBefore = null,
      dataAfter = null,
      metadata = {},
      ipAddress = null,
      userAgent = null,
      description = null
    } = auditData;

    if (!action || !entity || !entityId) {
      console.error('❌ Dados incompletos para auditoria:', { action, entity, entityId });
      return null;
    }

    // Gerar ID se não fornecido
    let auditId = auditData.id;
    if (!auditId) {
      // Usar crypto diretamente para evitar dependência circular
      const crypto = await import('crypto');
      auditId = crypto.randomBytes(16).toString('hex');
    }

    const auditLog = {
      id: auditId,
      action,
      entity,
      entityId,
      userId: userId || null,
      userEmail: userEmail || null,
      dataBefore: dataBefore ? JSON.parse(JSON.stringify(dataBefore)) : null,
      dataAfter: dataAfter ? JSON.parse(JSON.stringify(dataAfter)) : null,
      metadata: metadata || {},
      ipAddress,
      userAgent,
      description: description || `${action} em ${entity} ${entityId}`,
    };

    return await this.create(auditLog);
  } catch (error) {
    console.error('❌ Erro ao salvar log de auditoria:', error.message);
    return null;
  }
};

AuditSchema.statics.getLogs = async function (filters = {}, options = {}) {
  try {
    const {
      action,
      entity,
      entityId,
      userId,
      startDate,
      endDate
    } = filters;

    const {
      limit = 100,
      offset = 0
    } = options;

    const query = {};

    if (action) query.action = action;
    if (entity) query.entity = entity;
    if (entityId) query.entityId = entityId;
    if (userId) query.userId = userId;

    if (startDate || endDate) {
      query.createdAt = {};
      if (startDate) query.createdAt.$gte = new Date(startDate);
      if (endDate) query.createdAt.$lte = new Date(endDate);
    }

    const logs = await this.find(query)
      .sort({ createdAt: -1 })
      .skip(parseInt(offset))
      .limit(parseInt(limit));

    const total = await this.countDocuments(query);

    return {
      logs,
      total,
      limit: parseInt(limit),
      offset: parseInt(offset),
      hasMore: (parseInt(offset) + parseInt(limit)) < total
    };
  } catch (error) {
    console.error('❌ Erro ao buscar logs de auditoria:', error.message);
    return { logs: [], total: 0, limit: 0, offset: 0, hasMore: false };
  }
};

AuditSchema.statics.getLogsByEntity = async function (entity, entityId, limit = 50) {
  return await this.getLogs({ entity, entityId }, { limit });
};

AuditSchema.statics.getLogsByUser = async function (userId, limit = 50) {
  return await this.getLogs({ userId }, { limit });
};

export default mongoose.models.Audit || mongoose.model("Audit", AuditSchema);


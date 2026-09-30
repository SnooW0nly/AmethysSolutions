import mongoose from "mongoose";

const WithdrawSchema = new mongoose.Schema(
  {
    id: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    userId: {
      type: String,
      required: true,
      index: true,
    },
    correlationID: {
      type: String,
    },
    value: {
      type: Number,
      required: true,
    },
    description: {
      type: String,
    },
    status: {
      type: String,
      enum: ['PENDING', 'WAITING', 'CREATED', 'PROCESSING', 'QUEUED', 'COMPLETED', 'FAILED', 'CANCELLED', 'DELETED'],
      default: 'PENDING',
      index: true,
    },
    pixKey: {
      type: String,
      required: true,
    },
    pixKeyType: {
      type: String,
      enum: ['CPF', 'CNPJ', 'EMAIL', 'PHONE', 'RANDOM', 'CRYPTO_BEP20', 'COPYPASTE'],
      required: true,
    },
    transactionId: {
      type: String,
    },
    completedAt: {
      type: String, // ISO string
    },
    failedAt: {
      type: String, // ISO string
    },
    failureReason: {
      type: String,
    },
    metadata: {
      type: mongoose.Schema.Types.Mixed,
    },
    deletedAt: {
      type: String, // ISO string
    },
  },
  {
    timestamps: true,
    collection: 'withdraws'
  }
);

// Índices compostos
WithdrawSchema.index({ userId: 1, status: 1 });
WithdrawSchema.index({ userId: 1, createdAt: -1 });
WithdrawSchema.index({ correlationID: 1 });

// Métodos estáticos
WithdrawSchema.statics.getById = async function (id) {
  return await this.findOne({ id, status: { $ne: 'DELETED' } });
};

WithdrawSchema.statics.getByCorrelationID = async function (correlationID) {
  return await this.findOne({ correlationID });
};

WithdrawSchema.statics.getByUserId = async function (userId) {
  return await this.find({ userId, status: { $ne: 'DELETED' } }).sort({ createdAt: -1 });
};

WithdrawSchema.statics.getPending = async function (statuses = ['PENDING', 'WAITING', 'CREATED', 'PROCESSING']) {
  return await this.find({ status: { $in: statuses } });
};

export default mongoose.models.Withdraw || mongoose.model("Withdraw", WithdrawSchema);


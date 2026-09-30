import mongoose from "mongoose";

const PaymentSchema = new mongoose.Schema(
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
    netValue: {
      type: Number,
    },
    fee: {
      type: Number,
    },
    description: {
      type: String,
    },
    status: {
      type: String,
      enum: ['ACTIVE', 'PENDING', 'COMPLETED', 'PAID', 'CANCELLED', 'EXPIRED', 'FAILED'],
      default: 'PENDING',
      index: true,
    },
    misticTransactionId: {
      type: String,
    },
    pixKey: {
      type: String,
    },
    pixKeyType: {
      type: String,
      enum: ['CPF', 'CNPJ', 'EMAIL', 'PHONE', 'RANDOM'],
    },
    qrCode: {
      type: String,
    },
    qrCodeImage: {
      type: String,
    },
    transactionId: {
      type: String,
    },
    paidAt: {
      type: String, // ISO string
    },
    expiresAt: {
      type: String, // ISO string
    },
    metadata: {
      type: mongoose.Schema.Types.Mixed,
    },
  },
  {
    timestamps: true,
    collection: 'payments'
  }
);

// Índices compostos
PaymentSchema.index({ userId: 1, status: 1 });
PaymentSchema.index({ userId: 1, createdAt: -1 });
PaymentSchema.index({ correlationID: 1 });
PaymentSchema.index({ status: 1, createdAt: -1 }); // Índice otimizado para getPending

// Métodos estáticos
PaymentSchema.statics.getById = async function (id) {
  return await this.findOne({
    $or: [{ id }, { correlationID: id }]
  });
};

PaymentSchema.statics.getByUser = async function (userId) {
  return await this.find({ userId }).sort({ createdAt: -1 });
};

// Otimizado: ordena por createdAt para priorizar pagamentos mais recentes
PaymentSchema.statics.getPending = async function (statuses = ['ACTIVE', 'PENDING']) {
  return await this.find({ status: { $in: statuses } })
    .sort({ createdAt: -1 })
    .lean(); // lean() para performance (retorna objetos JS puros)
};

PaymentSchema.statics.countCompletedByUser = async function (userId, startDate, endDate) {
  return await this.countDocuments({
    userId,
    status: { $in: ['COMPLETED', 'PAID'] },
    createdAt: {
      $gte: startDate,
      $lte: endDate
    }
  });
};

PaymentSchema.statics.countMonthlyTransactions = async function (userId, year, month) {
  const startDate = new Date(year, month - 1, 1, 0, 0, 0, 0).toISOString();
  const lastDay = new Date(year, month, 0).getDate();
  const endDate = new Date(year, month - 1, lastDay, 23, 59, 59, 999).toISOString();
  return await this.countCompletedByUser(userId, startDate, endDate);
};

export default mongoose.models.Payment || mongoose.model("Payment", PaymentSchema);


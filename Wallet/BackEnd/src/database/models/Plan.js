import mongoose from 'mongoose';

const PlanSchema = new mongoose.Schema(
  {
    id: {
      type: String,
      required: true,
      unique: true,
      index: true,
      uppercase: true, // Sempre em maiúsculas
    },
    name: {
      type: String,
      required: true,
    },
    description: {
      type: String,
      default: '',
    },
    transactionFee: {
      type: Number,
      required: true,
      default: 70, // em centavos
    },
    monthlyFee: {
      type: Number,
      required: true,
      default: 0, // em centavos
    },
    minTransactions: {
      type: Number,
      required: true,
      default: 0,
    },
    maxTransactions: {
      type: Number,
      default: null, // null = sem limite (Infinity)
    },
    downgradeTo: {
      type: String,
      default: null, // null = não tem downgrade (plano base)
    },
    order: {
      type: Number,
      required: true,
      default: 0, // Ordem de exibição (0 = primeiro)
    },
    // Campos para taxa dinâmica (plano BLACK)
    transactionFeePercent: {
      type: Number,
      default: null, // Porcentagem da taxa (ex: 5 = 5%)
    },
    transactionFeeFixed: {
      type: Number,
      default: null, // Valor fixo adicional em centavos (ex: 200 = R$ 2,00)
    },
    splitFee: {
      type: Number,
      default: null, // Split fixo para Amethys em centavos (ex: 100 = R$ 1,00)
    },
    useSeparateMistic: {
      type: Boolean,
      default: false, // Se true, usa conta Mistic separada (BLACK)
    },
    active: {
      type: Boolean,
      default: true,
    },
  },
  {
    timestamps: true,
    collection: 'plans'
  }
);

// Índices
PlanSchema.index({ order: 1 });
PlanSchema.index({ active: 1 });

// Métodos estáticos
PlanSchema.statics.getById = async function (planId) {
  return await this.findOne({ id: planId.toUpperCase(), active: true });
};

PlanSchema.statics.getAll = async function () {
  return await this.find({ active: true }).sort({ order: 1 });
};

PlanSchema.statics.getPlanOrder = async function () {
  const plans = await this.find({ active: true }).sort({ order: 1 });
  return plans.map(p => p.id);
};

export default mongoose.models.Plan || mongoose.model('Plan', PlanSchema);


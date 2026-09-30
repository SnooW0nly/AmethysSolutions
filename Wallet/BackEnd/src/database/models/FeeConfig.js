import mongoose from 'mongoose';

/**
 * FeeConfig — Configuração de taxas do sistema.
 *
 * Existe apenas UM documento nessa collection (singleton).
 * Busque sempre por: FeeConfig.getSingleton()
 *
 * Fallbacks padrão (caso não exista nenhum doc no banco):
 *   transactionFee = 55  centavos  (R$ 0,55 por transação / envio)
 *   withdrawFee    = 30  centavos  (R$ 0,30 por saque PIX)
 */
const FeeConfigSchema = new mongoose.Schema(
  {
    // ID fixo do singleton
    _singleton: {
      type: String,
      default: 'GLOBAL',
      unique: true,
      index: true,
    },

    // Taxa cobrada em cada transação/envio (centavos)
    transactionFee: {
      type: Number,
      required: true,
      default: 55,
      min: 0,
    },

    // Taxa cobrada em cada saque PIX (centavos)
    withdrawFee: {
      type: Number,
      required: true,
      default: 30,
      min: 0,
    },

    // Descrição/nota interna (opcional)
    notes: {
      type: String,
      default: '',
    },

    // Quem atualizou por último
    updatedBy: {
      type: String,
      default: 'SYSTEM',
    },
  },
  {
    timestamps: true,
    collection: 'fee_config',
  }
);

// ─── Métodos estáticos ────────────────────────────────────────────────────────

/**
 * Retorna o documento singleton de taxas.
 * Se não existir no banco, retorna os defaults sem persistir.
 * Use upsert apenas via rota admin.
 */
FeeConfigSchema.statics.getSingleton = async function () {
  const doc = await this.findOne({ _singleton: 'GLOBAL' });
  if (doc) return doc;

  // Retorna objeto com defaults sem salvar no banco
  return {
    _singleton: 'GLOBAL',
    transactionFee: 55,
    withdrawFee: 30,
    notes: '',
    updatedBy: 'SYSTEM',
    createdAt: null,
    updatedAt: null,
    _fromDefault: true, // flag interna para saber que veio do fallback
  };
};

/**
 * Atualiza (ou cria) o singleton de taxas.
 * @param {object} data - { transactionFee?, withdrawFee?, notes?, updatedBy? }
 * @returns {Document} O documento atualizado
 */
FeeConfigSchema.statics.upsert = async function (data) {
  return await this.findOneAndUpdate(
    { _singleton: 'GLOBAL' },
    { $set: { ...data, _singleton: 'GLOBAL' } },
    { upsert: true, new: true, runValidators: true }
  );
};

export default mongoose.models.FeeConfig || mongoose.model('FeeConfig', FeeConfigSchema);

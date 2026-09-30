import mongoose from "mongoose";

const affiliateSchema = new mongoose.Schema(
  {
    // Usuário dono do link de afiliado
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      unique: true,
    },

    // Código único do link (ex: "abc123")
    code: {
      type: String,
      required: true,
      unique: true,
      uppercase: true,
      trim: true,
    },

    // Quantas vezes o link foi clicado/acessado
    clicks: {
      type: Number,
      default: 0,
    },

    // Quantas compras foram realizadas com esse link
    conversions: {
      type: Number,
      default: 0,
    },

    // Dias de recompensa acumulados (cada conversão = +1 dia)
    rewardDays: {
      type: Number,
      default: 0,
    },

    // Recompensas já resgatadas (dias que viraram bots)
    claimedDays: {
      type: Number,
      default: 0,
    },

    // Bots gerados como recompensa
    rewardApps: [
      {
        applicationId: { type: mongoose.Schema.Types.ObjectId, ref: "Application" },
        days: { type: Number },
        createdAt: { type: Date, default: Date.now },
      },
    ],

    // Histórico de conversões
    conversionHistory: [
      {
        paymentId: { type: mongoose.Schema.Types.ObjectId, ref: "Payment" },
        buyerUserId: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
        createdAt: { type: Date, default: Date.now },
        rewarded: { type: Boolean, default: false },
        rewardDays: { type: Number, default: 1 },
      },
    ],

    // Status do afiliado
    isActive: {
      type: Boolean,
      default: true,
    },
  },
  {
    timestamps: true,
  }
);

// Index para busca rápida por código
affiliateSchema.index({ code: 1 });
affiliateSchema.index({ userId: 1 });

const Affiliate = mongoose.model("Affiliate", affiliateSchema);
export default Affiliate;
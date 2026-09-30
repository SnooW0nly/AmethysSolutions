import mongoose from "mongoose";

/**
 * MemberOrder — pedido de membros via RevisionSMM
 *
 * Fluxo completo:
 *  1. Usuário informa link do servidor + quantidade
 *  2. Bot é verificado no servidor
 *  3. Gerado pagamento Mistic (preço + R$1,50 taxa + R$0,50 Mistic)
 *  4. Usuário paga
 *  5. Backend adiciona saldo na Revision e faz o pedido
 *  6. Status é atualizado conforme progresso
 */
const MemberOrderSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },

    // ── Dados do pedido ───────────────────────────────────────────────────────
    serviceId: { type: String, required: true },
    serviceName: { type: String, default: "" },
    quantity: { type: Number, required: true, min: 1 },
    serverLink: { type: String, required: true },
    guildId: { type: String, default: null },

    // ── Verificação do bot no servidor ────────────────────────────────────────
    botVerified: { type: Boolean, default: false },
    botVerifiedAt: { type: Date, default: null },

    // ── Precificação ──────────────────────────────────────────────────────────
    // Ex: 1000 membros = R$13,00 (serviço) → R$15,00 cobrado
    //     (R$13,00 + R$1,50 nossa taxa + R$0,50 Mistic)
    servicePrice: { type: Number, required: true },  // Custo real na Revision (R$)
    ourFee: { type: Number, default: 1.50 },         // Nossa taxa fixa
    misticFee: { type: Number, default: 0.50 },      // Taxa da Mistic
    totalCharged: { type: Number, required: true },  // Total cobrado do cliente

    // ── Pagamento Mistic ──────────────────────────────────────────────────────
    payment: {
      misticId: { type: String, default: null, index: true },
      status: {
        type: String,
        enum: ["pending", "approved", "cancelled", "expired"],
        default: "pending",
      },
      paidAt: { type: Date, default: null },
      emv: { type: String, default: null },
      qrCodeBase64: { type: String, default: null },
      expiresAt: { type: Date, default: null },
    },

    // ── Execução RevisionSMM ──────────────────────────────────────────────────
    revision: {
      addFundsStatus: {
        type: String,
        enum: ["pending", "success", "failed"],
        default: "pending",
      },
      addFundsAt: { type: Date, default: null },
      orderId: { type: String, default: null },
      orderStatus: { type: String, default: null },
      orderPlacedAt: { type: Date, default: null },
      lastCheckedAt: { type: Date, default: null },
    },

    // ── Status geral do pedido ────────────────────────────────────────────────
    status: {
      type: String,
      enum: [
        "awaiting_payment",   // aguardando pagamento
        "payment_confirmed",  // pago, processando
        "adding_funds",       // adicionando saldo na Revision
        "ordering",           // fazendo o pedido na Revision
        "in_progress",        // pedido aceito, membros sendo enviados
        "completed",          // concluído com sucesso
        "failed",             // falhou em alguma etapa
        "cancelled",          // cancelado / expirado
      ],
      default: "awaiting_payment",
      index: true,
    },

    failReason: { type: String, default: null },
    notes: { type: String, default: null }, // notas internas do admin
  },
  { timestamps: true }
);

MemberOrderSchema.index({ status: 1, createdAt: -1 });
MemberOrderSchema.index({ userId: 1, createdAt: -1 });

export default mongoose.models.MemberOrder ||
  mongoose.model("MemberOrder", MemberOrderSchema);
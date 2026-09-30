import mongoose from "mongoose";

const paymentSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  plan: {
    id: String,
    name: String,
    price: Number,
    monthId: String,
    months: Number,
  },
  coupon: {
    id: { type: mongoose.Schema.Types.ObjectId, ref: "Coupon" },
    code: String,
    discountPercent: Number,
  },
  priceFinal: { type: Number, required: true },
  // IDs dos provedores de pagamento (um será usado dependendo da configuração)
  efiId: { type: String },
  wooviId: { type: String },
  misticId: { type: String },
  // Provider usado: 'efi', 'woovi' ou 'mistic'
  // null é válido para carrinhos (status: 'cart') que ainda não geraram PIX
  provider: { type: String, enum: ["efi", "woovi", "mistic", null], default: null },
  // 'cart'      → carrinho aberto no Discord, aguardando "Continuar"
  // 'pending'   → PIX gerado, aguardando pagamento
  // 'approved'  → pago e processado
  // 'cancelled' → expirou ou cancelado
  status: { type: String, enum: ["cart", "pending", "approved", "cancelled"], default: "pending" },
  qrCodeBase64: String,
  qrCodeText: String,
  // Obrigatório apenas a partir de status "pending" (quando o PIX é gerado)
  // Carrinhos (status "cart") não têm expiresAt até confirmar o pagamento
  expiresAt: { type: Date, required: false },
  // ID do tópico Discord vinculado ao carrinho (apenas para compras pelo bot)
  threadId: { type: String },
  createdAt: { type: Date, default: Date.now },
  // Raw responses dos provedores
  efiRaw: { type: mongoose.Schema.Types.Mixed },
  wooviRaw: { type: mongoose.Schema.Types.Mixed },
  misticRaw: { type: mongoose.Schema.Types.Mixed },
  metadata: {
    isRenewal: { type: Boolean, default: false },
    applicationId: { type: mongoose.Schema.Types.ObjectId, ref: "Application" },
    months: Number,
    // Código de afiliado usado na compra (se houver)
    affiliateCode: { type: String, default: null },
  },
});

export default mongoose.models.Payment || mongoose.model("Payment", paymentSchema);

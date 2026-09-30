import express from "express";
import Payment from "../../database/models/Payment.js";
import Plan from "../../database/models/Plan.js";
import { createPixPayment, getDefaultProvider } from "../../services/payment/index.js";
import { validateCoupon } from "../../services/couponService.js";
import AuditLog from "../../database/models/AuditLog.js";
import chargeFloodProtection, { registerChargeCreation } from "../../middlewares/chargeFloodProtection.js";

const router = express.Router();

/**
 * Cria um pagamento PIX para um plano
 * Body: { planId, monthId, couponCode?, affiliateCode?, addons? }
 * userId vem do auth (req.user)
 */
router.post("/create", chargeFloodProtection, async (req, res, next) => {
  try {
    // ✅ CORREÇÃO: adicionar `addons` na desestruturação
    const { planId, monthId, couponCode, affiliateCode, addons } = req.body;
    const userId = req.user._id;

    // 1. Busca plano
    const plan = await Plan.findOne({ id: planId });
    if (!plan) return res.status(404).json({ error: "Plano não encontrado" });

    // Determina o preço base (sem desconto)
    const selectedOption = Array.isArray(plan.plans) && plan.plans.length > 0 ? plan.plans.find(p => p.id === monthId) : null;
    const basePrice = selectedOption?.value ?? plan.price;
    if (typeof basePrice !== "number" || Number.isNaN(basePrice)) {
      return res.status(400).json({ error: "Preço do plano inválido" });
    }

    let coupon = null;
    let price = basePrice;

    // 2. Verifica cupom (com base no preço atual selecionado)
    if (couponCode) {
      const result = await validateCoupon(couponCode, price);
      if (!result.valid) {
        return res.status(400).json({ error: result.error });
      }
      coupon = result.coupon;
      const discountPercent = coupon?.discountPercent ?? coupon?.percent ?? 0;
      price = price - (price * discountPercent) / 100;
      // Log coupon validation
      try {
        await AuditLog.create({ entity: "coupon", action: "validate", actorId: userId, targetId: coupon?.name || coupon?.code || String(couponCode), metadata: { planId, monthId } });
      } catch { }
    }

    // 3. Limpa pagamentos expirados há mais de 1 hora (manutenção do banco)
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    try {
      await Payment.deleteMany({
        userId,
        status: { $ne: "approved" },
        expiresAt: { $lt: oneHourAgo },
      });
    } catch (cleanupError) {
      console.warn("[PAYMENT CREATE] Erro ao limpar pagamentos expirados:", cleanupError);
    }

    // Normaliza valor para 2 casas decimais
    price = Number(Number(price).toFixed(2));

    // 4. Cria PIX usando o provedor configurado (Woovi ou Efi)
    const { provider, paymentId, emv, qrBase64, raw } = await createPixPayment({
      price,
      description: `Plano ${plan.name}`,
    });

    // 5. Cria pagamento no Mongo
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000);
    const paymentData = {
      userId,
      plan: {
        id: plan.id,
        name: plan.name,
        price: basePrice,
        monthId: selectedOption?.id,
        months: selectedOption?.months,
      },
      coupon: coupon
        ? {
          code: coupon.code ?? coupon.name,
          discountPercent: coupon.discountPercent ?? coupon.percent ?? 0,
        }
        : null,
      priceFinal: price,
      provider,
      status: "pending",
      qrCodeBase64: qrBase64,
      qrCodeText: emv,
      expiresAt,
      // Salva o código de afiliado nos metadados (se houver)
      metadata: {
        isRenewal: false,
        affiliateCode: affiliateCode ? String(affiliateCode).toUpperCase() : null,
        addons: Array.isArray(addons) ? addons : [], // ✅ `addons` agora está definido
      },
    };

    // Adiciona campos específicos do provedor
    if (provider === "mistic") {
      paymentData.misticId = paymentId;
      paymentData.misticRaw = raw;
    } else if (provider === "woovi") {
      paymentData.wooviId = paymentId;
      paymentData.wooviRaw = raw;
    } else {
      paymentData.efiId = paymentId;
      paymentData.efiRaw = raw;
    }

    const newPayment = await Payment.create(paymentData);

    // Registra criação bem-sucedida para cooldown
    registerChargeCreation(req, res, () => { });

    res.status(201).json({
      id: newPayment._id,
      copy_paste: newPayment.qrCodeText,
      qr_code_base64: newPayment.qrCodeBase64,
      status: newPayment.status,
      expiresAt: newPayment.expiresAt,
    });
  } catch (e) {
    console.log(e);
    next(e);
  }
});

export default router;
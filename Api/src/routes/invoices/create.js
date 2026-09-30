import Payment from "../../database/models/Payment.js";
import Application from "../../database/models/Application.js";
import Plan from "../../database/models/Plan.js";
import Coupon from "../../database/models/Coupon.js";
import { createPixPayment } from "../../services/payment/index.js";
import chargeFloodProtection, { registerChargeCreation } from "../../middlewares/chargeFloodProtection.js";


export default async function createRenewalInvoice(req, res) {
  try {
    const { applicationId, months, couponCode } = req.body;
    const userId = req.user._id;

    if (!applicationId) {
      return res.status(400).json({
        success: false,
        message: "ID da aplicação é obrigatório",
      });
    }

    if (!months || months < 1 || months > 12) {
      return res.status(400).json({
        success: false,
        message: "Meses deve ser entre 1 e 12",
      });
    }

    // Busca a aplicação
    const application = await Application.findOne({
      _id: applicationId,
      userId,
    });

    if (!application) {
      return res.status(404).json({
        success: false,
        message: "Aplicação não encontrada",
      });
    }

    // Busca o plano
    const plan = await Plan.findOne({ id: application.plan.id });
    if (!plan) {
      return res.status(404).json({
        success: false,
        message: "Plano não encontrado",
      });
    }

    // Busca a opção de plano com os meses especificados
    const planOption = plan.plans.find((p) => p.months === months);
    if (!planOption) {
      return res.status(404).json({
        success: false,
        message: "Opção de plano não encontrada",
      });
    }

    // Busca e valida cupom se fornecido
    let coupon = null;
    let discountPercent = 0;
    if (couponCode) {
      coupon = await Coupon.findOne({ name: couponCode.toUpperCase() });
      if (coupon && !coupon.archived) {
        // Validações alinhadas ao schema real
        const now = new Date();
        let valid = true;

        if (coupon.availableDays && coupon.createdAt) {
          const expiresAt = new Date(new Date(coupon.createdAt).getTime() + coupon.availableDays * 24 * 60 * 60 * 1000);
          if (expiresAt < now) valid = false;
        }
        if (coupon.maxUses && (coupon.usedCount ?? 0) >= coupon.maxUses) valid = false;
        if (coupon.minCart && Number(planOption.value) < Number(coupon.minCart)) valid = false;

        if (valid) {
          discountPercent = Number(coupon.percent || 0);
        } else {
          coupon = null;
        }
      } else {
        coupon = null;
      }
    }

    // Calcula o valor com desconto do cupom
    let amount = Number(planOption.value);
    if (coupon && discountPercent > 0) {
      amount = Number((amount * (1 - discountPercent / 100)).toFixed(2));
    }

    // Gera cobrança PIX via Mistic (usando serviço unificado)
    let pixData;
    try {
      pixData = await createPixPayment({
        price: amount,
        description: `Renovação ${plan.name} - ${months} mês(es)`,
      });
    } catch (error) {
      console.error("[CREATE RENEWAL] Erro ao gerar PIX:", error);
      return res.status(500).json({
        success: false,
        message: "Erro ao gerar cobrança PIX",
        error: error.message,
      });
    }

    // Cria o pagamento com todos os campos obrigatórios
    // O serviço unificado já retorna o provider correto (Woovi)
    const paymentData = {
      userId,
      plan: {
        id: plan.id,
        name: plan.name,
        price: planOption.value,
        monthId: planOption.id,
        months: months,
      },
      coupon: coupon ? {
        id: coupon._id,
        code: coupon.name,
        discountPercent: discountPercent,
      } : undefined,
      priceFinal: amount,
      provider: pixData.provider || "mistic", // Usa o provider retornado pelo serviço unificado
      status: "pending",
      qrCodeBase64: pixData.qrBase64,
      qrCodeText: pixData.emv,
      expiresAt: new Date(Date.now() + 10 * 60 * 1000), // 10 minutos
      metadata: {
        isRenewal: true,
        applicationId: applicationId,
        months: months,
      },
    };

    // Adiciona campos específicos do provedor
    if (pixData.provider === "mistic") {
      paymentData.misticId = pixData.paymentId;
      paymentData.misticRaw = pixData.raw;
    } else if (pixData.provider === "woovi") {
      paymentData.wooviId = pixData.paymentId;
      paymentData.wooviRaw = pixData.raw;
    } else {
      // Fallback para EFI
      paymentData.efiId = pixData.paymentId;
      paymentData.efiRaw = pixData.raw;
    }

    const payment = new Payment(paymentData);

    await payment.save();

    // Registra criação bem-sucedida para cooldown
    registerChargeCreation(req, res, () => { });

    return res.status(201).json({
      success: true,
      message: "Fatura de renovação criada com sucesso",
      data: {
        payment: {
          id: payment._id,
          amount: payment.priceFinal,
          pixCode: payment.qrCodeText,
          pixQrCode: payment.qrCodeBase64,
          expiresAt: payment.expiresAt,
        },
      },
    });
  } catch (error) {
    console.error("[CREATE RENEWAL ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao criar fatura de renovação",
      error: error.message,
    });
  }
}

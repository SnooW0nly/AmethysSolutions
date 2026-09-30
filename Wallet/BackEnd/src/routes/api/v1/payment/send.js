import express from 'express';
import { authenticateApiKey } from '../../../../middlewares/apiAuth.js';
import { paymentApiKeyRateLimiter } from '../../../../middlewares/apiKeyRateLimiter.js';
import Register from '../../../../database/models/Register.js';
import { withdraw as goatpayWithdraw } from '../../../../services/goatpayClient.js';
import { calculateFee, calculateSplit } from '../../../../services/categoryService.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';
import { sendWebhookEvent } from '../../../../services/webhookService.js';

const router = express.Router();

// POST /api/v1/payment/send - Enviar dinheiro/reembolsar
// Rate limit: API Key = 30 req/min
router.post('/', paymentApiKeyRateLimiter, authenticateApiKey, async (req, res) => {
  try {
    const user = req.user;
    let { amount, pixKey, pixKeyType, description } = req.body || {};

    if (amount === undefined || amount === null || amount === '') {
      return res.status(400).json({
        error: 'Valor obrigatório',
        message: 'Envie o campo "amount"'
      });
    }
    if (!pixKey || typeof pixKey !== 'string' || !pixKeyType || typeof pixKeyType !== 'string') {
      return res.status(400).json({
        error: 'Chave PIX obrigatória',
        message: 'Envie "pixKey" (string) e "pixKeyType" (CPF, CNPJ, EMAIL, PHONE, RANDOM)'
      });
    }

    let numericAmount;
    if (typeof amount === 'string') {
      const cleaned = amount.trim().replace(/\./g, '').replace(',', '.');
      numericAmount = parseFloat(cleaned);
    } else {
      numericAmount = Number(amount);
    }

    if (!isFinite(numericAmount) || numericAmount <= 0) {
      return res.status(400).json({
        error: 'Valor inválido',
        message: 'O valor deve ser maior que zero'
      });
    }

    const amountInCents = Math.round(numericAmount * 100);

    // Determinar categoria (fallback para WHITE)
    const category = user.category || 'WHITE';
    const tier = user.tier || 1;

    // Calcular taxas usando categoryService
    const userPaymentFee = await calculateFee(category, tier, amountInCents);

    // Split: Se user.splitFee estiver fixado no DB, usa ele (mas deveria ser deprecated).
    // Melhor usar calculateSplit do categoryService que segue regras novas.
    // Se quiser manter override do usuário:
    let userSplitFee;
    if (user.splitFee !== undefined) {
      userSplitFee = user.splitFee; // Legacy fixed split override?
    } else {
      userSplitFee = await calculateSplit(category, tier, amountInCents);
    }

    if (amountInCents <= userPaymentFee) {
      return res.status(400).json({
        error: 'Valor insuficiente',
        message: `O valor deve ser maior que a taxa de R$ ${(userPaymentFee / 100).toFixed(2)}`
      });
    }

    const available = user.balance || 0;
    if (available < amountInCents) {
      return res.status(400).json({
        error: 'Saldo insuficiente',
        balance: available,
        required: amountInCents
      });
    }

    // Débito atômico: verifica saldo e debita na mesma operação (evita race condition TOCTOU)
    const balanceResult = await Register.findOneAndUpdate(
      { id: user.id, balance: { $gte: amountInCents } },
      { $inc: { balance: -amountInCents } },
      { new: true }
    );

    if (!balanceResult) {
      const current = await Register.getById(user.id);
      return res.status(400).json({
        error: 'Saldo insuficiente',
        balance: current?.balance || 0,
        required: amountInCents
      });
    }

    const valueToSend = amountInCents - userPaymentFee;

    let providerResp;
    try {
      providerResp = await goatpayWithdraw({
        amount: valueToSend / 100,
        pixKey,
        pixKeyType: pixKeyType.toUpperCase(),
        coverFee: true,
        description: `Envio Amethys Wallet - ${user.name}`,
      });
    } catch (providerError) {
      await Register.findOneAndUpdate(
        { id: user.id },
        { $inc: { balance: amountInCents } }
      );
      return res.status(providerError.status || 500).json({
        error: 'Erro ao enviar via GoatPay',
        message: providerError.error || providerError.message || 'Falha na transferência',
        details: providerError.data || null
      });
    }

    // Acumular splitFee do usuário no saldo de split (taxa - 0,50)
    await Register.findOneAndUpdate(
      { id: user.id },
      { $inc: { saldo_split: userSplitFee } }
    );
    const newSplitBalance = (user.saldo_split || 0) + userSplitFee;
    console.log(`💰 Saldo split atualizado: +R$ ${(userSplitFee / 100).toFixed(2)} (total: R$ ${(newSplitBalance / 100).toFixed(2)})`);

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PAYMENT_SENT,
      entity: AUDIT_ENTITIES.PAYMENT,
      entityId: `send_${user.id}_${Date.now()}`,
      userId: user.id,
      userEmail: user.email,
      dataBefore: {
        balance: user.balance,
        saldo_split: user.saldo_split
      },
      dataAfter: {
        amount: amountInCents,
        sent: valueToSend,
        fee: userPaymentFee,
        destination: pixKey
      },
      metadata: {
        description: description || `Envio Amethys Wallet - ${user.name}`,
        providerResponse: providerResp
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Pagamento enviado: R$ ${(amountInCents / 100).toFixed(2)} para ${pixKey} - ${user.name}`
    });

    // Enviar webhook de reembolso (payment.refunded)
    await sendWebhookEvent(user.id, 'payment.refunded', {
      txid: `send_${user.id}_${Date.now()}`,
      amount: (amountInCents / 100).toFixed(2),
      netAmount: (valueToSend / 100).toFixed(2),
      status: 'refunded',
      refundedAt: Date.now()
    });

    return res.json({
      success: true,
      message: 'Envio processado com sucesso',
      data: {
        amount: amountInCents,
        fee: userPaymentFee,
        sent: valueToSend,
        destination: pixKey,
        provider: providerResp
      }
    });
  } catch (error) {
    console.error('Erro no envio:', error);
    return res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;

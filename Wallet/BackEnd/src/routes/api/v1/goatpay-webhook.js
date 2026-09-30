import express from 'express';
import crypto from 'crypto';
import Payment from '../../../database/models/Payment.js';
import Register from '../../../database/models/Register.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../database/models/Audit.js';
import { generateUniqueId } from '../../../services/security.js';
import { sendWebhookEvent } from '../../../services/webhookService.js';
import { notifyPaymentReceived } from '../../../services/pushService.js';

const router = express.Router();

function verifyGoatPayWebhook(rawBody, signatureHeader, webhookSecret) {
  if (!signatureHeader?.startsWith('sha256=')) return false;
  const received = signatureHeader.slice('sha256='.length);
  const expected = crypto
    .createHmac('sha256', webhookSecret)
    .update(typeof rawBody === 'string' ? rawBody : Buffer.from(rawBody))
    .digest('hex');
  const a = Buffer.from(expected, 'hex');
  const b = Buffer.from(received, 'hex');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function validateGoatPayWebhook(req, res, next) {
  const secret = process.env.GOATPAY_WEBHOOK_SECRET;
  let rawBody = req.body;

  if (!Buffer.isBuffer(rawBody)) {
    rawBody = Buffer.from(typeof rawBody === 'string' ? rawBody : JSON.stringify(rawBody || {}));
  }

  if (secret) {
    const signature = req.headers['x-goatpay-signature'];
    if (!verifyGoatPayWebhook(rawBody, signature, secret)) {
      return res.status(401).json({ error: 'Invalid signature' });
    }
  }

  try {
    req.goatpayEvent = JSON.parse(rawBody.toString('utf8'));
  } catch {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }

  next();
}

/**
 * POST /api/v1/goatpay-webhook
 * Webhook GoatPay (payment.paid, payment.failed, etc.)
 */
router.post('/', validateGoatPayWebhook, async (req, res) => {
  try {
    const event = req.goatpayEvent || req.body;
    const deliveryId = event?.id;
    const eventType = event?.event || req.headers['x-goatpay-event'];
    const tx = event?.data || {};

    if (!tx?.id && !tx?.externalReference) {
      return res.status(400).json({ success: false, error: 'Payload inválido' });
    }

    const lookupId = tx.externalReference || tx.id;

    const payment = await Payment.findOne({
      $or: [
        { id: String(lookupId) },
        { correlationID: String(tx.id) },
        { misticTransactionId: String(tx.id) },
      ],
    });

    if (!payment) {
      return res.status(200).json({ success: false, message: 'Pagamento não encontrado' });
    }

    if (payment.status === 'COMPLETED' || payment.status === 'PAID') {
      return res.status(200).json({ success: true, message: 'Pagamento já processado' });
    }

    const isPaid = eventType === 'payment.paid' || tx.status === 'COMPLETED';
    const isFailed = eventType === 'payment.failed'
      || eventType === 'payment.pix.expired'
      || tx.status === 'FAILED'
      || tx.status === 'CANCELED';

    if (isPaid) {
      const netValue = payment.netValue || (payment.fee ? payment.value - payment.fee : payment.value);

      const result = await Payment.findOneAndUpdate(
        { _id: payment._id, status: { $nin: ['COMPLETED', 'PAID'] } },
        {
          $set: {
            status: 'COMPLETED',
            paidAt: new Date().toISOString(),
            updatedAt: new Date(),
            'metadata.goatpayDeliveryId': deliveryId,
          },
        },
        { new: true },
      );

      if (!result) {
        return res.status(200).json({ success: true, message: 'Pagamento já processado' });
      }

      await Register.updateBalance(payment.userId, netValue, 'add');

      setImmediate(async () => {
        try {
          const user = await Register.findOne({ id: payment.userId }, { email: 1, referredBy: 1 }).lean();

          await sendWebhookEvent(payment.userId, 'payment.approved', {
            txid: payment.id,
            amount: (payment.value / 100).toFixed(2),
            netAmount: (netValue / 100).toFixed(2),
            fee: ((payment.value - netValue) / 100).toFixed(2),
            status: 'approved',
            approvedAt: Date.now(),
          });

          notifyPaymentReceived(payment.userId, netValue, payment.id).catch(() => {});

          await Audit.saveLog({
            id: generateUniqueId(),
            action: AUDIT_ACTIONS.PAYMENT_COMPLETED,
            entity: AUDIT_ENTITIES.PAYMENT,
            entityId: payment.id,
            userId: payment.userId,
            userEmail: user?.email || null,
            dataAfter: {
              status: 'COMPLETED',
              netValue,
              source: 'goatpay_webhook',
              deliveryId,
            },
            description: `Pagamento completado via webhook GoatPay: R$ ${(netValue / 100).toFixed(2)}`,
          }).catch(() => {});

          if (user?.referredBy) {
            await processAffiliateCommission(payment.id, payment.userId, user.referredBy, netValue);
          }
        } catch (err) {
          console.error('❌ [GoatPayWebhook] Erro em processamento background:', err.message);
        }
      });

      return res.status(200).json({ success: true, message: 'Pagamento processado com sucesso' });
    }

    if (isFailed) {
      await Payment.updateOne(
        { _id: payment._id },
        {
          $set: {
            status: tx.status === 'CANCELED' ? 'EXPIRED' : 'FAILED',
            updatedAt: new Date(),
            'metadata.goatpayDeliveryId': deliveryId,
          },
        },
      );

      return res.status(200).json({ success: true, message: 'Status de falha registrado' });
    }

    return res.status(200).json({ success: true, message: 'Evento recebido' });
  } catch (error) {
    console.error('❌ [GoatPayWebhook] Erro:', error.message);
    return res.status(200).json({ success: false, error: 'Erro interno' });
  }
});

async function processAffiliateCommission(paymentId, userId, referredBy, netValue) {
  try {
    const Affiliate = (await import('../../../database/models/Affiliate.js')).default;
    const affiliate = await Affiliate.findOne({ id: referredBy, status: 'active' }).lean();
    if (!affiliate) return;

    const commission = affiliate.commissionRate || 5;
    const marked = await Payment.updateOne(
      { id: paymentId, 'metadata.affiliateCommissionPaid': { $ne: true } },
      { $set: { 'metadata.affiliateCommissionPaid': true } },
    );

    if (marked.modifiedCount === 0) return;

    await Register.updateOne({ id: affiliate.userId }, { $inc: { balance: commission } });
    await Affiliate.updateOne({ id: affiliate.id }, { $inc: { totalEarnings: commission } });
  } catch (err) {
    console.error('❌ [GoatPayWebhook] Erro ao processar afiliado:', err.message);
  }
}

export default router;

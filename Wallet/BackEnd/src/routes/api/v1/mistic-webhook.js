import express from 'express';
import crypto from 'crypto';
import Payment from '../../../database/models/Payment.js';
import Register from '../../../database/models/Register.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../database/models/Audit.js';
import { generateUniqueId } from '../../../services/security.js';
import { sendWebhookEvent } from '../../../services/webhookService.js';
import { notifyPaymentReceived } from '../../../services/pushService.js';
import { getClientIP } from '../../../utils/getClientIP.js';

const router = express.Router();

/**
 * Middleware de autenticação do webhook da Mistic Pay
 * Valida por IP whitelist e/ou HMAC signature
 */
function validateMisticWebhook(req, res, next) {
    const MISTIC_IPS = (process.env.MISTIC_WEBHOOK_IPS || '').split(',').map(s => s.trim()).filter(Boolean);
    const clientIP = getClientIP(req);

    if (MISTIC_IPS.length > 0 && !MISTIC_IPS.includes(clientIP)) {
        console.warn(`[WEBHOOK] IP não autorizado bloqueado: ${clientIP}`);
        return res.status(403).json({ error: 'Forbidden' });
    }

    const secret = process.env.MISTIC_WEBHOOK_SECRET;
    const signature = req.headers['x-mistic-signature'];
    if (secret && signature) {
        const expected = crypto
            .createHmac('sha256', secret)
            .update(JSON.stringify(req.query))
            .digest('hex');
        try {
            if (!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) {
                return res.status(401).json({ error: 'Invalid signature' });
            }
        } catch {
            return res.status(401).json({ error: 'Invalid signature' });
        }
    }

    next();
}

/**
 * GET /api/v1/mistic-webhook
 * 
 * Webhook endpoint para receber notificações da MisticPay
 * 
 * Query params esperados (via GET):
 * - transactionId: ID da transação
 * - transactionType: DEPOSITO
 * - transactionMethod: PIX
 * - clientName: Nome do cliente que pagou
 * - clientDocument: CPF/CNPJ do cliente
 * - status: COMPLETO, FALHA, PENDENTE
 * - value: Valor em centavos
 * - fee: Taxa em centavos
 */
router.get('/', validateMisticWebhook, async (req, res) => {
    try {
        const {
            transactionId,
            transactionType,
            transactionMethod,
            clientName,
            clientDocument,
            status,
            value,
            fee
        } = req.query;

        console.log(`📥 [MisticWebhook] Recebido webhook: transactionId=${transactionId}, status=${status}`);

        // Validar campos obrigatórios
        if (!transactionId) {
            console.log('❌ [MisticWebhook] transactionId não fornecido');
            return res.status(400).json({
                success: false,
                error: 'transactionId é obrigatório'
            });
        }

        // Buscar pagamento pelo transactionId (pode ser correlationID ou misticTransactionId)
        const payment = await Payment.findOne({
            $or: [
                { correlationID: String(transactionId) },
                { misticTransactionId: String(transactionId) },
                { id: String(transactionId) }
            ]
        });

        if (!payment) {
            console.log(`⚠️ [MisticWebhook] Pagamento não encontrado: ${transactionId}`);
            // Retornar 200 para a MisticPay não ficar reenviando
            return res.status(200).json({
                success: false,
                message: 'Pagamento não encontrado'
            });
        }

        // Se já foi COMPLETADO, ignorar (mas EXPIRED pode ser aprovado via webhook)
        if (payment.status === 'COMPLETED' || payment.status === 'PAID') {
            console.log(`ℹ️ [MisticWebhook] Pagamento já processado: ${transactionId}`);
            return res.status(200).json({
                success: true,
                message: 'Pagamento já processado'
            });
        }

        // Log se pagamento estava expirado mas será aprovado
        if (payment.status === 'EXPIRED') {
            console.log(`🔄 [MisticWebhook] Pagamento EXPIRED será aprovado: ${transactionId}`);
        }

        // Atualizar informações do cliente (sempre, mesmo se pendente)
        const updateData = {};
        if (clientName) {
            updateData.clientName = clientName;
        }
        if (clientDocument) {
            updateData.clientDocument = clientDocument;
        }

        // Processar baseado no status
        const misticStatus = (status || '').toUpperCase();

        if (misticStatus === 'COMPLETO' || misticStatus === 'COMPLETED') {
            // Pagamento aprovado - creditar saldo
            const netValue = payment.netValue || (payment.fee ? payment.value - payment.fee : payment.value);

            // Atualizar pagamento atomicamente
            const result = await Payment.findOneAndUpdate(
                { _id: payment._id, status: { $nin: ['COMPLETED', 'PAID'] } },
                {
                    $set: {
                        ...updateData,
                        status: 'COMPLETED',
                        paidAt: new Date().toISOString(),
                        updatedAt: new Date()
                    }
                },
                { new: true }
            );

            if (!result) {
                console.log(`ℹ️ [MisticWebhook] Pagamento já foi processado por outro processo: ${transactionId}`);
                return res.status(200).json({
                    success: true,
                    message: 'Pagamento já processado'
                });
            }

            // Creditar saldo do usuário
            await Register.updateBalance(payment.userId, netValue, 'add');

            console.log(`✅ [MisticWebhook] Pagamento aprovado: ${transactionId} - R$ ${(netValue / 100).toFixed(2)} creditado`);

            // Processar em background: webhook, notificação, auditoria, afiliado
            setImmediate(async () => {
                try {
                    const user = await Register.findOne({ id: payment.userId }, { email: 1, referredBy: 1 }).lean();

                    // Enviar webhook para o cliente
                    await sendWebhookEvent(payment.userId, 'payment.approved', {
                        txid: payment.id,
                        amount: (payment.value / 100).toFixed(2),
                        netAmount: (netValue / 100).toFixed(2),
                        fee: ((payment.value - netValue) / 100).toFixed(2),
                        status: 'approved',
                        clientName: clientName || null,
                        clientDocument: clientDocument || null,
                        approvedAt: Date.now()
                    });

                    // Push notification
                    notifyPaymentReceived(payment.userId, netValue, payment.id).catch(() => { });

                    // Audit log
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
                            clientName: clientName || null,
                            clientDocument: clientDocument || null,
                            source: 'mistic_webhook'
                        },
                        description: `Pagamento completado via webhook: R$ ${(netValue / 100).toFixed(2)}`
                    }).catch(() => { });

                    // Processar afiliado se aplicável
                    if (user?.referredBy) {
                        await processAffiliateCommission(payment.id, payment.userId, user.referredBy, netValue);
                    }
                } catch (err) {
                    console.error('❌ [MisticWebhook] Erro em processamento background:', err.message);
                }
            });

            return res.status(200).json({
                success: true,
                message: 'Pagamento processado com sucesso'
            });

        } else if (misticStatus === 'FALHA' || misticStatus === 'FAILED') {
            // Pagamento falhou
            await Payment.updateOne(
                { _id: payment._id },
                {
                    $set: {
                        ...updateData,
                        status: 'FAILED',
                        updatedAt: new Date()
                    }
                }
            );

            console.log(`❌ [MisticWebhook] Pagamento falhou: ${transactionId}`);

            return res.status(200).json({
                success: true,
                message: 'Status de falha registrado'
            });

        } else {
            // Status pendente ou outro - apenas atualizar info do cliente se tiver
            if (Object.keys(updateData).length > 0) {
                await Payment.updateOne(
                    { _id: payment._id },
                    { $set: { ...updateData, updatedAt: new Date() } }
                );
                console.log(`ℹ️ [MisticWebhook] Info do cliente atualizada: ${transactionId}`);
            }

            return res.status(200).json({
                success: true,
                message: 'Status recebido'
            });
        }

    } catch (error) {
        console.error('❌ [MisticWebhook] Erro:', error.message);
        // Retornar 200 para não causar retries desnecessários
        return res.status(200).json({
            success: false,
            error: 'Erro interno'
        });
    }
});

/**
 * Processa comissão de afiliado
 */
async function processAffiliateCommission(paymentId, userId, referredBy, netValue) {
    try {
        const Affiliate = (await import('../../../database/models/Affiliate.js')).default;
        const affiliate = await Affiliate.findOne({ id: referredBy, status: 'active' }).lean();
        if (!affiliate) return;

        const commission = affiliate.commissionRate || 5;

        // Marcar como pago atomicamente
        const marked = await Payment.updateOne(
            { id: paymentId, 'metadata.affiliateCommissionPaid': { $ne: true } },
            { $set: { 'metadata.affiliateCommissionPaid': true } }
        );

        if (marked.modifiedCount === 0) return;

        // Creditar
        await Register.updateOne({ id: affiliate.userId }, { $inc: { balance: commission } });
        await Affiliate.updateOne({ id: affiliate.id }, { $inc: { totalEarnings: commission } });

        console.log(`💰 [MisticWebhook] Comissão: R$ ${(commission / 100).toFixed(2)} para afiliado ${affiliate.id}`);
    } catch (err) {
        console.error('❌ [MisticWebhook] Erro ao processar afiliado:', err.message);
    }
}

export default router;

import Payment from '../database/models/Payment.js';
import Register from '../database/models/Register.js';
import SplitPayment from '../database/models/SplitPayment.js';
import { checkTransaction, withdraw as goatpayWithdraw } from './goatpayClient.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../database/models/Audit.js';
import { generateUniqueId } from './security.js';
import { sendWebhookEvent } from './webhookService.js';
import { notifyPaymentReceived } from './pushService.js';

// ================== CONFIGURAÇÕES ULTRA OTIMIZADAS ==================
const BATCH_SIZE = 20;
const BATCH_DELAY = 1000;
const CONCURRENCY = 10;
const MAX_PENDING_TO_PROCESS = 100;
const DAYS_TO_DELETE_EXPIRED = 365;
const DISCORD_CLEANUP_WEBHOOK = process.env.DISCORD_WEBHOOK_CLEANUP;
// =====================================================================

// ================== CONFIGURAÇÕES TAXA DO DONO =======================
// Sua parte é a platformFee já descontada do netValue.
// Exemplo: pagamento de R$ 100 → fee = R$ 4,70 (4% + custo fixo do provedor)
// A GoatPay retém a taxa do adquirente; você saca sua margem via transfer-pix.
const OWNER_PIX_KEY      = process.env.OWNER_PIX_KEY      || '93de9204-4675-466e-a2a0-f3646aa2cd53';
const OWNER_PIX_KEY_TYPE = process.env.OWNER_PIX_KEY_TYPE || 'RANDOM';
const OWNER_FEE_RATE     = parseFloat(process.env.OWNER_FEE_RATE || '4'); // 4%
const MIN_PROVIDER_WITHDRAW = 100; // R$ 1,00 mínimo para saque na GoatPay
const DISCORD_FEE_WEBHOOK = process.env.DISCORD_WEBHOOK_FEE;
// =====================================================================

const backgroundQueue = [];
let isProcessingQueue = false;

function queueBackgroundTask(task) {
  backgroundQueue.push(task);
  processBackgroundQueue();
}

async function processBackgroundQueue() {
  if (isProcessingQueue || backgroundQueue.length === 0) return;
  isProcessingQueue = true;

  while (backgroundQueue.length > 0) {
    const task = backgroundQueue.shift();
    try {
      await task();
    } catch (err) {}
    if (backgroundQueue.length > 0) {
      await new Promise(r => setTimeout(r, 50));
    }
  }

  isProcessingQueue = false;
}

async function sendDiscordWebhook(payments) {
  if (!payments || payments.length === 0) return;

  try {
    const embeds = payments.slice(0, 10).map(p => ({
      title: '🗑️ Pagamento Deletado',
      color: 0xFF0000,
      fields: [
        { name: 'ID', value: p.id || 'N/A', inline: true },
        { name: 'Usuário', value: p.userId || 'N/A', inline: true },
        { name: 'Valor', value: `R$ ${((p.value || 0) / 100).toFixed(2)}`, inline: true },
        { name: 'Status', value: p.status || 'EXPIRED', inline: true },
        { name: 'Criado em', value: p.createdAt ? new Date(p.createdAt).toLocaleString('pt-BR') : 'N/A', inline: true },
        { name: 'Expirado em', value: p.metadata?.expiredAt ? new Date(p.metadata.expiredAt).toLocaleString('pt-BR') : 'N/A', inline: true },
      ],
      timestamp: new Date().toISOString()
    }));

    await fetch(DISCORD_CLEANUP_WEBHOOK, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: `📢 **${payments.length} pagamento(s) expirado(s) deletado(s) do banco de dados**`,
        embeds
      })
    });

    console.log(`📨 Notificação enviada ao Discord: ${payments.length} pagamento(s) deletado(s)`);
  } catch (error) {
    console.error('❌ Erro ao enviar webhook do Discord:', error.message);
  }
}

async function cleanupOldExpiredPayments() {
  try {
    const now = new Date();
    const cutoffDate = new Date(now.getTime() - DAYS_TO_DELETE_EXPIRED * 24 * 60 * 60 * 1000);

    const paymentsToDelete = await Payment.find(
      {
        status: 'EXPIRED',
        $or: [
          { 'metadata.expiredAt': { $lt: cutoffDate.toISOString() } },
          { updatedAt: { $lt: cutoffDate } }
        ]
      },
      { id: 1, userId: 1, value: 1, status: 1, createdAt: 1, 'metadata.expiredAt': 1 }
    ).limit(50).lean();

    if (paymentsToDelete.length === 0) {
      return { deleted: 0 };
    }

    queueBackgroundTask(() => sendDiscordWebhook(paymentsToDelete));

    const deleteResult = await Payment.deleteMany({
      _id: { $in: paymentsToDelete.map(p => p._id) }
    });

    console.log(`🗑️ ${deleteResult.deletedCount} pagamento(s) expirado(s) deletado(s) (>365 dias)`);

    return { deleted: deleteResult.deletedCount };
  } catch (error) {
    console.error('❌ Erro ao limpar pagamentos expirados:', error.message);
    return { deleted: 0 };
  }
}

// ─── Saque da taxa do dono ────────────────────────────────────────────────────

/**
 * Calcula a parte do dono sobre um pagamento.
 * Saca a margem do dono (OWNER_FEE_RATE %) via GoatPay transfer-pix.
 */
function calcOwnerFeeForPayment(payment) {
  // Usa payment.value (valor bruto do QR Code, em centavos)
  return Math.floor((payment.value * OWNER_FEE_RATE) / 100);
}

/**
 * Dispara o saque da taxa do dono para o Pix configurado.
 * Totalmente idempotente: a marcação `ownerFeeWithdrawn` acontece ANTES
 * da chamada à GoatPay, dentro da mesma operação que completa o pagamento.
 * Se a GoatPay falhar, o campo é revertido e o erro é logado — sem perda.
 */
async function withdrawOwnerFeeInBackground(paymentId, paymentValue, paymentDbId) {
  const ownerFeeAmount = Math.floor((paymentValue * OWNER_FEE_RATE) / 100);

  if (ownerFeeAmount <= 0) return;

  if (ownerFeeAmount < MIN_PROVIDER_WITHDRAW) {
    console.warn(
      `[FeeWithdraw] Taxa R$ ${(ownerFeeAmount / 100).toFixed(2)} abaixo do mínimo GoatPay (R$ 1,00). ` +
      `Pagamento ${paymentId} ignorado.`
    );
    // Desmarcar para não perder a taxa (será tentado novamente se implementar acumulador)
    await Payment.updateOne(
      { id: paymentId },
      { $unset: { 'metadata.ownerFeeWithdrawn': '', 'metadata.ownerFeeWithdrawId': '' } }
    ).catch(() => {});
    return;
  }

  let providerResponse;
  try {
    providerResponse = await goatpayWithdraw({
      amount: ownerFeeAmount / 100,
      pixKey: OWNER_PIX_KEY,
      pixKeyType: OWNER_PIX_KEY_TYPE,
      coverFee: true,
      description: `Taxa Amethys ${OWNER_FEE_RATE}% - pgto ${paymentId}`,
      useBlackCredentials: false,
    });
  } catch (providerErr) {
    console.error(
      `[FeeWithdraw] GoatPay recusou saque do pgto ${paymentId}: ` +
      `${providerErr.error || providerErr.message}. Revertendo marcação.`
    );
    await Payment.updateOne(
      { id: paymentId },
      { $unset: { 'metadata.ownerFeeWithdrawn': '', 'metadata.ownerFeeWithdrawId': '' } }
    ).catch(() => {});
    return;
  }

  const providerTxId = providerResponse?.data?.transactionId || providerResponse?.transactionId || 'simulated';

  await Payment.updateOne(
    { id: paymentId },
    { $set: { 'metadata.ownerFeeWithdrawProviderId': providerTxId } }
  ).catch(() => {});

  // Auditoria
  Audit.saveLog({
    id: generateUniqueId(),
    action: 'OWNER_FEE_WITHDRAWN',
    entity: 'FEE',
    entityId: paymentId,
    userId: 'PLATFORM',
    dataAfter: {
      paymentId,
      feeAmount: ownerFeeAmount,
      feeRate: OWNER_FEE_RATE,
      pixKey: OWNER_PIX_KEY,
      providerTxId,
    },
    description:
      `Taxa do dono: R$ ${(ownerFeeAmount / 100).toFixed(2)} ` +
      `(${OWNER_FEE_RATE}% de R$ ${(paymentValue / 100).toFixed(2)}) → Pix ${OWNER_PIX_KEY}`,
  }).catch(() => {});

  // Notificação Discord (opcional)
  if (DISCORD_FEE_WEBHOOK) {
    fetch(DISCORD_FEE_WEBHOOK, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        embeds: [{
          title: '💜 Taxa do Dono Sacada',
          color: 0x7B2FBE,
          fields: [
            { name: 'Valor',       value: `R$ ${(ownerFeeAmount / 100).toFixed(2)}`, inline: true },
            { name: 'Pagamento',   value: paymentId,                                 inline: true },
            { name: 'GoatPay TxID', value: providerTxId,                              inline: false },
          ],
          timestamp: new Date().toISOString(),
        }],
      }),
    }).catch(() => {});
  }

  console.log(
    `💜 [FeeWithdraw] R$ ${(ownerFeeAmount / 100).toFixed(2)} sacados ` +
    `(pgto ${paymentId}) → Pix ${OWNER_PIX_KEY} | GoatPayTx: ${providerTxId}`
  );
}

// ─────────────────────────────────────────────────────────────────────────────

async function processSinglePayment(payment) {
  try {
    const misticTransactionId = payment.misticTransactionId || payment.correlationID || payment.id;
    if (!misticTransactionId) return { updated: false };

    const useBlackCredentials = payment.metadata?.useBlackCredentials || false;

    const misticResponse = await checkTransaction({ transactionId: misticTransactionId, type: 'payment', useBlackCredentials });
    if (misticResponse.simulated || misticResponse.fromCache) {
      const cachedStatus = misticResponse.transaction?.transactionState ||
        misticResponse.data?.transactionState ||
        misticResponse.transactionState;
      if (!cachedStatus || cachedStatus === 'PENDENTE' || cachedStatus === 'PENDING') {
        return { updated: false };
      }
    }

    const misticData = misticResponse.transaction || misticResponse.data || misticResponse;
    const misticStatus = misticData.transactionState || misticData.status || misticData.state || 'PENDENTE';

    const newStatus = (misticStatus === 'COMPLETO' || misticStatus === 'COMPLETED') ? 'COMPLETED' :
      (misticStatus === 'FALHA' || misticStatus === 'FAILED') ? 'FAILED' :
        (misticStatus === 'PENDENTE' || misticStatus === 'PENDING') ? 'PENDING' :
          payment.status;

    if (newStatus === payment.status) return { updated: false };

    if (newStatus === 'COMPLETED') {
      const netValue = payment.netValue || (payment.fee ? payment.value - payment.fee : payment.value);

      // ── PASSO 1: Marcar como COMPLETED + marcar taxa do dono atomicamente ──
      // Uma única operação findOneAndUpdate com o guard status $nin.
      // Se retornar null, outro processo já processou → abortar (idempotente).
      const result = await Payment.findOneAndUpdate(
        {
          _id: payment._id,
          status: { $nin: ['COMPLETED', 'PAID'] },
          // Guard adicional: só processa se a taxa do dono ainda não foi marcada
          'metadata.ownerFeeWithdrawn': { $ne: true },
        },
        {
          $set: {
            status: 'COMPLETED',
            updatedAt: new Date(),
            // Marcar a taxa do dono JUNTO com o COMPLETED — mesma operação atômica.
            // Isso garante que só um processo ever processa esse pagamento.
            'metadata.ownerFeeWithdrawn': true,
            'metadata.ownerFeeWithdrawnAt': new Date().toISOString(),
            'metadata.ownerFeeAmount': Math.floor((payment.value * OWNER_FEE_RATE) / 100),
          },
        },
        { projection: { _id: 1 } }
      );

      // Se result for null: pagamento já foi processado por outro ciclo → skip.
      if (!result) return { updated: false };

      // ── PASSO 2: Creditar saldo do usuário ──
      await Register.updateBalance(payment.userId, netValue, 'add');

      const paymentId = payment.id;
      const userId = payment.userId;
      const value = payment.value;

      // ── PASSO 3: Saque da taxa do dono (background, não bloqueia o usuário) ──
      // Roda em background junto com webhook, Discord, auditoria etc.
      queueBackgroundTask(async () => {
        const user = await Register.findOne({ id: userId }, { email: 1, referredBy: 1, pixKey: 1, plan: 1 }).lean();

        // Taxa do dono → Pix (com idempotência garantida pelo Step 1)
        await withdrawOwnerFeeInBackground(paymentId, value, payment._id);

        await sendWebhookEvent(userId, 'payment.approved', {
          txid: paymentId,
          amount: (value / 100).toFixed(2),
          netAmount: (netValue / 100).toFixed(2),
          fee: ((value - netValue) / 100).toFixed(2),
          status: 'approved',
          approvedAt: Date.now()
        });

        try {
          const { notifyPaymentApproved } = await import('./discordNotifier.js');
          await notifyPaymentApproved({
            paymentId,
            email: user?.email || 'N/A',
            value,
            fee: value - netValue,
            netValue,
            status: 'APPROVED',
            pixKey: user?.pixKey,
            plan: user?.plan || 'FREE'
          });
        } catch (e) {
          console.error('[DISCORD] Erro ao notificar pagamento:', e.message);
        }

        notifyPaymentReceived(userId, netValue, paymentId).catch(() => { });

        Audit.saveLog({
          id: generateUniqueId(),
          action: AUDIT_ACTIONS.PAYMENT_COMPLETED,
          entity: AUDIT_ENTITIES.PAYMENT,
          entityId: paymentId,
          userId: userId,
          userEmail: user?.email || null,
          dataAfter: { status: 'COMPLETED', netValue },
          description: `Pagamento completado: R$ ${(netValue / 100).toFixed(2)}`
        }).catch(() => { });

        if (user?.referredBy) {
          processAffiliateInBackground(paymentId, userId, user.referredBy, netValue);
        }

        if (payment.metadata?.internalSplit && !payment.metadata.internalSplit.processed) {
          processInternalSplitInBackground(payment, user?.email, netValue);
        }
      });

      return { updated: true };
    }

    if (newStatus !== payment.status) {
      await Payment.updateOne(
        { _id: payment._id },
        { $set: { status: newStatus, updatedAt: new Date() } }
      );
      return { updated: true };
    }

    return { updated: false };
  } catch (error) {
    if (error.status === 429) return { updated: false, rateLimit: true };
    return { updated: false };
  }
}


async function processAffiliateInBackground(paymentId, userId, referredBy, netValue) {
  try {
    const Affiliate = (await import('../database/models/Affiliate.js')).default;
    const affiliate = await Affiliate.findOne({ id: referredBy, status: 'active' }, { id: 1, userId: 1, commissionRate: 1, userEmail: 1 }).lean();
    if (!affiliate) return;

    const commission = affiliate.commissionRate || 5;

    const marked = await Payment.updateOne(
      { id: paymentId, 'metadata.affiliateCommissionPaid': { $ne: true } },
      { $set: { 'metadata.affiliateCommissionPaid': true } }
    );

    if (marked.modifiedCount === 0) return;

    await Register.updateOne({ id: affiliate.userId }, { $inc: { balance: commission } });
    await Affiliate.updateOne({ id: affiliate.id }, { $inc: { totalEarnings: commission } });

    console.log(`💰 Comissão: R$ ${(commission / 100).toFixed(2)} para ${affiliate.userEmail}`);
  } catch (err) {}
}

async function processInternalSplitInBackground(payment, senderEmail, netValue) {
  try {
    const internalSplit = payment.metadata?.internalSplit;
    if (!internalSplit || internalSplit.processed) return;

    const { recipientId, recipientEmail, splitPercentage } = internalSplit;
    const splitAmount = Math.floor(netValue * (splitPercentage / 100));

    if (splitAmount <= 0) return;

    const marked = await Payment.updateOne(
      { id: payment.id, 'metadata.internalSplit.processed': { $ne: true } },
      { $set: { 'metadata.internalSplit.processed': true, 'metadata.internalSplit.processedAt': new Date().toISOString() } }
    );

    if (marked.modifiedCount === 0) return;

    await Register.updateOne({ id: recipientId }, { $inc: { balance: splitAmount } });

    const splitId = generateUniqueId();
    await SplitPayment.create({
      id: splitId,
      originalPaymentId: payment.id,
      senderId: payment.userId,
      senderEmail: senderEmail || 'unknown',
      recipientId: recipientId,
      recipientEmail: recipientEmail,
      amount: splitAmount,
      splitPercentage: splitPercentage,
      originalAmount: netValue,
      status: 'COMPLETED',
      createdAt: new Date().toISOString(),
      processedAt: new Date().toISOString()
    });

    notifyPaymentReceived(recipientId, splitAmount, splitId).catch(() => { });

    console.log(`💸 Split interno: R$ ${(splitAmount / 100).toFixed(2)} para ${recipientEmail} (${splitPercentage}%)`);
  } catch (err) {
    console.error('❌ Erro ao processar split interno:', err.message);
  }
}

async function processPaymentBatch(payments) {
  let updated = 0;
  let rateLimitHit = false;

  const chunks = [];
  for (let i = 0; i < payments.length; i += CONCURRENCY) {
    chunks.push(payments.slice(i, i + CONCURRENCY));
  }

  for (const chunk of chunks) {
    if (rateLimitHit) break;

    const results = await Promise.all(
      chunk.map(p => processSinglePayment(p).catch(() => ({ updated: false })))
    );

    for (const r of results) {
      if (r.updated) updated++;
      if (r.rateLimit) rateLimitHit = true;
    }
  }

  return { updated };
}


/**
 * Verifica um pagamento na Mistic ANTES de expirar
 * Se estiver pago na Mistic, processa normalmente (credita saldo, webhook, etc)
 * Se não estiver pago, expira o pagamento
 */
async function checkAndExpirePayment(payment) {
  try {
    const misticTransactionId = payment.misticTransactionId || payment.correlationID || payment.id;
    
    if (!misticTransactionId) {
      return { action: 'expire', reason: 'Sem ID de transação Mistic' };
    }

    const useBlackCredentials = payment.metadata?.useBlackCredentials || false;

    const misticResponse = await checkTransaction({ transactionId: misticTransactionId, type: 'payment', useBlackCredentials });
    
    const misticData = misticResponse.transaction || misticResponse.data || misticResponse;
    const misticStatus = misticData.transactionState || misticData.status || misticData.state || 'PENDENTE';

    if (misticStatus === 'COMPLETO' || misticStatus === 'COMPLETED') {
      console.log(`✅ Pagamento ${payment.id} está PAGO na Mistic! Processando...`);
      
      const netValue = payment.netValue || (payment.fee ? payment.value - payment.fee : payment.value);

      // Mesma lógica atômica: COMPLETED + ownerFeeWithdrawn juntos
      const result = await Payment.findOneAndUpdate(
        {
          _id: payment._id,
          status: { $nin: ['COMPLETED', 'PAID'] },
          'metadata.ownerFeeWithdrawn': { $ne: true },
        },
        {
          $set: {
            status: 'COMPLETED',
            updatedAt: new Date(),
            'metadata.ownerFeeWithdrawn': true,
            'metadata.ownerFeeWithdrawnAt': new Date().toISOString(),
            'metadata.ownerFeeAmount': Math.floor((payment.value * OWNER_FEE_RATE) / 100),
          },
        },
        { projection: { _id: 1 } }
      );

      if (!result) return { action: 'skip', reason: 'Já processado' };

      await Register.updateBalance(payment.userId, netValue, 'add');

      const paymentId = payment.id;
      const userId = payment.userId;
      const value = payment.value;

      queueBackgroundTask(async () => {
        const user = await Register.findOne({ id: userId }, { email: 1, referredBy: 1, pixKey: 1, plan: 1 }).lean();

        // Taxa do dono → Pix
        await withdrawOwnerFeeInBackground(paymentId, value, payment._id);

        await sendWebhookEvent(userId, 'payment.approved', {
          txid: paymentId,
          amount: (value / 100).toFixed(2),
          netAmount: (netValue / 100).toFixed(2),
          fee: ((value - netValue) / 100).toFixed(2),
          status: 'approved',
          approvedAt: Date.now()
        });

        try {
          const { notifyPaymentApproved } = await import('./discordNotifier.js');
          await notifyPaymentApproved({
            paymentId,
            email: user?.email || 'N/A',
            value,
            fee: value - netValue,
            netValue,
            status: 'APPROVED',
            pixKey: user?.pixKey,
            plan: user?.plan || 'FREE'
          });
        } catch (e) {
          console.error('[DISCORD] Erro ao notificar pagamento:', e.message);
        }

        notifyPaymentReceived(userId, netValue, paymentId).catch(() => { });

        Audit.saveLog({
          id: generateUniqueId(),
          action: AUDIT_ACTIONS.PAYMENT_COMPLETED,
          entity: AUDIT_ENTITIES.PAYMENT,
          entityId: paymentId,
          userId: userId,
          userEmail: user?.email || null,
          dataAfter: { status: 'COMPLETED', netValue },
          description: `Pagamento completado (recuperado antes de expirar): R$ ${(netValue / 100).toFixed(2)}`
        }).catch(() => { });

        if (user?.referredBy) {
          processAffiliateInBackground(paymentId, userId, user.referredBy, netValue);
        }

        if (payment.metadata?.internalSplit && !payment.metadata.internalSplit.processed) {
          processInternalSplitInBackground(payment, user?.email, netValue);
        }
      });

      return { action: 'completed', reason: 'Pago na Mistic' };
    }

    return { action: 'expire', reason: `Status na Mistic: ${misticStatus}` };

  } catch (error) {
    console.warn(`⚠️ Erro ao verificar pagamento ${payment.id} na Mistic: ${error.message}`);
    return { action: 'expire', reason: `Erro na verificação: ${error.message}` };
  }
}


/**
 * Poller principal
 */
export async function checkPendingPayments() {
  try {
    const now = new Date();
    const thirtyMinutesAgo = new Date(now.getTime() - 30 * 60 * 1000);
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    // ========== ETAPA 1: Verificar pagamentos que SERIAM expirados ==========
    const paymentsToExpire = await Payment.find(
      {
        status: { $in: ['PENDING', 'ACTIVE'] },
        createdAt: { $lt: thirtyMinutesAgo }
      },
      {
        id: 1, _id: 1, userId: 1, status: 1, value: 1, netValue: 1, fee: 1,
        misticTransactionId: 1, correlationID: 1, description: 1, createdAt: 1,
        'metadata.useBlackCredentials': 1, 'metadata.affiliateCommissionPaid': 1,
        'metadata.internalSplit': 1, 'metadata.ownerFeeWithdrawn': 1,
      }
    ).limit(50).lean();

    let expiredCount = 0;
    let recoveredCount = 0;

    if (paymentsToExpire.length > 0) {
      console.log(`🔍 Verificando ${paymentsToExpire.length} pagamento(s) na Mistic antes de expirar...`);

      for (const payment of paymentsToExpire) {
        const result = await checkAndExpirePayment(payment);

        if (result.action === 'completed') {
          recoveredCount++;
          console.log(`💰 Pagamento ${payment.id} recuperado! (${result.reason})`);
        } else if (result.action === 'expire') {
          await Payment.updateOne(
            { _id: payment._id },
            {
              $set: {
                status: 'EXPIRED',
                'metadata.expiredAt': now.toISOString(),
                'metadata.expirationReason': result.reason,
                updatedAt: now
              }
            }
          );
          expiredCount++;
        }

        await new Promise(r => setTimeout(r, 100));
      }

      if (expiredCount > 0) console.log(`⏰ ${expiredCount} pagamento(s) expirado(s)`);
      if (recoveredCount > 0) console.log(`🎉 ${recoveredCount} pagamento(s) recuperado(s) antes de expirar!`);
    }

    // ========== ETAPA 2: Limpar pagamentos expirados antigos ==========
    await cleanupOldExpiredPayments();

    // ========== ETAPA 3: Verificar pagamentos pendentes recentes ==========
    const pendingPayments = await Payment.find(
      {
        status: { $in: ['PENDING', 'ACTIVE'] },
        createdAt: { $gte: twentyFourHoursAgo },
        $or: [
          { misticTransactionId: { $exists: true, $ne: null } },
          { correlationID: { $exists: true, $ne: null } }
        ]
      },
      {
        id: 1, userId: 1, status: 1, value: 1, netValue: 1, fee: 1,
        misticTransactionId: 1, correlationID: 1, description: 1, createdAt: 1, expiresAt: 1,
        'metadata.useBlackCredentials': 1, 'metadata.affiliateCommissionPaid': 1,
        'metadata.internalSplit': 1, 'metadata.ownerFeeWithdrawn': 1,
      }
    ).sort({ createdAt: -1 }).limit(MAX_PENDING_TO_PROCESS).lean();

    if (pendingPayments.length === 0) {
      return { checked: paymentsToExpire.length, updated: expiredCount, recovered: recoveredCount };
    }

    console.log(`🔍 Verificando ${pendingPayments.length} pagamento(s) pendente(s)...`);

    let totalUpdated = 0;

    for (let i = 0; i < pendingPayments.length; i += BATCH_SIZE) {
      const batch = pendingPayments.slice(i, i + BATCH_SIZE);
      const result = await processPaymentBatch(batch);
      totalUpdated += result.updated;

      if (i + BATCH_SIZE < pendingPayments.length) {
        await new Promise(r => setTimeout(r, BATCH_DELAY));
      }
    }

    if (totalUpdated > 0) console.log(`✅ ${totalUpdated} pagamento(s) atualizado(s)`);

    return { 
      checked: pendingPayments.length + paymentsToExpire.length, 
      updated: totalUpdated + expiredCount,
      recovered: recoveredCount
    };

  } catch (error) {
    console.error('❌ Erro no poller:', error.message);
    return { checked: 0, updated: 0, error: 1 };
  }
}

export function startPaymentPoller(intervalMs = 5000) {
  console.log(`🚀 Payment Poller ULTRA OTIMIZADO`);
  console.log(`   - Intervalo: ${intervalMs / 1000}s`);
  console.log(`   - Lote: ${BATCH_SIZE} | Concorrência: ${CONCURRENCY}`);
  console.log(`   - Máx por ciclo: ${MAX_PENDING_TO_PROCESS}`);
  console.log(`   - Verifica GoatPay ANTES de expirar pagamentos`);
  console.log(`   - Auto-saque taxa ${OWNER_FEE_RATE}% → Pix ${OWNER_PIX_KEY}`);

  let isRunning = false;

  const runPoller = async () => {
    if (isRunning) {
      console.log('⏭️ Poller ainda em execução, pulando ciclo...');
      return;
    }

    isRunning = true;
    try {
      await checkPendingPayments();
    } catch (err) {
      console.error('❌ Erro no poller:', err.message);
    } finally {
      isRunning = false;
    }
  };

  runPoller();
  return setInterval(runPoller, intervalMs);
}
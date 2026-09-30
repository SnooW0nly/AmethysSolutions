import Withdraw from '../database/models/Withdraw.js';
import Register from '../database/models/Register.js';
import { checkTransaction } from './goatpayClient.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../database/models/Audit.js';
import { generateUniqueId } from './security.js';
import { sendWebhookEvent } from './webhookService.js';
import { notifyWithdrawCompleted, notifyWithdrawFailed } from './pushService.js';

async function processWithdrawBatch(withdraws) {
  let updated = 0;
  let errors = 0;

  for (const w of withdraws) {
    try {
      const misticTransactionId = w.transactionId || w.correlationID || w.id;
      if (!misticTransactionId) {
        console.warn(`⚠️ Saque ${w.id} sem transactionId, pulando...`);
        continue;
      }


      console.log(`🔍 Verificando saque ${w.id} com transactionId: ${misticTransactionId}`);

      // Usar credenciais BLACK se necessário
      const useBlackCredentials = w.metadata?.useBlackCredentials || false;

      const misticResponse = await checkTransaction({ transactionId: misticTransactionId, type: 'transfer', useBlackCredentials });
      const misticData = misticResponse.transaction || misticResponse.data || misticResponse;

      // Normalizar status
      const state = (misticData.transactionState || misticData.state || misticData.status || '').toString().toUpperCase();
      console.log(`📋 Saque ${w.id} - Status Mistic: "${state}" | Resposta completa:`, JSON.stringify(misticData));

      let newStatus = w.status;
      // Estados de sucesso (inglês e português)
      if (['COMPLETED', 'PAID', 'DONE', 'SUCCESS', 'COMPLETO', 'PAGO', 'CONCLUIDO', 'CONCLUÍDA', 'FINALIZADO', 'APROVADO'].includes(state)) {
        newStatus = 'COMPLETED';
        // Estados de falha (inglês e português)
      } else if (['FAILED', 'ERROR', 'CANCELLED', 'CANCELED', 'FALHA', 'ERRO', 'CANCELADO', 'REJEITADO', 'RECUSADO'].includes(state)) {
        newStatus = 'FAILED';
        // Estados pendentes (inglês e português)
      } else if (['PENDING', 'CREATED', 'PROCESSING', 'WAITING', 'PENDENTE', 'CRIADO', 'PROCESSANDO', 'AGUARDANDO', 'EM_PROCESSAMENTO'].includes(state)) {
        newStatus = 'PROCESSING';
      } else if (state && state !== '') {
        console.warn(`⚠️ Estado desconhecido da Mistic para saque ${w.id}: "${state}"`);
      }

      if (newStatus !== w.status) {
        const now = new Date();

        // Se o saque falhou, devolver o saldo ao usuário de forma atômica e idempotente
        if (newStatus === 'FAILED' && w.status !== 'FAILED') {
          try {
            const amountToRefund = w.value || 0;
            if (amountToRefund > 0) {
              // Marcar como refunded E como FAILED atomicamente ANTES de creditar
              // Se modifiedCount === 0, outro processo já processou — abortar
              const markResult = await Withdraw.findOneAndUpdate(
                {
                  id: w.id,
                  status: { $ne: 'FAILED' },
                  'metadata.refunded': { $ne: true }
                },
                {
                  $set: {
                    status: 'FAILED',
                    'metadata.refunded': true,
                    failedAt: new Date().toISOString(),
                    updatedAt: new Date()
                  }
                }
              );

              if (!markResult) {
                console.log(`[WITHDRAW] Saque ${w.id} já foi processado/reembolsado, ignorando`);
                updated++;
                continue;
              }

              // Só chega aqui se foi o único processo a marcar
              console.log(`💰 Devolvendo saldo de saque falho: R$ ${(amountToRefund / 100).toFixed(2)} para usuário ${w.userId}`);
              await Register.findOneAndUpdate(
                { id: w.userId },
                { $inc: { balance: amountToRefund } }
              );

              // Log de auditoria para o rollback
              await Audit.saveLog({
                id: generateUniqueId(),
                action: AUDIT_ACTIONS.BALANCE_CREDITED || 'BALANCE_CREDITED',
                entity: AUDIT_ENTITIES.WITHDRAW,
                entityId: w.id,
                userId: w.userId,
                dataAfter: {
                  refundedAmount: amountToRefund,
                  reason: 'WITHDRAW_FAILED_REFUND'
                },
                metadata: {
                  source: 'WITHDRAW_POLLER_REFUND',
                  misticData,
                  originalWithdrawValue: w.value
                },
                description: `Saldo devolvido por saque falho: R$ ${(amountToRefund / 100).toFixed(2)}`
              });

              console.log(`✅ Saldo devolvido com sucesso para saque ${w.id}`);
            }
          } catch (refundError) {
            console.error(`❌ Erro ao devolver saldo do saque ${w.id}:`, refundError.message);
          }
        }

        // Para COMPLETED (e casos não-FAILED), atualizar status normalmente
        if (newStatus !== 'FAILED') {
          await Withdraw.findOneAndUpdate(
            { id: w.id },
            {
              $set: {
                status: newStatus,
                completedAt: newStatus === 'COMPLETED' ? now.toISOString() : w.completedAt || null,
                metadata: { ...(w.metadata || {}), misticData },
                updatedAt: now,
              },
            }
          );
        }

        const user = await Register.getById(w.userId);
        await Audit.saveLog({
          id: generateUniqueId(),
          action: newStatus === 'COMPLETED' ? AUDIT_ACTIONS.WITHDRAW_COMPLETED : AUDIT_ACTIONS.WITHDRAW_UPDATED,
          entity: AUDIT_ENTITIES.WITHDRAW,
          entityId: w.id,
          userId: w.userId,
          userEmail: user?.email || null,
          dataBefore: { status: w.status },
          dataAfter: { status: newStatus },
          metadata: { source: 'WITHDRAW_POLLER', misticData },
          description:
            newStatus === 'COMPLETED'
              ? `Saque ${w.id} marcado como COMPLETED pelo poller`
              : newStatus === 'FAILED'
                ? `Saque ${w.id} marcado como FAILED pelo poller (saldo devolvido)`
                : `Saque ${w.id} atualizado para ${newStatus} pelo poller`,
        });

        // Webhook
        if (newStatus === 'COMPLETED') {
          await sendWebhookEvent(w.userId, 'withdrawal.completed', {
            id: w.id,
            amount: (w.value / 100).toFixed(2),
            status: 'completed',
            createdAt: w.createdAt ? new Date(w.createdAt).getTime() : Date.now(),
            completedAt: Date.now(),
          });

          // Enviar push notification de saque completado
          try {
            await notifyWithdrawCompleted(w.userId, w.value, w.id);
          } catch (pushError) {
            console.warn(`[Push] Erro ao enviar notificação de saque completado:`, pushError.message);
          }
        } else if (newStatus === 'FAILED') {
          await sendWebhookEvent(w.userId, 'withdrawal.failed', {
            id: w.id,
            amount: (w.value / 100).toFixed(2),
            status: 'failed',
            refunded: true,
            createdAt: w.createdAt ? new Date(w.createdAt).getTime() : Date.now(),
            failedAt: Date.now(),
            reason: misticData?.failureReason || null,
          });

          // Enviar push notification de saque falho
          try {
            await notifyWithdrawFailed(w.userId, w.value, w.id, misticData?.failureReason);
          } catch (pushError) {
            console.warn(`[Push] Erro ao enviar notificação de saque falho:`, pushError.message);
          }
        }

        updated++;
      }
    } catch (err) {
      errors++;
      console.error(`❌ Erro ao verificar saque ${w.id}:`, err.message || err);
    }
  }

  return { updated, errors };
}

export async function checkPendingWithdraws() {
  try {
    const pending = await Withdraw.getPending(['PENDING', 'WAITING', 'CREATED', 'PROCESSING', 'QUEUED']);
    if (!pending.length) {
      return { checked: 0, updated: 0, errors: 0 };
    }

    const BATCH_SIZE = 5;
    const BATCH_DELAY = 5000; // 5s
    let totalUpdated = 0;
    let totalErrors = 0;

    for (let i = 0; i < pending.length; i += BATCH_SIZE) {
      const batch = pending.slice(i, i + BATCH_SIZE);
      const result = await processWithdrawBatch(batch);
      totalUpdated += result.updated;
      totalErrors += result.errors;
      if (i + BATCH_SIZE < pending.length) {
        await new Promise((r) => setTimeout(r, BATCH_DELAY));
      }
    }

    console.log(`✅ Withdraw poller: ${totalUpdated} atualizado(s), ${totalErrors} erro(s)`);
    return { checked: pending.length, updated: totalUpdated, errors: totalErrors };
  } catch (error) {
    console.error('❌ Erro no poller de saques:', error.message || error);
  }
}

export function startWithdrawPoller(intervalMs = 30000) {
  console.log(`🚀 Iniciando poller de saques (intervalo ${intervalMs / 1000}s)`);
  // Execução imediata
  checkPendingWithdraws().catch((e) => console.error('Erro execução inicial withdraw poller:', e.message));
  // Agendado
  const interval = setInterval(() => {
    checkPendingWithdraws().catch((e) => console.error('Erro no withdraw poller:', e.message));
  }, intervalMs);
  return interval;
}

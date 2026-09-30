import webpush from 'web-push';
import PushSubscription from '../database/models/PushSubscription.js';

// Configurar VAPID keys (gerar com npx web-push generate-vapid-keys)
const VAPID_PUBLIC_KEY = process.env.VAPID_PUBLIC_KEY || '';
const VAPID_PRIVATE_KEY = process.env.VAPID_PRIVATE_KEY || '';
const VAPID_SUBJECT = process.env.VAPID_SUBJECT || 'mailto:suporte@visionwallet.com.br';

// Configurar web-push apenas se as chaves estiverem disponíveis
if (VAPID_PUBLIC_KEY && VAPID_PRIVATE_KEY) {
    webpush.setVapidDetails(VAPID_SUBJECT, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY);
    console.log('✅ Web Push configurado com sucesso');
} else {
    console.warn('⚠️ VAPID keys não configuradas. Push notifications desabilitadas.');
}

/**
 * Envia uma notificação push para um usuário específico
 * @param {string} userId - ID do usuário
 * @param {object} notification - { title, body, icon, tag, data, url }
 */
export async function sendPushToUser(userId, notification) {
    if (!VAPID_PUBLIC_KEY || !VAPID_PRIVATE_KEY) {
        console.warn('[Push] VAPID keys não configuradas, pulando notificação');
        return { success: false, reason: 'VAPID_NOT_CONFIGURED' };
    }

    try {
        const subscriptions = await PushSubscription.getByUserId(userId);

        if (!subscriptions || subscriptions.length === 0) {
            console.log(`[Push] Nenhuma subscription encontrada para usuário ${userId}`);
            return { success: false, reason: 'NO_SUBSCRIPTIONS' };
        }

        const payload = JSON.stringify({
            title: notification.title || 'Amethys Wallet',
            body: notification.body || '',
            icon: notification.icon || '/app.png',
            badge: notification.badge || '/badge.svg',
            tag: notification.tag || 'vision-notification',
            requireInteraction: notification.requireInteraction ?? true,
            data: {
                url: notification.url || '/dashboard',
                ...notification.data
            }
        });

        const results = await Promise.allSettled(
            subscriptions.map(async (sub) => {
                try {
                    await webpush.sendNotification(
                        {
                            endpoint: sub.endpoint,
                            keys: sub.keys
                        },
                        payload
                    );

                    // Atualizar lastUsed
                    await PushSubscription.findOneAndUpdate(
                        { id: sub.id },
                        { $set: { lastUsed: new Date() } }
                    );

                    return { success: true, subscriptionId: sub.id };
                } catch (error) {
                    // Se a subscription expirou ou foi removida, desativar
                    if (error.statusCode === 404 || error.statusCode === 410) {
                        console.log(`[Push] Subscription expirada, desativando: ${sub.id}`);
                        await PushSubscription.deactivate(sub.endpoint);
                    }
                    throw error;
                }
            })
        );

        const successful = results.filter(r => r.status === 'fulfilled').length;
        const failed = results.filter(r => r.status === 'rejected').length;

        console.log(`[Push] Enviado para ${userId}: ${successful} sucesso, ${failed} falhas`);
        return { success: successful > 0, sent: successful, failed };

    } catch (error) {
        console.error('[Push] Erro ao enviar notificação:', error.message);
        return { success: false, error: error.message };
    }
}

/**
 * Notifica sobre pagamento recebido
 */
export async function notifyPaymentReceived(userId, amount, paymentId) {
    const formattedAmount = `R$ ${(amount / 100).toFixed(2).replace('.', ',')}`;

    return sendPushToUser(userId, {
        title: 'Pagamento Recebido! 💰',
        body: `Você recebeu ${formattedAmount}`,
        tag: `payment-${paymentId}`,
        url: '/dashboard/transactions',
        data: {
            type: 'payment',
            paymentId,
            amount
        }
    });
}

/**
 * Notifica sobre saque completado
 */
export async function notifyWithdrawCompleted(userId, amount, withdrawId) {
    const formattedAmount = `R$ ${(amount / 100).toFixed(2).replace('.', ',')}`;

    return sendPushToUser(userId, {
        title: 'Transferência Realizada! 💸',
        body: `Sua transferência de ${formattedAmount} foi concluída`,
        tag: `withdraw-${withdrawId}`,
        url: '/dashboard/transactions',
        data: {
            type: 'withdraw',
            withdrawId,
            amount
        }
    });
}

/**
 * Notifica sobre saque falho (com saldo devolvido)
 */
export async function notifyWithdrawFailed(userId, amount, withdrawId, reason) {
    const formattedAmount = `R$ ${(amount / 100).toFixed(2).replace('.', ',')}`;

    return sendPushToUser(userId, {
        title: 'Transferência Falhou! 🚫',
        body: `Sua transferência de ${formattedAmount} falhou. Saldo devolvido.`,
        tag: `withdraw-failed-${withdrawId}`,
        url: '/dashboard/transactions',
        data: {
            type: 'withdraw_failed',
            withdrawId,
            amount,
            reason
        }
    });
}

/**
 * Retorna a chave pública VAPID para o frontend
 */
export function getVapidPublicKey() {
    return VAPID_PUBLIC_KEY;
}

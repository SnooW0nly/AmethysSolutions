import Payment from '../database/models/Payment.js';

// ================== CONFIGURAÇÕES ==================
const EXPIRATION_MINUTES = 30; // Expirar pagamentos após 30 minutos
// ====================================================

/**
 * Expira pagamentos pendentes há mais de 30 minutos
 */
async function expireOldPayments() {
    try {
        const now = new Date();
        const expirationTime = new Date(now.getTime() - EXPIRATION_MINUTES * 60 * 1000);

        const expireResult = await Payment.updateMany(
            {
                status: { $in: ['PENDING', 'ACTIVE'] },
                createdAt: { $lt: expirationTime }
            },
            {
                $set: {
                    status: 'EXPIRED',
                    'metadata.expiredAt': now.toISOString(),
                    'metadata.expirationReason': `Pagamento não aprovado após ${EXPIRATION_MINUTES} minutos`,
                    updatedAt: now
                }
            }
        );

        if (expireResult.modifiedCount > 0) {
            console.log(`⏰ ${expireResult.modifiedCount} pagamento(s) expirado(s) (>${EXPIRATION_MINUTES} min)`);
        }

        return { expired: expireResult.modifiedCount };
    } catch (error) {
        console.error('❌ Erro ao expirar pagamentos:', error.message);
        return { expired: 0 };
    }
}

/**
 * Executa expiração de pagamentos
 */
export async function runPaymentExpiration() {
    try {
        return await expireOldPayments();
    } catch (error) {
        console.error('❌ Erro na expiração de pagamentos:', error.message);
        return { expired: 0 };
    }
}

/**
 * Inicia o scheduler de expiração de pagamentos
 * Roda a cada 1 minuto para expirar pagamentos antigos
 */
export function startPaymentExpirationScheduler(intervalMs = 60000) { // 1 minuto padrão
    console.log(`⏰ Payment Expiration Scheduler iniciado`);
    console.log(`   - Intervalo: ${intervalMs / 1000}s`);
    console.log(`   - Expira pagamentos pendentes > ${EXPIRATION_MINUTES} minutos`);

    // Executar imediatamente
    runPaymentExpiration();

    // Executar periodicamente
    return setInterval(() => {
        runPaymentExpiration().catch(err => {
            console.error('❌ Erro no expiration scheduler:', err.message);
        });
    }, intervalMs);
}

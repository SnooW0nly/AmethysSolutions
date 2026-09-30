import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Payment from '../../../../database/models/Payment.js';
import Withdraw from '../../../../database/models/Withdraw.js';
import InternalTransfer from '../../../../database/models/InternalTransfer.js';

const router = express.Router();

/**
 * GET /api/v1/user/transactions - Lista todas as transações do usuário
 * Combina pagamentos, saques e transferências internas
 */
router.get('/', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
    try {
        const user = req.user;
        const { page = 1, limit = 50, type, status } = req.query;

        const parsedPage = parseInt(page);
        const parsedLimit = Math.min(parseInt(limit), 1000);
        const offset = (parsedPage - 1) * parsedLimit;

        const allTransactions = [];

        // Buscar pagamentos
        let payments = await Payment.getByUser(user.id);
        if (status) {
            payments = payments.filter(p => p.status === status.toUpperCase());
        }
        payments.forEach(p => {
            const isCommission = p.metadata?.type === 'commission';
            allTransactions.push({
                id: p.id,
                type: 'income',
                transactionType: isCommission ? 'commission' : 'payment',
                date: p.createdAt,
                amount: p.netValue || p.value,
                status: p.status,
                description: isCommission ? 'Comissão de Afiliado' : (p.description || 'Pagamento recebido'),
                originalData: p
            });
        });

        // Buscar saques
        let withdraws = await Withdraw.getByUserId(user.id);
        if (status) {
            withdraws = withdraws.filter(w => w.status === status.toUpperCase());
        }
        withdraws.forEach(w => {
            allTransactions.push({
                id: w.id,
                type: 'expense',
                transactionType: 'withdraw',
                date: w.createdAt,
                amount: w.value,
                status: w.status,
                description: w.description || 'Transferência realizada',
                originalData: w
            });
        });

        // Buscar transferências internas (enviadas e recebidas)
        try {
            const [sent, received] = await Promise.all([
                InternalTransfer.getBySenderId(user.id),
                InternalTransfer.getByRecipientId(user.id)
            ]);

            // Transferências enviadas
            sent.forEach(t => {
                if (!status || t.status === status.toUpperCase()) {
                    allTransactions.push({
                        id: t.id,
                        type: 'expense',
                        transactionType: 'internal_transfer_sent',
                        date: t.createdAt,
                        amount: t.amount,
                        status: t.status,
                        description: t.description || 'Transferência interna enviada',
                        originalData: t
                    });
                }
            });

            // Transferências recebidas
            received.forEach(t => {
                if (!status || t.status === status.toUpperCase()) {
                    allTransactions.push({
                        id: t.id,
                        type: 'income',
                        transactionType: 'internal_transfer_received',
                        date: t.createdAt,
                        amount: t.amount,
                        status: t.status,
                        description: t.description || 'Transferência interna recebida',
                        originalData: t
                    });
                }
            });
        } catch (e) {
            console.log('[Transactions] InternalTransfer error:', e.message);
        }

        // Filtrar por tipo
        let filtered = allTransactions;
        if (type === 'income') {
            filtered = filtered.filter(t => t.type === 'income');
        } else if (type === 'expense') {
            filtered = filtered.filter(t => t.type === 'expense');
        }

        // Ordenar por data (mais recente primeiro)
        filtered.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

        // Paginar
        const total = filtered.length;
        const paginatedTransactions = filtered.slice(offset, offset + parsedLimit);

        res.json({
            success: true,
            data: {
                transactions: paginatedTransactions.map(t => ({
                    id: t.id,
                    type: t.type,
                    transactionType: t.transactionType,
                    date: t.date,
                    amount: t.amount,
                    status: t.status,
                    description: t.description
                })),
                pagination: {
                    total,
                    page: parsedPage,
                    limit: parsedLimit,
                    totalPages: Math.ceil(total / parsedLimit),
                    hasMore: offset + parsedLimit < total
                }
            }
        });

    } catch (error) {
        console.error('Erro ao listar transações:', error);
        res.status(500).json({
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

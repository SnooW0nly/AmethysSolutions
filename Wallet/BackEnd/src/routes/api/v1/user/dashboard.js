import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Payment from '../../../../database/models/Payment.js';
import Withdraw from '../../../../database/models/Withdraw.js';
import InternalTransfer from '../../../../database/models/InternalTransfer.js';
import SplitPayment from '../../../../database/models/SplitPayment.js';
import Register from '../../../../database/models/Register.js';
import { getCategoryDisplay, getFeeDisplay, calculateFee } from '../../../../services/categoryService.js';

const router = express.Router();

/**
 * GET /api/v1/user/dashboard - Optimized combined dashboard endpoint
 * Returns all data needed for dashboard in a single request
 */
router.get('/', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
    try {
        const user = req.user;
        const userId = user.id;

        // Execute all queries in parallel for maximum performance
        const [
            // Recent payments (only last 20, with limit at DB level)
            recentPayments,
            // Recent withdraws (only last 20, with limit at DB level)
            recentWithdraws,
            // Payment stats using aggregation
            paymentStats,
            // Withdraw stats count
            completedWithdrawsCount,
            // Internal transfers (sent and received, last 20 each)
            recentTransfersSent,
            recentTransfersReceived,
            // Splits received
            recentSplitsReceived
        ] = await Promise.all([
            Payment.find({ userId }).sort({ createdAt: -1 }).limit(20).lean(),
            Withdraw.find({ userId, status: { $ne: 'DELETED' } }).sort({ createdAt: -1 }).limit(20).lean(),
            Payment.aggregate([
                { $match: { userId } },
                {
                    $group: {
                        _id: null,
                        total: { $sum: 1 },
                        completedCount: {
                            $sum: { $cond: [{ $in: ['$status', ['COMPLETED', 'PAID']] }, 1, 0] }
                        },
                        pendingCount: {
                            $sum: { $cond: [{ $in: ['$status', ['ACTIVE', 'PENDING']] }, 1, 0] }
                        },
                        totalReceived: {
                            $sum: {
                                $cond: [
                                    { $in: ['$status', ['COMPLETED', 'PAID']] },
                                    { $ifNull: ['$netValue', '$value'] },
                                    0
                                ]
                            }
                        },
                        totalFees: {
                            $sum: {
                                $cond: [
                                    { $in: ['$status', ['COMPLETED', 'PAID']] },
                                    { $ifNull: ['$fee', 0] },
                                    0
                                ]
                            }
                        },
                        pendingValue: {
                            $sum: {
                                $cond: [
                                    { $in: ['$status', ['ACTIVE', 'PENDING']] },
                                    '$value',
                                    0
                                ]
                            }
                        }
                    }
                }
            ]),
            Withdraw.countDocuments({ userId, status: 'COMPLETED' }),
            InternalTransfer.find({ senderId: userId }).sort({ createdAt: -1 }).limit(10).lean(),
            InternalTransfer.find({ recipientId: userId }).sort({ createdAt: -1 }).limit(10).lean(),
            SplitPayment.find({ recipientId: userId, status: 'COMPLETED' }).sort({ createdAt: -1 }).limit(10).lean()
        ]);

        // Process payment stats
        const stats = paymentStats[0] || {
            total: 0,
            completedCount: 0,
            pendingCount: 0,
            totalReceived: 0,
            totalFees: 0,
            pendingValue: 0
        };

        // Count internal transfers completed
        const completedInternalTransfersCount = await InternalTransfer.countDocuments({
            $or: [{ senderId: userId }, { recipientId: userId }],
            status: 'COMPLETED'
        });

        const balance = user.balance || 0;

        // Determinar taxas baseado na categoria
        const category = user.category || 'WHITE';
        const tier = user.tier || 1;

        const feeFixed = await calculateFee(category, tier, 0);
        let feePercent = 0;
        if (category === 'BLACK') {
          const blackPlan = await (await import('../../../../database/models/Plan.js')).default.findOne({ id: 'BLACK', active: true });
          feePercent = blackPlan?.transactionFeePercent ?? 6;
        }

        const transactionFeeDisplay = await getFeeDisplay(category, tier);
        const planName = getCategoryDisplay(category, tier);

        // Build recent transactions list (combined and sorted)
        const recentTransactions = [];

        // Add payments
        recentPayments.slice(0, 5).forEach(p => {
            recentTransactions.push({
                id: p.id,
                type: 'income',
                transactionType: (p.metadata?.type === 'commission') ? 'commission' : 'payment',
                date: p.createdAt,
                amount: p.netValue || p.value,
                status: p.status,
                description: p.description || 'Pagamento recebido'
            });
        });

        // Add withdraws
        recentWithdraws.slice(0, 5).forEach(w => {
            recentTransactions.push({
                id: w.id,
                type: 'expense',
                transactionType: 'withdraw',
                date: w.createdAt,
                amount: w.value,
                status: w.status,
                description: w.description || 'Saque realizado'
            });
        });

        // Add internal transfers
        recentTransfersSent.slice(0, 5).forEach(t => {
            recentTransactions.push({
                id: t.id,
                type: 'expense',
                transactionType: 'internal_transfer_sent',
                date: t.createdAt,
                amount: t.amount,
                status: t.status,
                description: t.description || 'Transferência enviada'
            });
        });

        recentTransfersReceived.slice(0, 5).forEach(t => {
            recentTransactions.push({
                id: t.id,
                type: 'income',
                transactionType: 'internal_transfer_received',
                date: t.createdAt,
                amount: t.amount,
                status: t.status,
                description: t.description || 'Transferência recebida'
            });
        });

        // Add splits received
        recentSplitsReceived.slice(0, 5).forEach(s => {
            recentTransactions.push({
                id: s.id,
                type: 'income',
                transactionType: 'split_received',
                date: s.createdAt,
                amount: s.amount,
                status: s.status,
                description: `Split recebido de ${s.senderEmail}`
            });
        });

        // Sort by date and take latest 10
        recentTransactions.sort((a, b) => new Date(b.date) - new Date(a.date));

        res.json({
            success: true,
            data: {
                balance: {
                    total: balance,
                    pendingPayments: stats.pendingValue,
                    totalWithPending: balance + stats.pendingValue,
                    isNegative: balance < 0
                },
                statistics: {
                    totalReceived: stats.totalReceived,
                    totalFees: stats.totalFees,
                    completedPayments: stats.completedCount,
                    pendingPayments: stats.pendingCount,
                    totalPayments: stats.total,
                    totalCompletedTransactions: stats.completedCount + completedWithdrawsCount + completedInternalTransfersCount
                },
                limits: {
                    daily: user.limits?.daily || 0,
                    dailyUsed: user.dailyUsed || 0,
                    dailyRemaining: Math.max(0, (user.limits?.daily || 0) - (user.dailyUsed || 0)),
                    monthly: user.limits?.monthly || 0,
                    monthlyUsed: user.monthlyUsed || 0,
                    monthlyRemaining: Math.max(0, (user.limits?.monthly || 0) - (user.monthlyUsed || 0)),
                    perTransaction: user.limits?.perTransaction || 0
                },
                plan: {
                    name: planName,
                    transactionFee: feeFixed,
                    transactionFeeInReais: transactionFeeDisplay,
                    isPercentage: category === 'BLACK',
                    transactionFeePercent: feePercent,
                    transactionFeeFixed: feeFixed
                },
                businessProfile: {
                    completed: user.businessProfileCompleted || false,
                    category: user.category || 'WHITE',
                    tier: user.tier || 1,
                    categoryLockedByAdmin: user.categoryLockedByAdmin || false,
                },
                recentPayments: recentPayments.slice(0, 20).map(p => ({
                    id: p.id,
                    correlationID: p.correlationID,
                    value: p.value,
                    netValue: p.netValue || p.value,
                    fee: p.fee,
                    status: p.status,
                    description: p.description,
                    createdAt: p.createdAt,
                    updatedAt: p.updatedAt
                })),
                recentWithdraws: recentWithdraws.slice(0, 20).map(w => ({
                    id: w.id,
                    correlationID: w.correlationID,
                    value: w.value,
                    status: w.status,
                    pixKey: w.pixKey,
                    description: w.description,
                    metadata: w.metadata,
                    createdAt: w.createdAt,
                    updatedAt: w.updatedAt
                })),
                recentTransactions: recentTransactions.slice(0, 50)
            }
        });

    } catch (error) {
        console.error('Erro ao buscar dados do dashboard:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

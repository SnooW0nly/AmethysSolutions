import express from 'express';
import { publicRateLimiter } from '../../../middlewares/apiRateLimiter.js';
import Register from '../../../database/models/Register.js';
import Payment from '../../../database/models/Payment.js';
import Withdraw from '../../../database/models/Withdraw.js';
import InternalTransfer from '../../../database/models/InternalTransfer.js';

const router = express.Router();

// GET /api/v1/public-stats - Public platform statistics (no auth required)
router.get('/', publicRateLimiter, async (req, res) => {
    try {
        // Count active registrations
        const activeRegistrations = await Register.countDocuments({ status: 'active' });

        // Sum completed payments
        const completedPayments = await Payment.aggregate([
            { $match: { status: { $in: ['COMPLETED', 'PAID'] } } },
            { $group: { _id: null, total: { $sum: '$value' } } }
        ]);
        const totalPaymentsValue = completedPayments[0]?.total || 0;

        // Sum completed withdrawals
        const completedWithdraws = await Withdraw.aggregate([
            { $match: { status: 'COMPLETED' } },
            { $group: { _id: null, total: { $sum: { $ifNull: ['$value', '$amount'] } } } }
        ]);
        const totalWithdrawsValue = completedWithdraws[0]?.total || 0;

        // Sum completed internal transfers
        const completedInternalTransfers = await InternalTransfer.aggregate([
            { $match: { status: 'COMPLETED' } },
            { $group: { _id: null, total: { $sum: '$amount' } } }
        ]);
        const totalInternalTransfersValue = completedInternalTransfers[0]?.total || 0;

        // Total money moved (payments + withdrawals + internal transfers)
        const totalMoneyMoved = totalPaymentsValue + totalWithdrawsValue + totalInternalTransfersValue;

        // Count total transactions (completed payments + withdrawals + internal transfers)
        const totalPaymentsCount = await Payment.countDocuments({ status: { $in: ['COMPLETED', 'PAID'] } });
        const totalWithdrawsCount = await Withdraw.countDocuments({ status: 'COMPLETED' });
        const totalInternalTransfersCount = await InternalTransfer.countDocuments({ status: 'COMPLETED' });
        const totalTransactions = totalPaymentsCount + totalWithdrawsCount + totalInternalTransfersCount;

        res.json({
            success: true,
            data: {
                totalMoneyMoved,
                activeRegistrations,
                totalTransactions,
                generatedAt: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Erro ao buscar estatísticas públicas:', error);
        res.status(500).json({
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

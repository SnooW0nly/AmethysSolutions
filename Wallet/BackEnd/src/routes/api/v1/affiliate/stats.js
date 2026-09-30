import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Affiliate from '../../../../database/models/Affiliate.js';
import Register from '../../../../database/models/Register.js';
import Payment from '../../../../database/models/Payment.js';

const router = express.Router();

// GET /api/v1/affiliate/stats - Estatísticas detalhadas do afiliado
router.get('/', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
    try {
        const user = req.user;

        const affiliate = await Affiliate.getByUserId(user.id);
        if (!affiliate) {
            return res.status(404).json({
                error: 'Não é afiliado',
                message: 'Você ainda não está cadastrado como afiliado'
            });
        }

        // Buscar indicados
        const referrals = await Register.find({
            referredBy: affiliate.id,
            status: 'active'
        }).select('id email name createdAt plan').sort({ createdAt: -1 });

        // Calcular estatísticas de transações dos indicados
        let totalTransactions = 0;
        const referralDetails = [];

        for (const referral of referrals) {
            const completedPayments = await Payment.countDocuments({
                userId: referral.id,
                status: { $in: ['COMPLETED', 'PAID'] }
            });

            totalTransactions += completedPayments;

            // Mascarar email para privacidade
            const emailParts = referral.email.split('@');
            const maskedEmail = emailParts[0].slice(0, 3) + '***@' + emailParts[1];

            referralDetails.push({
                id: referral.id,
                email: maskedEmail,
                name: referral.name ? (referral.name.split(' ')[0] + ' ***') : 'Usuário',
                plan: referral.plan,
                createdAt: referral.createdAt,
                transactions: completedPayments,
                earnings: completedPayments * (affiliate.commissionRate || 5) // Usa commissionRate do banco
            });
        }

        // Resumo por período
        const now = new Date();
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

        const referralsLast30Days = referrals.filter(r => new Date(r.createdAt) >= thirtyDaysAgo).length;
        const referralsLast7Days = referrals.filter(r => new Date(r.createdAt) >= sevenDaysAgo).length;

        res.json({
            success: true,
            data: {
                affiliate: {
                    id: affiliate.id,
                    code: affiliate.code,
                    link: `https://visionwallet.com.br/${affiliate.code}`,
                    status: affiliate.status,
                    createdAt: affiliate.createdAt
                },
                stats: {
                    totalReferrals: affiliate.totalReferrals || referrals.length,
                    totalEarnings: affiliate.totalEarnings || 0,
                    totalEarningsInReais: ((affiliate.totalEarnings || 0) / 100).toFixed(2),
                    totalTransactionsFromReferrals: totalTransactions,
                    commissionPerTransaction: affiliate.commissionRate || 5,
                    commissionPerTransactionInReais: `${((affiliate.commissionRate || 5) / 100).toFixed(2)}`,
                    referralsLast7Days,
                    referralsLast30Days
                },
                referrals: referralDetails,
                generatedAt: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('[AFFILIATE] Erro ao buscar estatísticas:', error.message);
        res.status(500).json({
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

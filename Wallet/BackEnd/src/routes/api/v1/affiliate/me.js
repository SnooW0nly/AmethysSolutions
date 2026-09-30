import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Affiliate from '../../../../database/models/Affiliate.js';

const router = express.Router();

// GET /api/v1/affiliate/me - Obter dados do afiliado
router.get('/', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
    try {
        const user = req.user;

        const affiliate = await Affiliate.getByUserId(user.id);

        if (!affiliate) {
            return res.status(404).json({
                error: 'Não é afiliado',
                message: 'Você ainda não está cadastrado como afiliado',
                isAffiliate: false
            });
        }

        res.json({
            success: true,
            isAffiliate: true,
            data: {
                id: affiliate.id,
                code: affiliate.code,
                link: `https://visionwallet.com.br/${affiliate.code}`,
                totalReferrals: affiliate.totalReferrals || 0,
                totalEarnings: affiliate.totalEarnings || 0,
                totalEarningsInReais: ((affiliate.totalEarnings || 0) / 100).toFixed(2),
                commissionPerTransaction: affiliate.commissionRate || 5,
                commissionPerTransactionInReais: `${((affiliate.commissionRate || 5) / 100).toFixed(2)}`,
                status: affiliate.status,
                createdAt: affiliate.createdAt
            }
        });

    } catch (error) {
        console.error('[AFFILIATE] Erro ao buscar dados do afiliado:', error.message);
        res.status(500).json({
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

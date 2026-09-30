import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Payment from '../../../../database/models/Payment.js';
import Register from '../../../../database/models/Register.js';
import { getCategoryDisplay, getFeeDisplay, getWhiteFeeTier, calculateFee } from '../../../../services/categoryService.js';

const router = express.Router();

// GET /api/v1/user/balance - Obtém saldo e extrato do usuário autenticado
// Rate limit: JWT = 60 req/min | API Key = 100 req/min (sem cache para saldo)
router.get('/', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const user = req.user;

    // Buscar pagamentos do usuário para estatísticas (APENAS ENTRADAS - não inclui saques)
    const payments = await Payment.getByUser(user.id);

    const completedPayments = payments.filter(p => p.status === 'COMPLETED' || p.status === 'PAID');
    const pendingPayments = payments.filter(p => p.status === 'ACTIVE' || p.status === 'PENDING');

    // Total recebido: apenas pagamentos completados (entradas), não inclui saques/transferências
    const totalReceived = completedPayments.reduce((sum, p) => sum + (p.netValue || p.value || 0), 0);
    const totalPending = pendingPayments.reduce((sum, p) => sum + (p.value || 0), 0);
    const totalFees = completedPayments.reduce((sum, p) => sum + (p.fee || 0), 0);

    const balance = user.balance || 0;

    // Determinar dados de taxas baseado na categoria
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

    res.json({
      success: true,
      data: {
        balance: {
          total: balance,
          pendingPayments: totalPending,
          totalWithPending: balance + totalPending,
          isNegative: balance < 0
        },
        disputes: {
          total: 0,
          pending: 0,
          totalDisputedAmount: 0,
          totalBlockedAmount: 0
        },
        statistics: {
          totalReceived: totalReceived,
          totalFees: totalFees,
          completedPayments: completedPayments.length,
          pendingPayments: pendingPayments.length,
          totalPayments: payments.length
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
          // Adicionando campos extras para paridade com dashboard
          transactionFeePercent: feePercent,
          transactionFeeFixed: feeFixed,
          isPercentage: category === 'BLACK'
        }
      }
    });

  } catch (error) {
    console.error('Erro ao buscar saldo:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


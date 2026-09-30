import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { getPlan, getSplitFee } from '../../../../services/planService.js';

const router = express.Router();

// GET /api/v1/user/get - Busca dados do próprio usuário
// Rate limit: JWT = 60 req/min | API Key = 100 req/min
router.get('/', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const user = req.user;

    const balance = user.balance || 0;
    
    // Obter informações do plano
    const currentPlan = user.plan || 'FREE';
    const planConfig = await getPlan(currentPlan);
    
    // Calcular dias restantes do plano
    const planEndDate = user.planEndDate ? new Date(user.planEndDate) : null;
    const now = new Date();
    const daysRemaining = planEndDate 
      ? Math.max(0, Math.ceil((planEndDate - now) / (1000 * 60 * 60 * 24)))
      : null;

    // Retornar dados do usuário sem informações sensíveis
    res.json({
      success: true,
      data: {
        id: user.id,
        name: user.name,
        email: user.email,
        taxID: user.taxID,
        phone: user.phone,
        balance: balance,
        blocked: user.blocked,
        status: user.status,
        limits: user.limits,
        dailyUsed: user.dailyUsed || 0,
        monthlyUsed: user.monthlyUsed || 0,
        pixKey: user.pixKey || null,
        pixKeyType: user.pixKeyType || null,
        pixKeyValidated: user.pixKeyValidated || false,
        plan: {
          name: currentPlan,
          transactionFee: planConfig.transactionFee,
          transactionFeeInReais: (planConfig.transactionFee / 100).toFixed(2),
          monthlyFee: planConfig.monthlyFee,
          monthlyFeeInReais: (planConfig.monthlyFee / 100).toFixed(2)
        },
        planDates: {
          startDate: user.planStartDate || null,
          endDate: user.planEndDate || null,
          renewalDate: user.planRenewalDate || null,
          daysRemaining: daysRemaining,
          autoRenew: user.planAutoRenew !== undefined ? user.planAutoRenew : true
        },
        paymentFee: planConfig.transactionFee,
        splitFee: await getSplitFee(currentPlan),
        autoUpgrade: user.autoUpgrade || false,
        monthlyTransactions: user.monthlyTransactions || 0,
        transferSecurityEnabled: user.transferSecurityEnabled || false,
        aiEnabled: user.aiEnabled !== undefined ? user.aiEnabled : true,
        createdAt: user.createdAt,
        updatedAt: user.updatedAt
      }
    });

  } catch (error) {
    console.error('Erro ao buscar usuário:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


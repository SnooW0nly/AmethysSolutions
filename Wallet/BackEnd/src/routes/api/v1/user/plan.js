import express from 'express';
import { authenticateApiKey } from '../../../../middlewares/apiAuth.js';
import { authenticate } from '../../../../middlewares/auth.js';
import { requireAdmin } from '../../../../middlewares/admin.js';
import { defaultApiKeyRateLimiter } from '../../../../middlewares/apiKeyRateLimiter.js';
import { strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import Register from '../../../../database/models/Register.js';
import Payment from '../../../../database/models/Payment.js';
import { getPlan, getAllPlans, PLAN_ORDER, calculatePlanConversion, initializePlanDates, getSplitFee } from '../../../../services/planService.js';
import { checkUserUpgradeEligibility } from '../../../../services/planAnalyzer.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';

const router = express.Router();

// Middleware que tenta autenticar via JWT primeiro, depois via API Key
async function authenticateAdmin(req, res, next) {
  // Se já autenticado, continuar
  if (req.user) {
    return next();
  }

  const token = req.headers.authorization?.replace('Bearer ', '') || req.cookies?.token;
  const apiKey = req.headers['x-api-key'] || (token && token.startsWith('vp_') ? token : null);

  // Tentar autenticar via JWT primeiro (se não for API Key)
  if (token && !apiKey && token.includes('.')) {
    try {
      const { verifyToken } = await import('../../../../services/authService.js');
      const User = (await import('../../../../database/models/User.js')).default;

      const decoded = verifyToken(token);
      if (decoded && decoded.userId) {
        const user = await User.findById(decoded.userId).select('-password');
        if (user) {
          req.user = user;
          return next();
        }
      }
    } catch (error) {
      // Se falhar, tentar API Key
      console.log('[AUTH] Falha ao autenticar via JWT, tentando API Key');
    }
  }

  // Tentar autenticar via API Key
  if (apiKey) {
    try {
      const Register = (await import('../../../../database/models/Register.js')).default;
      const user = await Register.getByApiKey(apiKey);

      if (user && user.status === 'active') {
        req.user = user;
        return next();
      }
    } catch (error) {
      console.error('[AUTH] Erro ao autenticar via API Key:', error);
    }
  }

  // Se nenhum método funcionou, retornar erro
  return res.status(401).json({
    error: 'Não autenticado',
    message: 'É necessário fornecer um token JWT válido ou uma API Key válida'
  });
}

// GET /api/v1/user/plan - Obtém informações do plano atual do usuário (Dashboard/JWT)
router.get('/', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const currentPlan = user.plan || 'FREE';
    const planConfig = await getPlan(currentPlan);

    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    const monthlyTransactions = await Payment.countMonthlyTransactions(user.id, currentYear, currentMonth);

    const upgradeEligibility = await checkUserUpgradeEligibility(user.id);

    const planEndDate = user.planEndDate ? new Date(user.planEndDate) : null;
    const daysRemaining = planEndDate
      ? Math.max(0, Math.ceil((planEndDate - now) / (1000 * 60 * 60 * 24)))
      : null;

    res.json({
      success: true,
      data: {
        currentPlan: {
          name: planConfig.name,
          transactionFee: planConfig.transactionFee,
          transactionFeeInReais: (planConfig.transactionFee / 100).toFixed(2),
          monthlyFee: planConfig.monthlyFee,
          monthlyFeeInReais: (planConfig.monthlyFee / 100).toFixed(2),
          minTransactions: planConfig.minTransactions,
          maxTransactions: planConfig.maxTransactions === Infinity ? null : planConfig.maxTransactions
        },
        planDates: {
          startDate: user.planStartDate || null,
          endDate: user.planEndDate || null,
          renewalDate: user.planRenewalDate || null,
          daysRemaining: daysRemaining,
          autoRenew: user.planAutoRenew !== undefined ? user.planAutoRenew : true
        },
        monthlyTransactions: user.monthlyTransactions || monthlyTransactions,
        autoUpgrade: user.autoUpgrade || false,
        lastPlanCheck: user.lastPlanCheck || null,
        planChangedAt: user.planChangedAt || null,
        upgradeEligibility: upgradeEligibility
      }
    });

  } catch (error) {
    console.error('Erro ao buscar plano do usuário:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// GET /api/v1/user/plan/list - Lista todos os planos disponíveis (pode ser público)
router.get('/list', defaultApiKeyRateLimiter, async (req, res) => {
  try {
    const plans = await getAllPlans();

    res.json({
      success: true,
      data: {
        plans: plans
      }
    });

  } catch (error) {
    console.error('Erro ao listar planos:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// PUT /api/v1/user/plan - Define o plano do usuário (Admin only - JWT)
router.put('/', strictJwtRateLimiter, authenticate, requireAdmin, async (req, res) => {
  try {
    const { userId, plan, autoUpgrade } = req.body;

    if (!userId) {
      return res.status(400).json({
        error: 'Campo obrigatório faltando',
        message: 'O campo "userId" é obrigatório para alterar plano'
      });
    }

    const user = await Register.getById(userId);
    if (!user) {
      return res.status(404).json({
        error: 'Usuário não encontrado',
        message: `Usuário com ID ${userId} não foi encontrado`
      });
    }

    const updates = {};

    if (plan) {
      // Buscar planos válidos do MongoDB
      const allPlans = await getAllPlans();
      const validPlans = allPlans.map(p => p.id);
      const requestedPlan = plan.toUpperCase();

      if (!validPlans.includes(requestedPlan)) {
        return res.status(400).json({
          error: 'Plano inválido',
          message: `O plano deve ser um dos seguintes: ${validPlans.join(', ')}`
        });
      }

      const currentPlan = user.plan || 'FREE';
      const planConfig = await getPlan(requestedPlan);
      const planOrder = await getPlanOrder();
      const currentPlanIndex = planOrder.indexOf(currentPlan);
      const requestedPlanIndex = planOrder.indexOf(requestedPlan);

      if (requestedPlanIndex > currentPlanIndex && planConfig.monthlyFee > 0) {
        const userBalance = user.balance || 0;
        const planEndDate = user.planEndDate || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();
        const conversion = await calculatePlanConversion(currentPlan, requestedPlan, planEndDate);

        if (!conversion.newEndDate || !conversion.planRenewalDate) {
          return res.status(500).json({
            error: 'Erro ao calcular conversão de planos',
            message: 'Não foi possível calcular as datas do novo plano'
          });
        }

        const requiredAmount = Math.max(0, planConfig.monthlyFee - conversion.creditAmount);

        if (userBalance < requiredAmount) {
          const missing = requiredAmount - userBalance;
          return res.status(400).json({
            error: 'Saldo insuficiente',
            message: `Saldo insuficiente para fazer upgrade para o plano ${requestedPlan}`,
            currentBalance: userBalance,
            required: requiredAmount,
            missing: missing,
            creditFromOldPlan: conversion.creditAmount
          });
        }

        if (requiredAmount > 0) {
          try {
            await Register.updateBalance(user.id, requiredAmount, 'subtract');
          } catch (balanceError) {
            return res.status(500).json({
              error: 'Erro ao processar pagamento da mensalidade',
              message: balanceError.message
            });
          }
        }

        updates.plan = requestedPlan;
        updates.paymentFee = planConfig.transactionFee;
        updates.splitFee = await getSplitFee(requestedPlan);
        updates.planStartDate = new Date().toISOString();
        updates.planEndDate = conversion.newEndDate;
        updates.planRenewalDate = conversion.planRenewalDate;
        updates.planChangedAt = new Date().toISOString();
        updates.planChangeReason = 'MANUAL_UPGRADE';
      } else if (requestedPlanIndex > currentPlanIndex && planConfig.monthlyFee === 0) {
        const newDates = initializePlanDates();
        updates.plan = requestedPlan;
        updates.paymentFee = planConfig.transactionFee;
        updates.splitFee = await getSplitFee(requestedPlan);
        updates.planStartDate = newDates.planStartDate;
        updates.planEndDate = newDates.planEndDate;
        updates.planRenewalDate = newDates.planRenewalDate;
        updates.planChangedAt = new Date().toISOString();
        updates.planChangeReason = 'MANUAL_UPGRADE';
      } else if (requestedPlanIndex < currentPlanIndex) {
        const newDates = initializePlanDates();
        updates.plan = requestedPlan;
        updates.paymentFee = planConfig.transactionFee;
        updates.splitFee = await getSplitFee(requestedPlan);
        updates.planStartDate = newDates.planStartDate;
        updates.planEndDate = newDates.planEndDate;
        updates.planRenewalDate = newDates.planRenewalDate;
        updates.planChangedAt = new Date().toISOString();
        updates.planChangeReason = 'MANUAL_DOWNGRADE';
      } else {
        updates.plan = requestedPlan;
        updates.paymentFee = planConfig.transactionFee;
        updates.splitFee = await getSplitFee(requestedPlan);
        updates.planChangedAt = new Date().toISOString();
        updates.planChangeReason = 'MANUAL';
      }
    }

    if (autoUpgrade !== undefined) {
      if (typeof autoUpgrade !== 'boolean') {
        return res.status(400).json({
          error: 'Valor inválido',
          message: 'O campo "autoUpgrade" deve ser true ou false'
        });
      }
      updates.autoUpgrade = autoUpgrade;
    }

    if (Object.keys(updates).length === 0) {
      return res.status(400).json({
        error: 'Nenhuma atualização fornecida',
        message: 'Informe "plan" ou "autoUpgrade" para atualizar'
      });
    }

    const currentPlan = user.plan || 'FREE';
    const planChanged = updates.plan && updates.plan !== currentPlan;
    const autoUpgradeChanged = updates.autoUpgrade !== undefined && updates.autoUpgrade !== user.autoUpgrade;

    const updatedUser = await Register.findOneAndUpdate(
      { id: user.id },
      { $set: updates },
      { new: true }
    );

    const updatedPlanConfig = await getPlan(updatedUser.plan || 'FREE');
    const userWithUpdatedBalance = await Register.getById(user.id);
    const finalBalance = userWithUpdatedBalance?.balance || updatedUser.balance || 0;

    if (planChanged) {
      const action = updates.planChangeReason === 'MANUAL_UPGRADE' ? AUDIT_ACTIONS.PLAN_UPGRADED :
        updates.planChangeReason === 'MANUAL_DOWNGRADE' ? AUDIT_ACTIONS.PLAN_DOWNGRADED :
          AUDIT_ACTIONS.PLAN_CHANGED;

      await Audit.saveLog({
        id: generateUniqueId(),
        action,
        entity: AUDIT_ENTITIES.PLAN,
        entityId: user.id,
        userId: 'ADMIN',
        userEmail: user.email,
        dataBefore: {
          plan: currentPlan,
          paymentFee: user.paymentFee,
          splitFee: user.splitFee,
          planEndDate: user.planEndDate
        },
        dataAfter: {
          plan: updatedUser.plan,
          paymentFee: updatedUser.paymentFee,
          splitFee: updatedUser.splitFee,
          planEndDate: updatedUser.planEndDate
        },
        metadata: {
          reason: updates.planChangeReason,
          conversion: updates.planEndDate ? { newEndDate: updates.planEndDate } : null
        },
        ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
        userAgent: req.headers['user-agent'],
        description: `Plano alterado de ${currentPlan} para ${updatedUser.plan} por ADMIN - ${user.name}`
      });
    }

    if (autoUpgradeChanged) {
      await Audit.saveLog({
        id: generateUniqueId(),
        action: AUDIT_ACTIONS.PLAN_AUTO_UPGRADE_TOGGLED,
        entity: AUDIT_ENTITIES.PLAN,
        entityId: user.id,
        userId: 'ADMIN',
        userEmail: user.email,
        dataBefore: { autoUpgrade: user.autoUpgrade },
        dataAfter: { autoUpgrade: updatedUser.autoUpgrade },
        ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
        userAgent: req.headers['user-agent'],
        description: `Auto-upgrade ${updatedUser.autoUpgrade ? 'ativado' : 'desativado'} por ADMIN - ${user.name}`
      });
    }

    res.json({
      success: true,
      message: 'Plano atualizado com sucesso',
      data: {
        plan: {
          name: updatedPlanConfig.name,
          transactionFee: updatedPlanConfig.transactionFee,
          transactionFeeInReais: (updatedPlanConfig.transactionFee / 100).toFixed(2),
          monthlyFee: updatedPlanConfig.monthlyFee,
          monthlyFeeInReais: (updatedPlanConfig.monthlyFee / 100).toFixed(2)
        },
        autoUpgrade: updatedUser.autoUpgrade || false,
        balance: finalBalance,
        balanceInReais: (finalBalance / 100).toFixed(2),
        updatedAt: updatedUser.updatedAt
      }
    });

  } catch (error) {
    console.error('Erro ao atualizar plano:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


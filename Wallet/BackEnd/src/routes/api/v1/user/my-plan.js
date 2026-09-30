import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { strictSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Register from '../../../../database/models/Register.js';
import { getPlan, getAllPlans, getPlanOrder, calculatePlanConversion, initializePlanDates, getSplitFee, clearPlanCache } from '../../../../services/planService.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';

const router = express.Router();

// GET /api/v1/user/my-plan - Obtém informações do plano atual do usuário
router.get('/', authenticateUser, async (req, res) => {
  try {
    const user = req.user;
    const currentPlan = user.plan || 'FREE';
    const planConfig = await getPlan(currentPlan);

    const planEndDate = user.planEndDate ? new Date(user.planEndDate) : null;
    const now = new Date();
    const daysRemaining = planEndDate
      ? Math.max(0, Math.ceil((planEndDate - now) / (1000 * 60 * 60 * 24)))
      : null;

    // Se autenticado via ApiKey secundária, usar o plano (WHITE/BLACK) da ApiKey
    // para definir a taxa de transação — buscado direto do banco, sem hardcode
    const usedApiKey = req.user.usedApiKey;
    const apiKeyPlan = (usedApiKey && usedApiKey.type === 'secondary')
      ? (usedApiKey.plan || 'WHITE')
      : null;

    let transactionFeePercent = planConfig.transactionFeePercent ?? 0;
    let transactionFeeFixed = planConfig.transactionFeeFixed ?? 0;
    let transactionFeeInReais = planConfig.transactionFeePercent > 0
      ? `${planConfig.transactionFeePercent}% + R$ ${((planConfig.transactionFeeFixed ?? 0) / 100).toFixed(2).replace('.', ',')}`
      : `R$ ${((planConfig.transactionFeeFixed ?? planConfig.transactionFee ?? 0) / 100).toFixed(2).replace('.', ',')}`;

    if (apiKeyPlan) {
      // Busca o plano WHITE ou BLACK do banco — taxa configurada pelo admin, sem hardcode
      const apiKeyPlanConfig = await getPlan(apiKeyPlan);
      transactionFeePercent = apiKeyPlanConfig.transactionFeePercent ?? 0;
      transactionFeeFixed = 0;
      transactionFeeInReais = `${transactionFeePercent}%`;
    }

    res.json({
      success: true,
      data: {
        currentPlan: {
          id: currentPlan,
          name: planConfig.name,
          transactionFeePercent,
          transactionFeeFixed,
          transactionFeeInReais,
          apiKeyPlan: apiKeyPlan || null,
          monthlyFee: planConfig.monthlyFee,
          monthlyFeeInReais: (planConfig.monthlyFee / 100).toFixed(2),
          minTransactions: planConfig.minTransactions,
          maxTransactions: planConfig.maxTransactions === Infinity ? null : planConfig.maxTransactions,
        },
        planDates: {
          startDate: user.planStartDate || null,
          endDate: user.planEndDate || null,
          renewalDate: user.planRenewalDate || null,
          daysRemaining: daysRemaining,
        },
        settings: {
          autoRenew: user.planAutoRenew !== undefined ? user.planAutoRenew : true,
          autoUpgrade: user.autoUpgrade !== undefined ? user.autoUpgrade : false,
          planLockedByAdmin: user.planLockedByAdmin || false,
        },
        balance: user.balance || 0,
        balanceInReais: ((user.balance || 0) / 100).toFixed(2),
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

// GET /api/v1/user/my-plan/available - Lista todos os planos disponíveis
router.get('/available', authenticateUser, async (req, res) => {
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

// PUT /api/v1/user/my-plan/upgrade - Faz upgrade do plano do usuário
// Rate limit: JWT = 30 req/min | API Key = 50 req/min
router.put('/upgrade', strictSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const user = req.user;
    const { plan } = req.body;

    // Verificar se plano está bloqueado por admin
    if (user.planLockedByAdmin) {
      return res.status(403).json({
        error: 'Plano bloqueado',
        message: 'Seu plano foi definido por um administrador e não pode ser alterado'
      });
    }

    if (!plan) {
      return res.status(400).json({
        error: 'Campo obrigatório faltando',
        message: 'O campo "plan" é obrigatório'
      });
    }

    const requestedPlan = plan.toUpperCase();
    const currentPlan = user.plan || 'FREE';

    // Verificar se é realmente um upgrade
    const planOrder = await getPlanOrder();
    const currentPlanIndex = planOrder.indexOf(currentPlan);
    const requestedPlanIndex = planOrder.indexOf(requestedPlan);

    if (requestedPlanIndex <= currentPlanIndex) {
      return res.status(400).json({
        error: 'Operação inválida',
        message: 'Você só pode fazer upgrade para um plano superior'
      });
    }

    const planConfig = await getPlan(requestedPlan);

    // Calcular conversão proporcional
    const planEndDate = user.planEndDate || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();
    const conversion = await calculatePlanConversion(currentPlan, requestedPlan, planEndDate);

    const requiredAmount = Math.max(0, planConfig.monthlyFee - conversion.creditAmount);
    const userBalance = user.balance || 0;

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

    // Debitar do saldo
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

    // Atualizar plano
    const updatedUser = await Register.findOneAndUpdate(
      { id: user.id },
      {
        $set: {
          plan: requestedPlan,
          paymentFee: planConfig.transactionFee,
          splitFee: await getSplitFee(requestedPlan),
          planStartDate: new Date().toISOString(),
          planEndDate: conversion.newEndDate,
          planRenewalDate: conversion.planRenewalDate,
          planChangedAt: new Date().toISOString(),
          planChangeReason: 'USER_UPGRADE'
        }
      },
      { new: true }
    );

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PLAN_UPGRADED,
      entity: AUDIT_ENTITIES.PLAN,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore: {
        plan: currentPlan,
        paymentFee: user.paymentFee,
        splitFee: user.splitFee,
        planEndDate: user.planEndDate,
        balance: userBalance
      },
      dataAfter: {
        plan: requestedPlan,
        paymentFee: updatedUser.paymentFee,
        splitFee: updatedUser.splitFee,
        planEndDate: updatedUser.planEndDate,
        balance: updatedUser.balance
      },
      metadata: {
        reason: 'USER_UPGRADE',
        conversion: {
          creditAmount: conversion.creditAmount,
          requiredAmount: requiredAmount,
          newEndDate: conversion.newEndDate
        }
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Upgrade de plano de ${currentPlan} para ${requestedPlan} pelo próprio usuário`
    });

    // Limpar cache de planos
    clearPlanCache();

    res.json({
      success: true,
      message: `Plano atualizado para ${requestedPlan} com sucesso`,
      data: {
        plan: requestedPlan,
        balance: updatedUser.balance,
        planEndDate: updatedUser.planEndDate,
        creditUsed: conversion.creditAmount,
        amountPaid: requiredAmount
      }
    });

  } catch (error) {
    console.error('Erro ao fazer upgrade do plano:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// PUT /api/v1/user/my-plan/settings - Atualiza configurações do plano (autoRenew, autoUpgrade)
// Rate limit: JWT = 30 req/min | API Key = 50 req/min
router.put('/settings', strictSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const user = req.user;
    const { autoRenew, autoUpgrade } = req.body;

    const updates = {};

    if (autoRenew !== undefined) {
      if (typeof autoRenew !== 'boolean') {
        return res.status(400).json({
          error: 'Valor inválido',
          message: 'O campo "autoRenew" deve ser true ou false'
        });
      }
      updates.planAutoRenew = autoRenew;
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
        message: 'Informe "autoRenew" ou "autoUpgrade" para atualizar'
      });
    }

    const dataBefore = {
      planAutoRenew: user.planAutoRenew !== undefined ? user.planAutoRenew : true,
      autoUpgrade: user.autoUpgrade !== undefined ? user.autoUpgrade : false,
    };

    const updatedUser = await Register.findOneAndUpdate(
      { id: user.id },
      { $set: updates },
      { new: true }
    );

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PLAN_CHANGED,
      entity: AUDIT_ENTITIES.PLAN,
      entityId: user.id,
      userId: user.id,
      userEmail: user.email,
      dataBefore,
      dataAfter: {
        planAutoRenew: updatedUser.planAutoRenew !== undefined ? updatedUser.planAutoRenew : true,
        autoUpgrade: updatedUser.autoUpgrade !== undefined ? updatedUser.autoUpgrade : false,
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Configurações de plano atualizadas pelo usuário`
    });

    res.json({
      success: true,
      message: 'Configurações atualizadas com sucesso',
      data: {
        settings: {
          autoRenew: updatedUser.planAutoRenew !== undefined ? updatedUser.planAutoRenew : true,
          autoUpgrade: updatedUser.autoUpgrade !== undefined ? updatedUser.autoUpgrade : false,
        }
      }
    });

  } catch (error) {
    console.error('Erro ao atualizar configurações do plano:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;
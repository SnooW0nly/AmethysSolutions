/**
 * Rotas de gerenciamento de plano para usuários autenticados via JWT
 * Estas rotas são para o dashboard web, não para a API
 */

import express from 'express';
import { authenticate } from '../middlewares/auth.js';
import { getPlan, getAllPlans, getSplitFee } from '../services/planService.js';
import User from '../database/models/User.js';
import Payment from '../database/models/Payment.js';
import Withdraw from '../database/models/Withdraw.js';
import Register from '../database/models/Register.js';
import InternalTransfer from '../database/models/InternalTransfer.js';

const router = express.Router();

/**
 * GET /auth/plan - Obter informações do plano atual do usuário
 */
router.get('/plan', authenticate, async (req, res) => {
  try {
    const user = req.user;

    // Buscar dados frescos do Register (não usar req.user que pode estar cacheado)
    const register = await Register.findOne({
      email: user.email.toLowerCase(),
      status: 'active'
    });

    if (!register) {
      return res.status(404).json({
        success: false,
        error: 'Registro financeiro não encontrado'
      });
    }

    // Obter informações do plano
    const currentPlan = register.plan || 'FREE';
    const planConfig = await getPlan(currentPlan);

    // Calcular dias restantes do plano
    const planEndDate = register.planEndDate ? new Date(register.planEndDate) : null;
    const now = new Date();
    const daysRemaining = planEndDate
      ? Math.max(0, Math.ceil((planEndDate - now) / (1000 * 60 * 60 * 24)))
      : null;

    res.json({
      success: true,
      data: {
        currentPlan: {
          id: currentPlan,
          name: planConfig.name,
          transactionFeePercent: planConfig.transactionFeePercent ?? 0,
          transactionFeeFixed: planConfig.transactionFeeFixed ?? 0,
          transactionFeeInReais: planConfig.transactionFeePercent > 0
            ? `${planConfig.transactionFeePercent}% + R$ ${((planConfig.transactionFeeFixed ?? 0) / 100).toFixed(2).replace('.', ',')}`
            : `R$ ${((planConfig.transactionFeeFixed ?? planConfig.transactionFee ?? 0) / 100).toFixed(2).replace('.', ',')}`,
          monthlyFee: planConfig.monthlyFee,
          monthlyFeeInReais: (planConfig.monthlyFee / 100).toFixed(2),
          minTransactions: planConfig.minTransactions,
          maxTransactions: planConfig.maxTransactions,
        },
        planDates: {
          startDate: register.planStartDate || null,
          endDate: register.planEndDate || null,
          renewalDate: register.planRenewalDate || null,
          daysRemaining: daysRemaining,
        },
        settings: {
          autoRenew: register.planAutoRenew !== undefined ? register.planAutoRenew : true,
          autoUpgrade: register.autoUpgrade || false,
        },
        balance: register.balance || 0,
        balanceInReais: ((register.balance || 0) / 100).toFixed(2),
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao buscar plano:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/plan/available - Listar planos disponíveis
 */
router.get('/plan/available', authenticate, async (req, res) => {
  try {
    const plans = await getAllPlans();

    // Formatar planos para o frontend (já vem formatado do getAllPlans)
    res.json({
      success: true,
      data: {
        plans: plans
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao buscar planos disponíveis:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * PUT /auth/plan/settings - Atualizar configurações do plano
 */
router.put('/plan/settings', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { autoRenew, autoUpgrade } = req.body;

    // Buscar Register do usuário
    const register = await Register.findOne({
      email: user.email.toLowerCase(),
      status: 'active'
    });

    if (!register) {
      return res.status(404).json({
        success: false,
        error: 'Registro financeiro não encontrado'
      });
    }

    // Atualizar configurações
    if (autoRenew !== undefined) {
      register.planAutoRenew = autoRenew;
    }
    if (autoUpgrade !== undefined) {
      register.autoUpgrade = autoUpgrade;
    }

    await register.save();

    res.json({
      success: true,
      message: 'Configurações atualizadas com sucesso',
      data: {
        settings: {
          autoRenew: register.planAutoRenew,
          autoUpgrade: register.autoUpgrade,
        }
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao atualizar configurações:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * PUT /auth/plan/upgrade - Fazer upgrade do plano
 */
router.put('/plan/upgrade', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { plan } = req.body;

    if (!plan) {
      return res.status(400).json({
        success: false,
        error: 'Plano não especificado'
      });
    }

    // Verificar se o plano existe
    const planConfig = await getPlan(plan);
    if (!planConfig) {
      return res.status(404).json({
        success: false,
        error: 'Plano não encontrado'
      });
    }

    // Buscar Register do usuário (onde está o saldo real e configurações)
    const register = await Register.findOne({
      email: user.email.toLowerCase(),
      status: 'active'
    });

    if (!register) {
      return res.status(404).json({
        success: false,
        error: 'Registro financeiro não encontrado'
      });
    }

    // Calcular custo do upgrade
    const monthlyFee = planConfig.monthlyFee;

    // Verificar se o usuário tem saldo suficiente
    if (register.balance < monthlyFee) {
      return res.status(400).json({
        success: false,
        error: 'Saldo insuficiente para fazer upgrade',
        required: monthlyFee,
        current: register.balance
      });
    }

    // Debitar do saldo
    // Usar Register.updateBalance para garantir atomicidade seria melhor, mas aqui estamos fazendo várias atualizações
    register.balance -= monthlyFee;

    // Atualizar plano
    register.plan = plan;

    // Atualizar taxas no registro
    register.paymentFee = planConfig.transactionFee;
    register.splitFee = await getSplitFee(plan);

    // Atualizar datas
    const now = new Date();
    const startDate = new Date(now);

    const endDate = new Date(now);
    endDate.setDate(endDate.getDate() + 30);

    // Data de renovação (um dia útil antes se possível, ou igual a endDate)
    // Usando mesma logica simples por enquanto
    const renewalDate = new Date(endDate);

    register.planStartDate = startDate.toISOString();
    register.planEndDate = endDate.toISOString();
    register.planRenewalDate = renewalDate.toISOString();

    // Registrar mudança
    register.planChangedAt = now.toISOString();
    register.planChangeReason = `Upgrade para ${plan} via dashboard`;

    await register.save();

    res.json({
      success: true,
      message: 'Upgrade realizado com sucesso',
      data: {
        plan: register.plan,
        balance: register.balance,
        planEndDate: register.planEndDate,
        creditUsed: 0,
        amountPaid: monthlyFee,
        paymentFee: register.paymentFee,
        splitFee: register.splitFee
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao fazer upgrade:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/balance - Obter saldo e estatísticas do usuário
 */
router.get('/balance', authenticate, async (req, res) => {
  try {
    const user = req.user;

    // Buscar Register correspondente para obter estatísticas completas
    let userId = user._id.toString();
    let register = null;

    try {
      const Register = (await import('../database/models/Register.js')).default;
      register = await Register.findOne({
        email: user.email.toLowerCase(),
        status: 'active'
      });

      if (register) {
        userId = register.id;
      }
    } catch (registerError) {
      // Se não encontrar Register, continuar com dados do User
      console.log('[AUTH BALANCE] Register não encontrado, usando dados do User');
    }

    // Buscar pagamentos para calcular estatísticas
    const Payment = (await import('../database/models/Payment.js')).default;
    const allPayments = await Payment.getByUser(userId);

    // Calcular estatísticas baseadas nos pagamentos
    const completedPayments = allPayments.filter(p =>
      p.status === 'COMPLETED' || p.status === 'PAID'
    );
    const pendingPayments = allPayments.filter(p =>
      p.status === 'PENDING' || p.status === 'ACTIVE'
    );

    // totalReceived: soma de TODOS os valores recebidos (pagamentos completados)
    // Isso inclui valores que já foram sacados, pois é o total que entrou na conta
    const totalReceived = completedPayments.reduce((sum, p) => sum + (p.value || 0), 0);
    const totalFees = completedPayments.reduce((sum, p) => sum + (p.fee || 0), 0);
    const pendingPaymentsValue = pendingPayments.reduce((sum, p) => sum + (p.value || 0), 0);

    const userData = register || user;
    const balance = userData.balance || 0;

    let balanceData = {
      balance: {
        total: balance,
        pendingPayments: pendingPaymentsValue,
        totalWithPending: balance + pendingPaymentsValue,
        isNegative: balance < 0,
      },
      disputes: {
        total: 0,
        pending: 0,
        totalDisputedAmount: 0,
        totalBlockedAmount: 0,
      },
      statistics: {
        totalReceived: totalReceived,
        totalFees: totalFees,
        completedPayments: completedPayments.length,
        pendingPayments: pendingPayments.length,
        totalPayments: allPayments.length,
        // Novos contadores de transações
        totalCompletedTransactions: 0 // Será preenchido abaixo
      },
      limits: {
        daily: userData.limits?.daily || 0,
        dailyUsed: userData.dailyUsed || 0,
        dailyRemaining: Math.max(0, (userData.limits?.daily || 0) - (userData.dailyUsed || 0)),
        monthly: userData.limits?.monthly || 0,
        monthlyUsed: userData.monthlyUsed || 0,
        monthlyRemaining: Math.max(0, (userData.limits?.monthly || 0) - (userData.monthlyUsed || 0)),
        perTransaction: userData.limits?.perTransaction || 0,
      },
      plan: null,
    };

    // Calcular total de transações completadas (Pagamentos + Saques + Transferências Internas)
    // Já temos completedPayments.length

    // Contar Saques Completados
    const Withdraw = (await import('../database/models/Withdraw.js')).default;
    const completedWithdrawsCount = await Withdraw.countDocuments({
      userId: userId,
      status: 'COMPLETED'
    });

    // Contar Transferências Internas (Enviadas e Recebidas)
    const InternalTransfer = (await import('../database/models/InternalTransfer.js')).default;
    const completedInternalTransfersCount = await InternalTransfer.countDocuments({
      $or: [{ senderId: userId }, { recipientId: userId }],
      status: 'COMPLETED'
    });

    balanceData.statistics.totalCompletedTransactions = completedPayments.length + completedWithdrawsCount + completedInternalTransfersCount;

    // Obter informações do plano usando dados do Register (frescos do banco)
    const currentPlan = register?.plan || user.plan || 'FREE';
    const planConfig = await getPlan(currentPlan);

    // Usar dados do plano (não o paymentFee salvo que pode estar desatualizado)
    const feePercent = planConfig.transactionFeePercent ?? 0;
    const feeFixed = planConfig.transactionFeeFixed ?? 0;

    balanceData.plan = {
      name: planConfig.name,
      transactionFeePercent: feePercent,
      transactionFeeFixed: feeFixed,
      transactionFeeInReais: feePercent > 0
        ? `${feePercent}% + R$ ${(feeFixed / 100).toFixed(2).replace('.', ',')}`
        : `R$ ${((planConfig.transactionFeeFixed ?? planConfig.transactionFee ?? 0) / 100).toFixed(2).replace('.', ',')}`,
    };

    res.json({
      success: true,
      data: balanceData
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao buscar saldo:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/payments - Listar pagamentos do usuário
 */
router.get('/payments', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { status, limit = 50, offset = 0 } = req.query;

    // Tentar buscar Register para obter o ID correto
    let userId = user._id.toString();
    try {
      const register = await Register.findOne({
        email: user.email.toLowerCase(),
        status: 'active'
      });
      if (register) {
        userId = register.id;
      }
    } catch (registerError) {
      // Se não encontrar Register, usar User ID
    }

    // Buscar pagamentos
    let payments = await Payment.getByUser(userId);

    if (status) {
      payments = payments.filter(p => p.status === status.toUpperCase());
    }

    payments.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    const total = payments.length;
    const paginatedPayments = payments.slice(parseInt(offset), parseInt(offset) + parseInt(limit));

    const stats = {
      total: payments.length,
      completed: payments.filter(p => p.status === 'COMPLETED' || p.status === 'PAID').length,
      pending: payments.filter(p => p.status === 'PENDING' || p.status === 'ACTIVE').length,
      totalValue: payments.reduce((sum, p) => sum + (p.value || 0), 0),
      totalNetValue: payments.reduce((sum, p) => sum + (p.netValue || p.value || 0), 0)
    };

    res.json({
      success: true,
      data: {
        payments: paginatedPayments.map(p => ({
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
        pagination: {
          total,
          limit: parseInt(limit),
          offset: parseInt(offset),
          hasMore: (parseInt(offset) + parseInt(limit)) < total
        },
        statistics: stats
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao listar pagamentos:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/withdraws - Listar saques do usuário
 */
router.get('/withdraws', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { status, limit = 50, offset = 0 } = req.query;

    // Tentar buscar Register para obter o ID correto
    let userId = user._id.toString();
    try {
      const register = await Register.findOne({
        email: user.email.toLowerCase(),
        status: 'active'
      });
      if (register) {
        userId = register.id;
      }
    } catch (registerError) {
      // Se não encontrar Register, usar User ID
    }

    // Buscar saques
    let withdraws = await Withdraw.getByUserId(userId);

    if (status) {
      withdraws = withdraws.filter(w => w.status === status.toUpperCase());
    }

    withdraws.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    const total = withdraws.length;
    const paginatedWithdraws = withdraws.slice(parseInt(offset), parseInt(offset) + parseInt(limit));

    const stats = {
      total: withdraws.length,
      completed: withdraws.filter(w => w.status === 'COMPLETED').length,
      pending: withdraws.filter(w => ['PENDING', 'PROCESSING', 'WAITING'].includes(w.status)).length,
      failed: withdraws.filter(w => w.status === 'FAILED').length,
      totalValue: withdraws.reduce((sum, w) => sum + (w.value || 0), 0)
    };

    res.json({
      success: true,
      data: {
        withdraws: paginatedWithdraws.map(w => ({
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
        pagination: {
          total,
          limit: parseInt(limit),
          offset: parseInt(offset),
          hasMore: (parseInt(offset) + parseInt(limit)) < total
        },
        statistics: stats
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao listar saques:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/user - Obter dados do usuário
 */
router.get('/user', authenticate, async (req, res) => {
  try {
    const user = req.user;

    // Tentar buscar Register para dados mais completos
    let register = null;
    try {
      register = await Register.findOne({
        email: user.email.toLowerCase(),
        status: 'active'
      });
    } catch (registerError) {
      // Se não encontrar Register, continuar com User
    }

    const userData = register || user;
    const balance = userData.balance || 0;

    // Obter informações do plano
    const currentPlan = userData.plan || 'FREE';
    const planConfig = await getPlan(currentPlan);

    // Calcular dias restantes do plano
    const planEndDate = userData.planEndDate ? new Date(userData.planEndDate) : null;
    const now = new Date();
    const daysRemaining = planEndDate
      ? Math.max(0, Math.ceil((planEndDate - now) / (1000 * 60 * 60 * 24)))
      : null;

    res.json({
      success: true,
      data: {
        id: userData.id || userData._id.toString(),
        name: userData.name,
        email: userData.email,
        taxID: userData.taxID || null,
        phone: userData.phone || null,
        balance: balance,
        blocked: userData.blocked || false,
        status: userData.status || 'active',
        limits: userData.limits || {},
        dailyUsed: userData.dailyUsed || 0,
        monthlyUsed: userData.monthlyUsed || 0,
        pixKey: userData.pixKey || null,
        pixKeyType: userData.pixKeyType || null,
        pixKeyValidated: userData.pixKeyValidated || false,
        plan: {
          name: currentPlan,
          transactionFeePercent: planConfig.transactionFeePercent ?? 0,
          transactionFeeFixed: planConfig.transactionFeeFixed ?? 0,
          transactionFeeInReais: planConfig.transactionFeePercent > 0
            ? `${planConfig.transactionFeePercent}% + R$ ${((planConfig.transactionFeeFixed ?? 0) / 100).toFixed(2).replace('.', ',')}`
            : `R$ ${((planConfig.transactionFeeFixed ?? planConfig.transactionFee ?? 0) / 100).toFixed(2).replace('.', ',')}`,
          monthlyFee: planConfig.monthlyFee,
          monthlyFeeInReais: (planConfig.monthlyFee / 100).toFixed(2)
        },
        planDates: {
          startDate: userData.planStartDate || null,
          endDate: userData.planEndDate || null,
          renewalDate: userData.planRenewalDate || null,
          daysRemaining: daysRemaining,
          autoRenew: userData.planAutoRenew !== undefined ? userData.planAutoRenew : true
        },
        paymentFee: userData.paymentFee || planConfig.transactionFee,
        splitFee: userData.splitFee || await getSplitFee(currentPlan),
        autoUpgrade: userData.autoUpgrade || false,
        monthlyTransactions: userData.monthlyTransactions || 0,
        transferSecurityEnabled: userData.transferSecurityEnabled || false,
        aiEnabled: userData.aiEnabled !== undefined ? userData.aiEnabled : true,
        createdAt: userData.createdAt,
        updatedAt: userData.updatedAt
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao buscar dados do usuário:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/payment/:id - Obter detalhes de um pagamento específico
 */
router.get('/payment/:id', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { id } = req.params;

    // Tentar buscar Register para obter o ID correto
    let userId = user._id.toString();
    try {
      const register = await Register.findOne({
        email: user.email.toLowerCase(),
        status: 'active'
      });
      if (register) {
        userId = register.id;
      }
    } catch (registerError) {
      // Se não encontrar Register, usar User ID
    }

    const payment = await Payment.findOne({ id });

    if (!payment) {
      return res.status(404).json({
        success: false,
        error: 'Pagamento não encontrado'
      });
    }

    // Verificar propriedade
    if (payment.userId !== userId) {
      return res.status(403).json({
        success: false,
        error: 'Acesso negado',
        message: 'Você não tem permissão para acessar este pagamento'
      });
    }

    res.json({
      success: true,
      data: {
        id: payment.id,
        correlationID: payment.correlationID,
        value: payment.value,
        netValue: payment.netValue || payment.value,
        fee: payment.fee,
        status: payment.status,
        description: payment.description,
        qrCode: payment.qrCode,
        pixKey: payment.pixKey,
        pixKeyType: payment.pixKeyType,
        createdAt: payment.createdAt,
        updatedAt: payment.updatedAt
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao buscar pagamento:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/withdraw/:id - Obter detalhes de um saque específico
 */
router.get('/withdraw/:id', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { id } = req.params;

    // Tentar buscar Register para obter o ID correto
    let userId = user._id.toString();
    try {
      const register = await Register.findOne({
        email: user.email.toLowerCase(),
        status: 'active'
      });
      if (register) {
        userId = register.id;
      }
    } catch (registerError) {
      // Se não encontrar Register, usar User ID
    }

    const withdraw = await Withdraw.findOne({ id });

    if (!withdraw) {
      return res.status(404).json({
        success: false,
        error: 'Saque não encontrado'
      });
    }

    // Verificar propriedade
    if (withdraw.userId !== userId) {
      return res.status(403).json({
        success: false,
        error: 'Acesso negado',
        message: 'Você não tem permissão para acessar este saque'
      });
    }

    // Extrair fee e sent do metadata se disponível
    const fee = withdraw.metadata?.fee || withdraw.metadata?.userPaymentFee || null;
    const sent = withdraw.metadata?.sent || withdraw.metadata?.amountToSend || null;

    res.json({
      success: true,
      data: {
        id: withdraw.id,
        correlationID: withdraw.correlationID,
        value: withdraw.value,
        status: withdraw.status,
        pixKey: withdraw.pixKey,
        pixKeyType: withdraw.pixKeyType,
        transactionId: withdraw.transactionId,
        fee: fee,
        sent: sent,
        completedAt: withdraw.completedAt,
        failedAt: withdraw.failedAt,
        failureReason: withdraw.failureReason,
        description: withdraw.description,
        metadata: withdraw.metadata,
        createdAt: withdraw.createdAt,
        updatedAt: withdraw.updatedAt
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao buscar saque:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/split/:id - Obter detalhes de um split recebido
 */
router.get('/split/:id', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const { id } = req.params;

    // Tentar buscar Register para obter o ID correto
    let userId = user._id.toString();
    try {
      const register = await Register.findOne({
        email: user.email.toLowerCase(),
        status: 'active'
      });
      if (register) {
        userId = register.id;
      }
    } catch (registerError) {
      // Se não encontrar Register, usar User ID
    }

    const SplitPayment = (await import('../database/models/SplitPayment.js')).default;
    const split = await SplitPayment.findOne({ id });

    if (!split) {
      return res.status(404).json({
        success: false,
        error: 'Split não encontrado'
      });
    }

    // Verificar se o usuário é o destinatário do split
    if (split.recipientId !== userId) {
      return res.status(403).json({
        success: false,
        error: 'Acesso negado',
        message: 'Você não tem permissão para acessar este split'
      });
    }

    // Buscar nome do remetente
    let senderName = 'Usuário';
    try {
      const sender = await Register.findOne({ id: split.senderId }, { name: 1 });
      if (sender) {
        senderName = sender.name;
      }
    } catch (e) {
      // Ignorar erro, usar nome padrão
    }

    res.json({
      success: true,
      data: {
        id: split.id,
        originalPaymentId: split.originalPaymentId,
        senderId: split.senderId,
        senderName: senderName,
        senderEmail: split.senderEmail,
        recipientId: split.recipientId,
        recipientEmail: split.recipientEmail,
        amount: split.amount,
        splitPercentage: split.splitPercentage,
        originalAmount: split.originalAmount,
        status: split.status,
        createdAt: split.createdAt,
        processedAt: split.processedAt
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao buscar split:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

/**
 * GET /auth/transactions - Listar todas as transações (pagamentos e saques) com paginação
 */
router.get('/transactions', authenticate, async (req, res) => {
  try {
    const user = req.user;
    const {
      page = 1,
      limit = 25,
      startDate,
      endDate,
      type = 'all', // 'all', 'income' (payments), 'expense' (withdraws)
      status = 'all'
    } = req.query;

    const pageNum = parseInt(page);
    const limitNum = parseInt(limit);
    const offset = (pageNum - 1) * limitNum;

    // Tentar buscar Register para obter o ID correto
    let userId = user._id.toString();
    try {
      const Register = (await import('../database/models/Register.js')).default;
      const register = await Register.findOne({
        email: user.email.toLowerCase(),
        status: 'active'
      });
      if (register) {
        userId = register.id;
      }
    } catch (registerError) {
      // Se não encontrar Register, usar User ID
    }

    // Buscar pagamentos e saques
    const Payment = (await import('../database/models/Payment.js')).default;
    const Withdraw = (await import('../database/models/Withdraw.js')).default;
    const SplitPayment = (await import('../database/models/SplitPayment.js')).default;

    let payments = [];
    let withdraws = [];
    let transfersSent = [];
    let transfersReceived = [];
    let splitsReceived = [];

    // Buscar dados baseado no tipo solicitado
    if (type === 'all' || type === 'income') {
      payments = await Payment.getByUser(userId);
      // Buscar transferências recebidas
      transfersReceived = await InternalTransfer.find({ recipientId: userId }).sort({ createdAt: -1 });
      // Buscar splits recebidos
      splitsReceived = await SplitPayment.find({ recipientId: userId, status: 'COMPLETED' }).sort({ createdAt: -1 });
    }

    if (type === 'all' || type === 'expense') {
      withdraws = await Withdraw.getByUserId(userId);
      // Buscar transferências enviadas
      transfersSent = await InternalTransfer.find({ senderId: userId }).sort({ createdAt: -1 });
    }

    // Coletar IDs de usuários para buscar nomes
    const userIdsToFetch = new Set();
    transfersSent.forEach(t => userIdsToFetch.add(t.recipientId));
    transfersReceived.forEach(t => userIdsToFetch.add(t.senderId));

    // Buscar usuários (Register)
    const usersMap = {};
    if (userIdsToFetch.size > 0) {
      const RegisterModel = (await import('../database/models/Register.js')).default;
      const users = await RegisterModel.find({ id: { $in: Array.from(userIdsToFetch) } }).select('id name email');
      users.forEach(u => {
        usersMap[u.id] = u;
      });
    }

    // Normalizar e mesclar transações
    let allTransactions = [];

    // Processar pagamentos (Entradas)
    payments.forEach(p => {
      allTransactions.push({
        id: p.id,
        type: 'income',
        transactionType: (p.metadata && p.metadata.type === 'commission') ? 'commission' : 'payment',
        date: new Date(p.createdAt),
        amount: p.netValue || p.value,
        status: p.status,
        description: p.description || 'Pagamento recebido',
        originalData: {
          correlationID: p.correlationID,
          fee: p.fee
        }
      });
    });

    // Processar saques (Saídas)
    withdraws.forEach(w => {
      allTransactions.push({
        id: w.id,
        type: 'expense',
        transactionType: 'withdraw',
        date: new Date(w.createdAt),
        amount: w.value,
        status: w.status,
        description: w.description || 'Saque realizado',
        originalData: {
          correlationID: w.correlationID,
          pixKey: w.pixKey
        }
      });
    });

    // Processar transferências internas enviadas (Saídas)
    transfersSent.forEach(t => {
      const recipientUser = usersMap[t.recipientId];
      allTransactions.push({
        id: t.id,
        type: 'expense',
        transactionType: 'internal_transfer_sent',
        date: new Date(t.createdAt),
        amount: t.amount,
        status: t.status,
        description: t.description || `Transferência para ${recipientUser ? recipientUser.name : t.recipientEmail}`,
        originalData: {
          recipient: {
            name: recipientUser ? recipientUser.name : 'Usuário',
            email: t.recipientEmail,
            id: t.recipientId
          }
        }
      });
    });

    // Processar transferências internas recebidas (Entradas)
    transfersReceived.forEach(t => {
      const senderUser = usersMap[t.senderId];
      allTransactions.push({
        id: t.id,
        type: 'income',
        transactionType: 'internal_transfer_received',
        date: new Date(t.createdAt),
        amount: t.amount,
        status: t.status,
        description: t.description || `Transferência de ${senderUser ? senderUser.name : t.senderEmail}`,
        originalData: {
          sender: {
            name: senderUser ? senderUser.name : 'Usuário',
            email: t.senderEmail,
            id: t.senderId
          }
        }
      });
    });

    // Processar splits recebidos (Entradas)
    splitsReceived.forEach(s => {
      allTransactions.push({
        id: s.id,
        type: 'income',
        transactionType: 'split_received',
        date: new Date(s.createdAt),
        amount: s.amount,
        status: s.status,
        description: `Split recebido de ${s.senderEmail}`,
        originalData: {
          sender: {
            email: s.senderEmail,
            id: s.senderId
          },
          originalPaymentId: s.originalPaymentId,
          splitPercentage: s.splitPercentage,
          originalAmount: s.originalAmount
        }
      });
    });

    // Filtrar por data
    if (startDate || endDate) {
      const start = startDate ? new Date(startDate) : new Date(0);
      const end = endDate ? new Date(endDate) : new Date();
      // Ajustar end para o final do dia se for apenas data
      if (endDate && endDate.length <= 10) {
        end.setHours(23, 59, 59, 999);
      }

      allTransactions = allTransactions.filter(t => t.date >= start && t.date <= end);
    }

    // Filtrar por status
    if (status && status !== 'all') {
      const statusUpper = status.toUpperCase();
      allTransactions = allTransactions.filter(t => {
        const tStatus = t.status.toUpperCase();
        if (statusUpper === 'COMPLETED') {
          return tStatus === 'COMPLETED' || tStatus === 'PAID';
        }
        if (statusUpper === 'PENDING') {
          return ['PENDING', 'PROCESSING', 'WAITING', 'ACTIVE'].includes(tStatus);
        }
        if (statusUpper === 'FAILED') {
          return ['FAILED', 'CANCELLED', 'EXPIRED'].includes(tStatus);
        }
        return tStatus === statusUpper;
      });
    }

    // Ordenar por data (mais recente primeiro)
    allTransactions.sort((a, b) => b.date - a.date);

    // Paginação
    const total = allTransactions.length;
    const totalPages = Math.ceil(total / limitNum);
    const paginatedTransactions = allTransactions.slice(offset, offset + limitNum);

    res.json({
      success: true,
      data: {
        transactions: paginatedTransactions,
        pagination: {
          total,
          page: pageNum,
          limit: limitNum,
          totalPages,
          hasMore: pageNum < totalPages
        }
      }
    });

  } catch (error) {
    console.error('[AUTH PLAN] Erro ao listar transações:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


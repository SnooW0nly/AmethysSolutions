import express from 'express';
import { strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import Register from '../../../../database/models/Register.js';
import Payment from '../../../../database/models/Payment.js';
import Withdraw from '../../../../database/models/Withdraw.js';

const router = express.Router();

import { authenticateAdmin } from '../../../../middlewares/adminAuth.js';

// GET /api/v1/admin/users - Lista todos os usuários (Admin only)
router.get('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { status, blocked, limit = 50, offset = 0, search } = req.query;

    let query = {};

    if (status) {
      query.status = status;
    }

    if (blocked !== undefined) {
      query.blocked = blocked === 'true';
    }

    // Pesquisa por nome, email ou ID
    if (search && search.trim()) {
      const searchRegex = new RegExp(search.trim(), 'i');
      query.$or = [
        { name: searchRegex },
        { email: searchRegex },
        { id: searchRegex },
        { taxID: searchRegex }
      ];
    }

    const users = await Register.find(query)
      .sort({ createdAt: -1 })
      .skip(parseInt(offset))
      .limit(parseInt(limit));

    const total = await Register.countDocuments(query);

    // Estatísticas gerais
    const allUsers = await Register.find({});
    const stats = {
      total: allUsers.length,
      active: allUsers.filter(u => u.status === 'active').length,
      blocked: allUsers.filter(u => u.blocked === true).length,
      deleted: allUsers.filter(u => u.status === 'deleted').length,
      totalBalance: allUsers.reduce((sum, u) => sum + (u.balance || 0), 0),
      totalSplit: allUsers.reduce((sum, u) => sum + (u.saldo_split || 0), 0)
    };

    res.json({
      success: true,
      data: {
        users: users.map(u => ({
          id: u.id,
          name: u.name,
          email: u.email,
          taxID: u.taxID,
          phone: u.phone,
          balance: u.balance || 0,
          saldo_split: u.saldo_split || 0,
          blocked: u.blocked,
          status: u.status,
          limits: u.limits,
          dailyUsed: u.dailyUsed || 0,
          monthlyUsed: u.monthlyUsed || 0,
          plan: u.plan,
          createdAt: u.createdAt,
          updatedAt: u.updatedAt
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
    console.error('Erro ao listar usuários:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// GET /api/v1/admin/users/:id - Busca um usuário específico (Admin only)
router.get('/:id', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { id } = req.params;

    const user = await Register.getById(id);

    if (!user) {
      return res.status(404).json({
        error: 'Usuário não encontrado'
      });
    }

    // Buscar pagamentos e saques do usuário
    const payments = await Payment.getByUser(id);
    const withdraws = await Withdraw.getByUserId(id);

    console.log(`[ADMIN USER] User ${id}: ${payments.length} payments, ${withdraws.length} withdraws`);

    // Estatísticas do usuário
    const completedPayments = payments.filter(p => p.status === 'COMPLETED' || p.status === 'PAID');
    const completedWithdraws = withdraws.filter(w => w.status === 'COMPLETED');

    const totalReceived = completedPayments.reduce((sum, p) => sum + (p.netValue || p.value || 0), 0);
    const totalWithdrawn = completedWithdraws.reduce((sum, w) => sum + (w.value || 0), 0);

    console.log(`[ADMIN USER] User ${id}: totalReceived=${totalReceived}, totalWithdrawn=${totalWithdrawn}`);

    const stats = {
      totalPayments: payments.length,
      completedPayments: completedPayments.length,
      totalReceived,
      totalFees: completedPayments.reduce((sum, p) => sum + (p.fee || 0), 0),
      totalWithdraws: withdraws.length,
      totalWithdrawn,
      totalMovement: totalReceived + totalWithdrawn
    };

    res.json({
      success: true,
      data: {
        user: {
          id: user.id,
          name: user.name,
          email: user.email,
          taxID: user.taxID,
          phone: user.phone,
          balance: user.balance || 0,
          saldo_split: user.saldo_split || 0,
          blocked: user.blocked,
          status: user.status,
          limits: user.limits,
          dailyUsed: user.dailyUsed || 0,
          monthlyUsed: user.monthlyUsed || 0,
          plan: user.plan,
          planStartDate: user.planStartDate,
          planEndDate: user.planEndDate,
          planRenewalDate: user.planRenewalDate,
          planAutoRenew: user.planAutoRenew,
          paymentFee: user.paymentFee,
          splitFee: user.splitFee,
          pixKey: user.pixKey,
          pixKeyType: user.pixKeyType,
          apiKey: user.apiKey,
          webhookUrl: user.webhookUrl,
          isAffiliate: user.isAffiliate,
          referredBy: user.referredBy,
          createdAt: user.createdAt,
          updatedAt: user.updatedAt
        },
        statistics: stats
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

// GET /api/v1/admin/users/:id/transactions - Lista transações do usuário (Admin only)
router.get('/:id/transactions', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { limit = 20, offset = 0, type = 'all' } = req.query;

    const user = await Register.getById(id);
    if (!user) {
      return res.status(404).json({
        error: 'Usuário não encontrado'
      });
    }

    let transactions = [];
    let total = 0;

    if (type === 'payment' || type === 'all') {
      const payments = await Payment.find({ userId: id })
        .sort({ createdAt: -1 })
        .skip(type === 'all' ? 0 : parseInt(offset))
        .limit(type === 'all' ? 1000 : parseInt(limit));

      transactions = transactions.concat(payments.map(p => ({
        id: p.id,
        type: 'payment',
        value: p.value,
        netValue: p.netValue,
        fee: p.fee,
        status: p.status,
        description: p.description,
        createdAt: p.createdAt,
        paidAt: p.paidAt
      })));
    }

    if (type === 'withdraw' || type === 'all') {
      const withdraws = await Withdraw.find({ userId: id, status: { $ne: 'DELETED' } })
        .sort({ createdAt: -1 })
        .skip(type === 'all' ? 0 : parseInt(offset))
        .limit(type === 'all' ? 1000 : parseInt(limit));

      transactions = transactions.concat(withdraws.map(w => ({
        id: w.id,
        type: 'withdraw',
        value: w.value,
        status: w.status,
        description: w.description,
        createdAt: w.createdAt,
        completedAt: w.completedAt
      })));
    }

    // Sort by date and apply pagination for 'all' type
    transactions.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    total = transactions.length;

    if (type === 'all') {
      transactions = transactions.slice(parseInt(offset), parseInt(offset) + parseInt(limit));
    }

    res.json({
      success: true,
      data: {
        transactions,
        pagination: {
          total,
          limit: parseInt(limit),
          offset: parseInt(offset),
          hasMore: (parseInt(offset) + parseInt(limit)) < total
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

// PUT /api/v1/admin/users/:id/plan - Define o plano do usuário com dias específicos (Admin only)
router.put('/:id/plan', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { plan, days } = req.body;

    if (!plan || !days) {
      return res.status(400).json({
        error: 'Dados incompletos',
        message: 'É necessário informar o plano e a quantidade de dias'
      });
    }

    const validPlans = ['FREE', 'BLACK', 'CARBON', 'DIAMOND', 'RICH', 'ENTERPRISE'];
    if (!validPlans.includes(plan)) {
      return res.status(400).json({
        error: 'Plano inválido',
        message: `O plano deve ser um dos seguintes: ${validPlans.join(', ')}`
      });
    }

    const daysNum = parseInt(days);
    if (isNaN(daysNum) || daysNum <= 0) {
      return res.status(400).json({
        error: 'Dias inválidos',
        message: 'A quantidade de dias deve ser um número positivo'
      });
    }

    const user = await Register.getById(id);
    if (!user) {
      return res.status(404).json({
        error: 'Usuário não encontrado'
      });
    }

    // Calcular datas
    const now = new Date();
    const planStartDate = now.toISOString();

    const planEndDate = new Date(now);
    planEndDate.setDate(planEndDate.getDate() + daysNum);
    const planEndDateISO = planEndDate.toISOString();

    // Atualizar usuário
    const updates = {
      plan: plan,
      planStartDate: planStartDate,
      planEndDate: planEndDateISO,
      planRenewalDate: planEndDateISO, // Renovação coincide com o fim neste caso manual
      planAutoRenew: false, // Desativa renovação automática pois é um período customizado
      planChangedAt: new Date().toISOString(),
      planChangeReason: `ADMIN_SET_DAYS_${daysNum}`,
      planLockedByAdmin: plan === 'BLACK', // Bloqueia troca quando admin seta BLACK
      // Atualizar taxas baseadas no plano (valores padrão, idealmente viriam de uma config de planos)
      // Vou manter as taxas atuais do usuário ou definir hardcoded se necessário? 
      // Melhor buscar as configs do plano se possível, mas para simplificar e seguir o User Model defaults:
      // O ideal seria importar o getPlan do service, mas para não quebrar a arquitetura deste arquivo simples:
      // Vou deixar as taxas como estão ou definir baseadas num switch simples se for crítico.
      // O usuário pediu apenas "setar plano... seta dias".
      // O Register model tem defaults.
      // Vou assumir que o sistema de check de plano lida com as taxas ou que isso é suficiente.
      // Mas espere, se eu mudo pra DIAMOND, as taxas deveriam cair.
      // Vou fazer um import dinâmico do serviço de planos para pegar as taxas corretas.
    };

    // Importar serviço de planos para pegar taxas corretas
    try {
      const { getPlan, getSplitFee } = await import('../../../../services/planService.js');
      const planConfig = await getPlan(plan);
      const splitFee = await getSplitFee(plan);
      updates.paymentFee = planConfig.transactionFee;
      updates.splitFee = splitFee;
      console.log(`[ADMIN SET PLAN] User ${id} -> Plan: ${plan}, paymentFee: ${planConfig.transactionFee}, splitFee: ${splitFee}`);
    } catch (err) {
      console.error('[ADMIN SET PLAN] Erro ao carregar config do plano:', err);
    }

    console.log('[ADMIN SET PLAN] Updates to apply:', JSON.stringify(updates));

    const updatedUser = await Register.findOneAndUpdate(
      { id: id },
      { $set: updates },
      { new: true }
    );

    console.log(`[ADMIN SET PLAN] User updated: plan=${updatedUser.plan}, paymentFee=${updatedUser.paymentFee}, splitFee=${updatedUser.splitFee}`);

    res.json({
      success: true,
      data: {
        plan: updatedUser.plan,
        planEndDate: updatedUser.planEndDate,
        days: daysNum
      }
    });

  } catch (error) {
    console.error('Erro ao definir plano do usuário:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// PUT /api/v1/admin/users/:id/category - Definir categoria WHITE/BLACK e tier
router.put('/:id/category', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { category, tier } = req.body;

    // Validar categoria
    if (!category || !['WHITE', 'BLACK'].includes(category.toUpperCase())) {
      return res.status(400).json({
        error: 'Categoria inválida',
        message: 'A categoria deve ser WHITE ou BLACK'
      });
    }

    const normalizedCategory = category.toUpperCase();

    // Validar tier para WHITE
    let normalizedTier = 1;
    if (normalizedCategory === 'WHITE') {
      normalizedTier = parseInt(tier) || 1;
      if (normalizedTier < 1 || normalizedTier > 5) {
        return res.status(400).json({
          error: 'Tier inválido',
          message: 'O tier WHITE deve ser entre 1 e 5'
        });
      }
    }

    // Verificar se usuário existe
    const user = await Register.findOne({ id });
    if (!user) {
      return res.status(404).json({
        error: 'Usuário não encontrado'
      });
    }

    // Calcular taxas baseado na categoria
    const { getWhiteFee, calculateSplit } = await import('../../../../services/categoryService.js');

    const paymentFee = normalizedCategory === 'BLACK' ? null : getWhiteFee(normalizedTier);
    const splitFee = await calculateSplit(normalizedCategory, normalizedTier);

    // Atualizar usuário
    const updates = {
      category: normalizedCategory,
      tier: normalizedTier,
      paymentFee,
      splitFee,
      planLockedByAdmin: true
    };

    const updatedUser = await Register.findOneAndUpdate(
      { id },
      { $set: updates },
      { new: true }
    );

    console.log(`[ADMIN SET CATEGORY] User ${id} -> Category: ${normalizedCategory}, Tier: ${normalizedTier}, Fee: ${paymentFee}, Split: ${splitFee}`);

    res.json({
      success: true,
      message: `Categoria alterada para ${normalizedCategory}${normalizedCategory === 'WHITE' ? ` ${normalizedTier}` : ''}`,
      data: {
        category: updatedUser.category,
        tier: updatedUser.tier,
        paymentFee: updatedUser.paymentFee,
        splitFee: updatedUser.splitFee
      }
    });

  } catch (error) {
    console.error('Erro ao definir categoria do usuário:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// PUT /api/v1/admin/users/:id/set-admin - Define ou remove admin de um usuário (Admin only)
router.put('/:id/set-admin', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { admin } = req.body;

    if (typeof admin !== 'boolean') {
      return res.status(400).json({
        error: 'Campo inválido',
        message: 'O campo "admin" deve ser true ou false'
      });
    }

    const user = await Register.getById(id);
    if (!user) {
      return res.status(404).json({
        error: 'Usuário não encontrado'
      });
    }

    // Impede que o admin remova a si mesmo
    if (req.user && (req.user._id?.toString() === user._id?.toString() || req.user.id === id)) {
      return res.status(400).json({
        error: 'Operação inválida',
        message: 'Você não pode alterar seu próprio status de admin'
      });
    }

    const updatedUser = await Register.findOneAndUpdate(
      { id },
      { $set: { admin } },
      { new: true }
    );

    console.log(`[ADMIN SET ADMIN] User ${id} -> admin: ${admin}`);

    res.json({
      success: true,
      message: admin ? 'Usuário promovido a admin com sucesso' : 'Permissão de admin removida com sucesso',
      data: {
        id: updatedUser.id,
        name: updatedUser.name,
        email: updatedUser.email,
        admin: updatedUser.admin
      }
    });
  } catch (error) {
    console.error('Erro ao alterar status de admin:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;
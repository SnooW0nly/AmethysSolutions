// src/routes/api/v1/admin/plans.js
// SUBSTITUIR o arquivo existente por este (já existia parcialmente, agora cobre todos os campos do Plan model)

import express from 'express';
import { strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import Plan from '../../../../database/models/Plan.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';
import { authenticateAdmin } from '../../../../middlewares/adminAuth.js';

const router = express.Router();

const formatPlan = (p) => ({
  id: p.id,
  name: p.name,
  description: p.description,
  transactionFee: p.transactionFee,
  transactionFeeInReais: (p.transactionFee / 100).toFixed(2),
  monthlyFee: p.monthlyFee,
  monthlyFeeInReais: (p.monthlyFee / 100).toFixed(2),
  minTransactions: p.minTransactions,
  maxTransactions: p.maxTransactions,
  downgradeTo: p.downgradeTo,
  order: p.order,
  transactionFeePercent: p.transactionFeePercent,
  transactionFeeFixed: p.transactionFeeFixed,
  splitFee: p.splitFee,
  useSeparateMistic: p.useSeparateMistic,
  active: p.active,
  createdAt: p.createdAt,
  updatedAt: p.updatedAt,
});

// GET /api/v1/admin/plans - Lista todos os planos incluindo inativos (Admin only)
router.get('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { includeInactive } = req.query;
    const query = includeInactive === 'true' ? {} : { active: true };
    const plans = await Plan.find(query).sort({ order: 1 });

    res.json({ success: true, data: { plans: plans.map(formatPlan) } });
  } catch (error) {
    console.error('Erro ao listar planos:', error);
    res.status(500).json({ error: 'Erro interno do servidor', message: error.message });
  }
});

// GET /api/v1/admin/plans/:id - Busca um plano (inclui inativos)
router.get('/:id', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const plan = await Plan.findOne({ id: req.params.id.toUpperCase() });
    if (!plan) return res.status(404).json({ error: 'Plano não encontrado' });
    res.json({ success: true, data: { plan: formatPlan(plan) } });
  } catch (error) {
    res.status(500).json({ error: 'Erro interno do servidor', message: error.message });
  }
});

// POST /api/v1/admin/plans - Cria um novo plano
router.post('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const {
      id, name, description,
      transactionFee, monthlyFee,
      minTransactions, maxTransactions,
      downgradeTo, order,
      transactionFeePercent, transactionFeeFixed,
      splitFee, useSeparateMistic,
    } = req.body;

    if (!id || !name) {
      return res.status(400).json({ error: 'Os campos "id" e "name" são obrigatórios' });
    }

    const existing = await Plan.findOne({ id: id.toUpperCase() });
    if (existing) {
      return res.status(409).json({ error: `Já existe um plano com o ID ${id.toUpperCase()}` });
    }

    const planData = {
      id: id.toUpperCase(),
      name,
      description: description || '',
      transactionFee: transactionFee ?? 70,
      monthlyFee: monthlyFee ?? 0,
      minTransactions: minTransactions ?? 0,
      maxTransactions: maxTransactions ?? null,
      downgradeTo: downgradeTo || null,
      order: order ?? 0,
      transactionFeePercent: transactionFeePercent ?? null,
      transactionFeeFixed: transactionFeeFixed ?? null,
      splitFee: splitFee ?? null,
      useSeparateMistic: useSeparateMistic ?? false,
      active: true,
    };

    const plan = await Plan.create(planData);

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PLAN_CHANGED,
      entity: AUDIT_ENTITIES.PLAN,
      entityId: plan.id,
      userId: req.user._id || req.user.id || 'ADMIN',
      userEmail: req.user.email || null,
      dataBefore: null,
      dataAfter: planData,
      ipAddress: req.ip || req.headers['x-forwarded-for'],
      userAgent: req.headers['user-agent'],
      description: `Plano criado: ${plan.name} (${plan.id})`,
    });

    res.status(201).json({ success: true, message: 'Plano criado com sucesso', data: { plan: formatPlan(plan) } });
  } catch (error) {
    if (error.code === 11000) return res.status(409).json({ error: 'Já existe um plano com este ID' });
    res.status(500).json({ error: 'Erro interno do servidor', message: error.message });
  }
});

// PUT /api/v1/admin/plans/:id - Atualiza um plano (todos os campos)
router.put('/:id', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const plan = await Plan.findOne({ id: id.toUpperCase() });
    if (!plan) return res.status(404).json({ error: 'Plano não encontrado' });

    const dataBefore = formatPlan(plan);

    const updatableFields = [
      'name', 'description', 'transactionFee', 'monthlyFee',
      'minTransactions', 'maxTransactions', 'downgradeTo', 'order',
      'transactionFeePercent', 'transactionFeeFixed', 'splitFee',
      'useSeparateMistic', 'active',
    ];

    const updates = {};
    for (const field of updatableFields) {
      if (req.body[field] !== undefined) {
        updates[field] = req.body[field] === '' ? null : req.body[field];
      }
    }
    // maxTransactions e downgradeTo podem ser explicitamente null
    if (req.body.maxTransactions === null) updates.maxTransactions = null;
    if (req.body.downgradeTo === null) updates.downgradeTo = null;

    const updatedPlan = await Plan.findOneAndUpdate(
      { id: id.toUpperCase() },
      { $set: updates },
      { new: true }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PLAN_CHANGED,
      entity: AUDIT_ENTITIES.PLAN,
      entityId: updatedPlan.id,
      userId: req.user._id || req.user.id || 'ADMIN',
      userEmail: req.user.email || null,
      dataBefore,
      dataAfter: formatPlan(updatedPlan),
      ipAddress: req.ip || req.headers['x-forwarded-for'],
      userAgent: req.headers['user-agent'],
      description: `Plano atualizado: ${updatedPlan.name} (${updatedPlan.id})`,
    });

    res.json({ success: true, message: 'Plano atualizado com sucesso', data: { plan: formatPlan(updatedPlan) } });
  } catch (error) {
    res.status(500).json({ error: 'Erro interno do servidor', message: error.message });
  }
});

// DELETE /api/v1/admin/plans/:id - Desativa (soft delete) um plano
router.delete('/:id', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const plan = await Plan.findOne({ id: req.params.id.toUpperCase() });
    if (!plan) return res.status(404).json({ error: 'Plano não encontrado' });

    const updatedPlan = await Plan.findOneAndUpdate(
      { id: req.params.id.toUpperCase() },
      { $set: { active: false } },
      { new: true }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PLAN_CHANGED,
      entity: AUDIT_ENTITIES.PLAN,
      entityId: updatedPlan.id,
      userId: req.user._id || req.user.id || 'ADMIN',
      userEmail: req.user.email || null,
      dataBefore: { active: true },
      dataAfter: { active: false },
      ipAddress: req.ip || req.headers['x-forwarded-for'],
      userAgent: req.headers['user-agent'],
      description: `Plano desativado: ${updatedPlan.name} (${updatedPlan.id})`,
    });

    res.json({ success: true, message: 'Plano desativado com sucesso' });
  } catch (error) {
    res.status(500).json({ error: 'Erro interno do servidor', message: error.message });
  }
});

// PATCH /api/v1/admin/plans/:id/restore - Reativa um plano desativado
router.patch('/:id/restore', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const plan = await Plan.findOne({ id: req.params.id.toUpperCase() });
    if (!plan) return res.status(404).json({ error: 'Plano não encontrado' });

    const updatedPlan = await Plan.findOneAndUpdate(
      { id: req.params.id.toUpperCase() },
      { $set: { active: true } },
      { new: true }
    );

    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PLAN_CHANGED,
      entity: AUDIT_ENTITIES.PLAN,
      entityId: updatedPlan.id,
      userId: req.user._id || req.user.id || 'ADMIN',
      userEmail: req.user.email || null,
      dataBefore: { active: false },
      dataAfter: { active: true },
      ipAddress: req.ip || req.headers['x-forwarded-for'],
      userAgent: req.headers['user-agent'],
      description: `Plano reativado: ${updatedPlan.name} (${updatedPlan.id})`,
    });

    res.json({ success: true, message: 'Plano reativado com sucesso', data: { plan: formatPlan(updatedPlan) } });
  } catch (error) {
    res.status(500).json({ error: 'Erro interno do servidor', message: error.message });
  }
});

export default router;
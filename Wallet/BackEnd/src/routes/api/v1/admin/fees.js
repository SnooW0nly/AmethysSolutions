import express from 'express';
import { authenticateAdmin } from '../../../../middlewares/adminAuth.js';
import { strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import FeeConfig from '../../../../database/models/FeeConfig.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';
import { DEFAULT_TRANSACTION_FEE, DEFAULT_WITHDRAW_FEE } from '../../../../services/feeService.js';

const router = express.Router();

// ─────────────────────────────────────────────────────────────────────────────
// GET /api/v1/admin/fees
// Retorna as taxas globais atuais (ou os defaults se ainda não configurado)
// ─────────────────────────────────────────────────────────────────────────────
router.get('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const config = await FeeConfig.getSingleton();

    return res.json({
      success: true,
      data: {
        transactionFee: config.transactionFee ?? DEFAULT_TRANSACTION_FEE,
        withdrawFee:    config.withdrawFee    ?? DEFAULT_WITHDRAW_FEE,
        transactionFeeDisplay: `R$ ${((config.transactionFee ?? DEFAULT_TRANSACTION_FEE) / 100).toFixed(2)}`,
        withdrawFeeDisplay:    `R$ ${((config.withdrawFee    ?? DEFAULT_WITHDRAW_FEE)    / 100).toFixed(2)}`,
        notes:       config.notes      || '',
        updatedBy:   config.updatedBy  || 'SYSTEM',
        updatedAt:   config.updatedAt  || null,
        _fromDefault: config._fromDefault ?? false,
      },
    });
  } catch (error) {
    console.error('[admin/fees] Erro ao buscar taxas:', error);
    return res.status(500).json({
      error: 'Erro ao buscar taxas',
      message: error.message,
    });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// PUT /api/v1/admin/fees
// Atualiza as taxas globais.
//
// Body (ao menos um campo obrigatório):
//   transactionFee  {number}  Taxa de transação em centavos (ex: 55 = R$ 0,55)
//   withdrawFee     {number}  Taxa de saque PIX em centavos (ex: 30 = R$ 0,30)
//   notes           {string}  Nota interna opcional
// ─────────────────────────────────────────────────────────────────────────────
router.put('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    const { transactionFee, withdrawFee, notes } = req.body || {};

    // Validação: ao menos um campo de taxa deve ser enviado
    if (transactionFee === undefined && withdrawFee === undefined) {
      return res.status(400).json({
        error: 'Campos obrigatórios ausentes',
        message: 'Envie ao menos um dos campos: "transactionFee" ou "withdrawFee" (em centavos)',
      });
    }

    // Validar transactionFee
    if (transactionFee !== undefined) {
      if (typeof transactionFee !== 'number' || !Number.isInteger(transactionFee) || transactionFee < 0) {
        return res.status(400).json({
          error: 'Valor inválido',
          message: '"transactionFee" deve ser um inteiro >= 0 (centavos). Ex: 55 para R$ 0,55',
        });
      }
    }

    // Validar withdrawFee
    if (withdrawFee !== undefined) {
      if (typeof withdrawFee !== 'number' || !Number.isInteger(withdrawFee) || withdrawFee < 0) {
        return res.status(400).json({
          error: 'Valor inválido',
          message: '"withdrawFee" deve ser um inteiro >= 0 (centavos). Ex: 30 para R$ 0,30',
        });
      }
    }

    // Estado anterior para auditoria
    const before = await FeeConfig.getSingleton();

    // Montar payload de atualização
    const updatePayload = { updatedBy: 'ADMIN' };
    if (transactionFee !== undefined) updatePayload.transactionFee = transactionFee;
    if (withdrawFee     !== undefined) updatePayload.withdrawFee    = withdrawFee;
    if (notes           !== undefined) updatePayload.notes          = String(notes).slice(0, 500);

    const updated = await FeeConfig.upsert(updatePayload);

    console.log(`✅ [admin/fees] Taxas atualizadas: transactionFee=${updated.transactionFee}c, withdrawFee=${updated.withdrawFee}c`);

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.CONFIG_UPDATED,
      entity: AUDIT_ENTITIES.CONFIG,
      entityId: 'FEE_CONFIG',
      userId: 'ADMIN',
      userEmail: null,
      dataBefore: {
        transactionFee: before.transactionFee ?? DEFAULT_TRANSACTION_FEE,
        withdrawFee:    before.withdrawFee    ?? DEFAULT_WITHDRAW_FEE,
      },
      dataAfter: {
        transactionFee: updated.transactionFee,
        withdrawFee:    updated.withdrawFee,
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Taxas atualizadas: transação=${updated.transactionFee}c, saque=${updated.withdrawFee}c`,
    });

    return res.json({
      success: true,
      message: 'Taxas atualizadas com sucesso',
      data: {
        transactionFee: updated.transactionFee,
        withdrawFee:    updated.withdrawFee,
        transactionFeeDisplay: `R$ ${(updated.transactionFee / 100).toFixed(2)}`,
        withdrawFeeDisplay:    `R$ ${(updated.withdrawFee    / 100).toFixed(2)}`,
        notes:     updated.notes     || '',
        updatedBy: updated.updatedBy,
        updatedAt: updated.updatedAt,
      },
    });
  } catch (error) {
    console.error('[admin/fees] Erro ao atualizar taxas:', error);
    return res.status(500).json({
      error: 'Erro ao atualizar taxas',
      message: error.message,
    });
  }
});

export default router;

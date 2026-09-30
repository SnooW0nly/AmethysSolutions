import express from 'express';
import { authenticate } from '../../../../middlewares/auth.js';
import { requireAdmin } from '../../../../middlewares/admin.js';
import { defaultJwtRateLimiter, strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import Register from '../../../../database/models/Register.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';

const router = express.Router();

// GET /api/v1/user/limit - Obtém limites do usuário (Dashboard/JWT)
router.get('/', defaultJwtRateLimiter, authenticate, async (req, res) => {
  try {
    const user = req.user;

    res.json({
      success: true,
      data: {
        limits: {
          daily: user.limits?.daily || 0,
          monthly: user.limits?.monthly || 0,
          perTransaction: user.limits?.perTransaction || 0
        },
        usage: {
          dailyUsed: user.dailyUsed || 0,
          monthlyUsed: user.monthlyUsed || 0,
          dailyRemaining: (user.limits?.daily || 0) - (user.dailyUsed || 0),
          monthlyRemaining: (user.limits?.monthly || 0) - (user.monthlyUsed || 0)
        }
      }
    });

  } catch (error) {
    console.error('Erro ao buscar limites:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// PUT /api/v1/user/limit - Atualiza limites (Admin only - JWT)
router.put('/', strictJwtRateLimiter, authenticate, requireAdmin, async (req, res) => {
  try {
    const { userId, limits } = req.body;

    if (!userId) {
      return res.status(400).json({
        error: 'Campo obrigatório faltando',
        message: 'O campo "userId" é obrigatório'
      });
    }

    if (!limits || typeof limits !== 'object') {
      return res.status(400).json({
        error: 'Limites inválidos',
        message: 'O campo "limits" deve ser um objeto com daily, monthly e perTransaction'
      });
    }

    const user = await Register.getById(userId);

    if (!user) {
      return res.status(404).json({
        error: 'Usuário não encontrado'
      });
    }

    const updatedLimits = {
      daily: limits.daily !== undefined ? parseInt(limits.daily) : user.limits?.daily || 1000000,
      monthly: limits.monthly !== undefined ? parseInt(limits.monthly) : user.limits?.monthly || 10000000,
      perTransaction: limits.perTransaction !== undefined ? parseInt(limits.perTransaction) : user.limits?.perTransaction || 500000
    };

    if (updatedLimits.daily < 0 || updatedLimits.monthly < 0 || updatedLimits.perTransaction < 0) {
      return res.status(400).json({
        error: 'Valores inválidos',
        message: 'Os limites devem ser valores positivos (em centavos)'
      });
    }

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.USER_LIMITS_UPDATED,
      entity: AUDIT_ENTITIES.USER,
      entityId: userId,
      userId: 'ADMIN',
      userEmail: user.email,
      dataBefore: {
        limits: user.limits
      },
      dataAfter: {
        limits: updatedLimits
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Limites atualizados para usuário ${user.name} (${user.email})`
    });

    const updatedUser = await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { limits: updatedLimits } },
      { new: true }
    );

    res.json({
      success: true,
      message: 'Limites atualizados com sucesso',
      data: {
        id: updatedUser.id,
        name: updatedUser.name,
        email: updatedUser.email,
        limits: updatedUser.limits,
        updatedAt: updatedUser.updatedAt
      }
    });

  } catch (error) {
    console.error('Erro ao atualizar limites:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


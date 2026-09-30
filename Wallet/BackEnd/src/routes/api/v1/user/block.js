import express from 'express';
import { authenticate } from '../../../../middlewares/auth.js';
import { requireAdmin } from '../../../../middlewares/admin.js';
import { strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import Register from '../../../../database/models/Register.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';

const router = express.Router();

// POST /api/v1/user/block - Bloqueia/desbloqueia usuário (Admin only)
router.post('/', strictJwtRateLimiter, authenticate, requireAdmin, async (req, res) => {
  try {
    const { userId, blocked } = req.body;

    if (!userId) {
      return res.status(400).json({
        error: 'Campo obrigatório faltando',
        message: 'O campo "userId" é obrigatório'
      });
    }

    if (typeof blocked !== 'boolean') {
      return res.status(400).json({
        error: 'Valor inválido',
        message: 'O campo "blocked" deve ser true ou false'
      });
    }

    const user = await Register.getById(userId);

    if (!user) {
      return res.status(404).json({
        error: 'Usuário não encontrado'
      });
    }

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: blocked ? AUDIT_ACTIONS.USER_BLOCKED : AUDIT_ACTIONS.USER_UNBLOCKED,
      entity: AUDIT_ENTITIES.USER,
      entityId: userId,
      userId: 'ADMIN',
      userEmail: user.email,
      dataBefore: {
        blocked: user.blocked,
        status: user.status
      },
      dataAfter: {
        blocked: blocked,
        status: user.status
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Usuário ${blocked ? 'bloqueado' : 'desbloqueado'}: ${user.name} (${user.email})`
    });

    const updatedUser = await Register.findOneAndUpdate(
      { id: user.id },
      { $set: { blocked: blocked } },
      { new: true }
    );

    res.json({
      success: true,
      message: `Usuário ${blocked ? 'bloqueado' : 'desbloqueado'} com sucesso`,
      data: {
        id: updatedUser.id,
        name: updatedUser.name,
        email: updatedUser.email,
        blocked: updatedUser.blocked,
        updatedAt: updatedUser.updatedAt
      }
    });

  } catch (error) {
    console.error('Erro ao bloquear/desbloquear usuário:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


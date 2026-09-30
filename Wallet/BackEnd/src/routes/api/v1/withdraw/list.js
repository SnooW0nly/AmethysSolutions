import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Withdraw from '../../../../database/models/Withdraw.js';
import Register from '../../../../database/models/Register.js';

const router = express.Router();

// GET /api/v1/withdraw/list - Lista todos os saques do usuário autenticado
// Rate limit: JWT = 60 req/min | API Key = 100 req/min
router.get('/', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const user = req.user;
    const { status, limit = 50, offset = 0 } = req.query;

    // Buscar saques apenas do usuário autenticado
    let withdraws = await Withdraw.getByUserId(user.id);

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
    console.error('Erro ao listar saques:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


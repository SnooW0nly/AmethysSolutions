import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Payment from '../../../../database/models/Payment.js';

const router = express.Router();

// GET /api/v1/payment/list - Lista todos os pagamentos do usuário autenticado
// Rate limit: JWT = 60 req/min | API Key = 100 req/min
router.get('/', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const user = req.user;
    const { status, limit = 50, offset = 0 } = req.query;

    // Buscar pagamentos apenas do usuário autenticado
    let payments = await Payment.getByUser(user.id);

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
    console.error('Erro ao listar pagamentos:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


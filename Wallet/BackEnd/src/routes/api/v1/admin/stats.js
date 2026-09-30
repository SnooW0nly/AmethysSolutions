import express from 'express';
import { strictJwtRateLimiter } from '../../../../middlewares/tokenRateLimiter.js';
import Register from '../../../../database/models/Register.js';
import Payment from '../../../../database/models/Payment.js';
import Withdraw from '../../../../database/models/Withdraw.js';
import InternalTransfer from '../../../../database/models/InternalTransfer.js';

const router = express.Router();

import { authenticateAdmin } from '../../../../middlewares/adminAuth.js';

// GET /api/v1/admin/stats - Estatísticas gerais do sistema (Admin only)
router.get('/', strictJwtRateLimiter, authenticateAdmin, async (req, res) => {
  try {
    // Usar agregações em paralelo para melhor performance
    const now = new Date();
    const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const last7d = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const last30d = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    // Executar todas as agregações em paralelo
    const [userAggregation, paymentAggregation, withdrawAggregation, transferAggregation, registrationAggregation] = await Promise.all([
      // Agregação de usuários
      Register.aggregate([
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            active: { $sum: { $cond: [{ $eq: ['$status', 'active'] }, 1, 0] } },
            blocked: { $sum: { $cond: [{ $eq: ['$blocked', true] }, 1, 0] } },
            deleted: { $sum: { $cond: [{ $eq: ['$status', 'deleted'] }, 1, 0] } },
            totalBalance: { $sum: { $ifNull: ['$balance', 0] } },
            totalSplit: { $sum: { $ifNull: ['$saldo_split', 0] } }
          }
        }
      ]),

      // Agregação de pagamentos
      Payment.aggregate([
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            active: { $sum: { $cond: [{ $eq: ['$status', 'ACTIVE'] }, 1, 0] } },
            completed: { $sum: { $cond: [{ $in: ['$status', ['COMPLETED', 'PAID']] }, 1, 0] } },
            pending: { $sum: { $cond: [{ $eq: ['$status', 'PENDING'] }, 1, 0] } },
            cancelled: { $sum: { $cond: [{ $eq: ['$status', 'CANCELLED'] }, 1, 0] } },
            totalValue: { $sum: { $ifNull: ['$value', 0] } },
            totalNetValue: {
              $sum: {
                $cond: [
                  { $in: ['$status', ['COMPLETED', 'PAID']] },
                  { $ifNull: ['$netValue', { $ifNull: ['$value', 0] }] },
                  0
                ]
              }
            },
            totalFees: {
              $sum: {
                $cond: [
                  { $in: ['$status', ['COMPLETED', 'PAID']] },
                  { $ifNull: ['$fee', 0] },
                  0
                ]
              }
            },
            pendingValue: {
              $sum: {
                $cond: [
                  { $in: ['$status', ['ACTIVE', 'PENDING']] },
                  { $ifNull: ['$value', 0] },
                  0
                ]
              }
            }
          }
        }
      ]),

      // Agregação de saques
      Withdraw.aggregate([
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            completed: { $sum: { $cond: [{ $eq: ['$status', 'COMPLETED'] }, 1, 0] } },
            failed: { $sum: { $cond: [{ $eq: ['$status', 'FAILED'] }, 1, 0] } },
            processing: { $sum: { $cond: [{ $in: ['$status', ['PROCESSING', 'PENDING']] }, 1, 0] } },
            totalAmount: {
              $sum: {
                $cond: [
                  { $eq: ['$status', 'COMPLETED'] },
                  { $ifNull: ['$value', { $ifNull: ['$amount', 0] }] },
                  0
                ]
              }
            }
          }
        }
      ]),

      // Agregação de transferências internas
      InternalTransfer.aggregate([
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            completed: { $sum: { $cond: [{ $eq: ['$status', 'COMPLETED'] }, 1, 0] } },
            totalAmount: {
              $sum: {
                $cond: [
                  { $eq: ['$status', 'COMPLETED'] },
                  { $ifNull: ['$amount', 0] },
                  0
                ]
              }
            }
          }
        }
      ]),

      // Agregação de cadastros por período
      Register.aggregate([
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            last24h: { $sum: { $cond: [{ $gte: ['$createdAt', last24h] }, 1, 0] } },
            last7d: { $sum: { $cond: [{ $gte: ['$createdAt', last7d] }, 1, 0] } },
            last30d: { $sum: { $cond: [{ $gte: ['$createdAt', last30d] }, 1, 0] } }
          }
        }
      ])
    ]);

    // Extrair resultados das agregações (com fallback para valores padrão)
    const userStats = userAggregation[0] || { total: 0, active: 0, blocked: 0, deleted: 0, totalBalance: 0, totalSplit: 0 };
    const paymentStats = paymentAggregation[0] || { total: 0, active: 0, completed: 0, pending: 0, cancelled: 0, totalValue: 0, totalNetValue: 0, totalFees: 0, pendingValue: 0 };
    const withdrawStats = withdrawAggregation[0] || { total: 0, completed: 0, failed: 0, processing: 0, totalAmount: 0 };
    const transferStats = transferAggregation[0] || { total: 0, completed: 0, totalAmount: 0 };
    const registrationsStats = registrationAggregation[0] || { total: 0, last24h: 0, last7d: 0, last30d: 0 };

    // Dinheiro movimentado (apenas transações completadas com sucesso)
    const totalMoneyMoved = paymentStats.totalNetValue + withdrawStats.totalAmount;

    // Estatísticas financeiras
    const financialStats = {
      totalReceived: paymentStats.totalNetValue,
      totalWithdrawn: withdrawStats.totalAmount,
      totalTransferred: transferStats.totalAmount,
      totalMoneyMoved: totalMoneyMoved,
      totalFeesCollected: paymentStats.totalFees,
      systemBalance: userStats.totalBalance,
      pendingPayments: paymentStats.pendingValue
    };

    res.json({
      success: true,
      data: {
        users: {
          total: userStats.total,
          active: userStats.active,
          blocked: userStats.blocked,
          deleted: userStats.deleted,
          totalBalance: userStats.totalBalance,
          totalSplit: userStats.totalSplit
        },
        payments: {
          total: paymentStats.total,
          active: paymentStats.active,
          completed: paymentStats.completed,
          pending: paymentStats.pending,
          cancelled: paymentStats.cancelled,
          totalValue: paymentStats.totalValue,
          totalNetValue: paymentStats.totalNetValue,
          totalFees: paymentStats.totalFees
        },
        withdraws: {
          total: withdrawStats.total,
          completed: withdrawStats.completed,
          failed: withdrawStats.failed,
          processing: withdrawStats.processing,
          totalAmount: withdrawStats.totalAmount
        },
        transfers: {
          total: transferStats.total,
          completed: transferStats.completed,
          totalAmount: transferStats.totalAmount
        },
        registrations: {
          total: registrationsStats.total,
          last24h: registrationsStats.last24h,
          last7d: registrationsStats.last7d,
          last30d: registrationsStats.last30d
        },
        financial: financialStats,
        split: {
          totalSplit: userStats.totalSplit
        },
        generatedAt: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('Erro ao buscar estatísticas:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;

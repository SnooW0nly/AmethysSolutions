import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Withdraw from '../../../../database/models/Withdraw.js';

const router = express.Router();

// GET /api/v1/withdraw/get/:id - Busca um saque específico (requer autenticação obrigatória)
// Rate limit: JWT = 60 req/min | API Key = 100 req/min
router.get('/:id', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const { id } = req.params;
    const withdraw = await Withdraw.getById(id);

    if (!withdraw) {
      return res.status(404).json({
        error: 'Saque não encontrado'
      });
    }

    // Verificar propriedade - apenas o usuário autenticado pode acessar seus próprios saques
    if (withdraw.userId !== req.user.id) {
      return res.status(403).json({
        error: 'Acesso negado',
        message: 'Você não tem permissão para acessar este saque'
      });
    }

    // Extrair fee e sent do metadata se disponível
    const fee = withdraw.metadata?.fee || withdraw.metadata?.userPaymentFee || null
    const sent = withdraw.metadata?.sent || withdraw.metadata?.amountToSend || null

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
        createdAt: withdraw.createdAt,
        updatedAt: withdraw.updatedAt
      }
    });

  } catch (error) {
    console.error('Erro ao buscar saque:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { defaultSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import Payment from '../../../../database/models/Payment.js';
import { checkTransaction } from '../../../../services/goatpayClient.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { generateUniqueId } from '../../../../services/security.js';

const router = express.Router();

// GET /api/v1/payment/get/:id - Busca um pagamento específico (requer autenticação obrigatória)
// Rate limit: JWT = 60 req/min | API Key = 100 req/min
router.get('/:id', defaultSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const { id } = req.params;
    let payment = await Payment.getById(id);

    if (!payment) {
      return res.status(404).json({
        error: 'Pagamento não encontrado'
      });
    }

    // Verificar propriedade - apenas o usuário autenticado pode acessar seus próprios pagamentos
    if (payment.userId !== req.user.id) {
      return res.status(403).json({
        error: 'Acesso negado',
        message: 'Você não tem permissão para acessar este pagamento'
      });
    }

    // Verificar se usuário é BLACK para usar credenciais corretas
    const userCategory = req.user.category || 'WHITE';
    const isBlack = userCategory === 'BLACK';

    // Consultar status na GoatPay se pendente
    // NOTA: NÃO atualizar status para COMPLETED aqui!
    // O crédito de saldo é feito EXCLUSIVAMENTE pelo paymentPoller.js
    // Se atualizarmos status aqui sem creditar saldo, o usuário perde dinheiro.
    // Este endpoint apenas retorna o status atual, sem modificar.
    let statusUpdated = false;

    // Podemos verificar na Mistic mas apenas para informar o usuário,
    // sem atualizar o banco de dados. O poller fará isso de forma segura.
    if ((payment.status === 'PENDING' || payment.status === 'ACTIVE') && payment.misticTransactionId) {
      try {
        const providerData = await checkTransaction({
          transactionId: payment.misticTransactionId,
          type: 'payment',
          useBlackCredentials: isBlack,
        });

        if (!providerData.simulated && !providerData.fromCache) {
          const providerStatus = providerData.transactionState || providerData.status || 'PENDENTE';

          // Apenas logar para debug, NÃO atualizar status no banco
          // O poller é o único responsável por atualizar status e creditar saldo
          if (providerStatus === 'COMPLETO' || providerStatus === 'COMPLETED') {
            console.log(`ℹ️ Payment ${payment.id} detectado como COMPLETED via GET, aguardando poller para creditar saldo`);
          }
        }
      } catch (syncError) {
        // Ignorar erros de sincronização - não é crítico para GET
      }
    }

    payment = await Payment.getById(id) || payment;

    res.json({
      success: true,
      statusUpdated: statusUpdated,
      data: {
        id: payment.id,
        transactionId: payment.correlationID || payment.id,
        value: payment.value,
        netValue: payment.netValue || payment.value,
        status: payment.status,
        qrCode: payment.qrCode || null,
        description: payment.description,
        createdAt: payment.createdAt,
        updatedAt: payment.updatedAt
      }
    });

  } catch (error) {
    console.error('Erro ao buscar pagamento:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


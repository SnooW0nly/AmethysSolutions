import express from 'express';
import { listTransactions } from '../../../../services/goatpayClient.js';

const router = express.Router();

router.get('{/:account}', async (req, res) => {
  const account = req.params.account || 'default';
  const useBlackCredentials = account === 'black';
  const apiKey = useBlackCredentials
    ? (process.env.GOATPAY_API_KEY_BLACK || process.env.GOATPAY_API_KEY)
    : process.env.GOATPAY_API_KEY;

  if (!apiKey) {
    return res.status(502).json({
      success: false,
      error: 'Credenciais GoatPay não configuradas (GOATPAY_API_KEY)',
    });
  }

  try {
    const limit = Math.min(parseInt(req.query.limit, 10) || 50, 100);
    const response = await listTransactions({ page: 1, pageSize: limit, useBlackCredentials });
    res.json({ success: true, data: response.data || response });
  } catch (error) {
    res.status(error.status || 502).json({
      success: false,
      error: error.error || error.message || 'Falha ao listar transações GoatPay',
    });
  }
});

export default router;

import express from 'express';
import { getBalance } from '../../../../services/goatpayClient.js';

const router = express.Router();

async function fetchGoatPayBalance(account = 'default') {
  const useBlackCredentials = account === 'black';
  const apiKey = useBlackCredentials
    ? (process.env.GOATPAY_API_KEY_BLACK || process.env.GOATPAY_API_KEY)
    : process.env.GOATPAY_API_KEY;

  if (!apiKey) {
    return {
      success: false,
      error: 'Credenciais GoatPay não configuradas (GOATPAY_API_KEY)',
    };
  }

  try {
    const response = await getBalance(useBlackCredentials);
    const data = response.data || response;
    return {
      success: true,
      balance: data.balance ?? data.availableAmount ?? 0,
      currency: data.currency || 'BRL',
      livre: data.livre,
      padrao: data.padrao,
    };
  } catch (error) {
    return {
      success: false,
      error: error.error || error.message || 'Falha ao consultar saldo GoatPay',
    };
  }
}

router.get('/all', async (_req, res) => {
  const white = await fetchGoatPayBalance('default');
  const black = await fetchGoatPayBalance('black');
  res.json({ success: true, white, black });
});

router.get('/white', async (_req, res) => {
  const result = await fetchGoatPayBalance('default');
  res.status(result.success ? 200 : 502).json(result);
});

router.get('/black', async (_req, res) => {
  const result = await fetchGoatPayBalance('black');
  res.status(result.success ? 200 : 502).json(result);
});

export default router;

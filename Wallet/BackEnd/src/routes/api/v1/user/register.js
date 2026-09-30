import express from 'express';
import { createRegister } from '../../../../services/registerService.js';
import { strictSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { getClientIP } from '../../../../utils/getClientIP.js';

const router = express.Router();

// POST /api/v1/user/register - Rate limit: JWT = 30 req/min | API Key = 50 req/min
// Cooldown de 30 segundos entre requisições de registro (implementado no serviço)
router.post('/', strictSmartRateLimiter, async (req, res) => {
  try {
    const { name, email, taxID, phone, pixKey, pixKeyType, webhookUrl, birthDate, zipCode } = req.body;

    // Validações
    if (!name || !email || !taxID || !birthDate || !zipCode || !pixKey || !pixKeyType) {
      return res.status(400).json({
        error: 'Campos obrigatórios faltando',
        required: ['name', 'email', 'taxID', 'birthDate', 'zipCode', 'pixKey', 'pixKeyType'],
        message: 'Nome, email, CPF, data de nascimento, CEP, chave PIX e tipo da chave PIX são obrigatórios'
      });
    }

    // Criar registro usando o serviço
    const register = await createRegister(
      { name, email, taxID, phone, pixKey, pixKeyType, webhookUrl, birthDate, zipCode },
      getClientIP(req),
      req.headers['user-agent']
    );

    res.status(201).json({
      success: true,
      message: 'Usuário registrado com sucesso',
      data: {
        id: register.id,
        apiKey: register.apiKey,
        name: register.name,
        email: register.email,
        pixKey: register.pixKey,
        pixKeyType: register.pixKeyType,
        balance: register.balance,
        paymentFee: register.paymentFee,
        splitFee: register.splitFee,
        limits: register.limits,
        message: 'Guarde sua API Key em local seguro!'
      }
    });

  } catch (error) {
    console.error('Erro ao registrar usuário:', error);

    // Erros de validação
    if (error.message.includes('já cadastrado') ||
      error.message.includes('inválido') ||
      error.message.includes('obrigatório')) {
      return res.status(400).json({
        error: error.message
      });
    }

    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


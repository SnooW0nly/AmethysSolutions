import express from 'express';
import rateLimit from 'express-rate-limit';
import { authenticate } from '../../../../middlewares/auth.js';
import User from '../../../../database/models/User.js';
import Register from '../../../../database/models/Register.js';
import VerificationCode from '../../../../database/models/VerificationCode.js';
import { generateVerificationCode, sendTransferVerificationCode } from '../../../../services/emailService.js';
import { getClientIP } from '../../../../utils/getClientIP.js';

const router = express.Router();

// Rate limiting para segurança de transferências (limites mais generosos)
const securityLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutos
  max: 30, // 30 tentativas por IP (aumentado de 10)
  message: {
    success: false,
    error: 'Muitas tentativas. Tente novamente em 15 minutos.',
  },
  // Usar função customizada para obter IP ao invés de confiar no trust proxy
  keyGenerator: (req) => {
    return getClientIP(req);
  }
});

// GET /api/v1/user/security - Obter status da segurança de transferências
router.get('/', authenticate, securityLimiter, async (req, res) => {
  try {
    const user = req.user;

    if (!user || !user.email) {
      return res.status(401).json({
        success: false,
        error: 'Autenticação necessária',
        message: 'Usuário não autenticado'
      });
    }

    // Buscar no Register usando email do User
    const register = await Register.findOne({ email: user.email.toLowerCase() });

    res.json({
      success: true,
      data: {
        transferSecurityEnabled: register?.transferSecurityEnabled || false
      }
    });
  } catch (error) {
    console.error('Erro ao buscar segurança:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/security/enable - Ativar segurança de transferências
router.post('/enable', authenticate, securityLimiter, async (req, res) => {
  try {
    const user = req.user;

    await Register.findOneAndUpdate(
      { email: user.email.toLowerCase() },
      {
        $set: {
          transferSecurityEnabled: true,
          updatedAt: new Date().toISOString()
        }
      }
    );

    res.json({
      success: true,
      message: 'Segurança de transferências ativada com sucesso',
      data: {
        transferSecurityEnabled: true
      }
    });
  } catch (error) {
    console.error('Erro ao ativar segurança:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/security/request-disable-code - Solicitar código para desativar segurança
router.post('/request-disable-code', authenticate, securityLimiter, async (req, res) => {
  try {
    const user = req.user;

    const register = await Register.findOne({ email: user.email.toLowerCase() });
    if (!register) {
      return res.status(404).json({
        success: false,
        error: 'Usuário não encontrado'
      });
    }

    if (!register.transferSecurityEnabled) {
      return res.status(400).json({
        success: false,
        error: 'Segurança não está ativada',
        message: 'A segurança de transferências já está desativada'
      });
    }

    const code = generateVerificationCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 10);

    await VerificationCode.create({
      email: user.email.toLowerCase(),
      code,
      expiresAt,
      type: 'transfer',
      metadata: {
        action: 'disable-security'
      },
      ip: req.ip,
      userAgent: req.headers['user-agent']
    });

    const emailSent = await sendTransferVerificationCode(
      user.email,
      code,
      0 // Valor zero para desativação
    );

    if (!emailSent) {
      console.error(`[SECURITY] Falha ao enviar código para ${user.email}`);
    }

    res.json({
      success: true,
      message: 'Código de verificação enviado para seu e-mail'
    });
  } catch (error) {
    console.error('Erro ao solicitar código:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/security/disable - Desativar segurança de transferências (requer código)
router.post('/disable', authenticate, securityLimiter, async (req, res) => {
  try {
    const user = req.user;
    const { code } = req.body;

    if (!code) {
      return res.status(400).json({
        success: false,
        error: 'Código obrigatório',
        message: 'Informe o código de verificação'
      });
    }

    const verificationCode = await VerificationCode.findOne({
      email: user.email.toLowerCase(),
      verified: false,
      expiresAt: { $gt: new Date() },
      type: 'transfer',
      'metadata.action': 'disable-security'
    }).sort({ createdAt: -1 });

    if (!verificationCode) {
      return res.status(401).json({
        success: false,
        error: 'Código inválido ou expirado'
      });
    }

    if (verificationCode.attempts >= 3) {
      return res.status(429).json({
        success: false,
        error: 'Limite de tentativas excedido. Solicite um novo código.'
      });
    }

    if (verificationCode.code !== code) {
      verificationCode.attempts += 1;
      await verificationCode.save();

      const remainingAttempts = 3 - verificationCode.attempts;
      return res.status(401).json({
        success: false,
        error: `Código inválido. ${remainingAttempts > 0 ? `Restam ${remainingAttempts} tentativa(s).` : 'Limite de tentativas excedido.'}`
      });
    }

    // Marcar código como verificado
    verificationCode.verified = true;
    await verificationCode.save();

    // Desativar segurança
    await Register.findOneAndUpdate(
      { email: user.email.toLowerCase() },
      {
        $set: {
          transferSecurityEnabled: false,
          updatedAt: new Date().toISOString()
        }
      }
    );

    res.json({
      success: true,
      message: 'Segurança de transferências desativada com sucesso',
      data: {
        transferSecurityEnabled: false
      }
    });
  } catch (error) {
    console.error('Erro ao desativar segurança:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/security/request-transfer-code - Solicitar código para transferência
router.post('/request-transfer-code', authenticate, securityLimiter, async (req, res) => {
  try {
    const user = req.user;
    const { amount } = req.body;

    if (!amount || amount <= 0) {
      return res.status(400).json({
        success: false,
        error: 'Valor inválido',
        message: 'Informe um valor válido para a transferência'
      });
    }

    const register = await Register.findOne({ email: user.email.toLowerCase() });
    if (!register) {
      return res.status(404).json({
        success: false,
        error: 'Usuário não encontrado'
      });
    }

    if (!register.transferSecurityEnabled) {
      return res.status(400).json({
        success: false,
        error: 'Segurança não ativada',
        message: 'A segurança de transferências não está ativada'
      });
    }

    const code = generateVerificationCode();
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 10);

    await VerificationCode.create({
      email: user.email.toLowerCase(),
      code,
      expiresAt,
      type: 'transfer',
      metadata: {
        action: 'transfer',
        amount: parseFloat(amount)
      },
      ip: req.ip,
      userAgent: req.headers['user-agent']
    });

    const emailSent = await sendTransferVerificationCode(
      user.email,
      code,
      parseFloat(amount)
    );

    if (!emailSent) {
      console.error(`[SECURITY] Falha ao enviar código para ${user.email}`);
    }

    res.json({
      success: true,
      message: 'Código de verificação enviado para seu e-mail'
    });
  } catch (error) {
    console.error('Erro ao solicitar código de transferência:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

// POST /api/v1/user/security/verify-transfer-code - Verificar código de transferência
router.post('/verify-transfer-code', authenticate, securityLimiter, async (req, res) => {
  try {
    const user = req.user;
    const { code, amount } = req.body;

    if (!code) {
      return res.status(400).json({
        success: false,
        error: 'Código obrigatório',
        message: 'Informe o código de verificação'
      });
    }

    if (!amount || amount <= 0) {
      return res.status(400).json({
        success: false,
        error: 'Valor inválido',
        message: 'Informe um valor válido para a transferência'
      });
    }

    const verificationCode = await VerificationCode.findOne({
      email: user.email.toLowerCase(),
      verified: false,
      expiresAt: { $gt: new Date() },
      type: 'transfer',
      'metadata.action': 'transfer',
      'metadata.amount': parseFloat(amount)
    }).sort({ createdAt: -1 });

    if (!verificationCode) {
      return res.status(401).json({
        success: false,
        error: 'Código inválido ou expirado'
      });
    }

    if (verificationCode.attempts >= 3) {
      return res.status(429).json({
        success: false,
        error: 'Limite de tentativas excedido. Solicite um novo código.'
      });
    }

    if (verificationCode.code !== code) {
      verificationCode.attempts += 1;
      await verificationCode.save();

      const remainingAttempts = 3 - verificationCode.attempts;
      return res.status(401).json({
        success: false,
        error: `Código inválido. ${remainingAttempts > 0 ? `Restam ${remainingAttempts} tentativa(s).` : 'Limite de tentativas excedido.'}`
      });
    }

    // Marcar código como verificado
    verificationCode.verified = true;
    await verificationCode.save();

    res.json({
      success: true,
      message: 'Código verificado com sucesso',
      verified: true
    });
  } catch (error) {
    console.error('Erro ao verificar código:', error);
    res.status(500).json({
      success: false,
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;


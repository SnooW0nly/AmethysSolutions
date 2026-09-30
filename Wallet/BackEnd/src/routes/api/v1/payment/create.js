import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { paymentSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { generateUniqueId } from '../../../../services/security.js';
import Payment from '../../../../database/models/Payment.js';
import Register from '../../../../database/models/Register.js';
import { createTransaction } from '../../../../services/goatpayClient.js';
import { calculateFee, calculateSplit } from '../../../../services/categoryService.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import Affiliate from '../../../../database/models/Affiliate.js';

const router = express.Router();

const MIN_PAYMENT = 100; // R$ 1,00 mínimo
const PROVIDER_FIXED_FEE = parseInt(process.env.GOATPAY_PROVIDER_FEE_CENTS || '0', 10);

// POST /api/v1/payment/create - Criar transação PIX (requer autenticação obrigatória)
// Rate limit: JWT = 20 req/min | API Key = 30 req/min
router.post('/', paymentSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const user = req.user;
    // Verificar limite por transação (máximo R$ 1.000,00)
    const MAX_PAYMENT_LIMIT = 100000; // R$ 1.000,00 em centavos
    let bodyData = req.body;

    if (typeof bodyData === 'string') {
      try {
        bodyData = JSON.parse(bodyData);
      } catch (e) {
        return res.status(400).json({
          error: 'Body inválido',
          message: 'O corpo da requisição deve ser um JSON válido'
        });
      }
    }

    const { value, description, coverFee, splitUser, splitTax } = bodyData || {};

    // Validar parâmetros de split interno (opcional)
    let splitRecipient = null;
    let splitPercentage = 0;
    if (splitUser) {
      // Buscar usuário de split na plataforma
      const Register = (await import('../../../../database/models/Register.js')).default;
      splitRecipient = await Register.findOne({
        email: splitUser.toLowerCase(),
        status: 'active'
      });
      if (!splitRecipient) {
        return res.status(400).json({
          error: 'Usuário de split não encontrado',
          message: `Não foi encontrada uma conta ativa com o email ${splitUser}`
        });
      }
      if (splitRecipient.id === user.id) {
        return res.status(400).json({
          error: 'Split inválido',
          message: 'Você não pode fazer split para sua própria conta'
        });
      }
      // Validar porcentagem
      splitPercentage = parseFloat(splitTax) || 0;
      if (splitPercentage <= 0 || splitPercentage > 100) {
        return res.status(400).json({
          error: 'Porcentagem de split inválida',
          message: 'splitTax deve ser um número entre 0.01 e 100'
        });
      }
    }

    if (value === undefined || value === null || value === '') {
      return res.status(400).json({
        error: 'Valor inválido',
        message: 'O campo "value" é obrigatório'
      });
    }

    let numericValue;
    if (typeof value === 'string') {
      const cleaned = value.trim().replace(/\./g, '').replace(',', '.');
      numericValue = parseFloat(cleaned);
    } else {
      numericValue = Number(value);
    }

    if (!isFinite(numericValue) || numericValue <= 0) {
      return res.status(400).json({
        error: 'Valor inválido',
        message: 'Envie um valor maior que zero'
      });
    }

    const valueInCents = Math.round(numericValue * 100);
    if (valueInCents < MIN_PAYMENT) {
      return res.status(400).json({
        error: 'Valor muito baixo',
        message: `O valor mínimo é R$ ${(MIN_PAYMENT / 100).toFixed(2)}`
      });
    }

    // Verificar limite máximo de R$ 1.000,00 por pagamento
    if (valueInCents > MAX_PAYMENT_LIMIT) {
      return res.status(400).json({
        error: 'Valor muito alto',
        message: `O valor máximo por pagamento é R$ ${(MAX_PAYMENT_LIMIT / 100).toFixed(2)}`
      });
    }

    // Categoria: secondary API key define o plano dela; main key e JWT usam user.category
    const usedKeyPlan = user.usedApiKey?.type === 'secondary' ? (user.usedApiKey.plan || 'WHITE') : null;
    const userCategory = usedKeyPlan || user.category || 'WHITE';
    const userTier = user.tier || 1;
    const isBlack = userCategory === 'BLACK';

    // Calcular taxa baseada na categoria
    const platformFee = await calculateFee(userCategory, userTier, valueInCents);
    const userPaymentFee = platformFee + PROVIDER_FIXED_FEE;

    // Se coverFee for true, o valor digitado é o valor líquido recebido, então o total do QR Code = valor + taxa
    // Se coverFee for false (padrão), o valor digitado é o total, então valor líquido = valor - taxa
    let finalValueInCents, netInCents;

    if (coverFee === true) {
      // Valor digitado é o valor líquido recebido
      netInCents = valueInCents;
      finalValueInCents = valueInCents + userPaymentFee; // Total do QR Code = valor líquido + taxa
    } else {
      // Valor digitado é o total (comportamento padrão)
      finalValueInCents = valueInCents;
      netInCents = valueInCents - userPaymentFee;
    }

    if (netInCents <= 0) {
      return res.status(400).json({
        error: 'Valor insuficiente',
        message: `O valor líquido deve ser maior que zero. ${coverFee ? 'Com "cobrir taxa" ativado, o valor digitado deve ser maior que zero.' : `O valor deve ser maior que a taxa de R$ ${(userPaymentFee / 100).toFixed(2)}`}`
      });
    }

    // Gerar ID único para a transação
    const paymentId = generateUniqueId();
    const now = new Date().toISOString();

    // Criar cobrança PIX na GoatPay (POST /payment-pix/create)
    let providerResponse;
    try {
      const splitEmail = process.env.EMAIL_SPLIT;
      const transactionData = {
        amount: finalValueInCents / 100,
        payerName: user.name,
        payerDocument: user.taxID || '55713741010',
        transactionId: paymentId,
        coverFee: coverFee === true,
        description: `Deposito - ${user.name}`,
        ...(user.goatpaySubaccountId ? { subaccountId: user.goatpaySubaccountId } : {}),
      };

      // Calcular split:
      // WHITE: Não faz split (dinheiro já cai na conta principal)
      // BLACK: 1% + R$ 1,00 (transfere da conta Black para a principal)
      let splitAmountInCents = 0;

      if (isBlack) {
        splitAmountInCents = await calculateSplit(userCategory, userTier, finalValueInCents);
      }

      if (splitEmail && splitAmountInCents > 0) {
        // Split interno GoatPay (splitUser + splitTax)
        // splitTax = (splitAmount / transactionAmount) * 100 (porcentagem)
        // Usar aritmética de alta precisão para evitar erros de ponto flutuante
        const splitAmountInReais = splitAmountInCents / 100;
        const transactionAmount = finalValueInCents / 100;

        // Calcular porcentagem com 6 casas decimais de precisão
        // Exemplo: split R$ 1,00 em transação de R$ 100,00 = 1%
        const splitTaxRaw = (splitAmountInReais / transactionAmount) * 100;
        const splitTax = Math.round(splitTaxRaw * 10000) / 10000;

        transactionData.splitUser = splitEmail;
        transactionData.splitTax = splitTax;
        // Não logar valores ou informações sensíveis
        // console.log removido para segurança
      }

      // Passar credenciais BLACK se for categoria BLACK
      transactionData.useBlackCredentials = isBlack;

      providerResponse = await createTransaction(transactionData);

      if (providerResponse.simulated) {
        providerResponse = {
          data: {
            transactionId: paymentId,
            transactionState: 'PENDENTE',
            transactionMethod: 'PIX',
            transactionAmount: numericValue,
            transactionFee: 0.50,
            qrcodeUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
            copyPaste: paymentId
          }
        };
      }

    } catch (providerErr) {
      const errMsg = providerErr?.message || providerErr?.error || JSON.stringify(providerErr);
      console.error('❌ Erro ao criar cobrança PIX na GoatPay:', errMsg);
      if (providerErr?.data) console.error('❌ Detalhes GoatPay:', JSON.stringify(providerErr.data));
      return res.status(providerErr.status || 500).json({
        error: 'Erro ao criar transação na gateway',
        message: providerErr.error || providerErr.message || 'Falha ao criar transação',
        details: providerErr.data || null
      });
    }

    const providerData = providerResponse.data || providerResponse;
    const providerTransactionId = providerData.transactionId || providerData.id || paymentId;
    const providerStatus = providerData.transactionState || providerData.status || 'PENDENTE';
    const localStatus = providerStatus === 'COMPLETO' || providerStatus === 'COMPLETED' ? 'COMPLETED' : 'PENDING';

    let qrcodeUrl = providerData.qrCodeBase64 || providerData.qrcodeUrl || providerData.qrcode || null;
    const copyPaste = providerData.copyPaste || providerData.pixKey || providerTransactionId;

    // Salvar pagamento
    const paymentData = {
      id: paymentId,
      userId: user.id,
      correlationID: providerTransactionId,
      value: finalValueInCents, // Valor total do QR Code (pode incluir taxa se coverFee for true)
      netValue: netInCents, // Valor líquido recebido (valor total - taxa)
      fee: userPaymentFee, // Taxa do plano do usuário
      description: description || `Deposito - ${user.name}`,
      status: localStatus,
      misticTransactionId: providerTransactionId,
      qrCode: qrcodeUrl,
      metadata: {
        ...providerResponse,
        provider: 'goatpay',
        useBlackCredentials: isBlack,
        coverFee: coverFee || false,
        // Split interno (se configurado)
        internalSplit: splitRecipient ? {
          recipientId: splitRecipient.id,
          recipientEmail: splitRecipient.email,
          splitPercentage: splitPercentage,
          processed: false
        } : null
      }
    };

    const payment = await Payment.create(paymentData);

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PAYMENT_CREATED,
      entity: AUDIT_ENTITIES.PAYMENT,
      entityId: paymentId,
      userId: user.id,
      userEmail: user.email,
      dataAfter: {
        value: paymentData.value,
        netValue: netInCents,
        fee: userPaymentFee,
        platformFee: platformFee,
        providerFee: PROVIDER_FIXED_FEE,
        status: paymentData.status,
        coverFee: coverFee || false
      },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Deposito criado: R$ ${(finalValueInCents / 100).toFixed(2)} (líquido: R$ ${(netInCents / 100).toFixed(2)}) - ${user.name}${coverFee ? ' [Cobrir taxa]' : ''}`
    });

    // Limites diários e mensais removidos - apenas limite por transação de R$ 1.000,00

    res.status(201).json({
      success: true,
      message: 'Transação criada com sucesso. Aguarde o deposito via PIX.',
      data: {
        id: payment.id,
        transactionId: providerTransactionId,
        value: paymentData.value, // Valor total do QR Code
        valueInReais: finalValueInCents / 100,
        netValue: netInCents, // Valor líquido recebido
        fee: userPaymentFee,
        status: localStatus,
        qrcodeUrl: qrcodeUrl,
        copyPaste: copyPaste,
        createdAt: payment.createdAt
      }
    });
  } catch (error) {
    // Não logar detalhes do erro que podem conter informações sensíveis (UIDs, valores, etc)
    console.error('Erro ao criar pagamento');
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;
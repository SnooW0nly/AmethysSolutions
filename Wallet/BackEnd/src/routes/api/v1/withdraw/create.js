import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { strictSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { generateUniqueId } from '../../../../services/security.js';
import Withdraw from '../../../../database/models/Withdraw.js';
import Register from '../../../../database/models/Register.js';
import VerificationCode from '../../../../database/models/VerificationCode.js';
import { withdraw as goatpayWithdraw, checkTransaction } from '../../../../services/goatpayClient.js';
import { calculateFee, calculateSplit } from '../../../../services/categoryService.js';
import { getWithdrawFee } from '../../../../services/feeService.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { sendWebhookEvent } from '../../../../services/webhookService.js';
import Affiliate from '../../../../database/models/Affiliate.js';


const router = express.Router();

const MIN_WITHDRAW = 500; // R$ 5,00

// POST /api/v1/withdraw/create - Saque imediato (requer autenticação obrigatória)
// Rate limit: JWT = 30 req/min | API Key = 50 req/min
router.post('/', strictSmartRateLimiter, authenticateUser, async (req, res) => {
  try {
    const user = req.user;
    const { amount, pixKey, pixKeyType, description, coverFee, verificationCode, splitUser, splitTax } = req.body || {};

    // Verificar se usuário está bloqueado - simular erro genérico
    if (user.blocked) {
      return res.status(500).json({
        error: 'Erro ao processar saque na gateway.',
        message: 'Falha no processamento. Tente novamente mais tarde.',
        details: null
      });
    }

    // Validar parâmetros de split interno (opcional)
    let splitRecipient = null;
    let splitPercentage = 0;
    if (splitUser) {
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
      splitPercentage = parseFloat(splitTax) || 0;
      if (splitPercentage <= 0 || splitPercentage > 100) {
        return res.status(400).json({
          error: 'Porcentagem de split inválida',
          message: 'splitTax deve ser um número entre 0.01 e 100'
        });
      }
    }

    // Verificar se já existe um saque em processamento para este usuário
    const pendingWithdraw = await Withdraw.findOne({
      userId: user.id,
      status: { $in: ['PENDING', 'WAITING', 'CREATED', 'PROCESSING'] }
    });

    if (pendingWithdraw) {
      return res.status(400).json({
        error: 'Saque em processamento',
        message: 'Você já possui um saque em processamento. Aguarde a conclusão antes de solicitar um novo saque.',
        pendingWithdrawId: pendingWithdraw.id,
        pendingWithdrawStatus: pendingWithdraw.status,
        pendingWithdrawValue: pendingWithdraw.value,
        pendingWithdrawCreatedAt: pendingWithdraw.createdAt
      });
    }

    if (amount === undefined || amount === null || amount === '') {
      return res.status(400).json({
        error: 'Valor inválido',
        message: 'Informe o campo "amount"'
      });
    }

    // Verificar se segurança de transferências está ativada
    // Bypass para requisições via API Key (integrações não precisam de código de verificação)
    const userDoc = await Register.findOne({ id: user.id });
    if (userDoc?.transferSecurityEnabled && req.authMethod !== 'apiKey') {
      if (!verificationCode) {
        return res.status(400).json({
          error: 'Código de verificação obrigatório',
          message: 'A segurança de transferências está ativada. É necessário informar o código de verificação enviado por e-mail.'
        });
      }

      // Calcular valor final para verificação
      let numericAmount;
      if (typeof amount === 'string') {
        const cleaned = amount.trim().replace(/\./g, '').replace(',', '.');
        numericAmount = parseFloat(cleaned);
      } else {
        numericAmount = Number(amount);
      }

      const userCategory = user.category || 'WHITE';
      const userTier = user.tier || 1;

      // Taxa de saque PIX vem do FeeConfig (configurável via /admin/fees). Default: 30c
      const baseAmountInCents = Math.round(numericAmount * 100);
      const userPaymentFee = await getWithdrawFee();

      let amountInCents;
      if (coverFee === true) {
        amountInCents = baseAmountInCents + userPaymentFee;
      } else {
        amountInCents = baseAmountInCents;
      }

      // Verificar código de verificação
      // NOTA: metadata.userId é validado após o findOne pois códigos antigos podem não ter o campo
      const codeDoc = await VerificationCode.findOne({
        email: userDoc.email.toLowerCase(),
        code: verificationCode,
        type: 'transfer',
        verified: false,
        expiresAt: { $gt: new Date() },
        'metadata.action': 'transfer',
        'metadata.amount': amountInCents / 100
      });

      if (!codeDoc) {
        return res.status(400).json({
          error: 'Código de verificação inválido',
          message: 'O código de verificação é inválido, expirou ou não corresponde a esta transferência. Solicite um novo código.'
        });
      }

      // Validar userId se o campo existir no documento (proteção extra)
      if (codeDoc.metadata?.userId && codeDoc.metadata.userId !== user.id) {
        return res.status(400).json({
          error: 'Código de verificação inválido',
          message: 'O código de verificação não pertence a este usuário.'
        });
      }

      if (codeDoc.attempts >= 3) {
        return res.status(400).json({
          error: 'Muitas tentativas',
          message: 'Você excedeu o número máximo de tentativas. Solicite um novo código.'
        });
      }

      // Marcar código como verificado e usado
      codeDoc.verified = true;
      await codeDoc.save();
    }

    let finalPixKey = pixKey || user.pixKey;
    let finalPixKeyType = pixKeyType || user.pixKeyType;

    if (!finalPixKey || !finalPixKeyType) {
      return res.status(400).json({
        error: 'Chave PIX não encontrada',
        message: 'Informe "pixKey" e "pixKeyType" na requisição ou cadastre uma chave PIX no seu registro'
      });
    }

    const validPixKeyTypes = ['CPF', 'CNPJ', 'EMAIL', 'PHONE', 'RANDOM', 'COPYPASTE'];
    if (!validPixKeyTypes.includes(finalPixKeyType.toUpperCase())) {
      return res.status(400).json({
        error: 'Tipo de chave PIX inválido',
        message: `O tipo deve ser um dos seguintes: ${validPixKeyTypes.join(', ')}`
      });
    }

    let numericAmount;
    if (typeof amount === 'string') {
      const cleaned = amount.trim().replace(/\./g, '').replace(',', '.');
      numericAmount = parseFloat(cleaned);
    } else {
      numericAmount = Number(amount);
    }

    if (!isFinite(numericAmount) || numericAmount <= 0) {
      return res.status(400).json({
        error: 'Valor inválido',
        message: 'O valor deve ser maior que zero'
      });
    }

    const userCategory = user.category || 'WHITE';
    const userTier = user.tier || 1;
    const userPlan = userCategory; // Definir userPlan para uso posterior
    const isBlack = userCategory === 'BLACK';

    // Calcular taxa baseada na categoria
    const baseAmountInCents = Math.round(numericAmount * 100);
    // Taxa de saque PIX vem do FeeConfig (configurável via /admin/fees). Default: 30c
    const userPaymentFee = await getWithdrawFee();
    const userSplitFee = await calculateSplit(userCategory, userTier, baseAmountInCents);

    // Se coverFee for true, o valor digitado é o valor enviado, então o total debitado = valor + taxa
    // Se coverFee for false (padrão), o valor digitado é o total, então valor enviado = valor - taxa
    let amountInCents, amountToSend;

    if (coverFee === true) {
      // Valor digitado é o valor enviado
      amountToSend = baseAmountInCents;
      amountInCents = baseAmountInCents + userPaymentFee; // Total debitado = valor enviado + taxa
    } else {
      // Valor digitado é o total (comportamento padrão)
      amountInCents = baseAmountInCents;
      amountToSend = baseAmountInCents - userPaymentFee;
    }

    if (amountToSend < MIN_WITHDRAW) {
      return res.status(400).json({
        error: 'Valor abaixo do mínimo',
        message: `O valor mínimo para saque é R$ ${(MIN_WITHDRAW / 100).toFixed(2)}`
      });
    }
    if (amountToSend <= 0) {
      return res.status(400).json({
        error: 'Valor insuficiente',
        message: `O valor do saque deve ser maior que a taxa de R$ ${(userPaymentFee / 100).toFixed(2)}`
      });
    }

    const withdrawId = generateUniqueId();

    // ========== FIX: Débito atômico ANTES da chamada Mistic ==========
    // Isso previne race conditions onde múltiplas requisições passam o check de saldo
    // Usando findOneAndUpdate com condição de saldo para garantir atomicidade
    const balanceDeductResult = await Register.findOneAndUpdate(
      {
        id: user.id,
        balance: { $gte: amountInCents }  // Só debita se tiver saldo suficiente
      },
      { $inc: { balance: -amountInCents } },
      { new: true }
    );

    if (!balanceDeductResult) {
      // Re-buscar saldo atual para dar mensagem de erro precisa
      const currentUser = await Register.getById(user.id);
      const currentBalance = currentUser?.balance || 0;
      console.log(`❌ Saque negado: Saldo insuficiente. Saldo atual: R$ ${(currentBalance / 100).toFixed(2)}, Requerido: R$ ${(amountInCents / 100).toFixed(2)}`);
      return res.status(400).json({
        error: 'Saldo insuficiente',
        balance: currentBalance,
        required: amountInCents
      });
    }

    const balanceBefore = (balanceDeductResult.balance || 0) + amountInCents; // Reconstruir saldo anterior
    const balanceAfter = balanceDeductResult.balance || 0;
    console.log(`💸 Saque: Saldo debitado atomicamente. Antes: R$ ${(balanceBefore / 100).toFixed(2)} → Depois: R$ ${(balanceAfter / 100).toFixed(2)} (debitado: R$ ${(amountInCents / 100).toFixed(2)})`);

    // ========== Efetuar saque via GoatPay (POST /transfer-pix/create) ==========
    let providerResp;
    try {
      providerResp = await goatpayWithdraw({
        amount: amountToSend / 100,
        pixKey: finalPixKey,
        pixKeyType: finalPixKeyType.toUpperCase() === 'COPYPASTE' ? 'copypaste' : finalPixKeyType.toUpperCase(),
        coverFee: coverFee !== false,
        externalReference: withdrawId,
        description: `Transferência - ${user.name}`,
        useBlackCredentials: isBlack,
        ...(user.goatpaySubaccountId ? { subaccountId: user.goatpaySubaccountId } : {}),
      });
    } catch (providerError) {
      console.error(`❌ GoatPay falhou, devolvendo saldo de R$ ${(amountInCents / 100).toFixed(2)}`);
      try {
        await Register.findOneAndUpdate(
          { id: user.id },
          { $inc: { balance: amountInCents } }
        );
        console.log(`✅ Saldo devolvido com sucesso após falha da GoatPay`);
      } catch (refundError) {
        console.error(`❌ ERRO CRÍTICO: Não foi possível devolver saldo após falha da GoatPay:`, refundError.message);
      }
      return res.status(providerError.status || 500).json({
        error: 'Erro ao processar saque na gateway.',
        message: providerError.error || providerError.message || 'Falha no saque',
        details: providerError.data || null
      });
    }

    // Invalidar cache do balance para garantir que o saldo atualizado seja retornado
    // Cache removido
    // clearCache('/v1/user/balance');

    // Acumular splitFee do usuário no saldo de split
    // Regra:
    // Enterprise: 0
    // Não indicado: userSplitFee
    // Indicado: userSplitFee + commission

    let adjustedSplitFee = 0;

    if (userPlan !== 'ENTERPRISE') {
      let commission = 0;
      if (user.referredBy) {
        const affiliate = await Affiliate.findOne({ id: user.referredBy });
        commission = affiliate?.commissionRate || 5;
      }

      // userSplitFee já deve ser a "taxa do plano - 0,50" configurada no DB
      if (user.referredBy) {
        adjustedSplitFee = Math.max(0, userSplitFee - commission);
      } else {
        adjustedSplitFee = userSplitFee;
      }
    }

    await Register.findOneAndUpdate(
      { id: user.id },
      {
        $inc: {
          saldo_split: adjustedSplitFee
        }
      }
    );
    const newSplitBalance = (user.saldo_split || 0) + adjustedSplitFee;
    console.log(`💰 Saldo split atualizado: +R$ ${(adjustedSplitFee / 100).toFixed(2)} (total: R$ ${(newSplitBalance / 100).toFixed(2)})${user.referredBy ? ' [Usuário indicado - split reduzido]' : ''}`);

    // Salvar saque
    const withdrawData = {
      id: withdrawId,
      userId: user.id,
      correlationID: providerResp?.data?.transactionId || withdrawId,
      value: amountInCents,
      description: description || `Transferência - ${user.name}`,
      status: 'PROCESSING',
      pixKey: finalPixKey,
      pixKeyType: finalPixKeyType.toUpperCase(),
      transactionId: providerResp?.data?.transactionId || null,
      metadata: {
        ...providerResp,
        provider: 'goatpay',
        useBlackCredentials: isBlack,
        fee: userPaymentFee,
        sent: amountToSend,
        // Split interno (se configurado)
        internalSplit: splitRecipient ? {
          recipientId: splitRecipient.id,
          recipientEmail: splitRecipient.email,
          splitPercentage: splitPercentage,
          processed: false
        } : null
      }
    };

    console.log(`📝 Salvando saque no MongoDB:`, JSON.stringify({
      id: withdrawData.id,
      userId: withdrawData.userId,
      value: withdrawData.value,
      status: withdrawData.status
    }));

    let withdraw;
    try {
      withdraw = await Withdraw.create(withdrawData);
      console.log(`✅ Saque ${withdrawId} salvo com sucesso no MongoDB. ID do documento: ${withdraw._id}`);
    } catch (saveError) {
      console.error(`❌ ERRO ao salvar saque no MongoDB:`, saveError.message);
      console.error(`   Dados do saque:`, JSON.stringify(withdrawData, null, 2));

      // Devolver saldo já que o saque não foi salvo
      try {
        await Register.findOneAndUpdate(
          { id: user.id },
          { $inc: { balance: amountInCents } }
        );
        console.log(`💰 Saldo devolvido após falha ao salvar saque`);
      } catch (refundError) {
        console.error(`❌ ERRO CRÍTICO: Não foi possível devolver saldo após falha:`, refundError.message);
      }

      return res.status(500).json({
        error: 'Erro ao salvar saque',
        message: 'Ocorreu um erro ao registrar o saque. Seu saldo foi devolvido. Tente novamente.'
      });
    }


    // Verificar status rapidamente após alguns segundos (se tiver transactionId)
    const transactionId = providerResp?.data?.transactionId || providerResp?.transaction?.transactionId;
    if (transactionId) {
      // Aguardar 3 segundos e verificar status
      setTimeout(async () => {
        try {
          const checkResp = await checkTransaction({ transactionId, type: 'transfer', useBlackCredentials: isBlack });
          const checkData = checkResp.transaction || checkResp.data || checkResp;
          const misticStatus = (checkData.transactionState || checkData.status || checkData.state || '').toString().toUpperCase();

          console.log(`📋 Verificação rápida saque ${withdrawId} - Status: "${misticStatus}"`);

          let newStatus = 'PROCESSING';
          // Estados de sucesso (inglês e português)
          if (['COMPLETED', 'PAID', 'DONE', 'SUCCESS', 'COMPLETO', 'PAGO', 'CONCLUIDO', 'CONCLUÍDA', 'FINALIZADO', 'APROVADO'].includes(misticStatus)) {
            newStatus = 'COMPLETED';
            // Estados de falha (inglês e português)
          } else if (['FAILED', 'ERROR', 'CANCELLED', 'CANCELED', 'FALHA', 'ERRO', 'CANCELADO', 'REJEITADO', 'RECUSADO'].includes(misticStatus)) {
            newStatus = 'FAILED';
          }

          if (newStatus !== 'PROCESSING') {
            // ========== FIX: Se falhou, devolver saldo ao usuário ==========
            if (newStatus === 'FAILED') {
              try {
                console.log(`💰 Devolvendo saldo de saque falho (verificação rápida): R$ ${(amountInCents / 100).toFixed(2)} para usuário ${user.id}`);
                await Register.findOneAndUpdate(
                  { id: user.id },
                  { $inc: { balance: amountInCents } }
                );
                console.log(`✅ Saldo devolvido com sucesso para saque ${withdrawId} (verificação rápida)`);
              } catch (refundError) {
                console.error(`❌ Erro ao devolver saldo do saque ${withdrawId}:`, refundError.message);
              }
            }

            await Withdraw.findOneAndUpdate(
              { id: withdrawId },
              {
                $set: {
                  status: newStatus,
                  metadata: { ...(withdraw.metadata || {}), checkResponse: checkResp },
                  ...(newStatus === 'COMPLETED' ? { completedAt: new Date().toISOString() } : {}),
                  ...(newStatus === 'FAILED' ? { failedAt: new Date().toISOString(), failureReason: checkData.error || 'Falha no processamento', refunded: true } : {})
                }
              }
            );
            console.log(`✅ Saque ${withdrawId} atualizado para ${newStatus} após verificação rápida`);
          }
        } catch (checkError) {
          console.warn(`⚠️ Erro ao verificar status do saque ${withdrawId}:`, checkError.message);
        }
      }, 3000); // 3 segundos
    }

    // Log de auditoria
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.WITHDRAW_CREATED,
      entity: AUDIT_ENTITIES.WITHDRAW,
      entityId: withdrawId,
      userId: user.id,
      userEmail: user.email,
      dataAfter: {
        value: amountInCents,
        sent: amountToSend,
        fee: userPaymentFee,
        pixKey: finalPixKey
      },
      metadata: { providerResponse: providerResp },
      ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
      userAgent: req.headers['user-agent'],
      description: `Saque criado: R$ ${(amountInCents / 100).toFixed(2)} - ${user.name}`
    });

    if (providerResp?.success === true || providerResp?.status === 'completed') {
      await sendWebhookEvent(user.id, 'withdrawal.completed', {
        txid: withdrawId,
        amount: (amountInCents / 100).toFixed(2),
        netAmount: (amountToSend / 100).toFixed(2),
        fee: (userPaymentFee / 100).toFixed(2),
        status: 'completed',
        type: 'pix',
        pixKey: finalPixKey,
        completedAt: Date.now()
      });
    } else if (providerResp?.success === false || providerResp?.error) {
      await sendWebhookEvent(user.id, 'withdrawal.failed', {
        txid: withdrawId,
        amount: (amountInCents / 100).toFixed(2),
        status: 'failed',
        reason: providerResp?.error || providerResp?.message || 'Erro desconhecido',
        failedAt: Date.now()
      });
    }

    // Notificação Discord
    (async () => {
      try {
        const { notifyWithdraw } = await import('../../../../services/discordNotifier.js');
        await notifyWithdraw({
          withdrawId: withdraw.id,
          email: user.email,
          value: amountInCents,
          fee: userPaymentFee,
          sent: amountToSend,
          status: withdraw.status,
          pixKey: finalPixKey,
          pixKeyType: finalPixKeyType,
          plan: userPlan,
          ip: req.ip || req.headers['x-forwarded-for'] || 'N/A'
        });
      } catch (e) {
        console.error('[DISCORD] Erro ao notificar saque:', e.message);
      }
    })();

    res.status(201).json({
      success: true,
      message: 'Saque processado com sucesso',
      data: {
        id: withdraw.id,
        value: amountInCents,
        fee: userPaymentFee,
        sent: amountToSend,
        status: withdraw.status,
        pixKey: finalPixKey,
        createdAt: withdraw.createdAt
      }
    });

  } catch (error) {
    console.error('Erro ao criar saque:', error);
    res.status(500).json({
      error: 'Erro interno do servidor',
      message: error.message
    });
  }
});

export default router;

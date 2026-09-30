import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { strictSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { generateUniqueId } from '../../../../services/security.js';
import Withdraw from '../../../../database/models/Withdraw.js';
import Register from '../../../../database/models/Register.js';
import { cryptoWithdraw as goatpayCryptoWithdraw } from '../../../../services/goatpayClient.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';
import { sendWebhookEvent } from '../../../../services/webhookService.js';

const router = express.Router();

// Constantes de limites e taxas
const MIN_CRYPTO_WITHDRAW = 2000;   // R$ 20,00 em centavos
const MAX_CRYPTO_WITHDRAW = 300000; // R$ 3.000,00 em centavos
const CRYPTO_FEE_PERCENT = 6;       // 6%
const CRYPTO_FEE_FIXED = 200;       // R$ 2,00 em centavos

// Regex para validar wallet BEP20
const BEP20_WALLET_REGEX = /^0x[a-fA-F0-9]{40}$/;

// POST /api/v1/withdraw/crypto - Saque via Crypto (USDT BEP20)
router.post('/', strictSmartRateLimiter, authenticateUser, async (req, res) => {
    try {
        const user = req.user;
        const { amount, wallet, description } = req.body || {};

        // Verificar se usuário está bloqueado
        if (user.blocked) {
            return res.status(500).json({
                error: 'Erro ao processar saque crypto.',
                message: 'Falha no processamento. Tente novamente mais tarde.'
            });
        }

        // Validar amount
        if (amount === undefined || amount === null || amount === '') {
            return res.status(400).json({
                error: 'Valor inválido',
                message: 'Informe o campo "amount"'
            });
        }

        // Validar wallet
        if (!wallet) {
            return res.status(400).json({
                error: 'Wallet não informada',
                message: 'Informe o campo "wallet" com o endereço BEP20'
            });
        }

        if (!BEP20_WALLET_REGEX.test(wallet)) {
            return res.status(400).json({
                error: 'Wallet inválida',
                message: 'O endereço da wallet deve estar no formato BEP20 (0x seguido de 40 caracteres hexadecimais)'
            });
        }

        // Verificar se já existe um saque em processamento
        const pendingWithdraw = await Withdraw.findOne({
            userId: user.id,
            status: { $in: ['PENDING', 'WAITING', 'CREATED', 'PROCESSING', 'QUEUED'] }
        });

        if (pendingWithdraw) {
            return res.status(400).json({
                error: 'Saque em processamento',
                message: 'Você já possui um saque em processamento. Aguarde a conclusão antes de solicitar um novo.',
                pendingWithdrawId: pendingWithdraw.id,
                pendingWithdrawStatus: pendingWithdraw.status
            });
        }

        // Converter amount para número
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

        const amountInCents = Math.round(numericAmount * 100);

        // Validar limites
        if (amountInCents < MIN_CRYPTO_WITHDRAW) {
            return res.status(400).json({
                error: 'Valor abaixo do mínimo',
                message: `O valor mínimo para saque crypto é R$ ${(MIN_CRYPTO_WITHDRAW / 100).toFixed(2)}`
            });
        }

        if (amountInCents > MAX_CRYPTO_WITHDRAW) {
            return res.status(400).json({
                error: 'Valor acima do máximo',
                message: `O valor máximo para saque crypto é R$ ${(MAX_CRYPTO_WITHDRAW / 100).toFixed(2)}`
            });
        }

        // Calcular taxa: 6% + R$ 2,00
        const percentageFee = Math.round(amountInCents * CRYPTO_FEE_PERCENT / 100);
        const totalFee = percentageFee + CRYPTO_FEE_FIXED;
        const totalDebit = amountInCents + totalFee;

        // Débito atômico do saldo
        const balanceDeductResult = await Register.findOneAndUpdate(
            {
                id: user.id,
                balance: { $gte: totalDebit }
            },
            { $inc: { balance: -totalDebit } },
            { new: true }
        );

        if (!balanceDeductResult) {
            const currentUser = await Register.getById(user.id);
            const currentBalance = currentUser?.balance || 0;
            return res.status(400).json({
                error: 'Saldo insuficiente',
                message: `Saldo insuficiente. Necessário: R$ ${(totalDebit / 100).toFixed(2)}, Disponível: R$ ${(currentBalance / 100).toFixed(2)}`,
                balance: currentBalance,
                required: totalDebit
            });
        }

        const balanceBefore = (balanceDeductResult.balance || 0) + totalDebit;
        const balanceAfter = balanceDeductResult.balance || 0;
        console.log(`💎 Saque Crypto: Saldo debitado. Antes: R$ ${(balanceBefore / 100).toFixed(2)} → Depois: R$ ${(balanceAfter / 100).toFixed(2)}`);

        const withdrawId = generateUniqueId();

        let providerResp;
        try {
            providerResp = await goatpayCryptoWithdraw({
                amount: numericAmount,
                wallet,
                externalReference: withdrawId,
                description: description || 'Saque Crypto',
            });
        } catch (providerError) {
            console.error(`❌ GoatPay crypto falhou, devolvendo saldo de R$ ${(totalDebit / 100).toFixed(2)}`);
            try {
                await Register.findOneAndUpdate(
                    { id: user.id },
                    { $inc: { balance: totalDebit } }
                );
                console.log(`✅ Saldo devolvido com sucesso após falha da GoatPay`);
            } catch (refundError) {
                console.error(`❌ ERRO CRÍTICO: Não foi possível devolver saldo:`, refundError.message);
            }
            return res.status(providerError.status || 500).json({
                error: 'Erro ao processar saque crypto na gateway.',
                message: providerError.error || providerError.message || 'Falha no saque crypto',
                details: providerError.data || null
            });
        }

        // Salvar saque
        const withdrawData = {
            id: withdrawId,
            userId: user.id,
            correlationID: providerResp?.data?.transactionId || providerResp?.data?.jobId || withdrawId,
            value: amountInCents,
            description: description || `Saque Crypto - USDT BEP20`,
            status: 'QUEUED',
            pixKey: wallet,
            pixKeyType: 'CRYPTO_BEP20',
            transactionId: providerResp?.data?.transactionId || null,
            metadata: {
                ...providerResp,
                provider: 'goatpay',
                type: 'CRYPTO_BEP20',
                fee: totalFee,
                feePercent: CRYPTO_FEE_PERCENT,
                feeFixed: CRYPTO_FEE_FIXED,
                sent: amountInCents,
                wallet: wallet,
                jobId: providerResp?.data?.jobId || null
            }
        };

        let withdraw;
        try {
            withdraw = await Withdraw.create(withdrawData);
            console.log(`✅ Saque crypto ${withdrawId} salvo com sucesso no MongoDB`);
        } catch (saveError) {
            console.error(`❌ ERRO ao salvar saque crypto no MongoDB:`, saveError.message);

            // Devolver saldo
            try {
                await Register.findOneAndUpdate(
                    { id: user.id },
                    { $inc: { balance: totalDebit } }
                );
                console.log(`💰 Saldo devolvido após falha ao salvar saque crypto`);
            } catch (refundError) {
                console.error(`❌ ERRO CRÍTICO:`, refundError.message);
            }

            return res.status(500).json({
                error: 'Erro ao salvar saque crypto',
                message: 'Ocorreu um erro ao registrar o saque. Seu saldo foi devolvido.'
            });
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
                type: 'CRYPTO_BEP20',
                value: amountInCents,
                fee: totalFee,
                wallet: wallet
            },
            metadata: { providerResponse: providerResp },
            ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
            userAgent: req.headers['user-agent'],
            description: `Saque crypto criado: R$ ${numericAmount.toFixed(2)} - ${user.name}`
        });

        // Webhook
        await sendWebhookEvent(user.id, 'withdrawal.queued', {
            txid: withdrawId,
            type: 'crypto',
            currency: 'USDT',
            network: 'BEP20',
            amount: numericAmount.toFixed(2),
            fee: (totalFee / 100).toFixed(2),
            wallet: wallet,
            status: 'queued',
            queuedAt: Date.now()
        });

        // Notificação Discord
        (async () => {
            try {
                const { notifyWithdraw } = await import('../../../../services/discordNotifier.js');
                await notifyWithdraw({
                    withdrawId: withdraw.id,
                    email: user.email,
                    value: amountInCents,
                    fee: totalFee,
                    sent: amountInCents,
                    status: withdraw.status,
                    pixKey: wallet,
                    pixKeyType: 'CRYPTO_BEP20',
                    plan: user.category || 'WHITE',
                    ip: req.ip || req.headers['x-forwarded-for'] || 'N/A'
                });
            } catch (e) {
                console.error('[DISCORD] Erro ao notificar saque crypto:', e.message);
            }
        })();

        res.status(201).json({
            success: true,
            message: 'Saque crypto adicionado à fila de processamento',
            data: {
                id: withdraw.id,
                type: 'CRYPTO_BEP20',
                currency: 'USDT',
                network: 'BEP20',
                value: amountInCents,
                valueInReais: numericAmount,
                fee: totalFee,
                feeInReais: totalFee / 100,
                wallet: wallet,
                status: withdraw.status,
                jobId: providerResp?.data?.jobId || null,
                createdAt: withdraw.createdAt
            }
        });

    } catch (error) {
        console.error('Erro ao criar saque crypto:', error);
        res.status(500).json({
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

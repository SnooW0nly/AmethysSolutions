import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { strictSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { generateUniqueId } from '../../../../services/security.js';
import Register from '../../../../database/models/Register.js';
import InternalTransfer from '../../../../database/models/InternalTransfer.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';

const router = express.Router();

/**
 * POST /api/v1/transfer/internal
 * Transferência interna entre contas Amethys Wallet via email
 * - Sem taxa
 * - Sem limites
 * - Instantânea
 */
router.post('/', strictSmartRateLimiter, authenticateUser, async (req, res) => {
    try {
        const user = req.user;
        const { email, amount, description } = req.body || {};

        // Verificar se usuário está bloqueado - simular erro genérico
        if (user.blocked) {
            return res.status(500).json({
                error: 'Erro ao processar transferência',
                message: 'Falha no processamento. Tente novamente mais tarde.'
            });
        }

        // ========== Anti-spam: verificar se há transferência pendente ==========
        const pendingTransfer = await InternalTransfer.getPending(user.id);
        if (pendingTransfer) {
            return res.status(400).json({
                error: 'Transferência em processamento',
                message: 'Você já possui uma transferência em processamento. Aguarde a conclusão.',
                pendingTransferId: pendingTransfer.id,
                pendingTransferAmount: pendingTransfer.amount,
                pendingTransferCreatedAt: pendingTransfer.createdAt
            });
        }

        // Validar email do destinatário
        if (!email || typeof email !== 'string') {
            return res.status(400).json({
                error: 'Email obrigatório',
                message: 'Informe o email da conta de destino'
            });
        }

        // Validar valor
        if (amount === undefined || amount === null || amount === '') {
            return res.status(400).json({
                error: 'Valor obrigatório',
                message: 'Informe o campo "amount"'
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

        const amountInCents = Math.round(numericAmount * 100);

        // Não permitir transferir para si mesmo
        if (email.toLowerCase() === user.email.toLowerCase()) {
            return res.status(400).json({
                error: 'Operação inválida',
                message: 'Você não pode transferir para sua própria conta'
            });
        }

        // Buscar destinatário
        const recipient = await Register.findOne({
            email: email.toLowerCase(),
            status: 'active'
        });

        if (!recipient) {
            return res.status(404).json({
                error: 'Usuário não encontrado',
                message: 'Não foi encontrada uma conta ativa com este email na plataforma'
            });
        }

        if (recipient.blocked) {
            return res.status(400).json({
                error: 'Conta bloqueada',
                message: 'A conta de destino está bloqueada e não pode receber transferências'
            });
        }

        const transferId = generateUniqueId();
        const now = new Date().toISOString();

        // ========== Débito atômico do remetente ==========
        const senderUpdate = await Register.findOneAndUpdate(
            {
                id: user.id,
                balance: { $gte: amountInCents }
            },
            { $inc: { balance: -amountInCents } },
            { new: true }
        );

        if (!senderUpdate) {
            const currentUser = await Register.getById(user.id);
            const currentBalance = currentUser?.balance || 0;
            console.log(`❌ Transferência interna negada: Saldo insuficiente. Saldo: R$ ${(currentBalance / 100).toFixed(2)}, Requerido: R$ ${(amountInCents / 100).toFixed(2)}`);
            return res.status(400).json({
                error: 'Saldo insuficiente',
                balance: currentBalance,
                required: amountInCents
            });
        }

        console.log(`💸 Transferência interna: Saldo debitado atomicamente de ${user.email}. Valor: R$ ${(amountInCents / 100).toFixed(2)}`);

        // ========== Creditar destinatário ==========
        const recipientUpdate = await Register.findOneAndUpdate(
            { id: recipient.id },
            { $inc: { balance: amountInCents } },
            { new: true }
        );

        if (!recipientUpdate) {
            // Reverter débito se não conseguiu creditar
            console.error(`❌ Erro ao creditar destinatário, devolvendo saldo ao remetente`);
            await Register.findOneAndUpdate(
                { id: user.id },
                { $inc: { balance: amountInCents } }
            );
            return res.status(500).json({
                error: 'Erro ao processar transferência',
                message: 'Não foi possível creditar o destinatário. Seu saldo foi devolvido.'
            });
        }

        // ========== Salvar registro da transferência ==========
        try {
            await InternalTransfer.create({
                id: transferId,
                senderId: user.id,
                senderEmail: user.email,
                recipientId: recipient.id,
                recipientEmail: recipient.email,
                amount: amountInCents,
                description: description || 'Transferência interna',
                status: 'COMPLETED',
                metadata: {
                    senderBalanceBefore: senderUpdate.balance + amountInCents,
                    senderBalanceAfter: senderUpdate.balance,
                    recipientBalanceBefore: recipientUpdate.balance - amountInCents,
                    recipientBalanceAfter: recipientUpdate.balance
                }
            });
        } catch (saveError) {
            console.error(`⚠️ Erro ao salvar registro de transferência (transferência já foi processada):`, saveError.message);
        }

        // Log de auditoria - remetente
        await Audit.saveLog({
            id: generateUniqueId(),
            action: AUDIT_ACTIONS.TRANSFER_SENT || 'TRANSFER_SENT',
            entity: AUDIT_ENTITIES.TRANSFER || 'TRANSFER',
            entityId: transferId,
            userId: user.id,
            userEmail: user.email,
            dataBefore: { balance: senderUpdate.balance + amountInCents },
            dataAfter: {
                balance: senderUpdate.balance,
                transferId,
                recipientEmail: recipient.email,
                amount: amountInCents
            },
            ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
            userAgent: req.headers['user-agent'],
            description: `Transferência interna enviada: R$ ${(amountInCents / 100).toFixed(2)} para ${recipient.email}`
        });

        // Log de auditoria - destinatário
        await Audit.saveLog({
            id: generateUniqueId(),
            action: AUDIT_ACTIONS.TRANSFER_RECEIVED || 'TRANSFER_RECEIVED',
            entity: AUDIT_ENTITIES.TRANSFER || 'TRANSFER',
            entityId: transferId,
            userId: recipient.id,
            userEmail: recipient.email,
            dataBefore: { balance: recipientUpdate.balance - amountInCents },
            dataAfter: {
                balance: recipientUpdate.balance,
                transferId,
                senderEmail: user.email,
                amount: amountInCents
            },
            ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
            userAgent: req.headers['user-agent'],
            description: `Transferência interna recebida: R$ ${(amountInCents / 100).toFixed(2)} de ${user.email}`
        });

        console.log(`✅ Transferência interna ${transferId}: R$ ${(amountInCents / 100).toFixed(2)} de ${user.email} para ${recipient.email}`);

        // Notificação Discord
        (async () => {
            try {
                const { notifyInternalTransfer } = await import('../../../../services/discordNotifier.js');
                await notifyInternalTransfer({
                    transferId,
                    senderEmail: user.email,
                    recipientEmail: recipient.email,
                    recipientName: recipient.name,
                    value: amountInCents,
                    description: description || 'Transferência interna',
                    ip: req.ip || req.headers['x-forwarded-for'] || 'N/A'
                });
            } catch (e) {
                console.error('[DISCORD] Erro ao notificar transferência:', e.message);
            }
        })();

        res.status(201).json({
            success: true,
            message: 'Transferência realizada com sucesso',
            data: {
                id: transferId,
                amount: amountInCents,
                amountInReais: amountInCents / 100,
                recipient: {
                    email: recipient.email,
                    name: recipient.name
                },
                description: description || 'Transferência interna',
                fee: 0,
                createdAt: now
            }
        });

    } catch (error) {
        console.error('Erro ao processar transferência interna:', error);
        res.status(500).json({
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

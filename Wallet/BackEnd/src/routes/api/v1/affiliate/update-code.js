import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { strictSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { generateUniqueId } from '../../../../services/security.js';
import Affiliate from '../../../../database/models/Affiliate.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';

const router = express.Router();

// Palavras reservadas
const RESERVED_CODES = [
    'dashboard', 'login', 'signup', 'about', 'pricing', 'terms', 'api',
    'admin', 'settings', 'profile', 'wallet', 'deposit', 'withdraw',
    'transfer', 'transactions', 'goals', 'credentials', 'summary',
    'changelogs', 'affiliates-program', 'error', 'not-found', '404', '500'
];

// Validar código
function isValidCode(code) {
    if (!code || typeof code !== 'string') return false;
    const trimmed = code.trim().toLowerCase();
    if (trimmed.length < 3 || trimmed.length > 30) return false;
    if (!/^[a-z0-9_-]+$/.test(trimmed)) return false;
    if (RESERVED_CODES.includes(trimmed)) return false;
    return true;
}

// PUT /api/v1/affiliate/code - Atualizar código do afiliado
router.put('/', strictSmartRateLimiter, authenticateUser, async (req, res) => {
    try {
        const user = req.user;
        const { code } = req.body || {};

        if (!code) {
            return res.status(400).json({
                error: 'Código obrigatório',
                message: 'Informe o novo código desejado'
            });
        }

        const affiliate = await Affiliate.getByUserId(user.id);
        if (!affiliate) {
            return res.status(404).json({
                error: 'Não é afiliado',
                message: 'Você ainda não está cadastrado como afiliado'
            });
        }

        if (!isValidCode(code)) {
            return res.status(400).json({
                error: 'Código inválido',
                message: 'O código deve ter entre 3 e 30 caracteres e conter apenas letras, números, - e _'
            });
        }

        const newCode = code.toLowerCase().trim();

        // Se é o mesmo código, não precisa fazer nada
        if (newCode === affiliate.code) {
            return res.json({
                success: true,
                message: 'Código mantido',
                data: {
                    code: affiliate.code,
                    link: `https://visionwallet.com.br/${affiliate.code}`
                }
            });
        }

        // Verificar disponibilidade
        const isAvailable = await Affiliate.isCodeAvailable(newCode);
        if (!isAvailable) {
            return res.status(400).json({
                error: 'Código indisponível',
                message: 'Este código já está em uso. Escolha outro.'
            });
        }

        const oldCode = affiliate.code;

        // Atualizar código
        await Affiliate.findOneAndUpdate(
            { id: affiliate.id },
            { $set: { code: newCode } }
        );

        // Log de auditoria
        await Audit.saveLog({
            id: generateUniqueId(),
            action: AUDIT_ACTIONS.USER_UPDATED || 'USER_UPDATED',
            entity: AUDIT_ENTITIES.USER || 'USER',
            entityId: affiliate.id,
            userId: user.id,
            userEmail: user.email,
            dataBefore: { code: oldCode },
            dataAfter: { code: newCode },
            ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
            userAgent: req.headers['user-agent'],
            description: `Afiliado ${user.name} alterou código de ${oldCode} para ${newCode}`
        });

        res.json({
            success: true,
            message: 'Código atualizado com sucesso!',
            data: {
                code: newCode,
                link: `https://visionwallet.com.br/${newCode}`
            }
        });

    } catch (error) {
        console.error('[AFFILIATE] Erro ao atualizar código:', error.message);
        res.status(500).json({
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

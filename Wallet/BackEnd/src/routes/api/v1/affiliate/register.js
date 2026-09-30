import express from 'express';
import { authenticateUser } from '../../../../middlewares/userAuth.js';
import { strictSmartRateLimiter } from '../../../../middlewares/smartRateLimiter.js';
import { generateUniqueId } from '../../../../services/security.js';
import Affiliate from '../../../../database/models/Affiliate.js';
import Register from '../../../../database/models/Register.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../../../../database/models/Audit.js';

const router = express.Router();

// Palavras reservadas que não podem ser usadas como código de afiliado
const RESERVED_CODES = [
    'dashboard', 'login', 'signup', 'about', 'pricing', 'terms', 'api',
    'admin', 'settings', 'profile', 'wallet', 'deposit', 'withdraw',
    'transfer', 'transactions', 'goals', 'credentials', 'summary',
    'changelogs', 'affiliates-program', 'error', 'not-found', '404', '500'
];

// Validar código de afiliado
function isValidCode(code) {
    if (!code || typeof code !== 'string') return false;
    const trimmed = code.trim().toLowerCase();
    if (trimmed.length < 3 || trimmed.length > 30) return false;
    if (!/^[a-z0-9_-]+$/.test(trimmed)) return false;
    if (RESERVED_CODES.includes(trimmed)) return false;
    return true;
}

// Gerar código único baseado no nome
function generateCodeFromName(name) {
    const base = name
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '') // Remove acentos
        .replace(/[^a-z0-9]/g, '') // Remove caracteres especiais
        .slice(0, 15);

    const suffix = Math.random().toString(36).substring(2, 6);
    return `${base}${suffix}`;
}

// POST /api/v1/affiliate/register - Registrar como afiliado
router.post('/', strictSmartRateLimiter, authenticateUser, async (req, res) => {
    try {
        const user = req.user;
        const { code } = req.body || {};

        // Verificar se já é afiliado
        const existingAffiliate = await Affiliate.getByUserId(user.id);
        if (existingAffiliate) {
            return res.status(400).json({
                error: 'Já é afiliado',
                message: 'Você já está cadastrado como afiliado',
                data: {
                    code: existingAffiliate.code,
                    link: `https://visionwallet.com.br/${existingAffiliate.code}`
                }
            });
        }

        // Gerar ou validar código
        let affiliateCode;
        if (code) {
            if (!isValidCode(code)) {
                return res.status(400).json({
                    error: 'Código inválido',
                    message: 'O código deve ter entre 3 e 30 caracteres e conter apenas letras, números, - e _'
                });
            }

            const isAvailable = await Affiliate.isCodeAvailable(code);
            if (!isAvailable) {
                return res.status(400).json({
                    error: 'Código indisponível',
                    message: 'Este código já está em uso. Escolha outro.'
                });
            }
            affiliateCode = code.toLowerCase().trim();
        } else {
            // Gerar código baseado no nome
            let attempts = 0;
            do {
                affiliateCode = generateCodeFromName(user.name);
                attempts++;
            } while (!(await Affiliate.isCodeAvailable(affiliateCode)) && attempts < 5);

            if (attempts >= 5) {
                affiliateCode = `user${generateUniqueId().slice(0, 8)}`;
            }
        }

        const affiliateId = generateUniqueId();
        const now = new Date().toISOString();

        // Criar afiliado
        const affiliate = await Affiliate.create({
            id: affiliateId,
            userId: user.id,
            userEmail: user.email,
            userName: user.name,
            code: affiliateCode,
            totalReferrals: 0,
            totalEarnings: 0,
            status: 'active'
        });

        // Atualizar registro do usuário
        await Register.findOneAndUpdate(
            { id: user.id },
            { $set: { isAffiliate: true } }
        );

        // Log de auditoria
        await Audit.saveLog({
            id: generateUniqueId(),
            action: AUDIT_ACTIONS.USER_UPDATED || 'USER_UPDATED',
            entity: AUDIT_ENTITIES.USER || 'USER',
            entityId: affiliateId,
            userId: user.id,
            userEmail: user.email,
            dataAfter: {
                affiliateId,
                code: affiliateCode
            },
            ipAddress: req.ip || req.headers['x-forwarded-for'] || req.connection?.remoteAddress,
            userAgent: req.headers['user-agent'],
            description: `Usuário ${user.name} se cadastrou como afiliado com código ${affiliateCode}`
        });

        res.status(201).json({
            success: true,
            message: 'Cadastro como afiliado realizado com sucesso!',
            data: {
                id: affiliate.id,
                code: affiliate.code,
                link: `https://visionwallet.com.br/${affiliate.code}`,
                totalReferrals: 0,
                totalEarnings: 0,
                status: 'active'
            }
        });

    } catch (error) {
        console.error('[AFFILIATE] Erro ao registrar afiliado:', error.message);
        res.status(500).json({
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;

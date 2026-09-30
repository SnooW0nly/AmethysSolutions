import express from 'express';
import { authenticate } from '../../../../middlewares/auth.js';
import Register from '../../../../database/models/Register.js';
import BusinessProfile from '../../../../database/models/BusinessProfile.js';
import { generateUniqueId } from '../../../../services/security.js';
import { analyzeBusinessDescription } from '../../../../services/aiService.js';
import { determineCategory } from '../../../../services/categoryService.js';

const router = express.Router();

/**
 * PUT /api/v1/user/complete-business-profile
 * Completa o perfil de negócio para usuários que não preencheram no cadastro
 */
router.put('/', authenticate, async (req, res) => {
    try {
        const { businessName, website, description, medFrequency } = req.body;

        // Validações
        if (!businessName || !description) {
            return res.status(400).json({
                success: false,
                error: 'Nome e descrição são obrigatórios',
            });
        }

        if (description.length < 100) {
            return res.status(400).json({
                success: false,
                error: `Descrição deve ter pelo menos 100 caracteres (atual: ${description.length})`,
            });
        }

        if (description.length > 1000) {
            return res.status(400).json({
                success: false,
                error: `Descrição deve ter no máximo 1000 caracteres (atual: ${description.length})`,
            });
        }

        // Buscar registro do usuário
        const register = await Register.findOne({ email: req.user.email.toLowerCase() });
        if (!register) {
            return res.status(404).json({
                success: false,
                error: 'Registro não encontrado',
            });
        }

        // Verificar se já completou o perfil
        if (register.businessProfileCompleted && !register.categoryLockedByAdmin) {
            // Permitir atualização se não estiver travado pelo admin
        }

        // Analisar descrição com IA
        let aiAnalysis = { isHighRisk: false };
        try {
            aiAnalysis = await analyzeBusinessDescription(description);
        } catch (aiError) {
            console.error('[PROFILE] Erro na análise de IA:', aiError.message);
        }

        // Determinar categoria baseado na análise
        const businessProfileData = {
            businessName,
            website,
            description,
            medFrequency: medFrequency || 'NEVER',
        };

        // Se IA detectou alto risco, forçar categoria BLACK
        let category = determineCategory(businessProfileData);
        if (aiAnalysis.isHighRisk) {
            category = 'BLACK';
            businessProfileData.medFrequency = 'ALWAYS';
        }

        const now = new Date().toISOString();

        // Criar ou atualizar BusinessProfile
        let businessProfileId = register.businessProfileId;

        if (businessProfileId) {
            // Atualizar perfil existente
            await BusinessProfile.findOneAndUpdate(
                { id: businessProfileId },
                {
                    businessName,
                    website: website || null,
                    description,
                    medFrequency: businessProfileData.medFrequency,
                    category,
                    categorizedAt: now,
                    categorizedBy: aiAnalysis.aiAnalyzed ? 'AI' : 'SYSTEM',
                    aiAnalysis: aiAnalysis.aiAnalyzed ? {
                        isHighRisk: aiAnalysis.isHighRisk,
                        reason: aiAnalysis.reason,
                        confidence: aiAnalysis.confidence,
                        analyzedAt: now,
                    } : undefined,
                }
            );
        } else {
            // Criar novo perfil
            const profileId = generateUniqueId();
            await BusinessProfile.create({
                id: profileId,
                userId: register.id,
                businessName,
                website: website || null,
                description,
                medFrequency: businessProfileData.medFrequency,
                category,
                categorizedAt: now,
                categorizedBy: aiAnalysis.aiAnalyzed ? 'AI' : 'SYSTEM',
                aiAnalysis: aiAnalysis.aiAnalyzed ? {
                    isHighRisk: aiAnalysis.isHighRisk,
                    reason: aiAnalysis.reason,
                    confidence: aiAnalysis.confidence,
                    analyzedAt: now,
                } : undefined,
            });
            businessProfileId = profileId;
        }

        // Atualizar registro do usuário
        const updateData = {
            businessProfileId,
            businessProfileCompleted: true,
        };

        // Só atualiza categoria se não estiver travado pelo admin
        if (!register.categoryLockedByAdmin) {
            updateData.category = category;
        }

        await Register.findOneAndUpdate(
            { id: register.id },
            updateData
        );

        res.json({
            success: true,
            message: 'Perfil de negócio atualizado com sucesso',
            category: register.categoryLockedByAdmin ? register.category : category,
            businessProfileCompleted: true,
            aiAnalysis: aiAnalysis.aiAnalyzed ? {
                isHighRisk: aiAnalysis.isHighRisk,
                reason: aiAnalysis.reason,
            } : null,
        });

    } catch (error) {
        console.error('[PROFILE] Erro ao completar perfil:', error);
        res.status(500).json({
            success: false,
            error: 'Erro ao atualizar perfil de negócio',
        });
    }
});

export default router;

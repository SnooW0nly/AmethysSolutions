import express from "express";
import { authenticate } from "../middlewares/auth.js";
import Affiliate from "../database/models/Affiliate.js";
import Register from "../database/models/Register.js";
import { generateUniqueId } from "../services/security.js";

const router = express.Router();

// Rota pública para tracking de cliques
router.post("/track/:code", async (req, res) => {
    try {
        const { code } = req.params;
        const affiliate = await Affiliate.getByCode(code);

        if (affiliate) {
            // Incrementar contador de forma atômica
            await Affiliate.updateOne(
                { _id: affiliate._id },
                { $inc: { clicks: 1 } }
            );
        }

        // Retorna sucesso independente de encontrar para não vazar info
        res.status(200).json({ success: true });
    } catch (error) {
        console.error("Erro no tracking:", error);
        res.status(200).json({ success: true }); // Falha silenciosa
    }
});

// Middleware de autenticação para as rotas abaixo
router.use(authenticate);

/**
 * GET /
 * Retorna os dados do afiliado logado (stats, código, link)
 * Se não for afiliado, retorna 404
 */
router.get("/", async (req, res) => {
    try {
        const userId = req.user.id;
        const affiliate = await Affiliate.getByUserId(userId);

        if (!affiliate) {
            return res.status(404).json({
                success: false,
                message: "Usuário não é um afiliado",
                isAffiliate: false
            });
        }

        // Buscar lista de indicados recentes
        const recentReferrals = await Affiliate.getReferrals(affiliate.id);

        // Contar indicados reais (baseado na lista, não no valor armazenado)
        const realReferralCount = recentReferrals.length;

        // Formatar resposta
        res.json({
            success: true,
            data: {
                id: affiliate.id,
                code: affiliate.code,
                link: `${process.env.FRONTEND_URL}/signup?ref=${affiliate.code}`,
                totalReferrals: realReferralCount, // Usar contagem real
                totalEarnings: affiliate.totalEarnings,
                totalEarningsInReais: (affiliate.totalEarnings / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
                // Taxa de comissão do afiliado
                commissionRate: affiliate.commissionRate || 5,
                commissionRateInReais: `R$ ${((affiliate.commissionRate || 5) / 100).toFixed(2).replace('.', ',')}`,
                stats: {
                    clicks: affiliate.clicks || 0,
                    referrals: realReferralCount, // Usar contagem real
                    earnings: affiliate.totalEarnings,
                    conversion: affiliate.clicks > 0
                        ? ((realReferralCount / affiliate.clicks) * 100).toFixed(1)
                        : "0.0"
                },
                recentReferrals: recentReferrals.map(ref => ({
                    name: ref.name,
                    email: ref.email.replace(/(.{3})(.*)(@.*)/, "$1***$3"), // Mascarar email
                    plan: ref.plan,
                    date: ref.createdAt
                })),
                status: affiliate.status,
                createdAt: affiliate.createdAt
            }
        });

    } catch (error) {
        console.error("Erro ao buscar dados do afiliado:", error);
        res.status(500).json({
            success: false,
            error: "Erro ao buscar dados do afiliado"
        });
    }
});

/**
 * POST /join
 * Torna o usuário atual um afiliado
 */
router.post("/join", async (req, res) => {
    try {
        const userId = req.user.id;

        // Verificar se já é afiliado
        const existing = await Affiliate.getByUserId(userId);
        if (existing) {
            return res.status(400).json({
                success: false,
                error: "Usuário já é um afiliado"
            });
        }

        // Gerar código inicial base (primeiro nome + random ou hash curto)
        const baseCode = req.user.fullName.split(' ')[0].toLowerCase().replace(/[^a-z0-9]/g, '');
        let code = baseCode;
        let suffix = Math.floor(Math.random() * 1000);

        // Garantir unicidade do código inicial
        while (!(await Affiliate.isCodeAvailable(code))) {
            code = `${baseCode}${suffix}`;
            suffix++;
        }

        // Criar afiliado
        const newAffiliate = await Affiliate.create({
            id: generateUniqueId(),
            userId: userId,
            userEmail: req.user.email,
            userName: req.user.fullName,
            code: code,
            status: 'active'
        });

        // Atualizar flag isAffiliate no Register (se existir)
        const register = await Register.getByEmailOrTaxID(req.user.email, null);
        if (register) {
            await Register.updateOne({ id: register.id }, { isAffiliate: true });
        }

        // Atualizar flag isAffiliate no User (para manter consistência)
        const User = (await import("../database/models/User.js")).default;
        await User.updateOne({ _id: userId }, { $set: { isAffiliate: true } });

        res.status(201).json({
            success: true,
            message: "Afiliado criado com sucesso",
            data: {
                ...newAffiliate.toObject(),
                link: `${process.env.FRONTEND_URL}/signup?ref=${newAffiliate.code}`,
                totalEarningsInReais: "R$ 0,00"
            }
        });

    } catch (error) {
        console.error("Erro ao criar afiliado:", error);
        res.status(500).json({
            success: false,
            error: "Erro ao processar solicitação"
        });
    }
});

/**
 * PUT /code
 * Altera o código de afiliado
 */
router.put("/code", async (req, res) => {
    try {
        const { newCode } = req.body;
        const userId = req.user.id;

        if (!newCode || newCode.length < 3) {
            return res.status(400).json({
                success: false,
                error: "Código deve ter pelo menos 3 caracteres"
            });
        }

        if (!/^[a-zA-Z0-9]+$/.test(newCode)) {
            return res.status(400).json({
                success: false,
                error: "Código deve conter apenas letras e números"
            });
        }

        const affiliate = await Affiliate.getByUserId(userId);
        if (!affiliate) {
            return res.status(404).json({
                success: false,
                error: "Afiliado não encontrado"
            });
        }

        // Verificar disponibilidade
        if (newCode.toLowerCase() !== affiliate.code) {
            const isAvailable = await Affiliate.isCodeAvailable(newCode);
            if (!isAvailable) {
                return res.status(400).json({
                    success: false,
                    error: "Este código já está em uso"
                });
            }
        }

        affiliate.code = newCode.toLowerCase();
        await affiliate.save();

        res.json({
            success: true,
            message: "Código atualizado com sucesso",
            data: {
                code: affiliate.code,
                link: `${process.env.FRONTEND_URL}/signup?ref=${affiliate.code}`
            }
        });

    } catch (error) {
        console.error("Erro ao atualizar código:", error);
        res.status(500).json({
            success: false,
            error: "Erro ao atualizar código"
        });
    }
});

export default router;

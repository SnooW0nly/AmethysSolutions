import express from "express";
import Ticket from "../database/models/Ticket.js";
import Register from "../database/models/Register.js";
import User from "../database/models/User.js";
import { authenticate } from "../middlewares/auth.js";
import { generateUniqueId } from "../services/security.js";

const router = express.Router();

/**
 * Criar ticket de solicitação de mudança de categoria
 * POST /api/tickets/category-change
 */
router.post("/category-change", authenticate, async (req, res) => {
    try {
        const { reason } = req.body;
        const userId = req.user.id;
        const userEmail = req.user.email;

        if (!reason || reason.trim().length < 20) {
            return res.status(400).json({
                success: false,
                error: "Justificativa deve ter pelo menos 20 caracteres"
            });
        }

        // Buscar dados atuais do usuário
        const register = await Register.findOne({ email: userEmail });
        if (!register) {
            return res.status(404).json({
                success: false,
                error: "Usuário não encontrado"
            });
        }

        // Verificar se já existe ticket pendente
        const existingTicket = await Ticket.findOne({
            userId: register.id,
            type: 'CATEGORY_CHANGE',
            status: 'PENDING'
        });

        if (existingTicket) {
            return res.status(400).json({
                success: false,
                error: "Você já possui uma solicitação pendente"
            });
        }

        // Criar ticket
        const ticket = await Ticket.create({
            id: generateUniqueId(),
            userId: register.id,
            userEmail: userEmail,
            type: 'CATEGORY_CHANGE',
            status: 'PENDING',
            data: {
                currentCategory: register.category || 'WHITE',
                currentTier: register.tier || 1,
                reason: reason.trim()
            }
        });

        res.status(201).json({
            success: true,
            message: "Solicitação enviada com sucesso",
            ticket: {
                id: ticket.id,
                status: ticket.status,
                createdAt: ticket.createdAt
            }
        });

    } catch (error) {
        console.error("[TICKETS] Erro ao criar ticket:", error);
        res.status(500).json({
            success: false,
            error: "Erro ao criar solicitação"
        });
    }
});

/**
 * Listar tickets do usuário
 * GET /api/tickets/my
 */
router.get("/my", authenticate, async (req, res) => {
    try {
        const userEmail = req.user.email;
        const register = await Register.findOne({ email: userEmail });

        if (!register) {
            return res.status(404).json({
                success: false,
                error: "Usuário não encontrado"
            });
        }

        const tickets = await Ticket.getByUser(register.id);

        res.json({
            success: true,
            tickets: tickets.map(t => ({
                id: t.id,
                type: t.type,
                status: t.status,
                data: {
                    currentCategory: t.data?.currentCategory,
                    currentTier: t.data?.currentTier,
                    reason: t.data?.reason,
                    resolvedCategory: t.data?.resolvedCategory,
                    resolvedTier: t.data?.resolvedTier,
                    adminNotes: t.data?.adminNotes
                },
                createdAt: t.createdAt,
                resolvedAt: t.resolvedAt
            }))
        });

    } catch (error) {
        console.error("[TICKETS] Erro ao listar tickets:", error);
        res.status(500).json({
            success: false,
            error: "Erro ao listar solicitações"
        });
    }
});

/**
 * [ADMIN] Listar todos os tickets pendentes
 * GET /api/tickets/admin/pending
 */
router.get("/admin/pending", authenticate, async (req, res) => {
    try {
        // Verificar se é admin
        const user = await User.findOne({ email: req.user.email });
        if (!user?.admin) {
            return res.status(403).json({
                success: false,
                error: "Acesso negado"
            });
        }

        const tickets = await Ticket.getPending();

        res.json({
            success: true,
            tickets: tickets.map(t => ({
                id: t.id,
                userId: t.userId,
                userEmail: t.userEmail,
                type: t.type,
                status: t.status,
                data: t.data,
                createdAt: t.createdAt
            }))
        });

    } catch (error) {
        console.error("[TICKETS] Erro ao listar tickets pendentes:", error);
        res.status(500).json({
            success: false,
            error: "Erro ao listar solicitações"
        });
    }
});

/**
 * [ADMIN] Resolver ticket
 * POST /api/tickets/admin/:id/resolve
 */
router.post("/admin/:id/resolve", authenticate, async (req, res) => {
    try {
        const { id } = req.params;
        const { action, category, tier, notes } = req.body;

        // Verificar se é admin
        const adminUser = await User.findOne({ email: req.user.email });
        if (!adminUser?.admin) {
            return res.status(403).json({
                success: false,
                error: "Acesso negado"
            });
        }

        // Buscar ticket
        const ticket = await Ticket.findOne({ id });
        if (!ticket) {
            return res.status(404).json({
                success: false,
                error: "Ticket não encontrado"
            });
        }

        if (ticket.status !== 'PENDING') {
            return res.status(400).json({
                success: false,
                error: "Ticket já foi resolvido"
            });
        }

        if (action === 'approve') {
            if (!category || !['WHITE', 'BLACK'].includes(category)) {
                return res.status(400).json({
                    success: false,
                    error: "Categoria inválida"
                });
            }

            const newTier = category === 'WHITE' ? (tier || 1) : 1;

            // Atualizar categoria do usuário no Register
            await Register.updateOne(
                { id: ticket.userId },
                {
                    $set: {
                        category: category,
                        tier: newTier,
                        categoryLockedByAdmin: true
                    }
                }
            );

            // Atualizar categoria do usuário no User também
            await User.updateOne(
                { email: ticket.userEmail },
                {
                    $set: {
                        category: category,
                        tier: newTier,
                        categoryLockedByAdmin: true
                    }
                }
            );

            // Atualizar ticket
            await Ticket.updateOne(
                { id },
                {
                    $set: {
                        status: 'APPROVED',
                        'data.resolvedCategory': category,
                        'data.resolvedTier': newTier,
                        'data.adminNotes': notes || '',
                        resolvedBy: adminUser.email,
                        resolvedAt: new Date().toISOString()
                    }
                }
            );

            res.json({
                success: true,
                message: `Categoria alterada para ${category}${category === 'WHITE' ? ` Tier ${newTier}` : ''}`
            });

        } else if (action === 'reject') {
            await Ticket.updateOne(
                { id },
                {
                    $set: {
                        status: 'REJECTED',
                        'data.adminNotes': notes || '',
                        resolvedBy: adminUser.email,
                        resolvedAt: new Date().toISOString()
                    }
                }
            );

            res.json({
                success: true,
                message: "Solicitação rejeitada"
            });

        } else {
            return res.status(400).json({
                success: false,
                error: "Ação inválida. Use 'approve' ou 'reject'"
            });
        }

    } catch (error) {
        console.error("[TICKETS] Erro ao resolver ticket:", error);
        res.status(500).json({
            success: false,
            error: "Erro ao resolver solicitação"
        });
    }
});

export default router;

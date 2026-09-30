import Gift from "../../../database/models/Gift.js";
import Plan from "../../../database/models/Plan.js";
import { v4 as uuidv4 } from "uuid";

/**
 * POST /admin/gifts/create
 * Cria um ou múltiplos gifts para um plano específico
 */
export default async function createGifts(req, res) {
  try {
    console.log("[ADMIN GIFTS CREATE] req.user:", req.user);
    const { planId, months, quantity = 1, expiresAt, description } = req.body;

    // Validações
    if (!planId || !months) {
      return res.status(400).json({
        success: false,
        message: "planId e months são obrigatórios",
      });
    }

    if (quantity < 1 || quantity > 100) {
      return res.status(400).json({
        success: false,
        message: "Quantidade deve ser entre 1 e 100",
      });
    }

    if (months < 1 || months > 120) {
      return res.status(400).json({
        success: false,
        message: "Meses deve ser entre 1 e 120",
      });
    }

    // Verifica se o plano existe
    const plan = await Plan.findOne({ id: planId });
    if (!plan) {
      return res.status(404).json({
        success: false,
        message: "Plano não encontrado",
      });
    }

    // Valida data de expiração se fornecida
    let expirationDate = null;
    if (expiresAt) {
      expirationDate = new Date(expiresAt);
      if (isNaN(expirationDate.getTime()) || expirationDate < new Date()) {
        return res.status(400).json({
          success: false,
          message: "Data de expiração inválida ou no passado",
        });
      }
    }

    // Gera um batchId único para este lote
    const batchId = uuidv4();
    const gifts = [];

    // Obtém o ID do usuário
    const userId = req.user?._id || req.user?._id;
    if (!userId) {
      console.error("[ADMIN GIFTS CREATE] req.user não contém id:", req.user);
      return res.status(401).json({
        success: false,
        message: "Usuário não autenticado corretamente",
      });
    }

    // Cria os gifts
    for (let i = 0; i < quantity; i++) {
      const code = await Gift.generateUniqueCode();
      
      const gift = new Gift({
        code,
        planId: plan.id,
        planName: plan.name,
        months,
        expiresAt: expirationDate,
        description: description || `Gift ${plan.name} - ${months} mês(es)`,
        createdBy: userId,
        batchId,
      });

      await gift.save();
      gifts.push(gift);
    }

    return res.status(201).json({
      success: true,
      message: `${quantity} gift(s) criado(s) com sucesso`,
      data: {
        batchId,
        quantity: gifts.length,
        gifts: gifts.map(g => ({
          id: g._id,
          code: g.code,
          planName: g.planName,
          months: g.months,
          expiresAt: g.expiresAt,
        })),
      },
    });
  } catch (error) {
    console.error("[ADMIN GIFTS CREATE ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao criar gifts",
      error: error.message,
    });
  }
}

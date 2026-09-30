/**
 * Rotas de Afiliados
 * GET  /affiliates/me      → stats do afiliado logado
 * POST /affiliates/click   → registra clique (público, com code)
 */

import { Router } from "express";
import authMiddleware from "../../middlewares/authMiddleware.js";
import {
  getAffiliateStats,
  registerAffiliateClick,
} from "../../services/affiliateService.js";

const router = Router();

/**
 * GET /affiliates/me
 * Retorna as estatísticas do afiliado do usuário logado.
 * Cria automaticamente o afiliado se ainda não existir.
 */
router.get("/me", authMiddleware, async (req, res) => {
  try {
    const userId = req.user._id;
    const stats = await getAffiliateStats(userId);

    return res.status(200).json({
      success: true,
      data: stats,
    });
  } catch (error) {
    console.error("[AFFILIATES] Erro ao buscar stats:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao buscar informações de afiliado",
    });
  }
});

/**
 * POST /affiliates/click
 * Registra um clique no link de afiliado.
 * Body: { code: "ABC123" }
 * Público (sem auth).
 */
router.post("/click", async (req, res) => {
  try {
    const { code } = req.body;
    if (!code) {
      return res.status(400).json({ success: false, message: "Código obrigatório" });
    }

    const affiliate = await registerAffiliateClick(code);

    if (!affiliate) {
      return res.status(404).json({ success: false, message: "Código inválido" });
    }

    return res.status(200).json({ success: true });
  } catch (error) {
    console.error("[AFFILIATES] Erro ao registrar clique:", error);
    return res.status(500).json({ success: false, message: "Erro interno" });
  }
});

export default router;
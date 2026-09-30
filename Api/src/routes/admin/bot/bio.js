// src/routes/admin/bot/bio.js
// Rota para gerenciar a biografia global dos bots
import { Router } from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";

const router = Router();

// Middleware de autenticação e admin em todas as rotas
router.use(authMiddleware, requireAdmin);

// Chave no banco para armazenar a bio global
// Usa o model de configuração global (Settings) ou uma coleção simples
// Vamos usar um model novo chamado GlobalConfig

/**
 * GET /api/admin/bot/bio
 * Retorna a bio global atual
 */
router.get("/", async (req, res) => {
  try {
    const GlobalConfig = (await import("../../../database/models/GlobalConfig.js")).default;
    const config = await GlobalConfig.findOne({ key: "bot_bio" }).lean();

    res.json({
      success: true,
      bio: config?.value || "",
      updatedAt: config?.updatedAt || null,
      updatedBy: config?.updatedBy || null,
    });
  } catch (error) {
    console.error("[ADMIN] Erro ao buscar bio:", error);
    res.status(500).json({ error: "Erro ao buscar bio" });
  }
});

/**
 * PUT /api/admin/bot/bio
 * Atualiza a bio global
 * Body: { bio: string }
 */
router.put("/", async (req, res) => {
  try {
    const { bio } = req.body;
    const adminId = String(req.user?._id || "");

    if (bio === undefined || bio === null) {
      return res.status(400).json({ error: "Campo 'bio' é obrigatório" });
    }

    if (typeof bio !== "string") {
      return res.status(400).json({ error: "Bio deve ser uma string" });
    }

    if (bio.length > 400) {
      return res.status(400).json({ error: "Bio não pode ter mais de 400 caracteres" });
    }

    const GlobalConfig = (await import("../../../database/models/GlobalConfig.js")).default;

    const updated = await GlobalConfig.findOneAndUpdate(
      { key: "bot_bio" },
      {
        key: "bot_bio",
        value: bio,
        updatedBy: adminId,
      },
      { upsert: true, new: true }
    );

    res.json({
      success: true,
      message: "Bio atualizada com sucesso",
      bio: updated.value,
      updatedAt: updated.updatedAt,
    });
  } catch (error) {
    console.error("[ADMIN] Erro ao atualizar bio:", error);
    res.status(500).json({ error: "Erro ao atualizar bio" });
  }
});

export default router;
import express from "express";
import UpdateLog from "../../../database/models/UpdateLog.js";

const router = express.Router();

/**
 * GET /admin/updates/list
 * Lista todas as atualizações (histórico) do MongoDB
 */
router.get("/", async (req, res) => {
  try {
    const { limit = 50, page = 1 } = req.query;
    
    const updates = await UpdateLog.find()
      .sort({ startedAt: -1 })
      .limit(parseInt(limit))
      .skip((parseInt(page) - 1) * parseInt(limit))
      .populate("adminUserId", "name email")
      .select("-logs") // Não retorna logs completos na listagem
      .lean();

    const total = await UpdateLog.countDocuments();

    return res.status(200).json({
      success: true,
      data: updates,
      pagination: {
        total,
        page: parseInt(page),
        limit: parseInt(limit),
        pages: Math.ceil(total / parseInt(limit)),
      },
    });
  } catch (error) {
    console.error("[ADMIN UPDATES] Erro ao listar atualizações:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao listar atualizações",
      error: error.message,
    });
  }
});

export default router;

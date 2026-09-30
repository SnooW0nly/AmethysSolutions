import { Router } from "express";
import Transcript from "../../database/models/Transcript.js";
import authMiddleware from "../../middlewares/authMiddleware.js";
import requireAdmin from "../../middlewares/requireAdmin.js";

const router = Router();

// Todas as rotas admin exigem auth + admin
router.use(authMiddleware, requireAdmin);

/**
 * GET /api/v1/transcript/admin/list
 * Lista todos os transcripts (paginado)
 */
router.get("/list", async (req, res) => {
  try {
    const { page = 1, limit = 20, guildId, channelId } = req.query;
    const skip = (parseInt(page) - 1) * parseInt(limit);

    const filter = { isDeleted: false };
    if (guildId) filter.guildId = guildId;
    if (channelId) filter.channelId = channelId;

    const [transcripts, total] = await Promise.all([
      Transcript.find(filter)
        .select("-htmlContent")
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(parseInt(limit))
        .lean(),
      Transcript.countDocuments(filter),
    ]);

    return res.json({
      success: true,
      transcripts,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / parseInt(limit)),
      },
    });
  } catch (err) {
    console.error("[TRANSCRIPT ADMIN LIST]", err);
    return res.status(500).json({ error: "Erro ao listar transcripts" });
  }
});

/**
 * DELETE /api/v1/transcript/admin/:id
 * Soft delete de um transcript
 */
router.delete("/:id", async (req, res) => {
  try {
    const { id } = req.params;

    const transcript = await Transcript.findOneAndUpdate(
      { publicId: id },
      { isDeleted: true },
      { new: true }
    ).select("publicId channelName");

    if (!transcript) {
      return res.status(404).json({ error: "Transcript não encontrado" });
    }

    console.log(`[TRANSCRIPT ADMIN] Transcript deletado: ${id} — ${transcript.channelName}`);

    return res.json({ success: true, message: "Transcript removido com sucesso" });
  } catch (err) {
    console.error("[TRANSCRIPT ADMIN DELETE]", err);
    return res.status(500).json({ error: "Erro ao deletar transcript" });
  }
});

/**
 * GET /api/v1/transcript/admin/stats
 * Estatísticas gerais dos transcripts
 */
router.get("/stats", async (req, res) => {
  try {
    const [total, active, expired, totalViews] = await Promise.all([
      Transcript.countDocuments({ isDeleted: false }),
      Transcript.countDocuments({ isDeleted: false, expiresAt: { $gt: new Date() } }),
      Transcript.countDocuments({ isDeleted: false, expiresAt: { $lte: new Date() } }),
      Transcript.aggregate([
        { $match: { isDeleted: false } },
        { $group: { _id: null, totalViews: { $sum: "$views" } } },
      ]),
    ]);

    return res.json({
      success: true,
      stats: {
        total,
        active,
        expired,
        totalViews: totalViews[0]?.totalViews || 0,
      },
    });
  } catch (err) {
    console.error("[TRANSCRIPT ADMIN STATS]", err);
    return res.status(500).json({ error: "Erro ao buscar estatísticas" });
  }
});

export default router;
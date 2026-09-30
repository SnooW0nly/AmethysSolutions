import express from "express";
import { getUpdateProgress } from "../../../services/massUpdate.js";
import UpdateLog from "../../../database/models/UpdateLog.js";

const router = express.Router();

/**
 * GET /admin/updates/progress/:updateId
 * Obtém o progresso de uma atualização em tempo real
 * Busca primeiro na memória (para atualizações em andamento)
 * Se não encontrar, busca no MongoDB (para atualizações finalizadas)
 */
router.get("/:updateId", async (req, res) => {
  try {
    const { updateId } = req.params;

    // Tenta buscar na memória primeiro (atualização em andamento)
    let progress = getUpdateProgress(updateId);

    // Se não encontrou na memória, busca no MongoDB
    if (!progress) {
      const updateLog = await UpdateLog.findOne({ updateId })
        .populate("adminUserId", "name email")
        .lean();

      if (!updateLog) {
        return res.status(404).json({
          success: false,
          message: "Atualização não encontrada",
        });
      }

      // Converte formato do MongoDB para o formato esperado
      progress = {
        id: updateLog.updateId,
        planId: updateLog.planId,
        updateVersion: updateLog.updateVersion,
        status: updateLog.status,
        startedAt: updateLog.startedAt,
        finishedAt: updateLog.finishedAt,
        total: updateLog.stats.total,
        processed: updateLog.stats.processed,
        successful: updateLog.stats.successful,
        failed: updateLog.stats.failed,
        skipped: updateLog.stats.skipped,
        logs: updateLog.logs,
        errors: updateLog.errors,
      };
    }

    return res.status(200).json({
      success: true,
      data: progress,
    });
  } catch (error) {
    console.error("[ADMIN UPDATES] Erro ao buscar progresso:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao buscar progresso",
      error: error.message,
    });
  }
});

export default router;

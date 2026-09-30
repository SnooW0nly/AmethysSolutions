import express from "express";
import fs from "fs";
import { startMassUpdate } from "../../../services/massUpdate.js";

const router = express.Router();

/**
 * POST /admin/updates/start-from-path
 * Inicia uma atualização usando um ZIP já uploadado (retornado pelo /analyze)
 * Body (JSON): { planId, zipPath, updateVersion?, foldersToDelete? }
 */
router.post("/", async (req, res) => {
  try {
    const { planId, zipPath, updateVersion, foldersToDelete } = req.body;
    const adminUserId = req.user?._id;

    if (!planId) {
      return res.status(400).json({ success: false, message: "planId é obrigatório" });
    }

    if (!zipPath || !fs.existsSync(zipPath)) {
      return res.status(400).json({ success: false, message: "zipPath inválido ou não encontrado" });
    }

    let folders = [];
    if (foldersToDelete) {
      try {
        folders = typeof foldersToDelete === "string"
          ? JSON.parse(foldersToDelete)
          : foldersToDelete;
        if (!Array.isArray(folders)) folders = [];
      } catch {
        folders = [];
      }
    }

    console.log(`[ADMIN UPDATES] Iniciando atualização via path - Plano: ${planId}, Versão: ${updateVersion || "AUTO"}, Pastas: ${folders.join(", ") || "nenhuma"}`);

    const updateId = await startMassUpdate(planId, zipPath, adminUserId, updateVersion || null, folders);

    return res.status(200).json({
      success: true,
      message: "Atualização iniciada com sucesso",
      data: { updateId },
    });
  } catch (error) {
    console.error("[ADMIN UPDATES] Erro ao iniciar atualização:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao iniciar atualização",
      error: error.message,
    });
  }
});

export default router;
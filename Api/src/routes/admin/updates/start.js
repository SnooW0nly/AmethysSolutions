import express from "express";
import multer from "multer";
import path from "path";
import fs from "fs";
import { startMassUpdate } from "../../../services/massUpdate.js";

const router = express.Router();

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.resolve(process.cwd(), "src/temp/updates");
    if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, `update-${Date.now()}-${file.originalname}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 100 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    if (file.mimetype === "application/zip" || file.originalname.endsWith(".zip")) {
      cb(null, true);
    } else {
      cb(new Error("Apenas arquivos ZIP são permitidos"));
    }
  },
});

/**
 * POST /admin/updates/start
 * Inicia uma atualização em massa.
 *
 * Body (multipart):
 *   planId          string | string[] | "all"
 *                   Um planId, array JSON de planIds, ou "all" para atualizar todos os planos.
 *                   Exemplos:
 *                     planId=amethys-pro
 *                     planId=["amethys-pro","amethys-pro-gift"]
 *                     planId=all
 *   file            ZIP de atualização (obrigatório)
 *   updateVersion   string (opcional — gerado automaticamente se omitido)
 *   foldersToDelete JSON array string de pastas a deletar antes do commit (opcional)
 */
router.post(
  "/",
  upload.single("file"),
  (err, req, res, next) => {
    if (err) {
      console.error("[ADMIN UPDATES] Erro no upload do arquivo:", err);
      return res.status(400).json({ success: false, message: "Erro no upload do arquivo", error: err.message });
    }
    next();
  },
  async (req, res) => {
    console.log(`[ADMIN UPDATES] Nova requisição de atualização recebida`);
    console.log(`[ADMIN UPDATES] Body:`, req.body);
    console.log(`[ADMIN UPDATES] File:`, req.file ? { name: req.file.originalname, size: req.file.size } : "Nenhum arquivo");

    try {
      const { planId: planIdRaw, updateVersion, foldersToDelete: foldersToDeleteRaw } = req.body;
      const adminUserId = req.user?._id;

      // ── Normaliza planId ─────────────────────────────────────────────────
      let planIdOrIds;
      if (!planIdRaw) {
        return res.status(400).json({ success: false, message: "planId é obrigatório (string, array JSON ou 'all')" });
      }

      if (planIdRaw === "all") {
        planIdOrIds = "all";
      } else {
        // Tenta fazer parse como array JSON, senão trata como string simples
        try {
          const parsed = JSON.parse(planIdRaw);
          planIdOrIds = Array.isArray(parsed) ? parsed.filter(Boolean) : [String(parsed)];
        } catch {
          planIdOrIds = [String(planIdRaw).trim()];
        }

        if (planIdOrIds.length === 0) {
          return res.status(400).json({ success: false, message: "planId não pode ser vazio" });
        }
      }

      // ── Normaliza foldersToDelete ────────────────────────────────────────
      let foldersToDelete = [];
      if (foldersToDeleteRaw) {
        try {
          const parsed =
            typeof foldersToDeleteRaw === "string"
              ? JSON.parse(foldersToDeleteRaw)
              : foldersToDeleteRaw;
          foldersToDelete = Array.isArray(parsed) ? parsed : [];
        } catch {
          foldersToDelete = [];
        }
      }

      if (!req.file) {
        return res.status(400).json({ success: false, message: "Arquivo ZIP é obrigatório" });
      }

      const planLabel = planIdOrIds === "all" ? "all" : planIdOrIds.join(", ");
      console.log(
        `[ADMIN UPDATES] Iniciando atualização — Planos: [${planLabel}], Versão: ${updateVersion || "AUTO"}, ` +
        `Pastas a deletar: ${foldersToDelete.join(", ") || "nenhuma"}`
      );

      const updateId = await startMassUpdate(
        planIdOrIds,
        req.file.path,
        adminUserId,
        updateVersion || null,
        foldersToDelete
      );

      console.log(`[ADMIN UPDATES] Atualização iniciada — UpdateID: ${updateId}`);

      return res.status(200).json({
        success: true,
        message: "Atualização iniciada com sucesso",
        data: { updateId, planIds: planIdOrIds },
      });

    } catch (error) {
      console.error("[ADMIN UPDATES] Erro ao iniciar atualização:", error);

      // Remove o ZIP em caso de erro antes de iniciar o processamento
      if (req.file?.path && fs.existsSync(req.file.path)) {
        try { fs.unlinkSync(req.file.path); } catch (_) {}
      }

      return res.status(500).json({
        success: false,
        message: "Erro ao iniciar atualização",
        error: error.message,
      });
    }
  }
);

export default router;
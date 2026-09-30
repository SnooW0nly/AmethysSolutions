/**
 * POST /admin/updates/commit-single
 * Realiza commit em um bot específico pelo appId ou botId
 * Body (multipart): appId, file (zip), foldersToDelete? (JSON array string)
 */

import express from "express";
import multer from "multer";
import path from "path";
import fs from "fs";
import Application from "../../../database/models/Application.js";
import { commitApp } from "../../../services/discloud/commit.js";
import { setRestartFlag } from "../../../utils/setRestartFlag.js";
import discloudService from "../../../services/discloudService.js";

const router = express.Router();

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.resolve(process.cwd(), "src/temp/updates");
    if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, `single-commit-${Date.now()}-${file.originalname}`);
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

router.post(
  "/",
  (req, res, next) => {
    upload.single("file")(req, res, (err) => {
      if (err) return res.status(400).json({ success: false, message: err.message });
      next();
    });
  },
  async (req, res) => {
    const { appId, foldersToDelete: foldersRaw } = req.body;

    if (!appId || !appId.trim()) {
      return res.status(400).json({ success: false, message: "appId é obrigatório" });
    }

    if (!req.file) {
      return res.status(400).json({ success: false, message: "Arquivo ZIP é obrigatório" });
    }

    let foldersToDelete = [];
    if (foldersRaw) {
      try {
        const parsed = typeof foldersRaw === "string" ? JSON.parse(foldersRaw) : foldersRaw;
        if (Array.isArray(parsed)) foldersToDelete = parsed;
      } catch {
        foldersToDelete = [];
      }
    }

    const logs = [];
    const addLog = (type, message) => logs.push({ timestamp: new Date(), type, message });

    try {
      // Busca a aplicação no banco pelo appId da Discloud
      const app = await Application.findOne({
        "hosting.appId": appId.trim(),
        isDeleted: { $ne: true },
      });

      if (!app) {
        return res.status(404).json({
          success: false,
          message: `Nenhuma aplicação encontrada com appId "${appId}"`,
        });
      }

      addLog("info", `Iniciando commit único para ${app.name} (${appId})`);

      // Deleta pastas via console antes do commit
      if (foldersToDelete.length > 0) {
        for (const folder of foldersToDelete) {
          const safe = folder.replace(/[^a-zA-Z0-9_\-./]/g, "");
          if (!safe) continue;
          const result = await discloudService.exec(appId, `rm -rf /home/container/${safe}`);
          if (result.success) {
            addLog("info", `🗑️ Pasta '${safe}' removida`);
          } else {
            addLog("warning", `⚠️ Falha ao remover '${safe}': ${result.error}`);
          }
        }
      }

      if (app.botID) {
        await setRestartFlag(app.botID);
      }

      const fileBuffer = fs.readFileSync(req.file.path);
      const commitResult = await commitApp(appId, fileBuffer);

      if (!commitResult.success) {
        throw new Error(commitResult.error || "Erro desconhecido no commit");
      }

      app.lastUpdateAt = new Date();
      await app.save();

      addLog("success", `✅ Commit realizado com sucesso em ${app.name}`);

      return res.status(200).json({
        success: true,
        message: "Commit realizado com sucesso",
        data: {
          appId,
          appName: app.name,
          logs,
          warning: commitResult.warning || null,
        },
      });
    } catch (error) {
      console.error("[COMMIT SINGLE] Erro:", error);
      addLog("error", `❌ Erro: ${error.message}`);

      // Se app não existe na Discloud, limpa o appId
      if (
        error.message?.includes("não encontrada") ||
        error.message?.includes("not found") ||
        error.message?.includes("404")
      ) {
        await Application.updateOne(
          { "hosting.appId": appId.trim() },
          { $set: { "hosting.appId": null, invalidHosting: true } }
        ).catch(() => {});
        addLog("warning", "appId inválido removido da base (app não existe na Discloud)");
      }

      return res.status(500).json({
        success: false,
        message: "Erro ao realizar commit",
        error: error.message,
        data: { logs },
      });
    } finally {
      // Limpa o arquivo temporário
      if (req.file?.path && fs.existsSync(req.file.path)) {
        fs.unlinkSync(req.file.path);
      }
    }
  }
);

export default router;
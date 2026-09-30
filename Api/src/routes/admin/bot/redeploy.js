import express from "express";
import Application from "../../../database/models/Application.js";
import Plan from "../../../database/models/Plan.js";
import { updateBotWithConfig } from "../../../services/botDeployment.js";
import path from "path";

const router = express.Router();

router.post("/:applicationId/redeploy", async (req, res) => {
  try {
    const { applicationId } = req.params;

    const app = await Application.findById(applicationId).lean();
    if (!app) return res.status(404).json({ error: "Aplicação não encontrada" });

    const appId = app.hosting?.appId;
    if (!appId) {
      // CORRIGIDO: era "sem appId da Discloud"
      return res.status(400).json({ error: "Aplicação sem appId na Discloud" });
    }

    const botID = app.botID;
    if (!botID) return res.status(400).json({ error: "Aplicação sem botID vinculado" });

    const plan = await Plan.findOne({ id: app.plan?.id }).lean();
    if (!plan || !plan.zipFilename) {
      return res.status(404).json({ error: "Plano ou ZIP não encontrado" });
    }

    const zipPath = path.resolve(process.cwd(), "src/database/zip", plan.zipFilename);
    const result = await updateBotWithConfig(appId, zipPath, botID);

    return res.json({ success: true, message: "Re-deploy realizado com sucesso", result });
  } catch (err) {
    console.error("[admin/bot/redeploy]", err);
    return res.status(500).json({ error: "Erro ao fazer re-deploy", details: err.message });
  }
});

export default router;

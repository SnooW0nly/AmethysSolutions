import express from "express";
import Application from "../../database/models/Application.js";
import discloudService from "../../services/discloudService.js";

const router = express.Router();

// PATCH /apps/:id/settings
router.patch("/:id/settings", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;
    const { name, memoryMb } = req.body;

    const app = await Application.findOne({ _id: id, userId })
      .select({ hosting: { appId: 1, provider: 1 } })
      .lean();

    if (!app) return res.status(404).json({ error: "Aplicação não encontrada" });

    const appId = app?.hosting?.appId;
    if (!appId) return res.status(400).json({ error: "Aplicação sem provider/appId vinculado" });

    if (app?.hosting?.provider !== "discloud") {
      return res.status(400).json({ error: "Aplicação ainda não migrada para a Discloud. Entre em contato com o suporte." });
    }

    const settings = {};
    if (memoryMb) settings.ram = memoryMb;

    if (Object.keys(settings).length > 0) {
      const result = await discloudService.updateSettings(appId, settings);
      if (!result.success) return res.status(400).json({ error: result.error });
    }

    // Se o nome mudou, atualizamos no nosso banco também
    if (name) {
      await Application.updateOne({ _id: id }, { $set: { name } });
    }

    return res.json({ success: true, message: "Configurações atualizadas" });
  } catch (err) {
    return res.status(500).json({ error: "Erro ao atualizar configurações" });
  }
});

// POST /apps/:id/oom-notified
router.post("/:id/oom-notified", async (req, res) => {
  // Discloud não tem um endpoint de notificação de OOM específico como a Stackr.
  // Podemos apenas retornar sucesso ou implementar um log interno.
  return res.sendStatus(200);
});

export default router;
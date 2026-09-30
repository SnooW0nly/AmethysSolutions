import express from "express";
import Application from "../../database/models/Application.js";
import { generateInviteUrl } from "../../services/discordService.js";

const router = express.Router();

/**
 * GET /apps/:id/bot/invite
 * Retorna URL de convite do bot
 */
router.get("/:id/bot/invite", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.id": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const botId = app.bot?.id;
    if (!botId) {
      return res.status(400).json({ error: "Bot ID não configurado. Configure o token primeiro." });
    }

    // Permissão 8 = Administrator + bot + applications.commands
    const inviteUrl = generateInviteUrl(botId, "8");

    return res.json({
      inviteUrl,
      botId,
    });
  } catch (err) {
    console.error("[INVITE LINK]", err);
    return res.status(500).json({ error: "Erro ao gerar link de convite" });
  }
});

export default router;

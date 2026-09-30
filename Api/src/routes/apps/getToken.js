import express from "express";
import Application from "../../database/models/Application.js";

const router = express.Router();

/**
 * GET /apps/:id/bot/token
 * Retorna o token do bot (mascarado ou completo)
 */
router.get("/:id/bot/token", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;
    const { reveal } = req.query; // ?reveal=true para mostrar completo

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.token": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const token = app.bot?.token || "";
    const configured = Boolean(token);

    if (!configured) {
      return res.json({
        configured: false,
        token: null,
        masked: null,
      });
    }

    // Mascara token: mostra primeiros 20 e últimos 10 caracteres
    const maskToken = (t) => {
      if (t.length <= 30) return "***";
      return `${t.substring(0, 20)}...${t.substring(t.length - 10)}`;
    };

    return res.json({
      configured: true,
      token: reveal === "true" ? token : null,
      masked: maskToken(token),
    });
  } catch (err) {
    console.error("[GET TOKEN]", err);
    return res.status(500).json({ error: "Erro ao buscar token" });
  }
});

export default router;

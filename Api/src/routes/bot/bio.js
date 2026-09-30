// src/routes/bot/bio.js
// Rota PÚBLICA para os bots buscarem a bio global
// Autenticada pelo botToken da aplicação
import { Router } from "express";
import BotConfig from "../../database/models/BotConfig.js";

const router = Router();

/**
 * GET /bot/bio
 * Headers: authorization: <botToken>
 * Retorna a bio global que o bot deve aplicar
 */
router.get("/bio", async (req, res) => {
  try {
    const authHeader = req.headers["authorization"] || req.headers["x-bot-token"];

    if (!authHeader) {
      return res.status(401).json({ error: "Token não fornecido" });
    }

    // Valida que o botToken existe (qualquer bot cadastrado pode buscar a bio)
    const botConfig = await BotConfig.findOne({ botToken: authHeader }).lean();

    if (!botConfig) {
      return res.status(401).json({ error: "Token inválido" });
    }

    const GlobalConfig = (await import("../../database/models/GlobalConfig.js")).default;
    const config = await GlobalConfig.findOne({ key: "bot_bio" }).lean();

    res.json({
      success: true,
      bio: config?.value || "",
      updatedAt: config?.updatedAt || null,
    });
  } catch (error) {
    console.error("[BOT BIO] Erro ao buscar bio:", error);
    res.status(500).json({ error: "Erro interno" });
  }
});

export default router;
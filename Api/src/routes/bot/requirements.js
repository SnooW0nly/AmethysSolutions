// src/routes/bot/requirements.js
// Rota PÚBLICA para os bots buscarem o requirements.txt global
// Autenticada pelo botToken da aplicação
import { Router } from "express";
import BotConfig from "../../database/models/BotConfig.js";

const router = Router();

const DEFAULT_REQUIREMENTS = `disnake
py-discord-html-transcripts
pymongo
dnspython
requests
pytz
aiohttp
websockets>=12.0
python-socketio
PyJWT>=2.8.0
matplotlib
psutil
PyNaCl
Pillow`;

/**
 * GET /bot/requirements
 * Headers: authorization: <botToken>
 * Retorna o requirements.txt global que o bot deve usar
 */
router.get("/requirements", async (req, res) => {
  try {
    const authHeader = req.headers["authorization"] || req.headers["x-bot-token"];

    if (!authHeader) {
      return res.status(401).json({ error: "Token não fornecido" });
    }

    const botConfig = await BotConfig.findOne({ botToken: authHeader }).lean();

    if (!botConfig) {
      return res.status(401).json({ error: "Token inválido" });
    }

    const GlobalConfig = (await import("../../database/models/GlobalConfig.js")).default;
    const config = await GlobalConfig.findOne({ key: "bot_requirements" }).lean();

    res.json({
      success: true,
      requirements: config?.value || DEFAULT_REQUIREMENTS,
      updatedAt: config?.updatedAt || null,
    });
  } catch (error) {
    console.error("[BOT REQUIREMENTS] Erro ao buscar requirements:", error);
    res.status(500).json({ error: "Erro interno" });
  }
});

export default router;
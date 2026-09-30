import express from "express";
import JSZip from "jszip";
import BotConfig from "../../database/models/BotConfig.js";
import authMiddleware from "../../middlewares/authMiddleware.js";
import requireAdmin from "../../middlewares/requireAdmin.js";
import bioPublicRoute from "./bio.js";
import requirementsPublicRoute from "./requirements.js";

const router = express.Router();

function toConfigJson(doc) {
  return {
    botID: doc.botID,
    botToken: doc.botToken,
    apiURL: doc.apiURL,
    version: doc.version ?? "BETA",
    syncEmojis: !!doc.syncEmojis,
    saveConfig: !!doc.saveConfig,
    startOnBackup: !!doc.startOnBackup,
    bot: {
      token: doc.bot?.token || "",
      owner: doc.bot?.owner || "",
      id: doc.bot?.id || "",
      perms: Array.isArray(doc.bot?.perms) ? doc.bot.perms : [],
      server: doc.bot?.server || "",
    },
  };
}

function generateBotToken() {
  return String(Math.floor(10000 + Math.random() * 90000)); // 5 dígitos
}

// GET /api/bot/:id/info
// Autenticação via header Authorization: <botToken>
router.use(bioPublicRoute);

router.get("/:id/info", async (req, res) => {
  try {
    const { id } = req.params;
    const provided = req.headers["authorization"];

    if (!provided) {
      return res.status(401).json({ error: "authorization header requerido" });
    }

    const doc = await BotConfig.findOne({ botID: id }).lean();
    if (!doc) return res.status(404).json({ error: "Bot não encontrado" });

    if (String(provided) !== String(doc.botToken)) {
      return res.status(401).json({ error: "Token inválido" });
    }

    const info = {
      token: doc.bot?.token || "",
      owner: doc.bot?.owner || "",
      id: doc.bot?.id || "",
      perms: Array.isArray(doc.bot?.perms) ? doc.bot.perms : [],
      server: doc.bot?.server || "",
      version: doc.version || "BETA",
    };

    return res.json(info);
  } catch (err) {
    console.error("[BOT INFO]", err);
    return res.status(500).json({ error: "Erro interno" });
  }
});

// GET /api/bot/:id/config
// Retorna o JSON que deve ser escrito no config.json (apenas admin)
router.get("/:id/config", authMiddleware, requireAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const doc = await BotConfig.findOne({ botID: id });
    if (!doc) return res.status(404).json({ error: "Bot não encontrado" });

    return res.json(toConfigJson(doc));
  } catch (err) {
    console.error("[BOT CONFIG GET]", err);
    return res.status(500).json({ error: "Erro interno" });
  }
});

// GET /api/bot/:id/config.zip
// Retorna um ZIP contendo config.json (apenas admin)
router.get("/:id/config.zip", authMiddleware, requireAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const doc = await BotConfig.findOne({ botID: id });
    if (!doc) return res.status(404).json({ error: "Bot não encontrado" });

    const json = JSON.stringify(toConfigJson(doc), null, 2);

    const zip = new JSZip();
    zip.file("config.json", json);
    const content = await zip.generateAsync({ type: "nodebuffer" });

    res.setHeader("Content-Type", "application/zip");
    res.setHeader("Content-Disposition", `attachment; filename=config_${id}.zip`);
    return res.send(content);
  } catch (err) {
    console.error("[BOT CONFIG ZIP]", err);
    return res.status(500).json({ error: "Erro interno" });
  }
});

// POST /api/bot/:id/config
// Cria/atualiza config no Mongo (apenas admin)
router.post("/:id/config", authMiddleware, requireAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const body = req.body || {};

    // Busca ou cria documento
    let doc = await BotConfig.findOne({ botID: id });

    if (!doc) {
      doc = new BotConfig({
        botID: id,
        botToken: body.botToken || generateBotToken(),
        apiURL: body.apiURL || process.env.BACKEND_URL || "http://localhost",
        version: body.version || "BETA",
        syncEmojis: body.syncEmojis ?? true,
        saveConfig: body.saveConfig ?? true,
        startOnBackup: body.startOnBackup ?? true,
        bot: {
          token: body.bot?.token || "",
          owner: body.bot?.owner || "",
          id: body.bot?.id || "",
          perms: Array.isArray(body.bot?.perms) ? body.bot.perms : [],
          server: body.bot?.server || "",
        },
      });
    } else {
      // Atualiza campos permitidos
      doc.botToken = body.botToken || doc.botToken || generateBotToken();
      doc.apiURL = body.apiURL || doc.apiURL || process.env.BACKEND_URL || "http://localhost";
      doc.version = body.version || doc.version || "BETA";
      doc.syncEmojis = body.syncEmojis ?? doc.syncEmojis ?? true;
      doc.saveConfig = body.saveConfig ?? doc.saveConfig ?? true;
      doc.startOnBackup = body.startOnBackup ?? doc.startOnBackup ?? true;
      doc.bot = {
        token: body.bot?.token ?? doc.bot?.token ?? "",
        owner: body.bot?.owner ?? doc.bot?.owner ?? "",
        id: body.bot?.id ?? doc.bot?.id ?? "",
        perms: Array.isArray(body.bot?.perms) ? body.bot.perms : doc.bot?.perms || [],
        server: body.bot?.server ?? doc.bot?.server ?? "",
      };
    }

    await doc.save();
    return res.status(200).json({ message: "Config salvo", config: toConfigJson(doc) });
  } catch (err) {
    console.error("[BOT CONFIG POST]", err);
    return res.status(500).json({ error: "Erro interno" });
  }
});

router.use(requirementsPublicRoute)

export default router;

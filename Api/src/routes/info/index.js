// src/routes/info/index.js
import express from "express";
import statsRoute from "./stats.js";
import couponsRoute from "./coupons.js";
import plansRoute from "./plans.js";
import BotConfig from "../../database/models/BotConfig.js";
import feedbacksRoute from "./feedbacks.js";
import partnershipsRoute from "./partnerships.js";
import changelogsRoute from "./changelogs.js";
import addonsRoute from "./addons.js";
import freePlanRoute from "./free-plan.js"; // ✅ novo

const router = express.Router();

router.use("/feedbacks", feedbacksRoute);
router.use("/stats", statsRoute);
router.use("/coupons", couponsRoute);
router.use("/plans", plansRoute);
router.use("/partnerships", partnershipsRoute);
router.use("/changelogs", changelogsRoute);
router.use("/addons", addonsRoute);
router.use("/free-plan", freePlanRoute); // ✅ novo — GET /info/free-plan

// Alias: GET /info/:id -> mesmo retorno de /api/bot/:id/info
router.get("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const provided = req.headers["authorization"];
    if (!provided) return res.status(401).json({ error: "authorization header requerido" });

    const doc = await BotConfig.findOne({ botID: id }).lean();
    if (!doc) return res.status(404).json({ error: "Bot não encontrado" });
    if (String(provided) !== String(doc.botToken)) return res.status(401).json({ error: "Token inválido" });

    return res.json({
      token: doc.bot?.token || "",
      owner: doc.bot?.owner || "",
      id: doc.bot?.id || "",
      perms: Array.isArray(doc.bot?.perms) ? doc.bot.perms : [],
      server: doc.bot?.server || "",
    });
  } catch (err) {
    return res.status(500).json({ error: "Erro interno" });
  }
});

export default router;
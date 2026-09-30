import express from "express";
import Application from "../../database/models/Application.js";
import infoApp from "../../services/discloud/info.js";

const router = express.Router();

// GET /apps
router.get("/", async (req, res) => {
  try {
    const userId = req.user?._id;
    const discordId = req.user?.discordId;

    const baseFilter = { isDeleted: { $ne: true }, isBlocked: { $ne: true } };
    const filter = discordId
      ? { $and: [baseFilter, { $or: [{ userId }, { "bot.perms": discordId }] }] }
      : { ...baseFilter, userId };

    const apps = await Application.find(filter)
      .sort({ createdAt: -1 })
      .select({
        name: 1,
        plan: 1,
        hosting: { appId: 1, provider: 1 },
        "bot.token": 1,
        "bot.server": 1,
        "bot.perms": 1,
        expiresAt: 1,
        isDeleted: 1,
        isBlocked: 1,
      })
      .lean();

    const enriched = await Promise.all(
      apps.map(async (a) => {
        let utilizedRam = null;
        let hostingStatus = null;
        try {
          if (a?.hosting?.appId && a?.hosting?.provider === "discloud") {
            const info = await infoApp(a.hosting.appId);

            const container = info?.status?.container;
            if (typeof container === "string") {
              hostingStatus = container === "online" || container === "running" ? "running" : container;
            }

            const ramStr = info?.status?.ram;
            if (typeof ramStr === "string") {
              const match = ramStr.match(/^(\d+(?:\.\d+)?)\s*M/i);
              if (match) utilizedRam = Math.round(parseFloat(match[1]));
            }
          }
        } catch {}

        return {
          _id: a._id,
          name: a.name,
          plan: { id: a.plan?.id, name: a.plan?.name, months: a.plan?.months },
          hosting: { utilizedRam, status: hostingStatus },
          bot: { configured: Boolean(a?.bot?.token), server: a?.bot?.server || null },
          expiresAt: a.expiresAt,
        };
      })
    );

    res.json({ applications: enriched });
  } catch (e) {
    res.status(400).json({ error: "Erro ao listar aplicações" });
  }
});

export default router;
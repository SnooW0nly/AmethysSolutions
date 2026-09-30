import express from "express";
import Application from "../../database/models/Application.js";
import infoApp from "../../services/discloud/info.js";
import { getPermissionsFlags } from "../../utils/authz.js";

const router = express.Router();

// GET /apps/:id/info
router.get("/:id/info", async (req, res) => {
  try {
    const userId = req.user?._id;
    const userDiscordId = req.user?.discordId;
    const { id } = req.params;

    const app = await Application.findOne({
      _id: id,
      $or: [{ userId }, { "bot.perms": userDiscordId || "__none__" }],
    })
      .select({
        name: 1,
        plan: { id: 1, name: 1, months: 1 },
        hosting: { appId: 1, provider: 1 },
        bot: { id: 1, owner: 1, server: 1, perms: 1, token: 1 },
        info: { name: 1, imageUrl: 1 },
        expiresAt: 1,
        userId: 1,
      })
      .lean();

    if (!app) return res.status(404).json({ error: "Aplicação não encontrada" });

    let hostingStatus = null;
    let utilizedRam = null;

    try {
      const appId = app?.hosting?.appId;
      if (appId && app?.hosting?.provider === "discloud") {
        const info = await infoApp(appId);

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

    const permsFlags = getPermissionsFlags(app, req.user);

    res.json({
      application: {
        _id: app._id,
        name: app.name,
        plan: { id: app.plan?.id, name: app.plan?.name, months: app.plan?.months },
        hosting: {
          utilizedRam,
          status: hostingStatus,
          startedAt: null,
        },
        bot: {
          id: app.bot?.id || null,
          owner: app.bot?.owner || null,
          server: app.bot?.server || null,
          perms: (() => {
            const arr = Array.isArray(app.bot?.perms) ? app.bot.perms.slice() : [];
            const owner = app.bot?.owner;
            if (owner && !arr.includes(owner)) arr.push(owner);
            return arr;
          })(),
          configured: Boolean(app?.bot?.token),
        },
        info: {
          name: app.info?.name || "Vision Pro",
          imageUrl: app.info?.imageUrl || "/vision.png",
        },
        expiresAt: app.expiresAt || null,
        permissions: permsFlags,
      },
    });
  } catch (e) {
    res.status(400).json({ error: "Erro ao buscar aplicação" });
  }
});

export default router;
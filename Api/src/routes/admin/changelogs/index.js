/**
 * src/routes/admin/changelogs/index.js
 *
 * Admin CRUD for changelogs + Discord webhook sender (Components V2).
 *
 * Register in src/routes/admin/index.js:
 *   import changelogsAdminRoute from "./changelogs/index.js";
 *   router.use("/changelogs", changelogsAdminRoute);
 *
 * Register public route in your main router (no auth):
 *   import { publicChangelogsRouter } from "./admin/changelogs/index.js";
 *   mainRouter.use("/changelogs", publicChangelogsRouter);
 */

import express from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import Changelog from "../../../database/models/Changelog.js";

// ── Public router (no auth — for /changelogs on main router) ──────────────────

export const publicChangelogsRouter = express.Router();

publicChangelogsRouter.get("/", async (req, res) => {
  try {
    const { limit = 20, page = 1 } = req.query;
    const skip = (parseInt(page) - 1) * parseInt(limit);

    const [items, total] = await Promise.all([
      Changelog.find({ published: true })
        .sort({ publishedAt: -1, createdAt: -1 })
        .limit(parseInt(limit))
        .skip(skip)
        .select("-webhookConfig -createdBy -updatedBy")
        .lean(),
      Changelog.countDocuments({ published: true }),
    ]);

    return res.json({
      success: true,
      data: items,
      pagination: {
        total,
        page: parseInt(page),
        limit: parseInt(limit),
        pages: Math.ceil(total / parseInt(limit)),
      },
    });
  } catch (e) {
    return res.status(500).json({ success: false, message: e.message });
  }
});

// ── Admin router ──────────────────────────────────────────────────────────────

const router = express.Router();
router.use(authMiddleware, requireAdmin);

// GET /admin/changelogs
router.get("/", async (req, res) => {
  try {
    const items = await Changelog.find()
      .sort({ createdAt: -1 })
      .populate("createdBy", "globalName username")
      .lean();
    return res.json({ success: true, data: items });
  } catch (e) {
    return res.status(500).json({ success: false, message: e.message });
  }
});

// GET /admin/changelogs/:id
router.get("/:id", async (req, res) => {
  try {
    const item = await Changelog.findById(req.params.id)
      .populate("createdBy", "globalName username")
      .lean();
    if (!item)
      return res.status(404).json({ success: false, message: "Não encontrado" });
    return res.json({ success: true, data: item });
  } catch (e) {
    return res.status(500).json({ success: false, message: e.message });
  }
});

// POST /admin/changelogs
router.post("/", async (req, res) => {
  try {
    const { version, title, description, items, webhookConfig } = req.body;
    if (!version?.trim() || !title?.trim()) {
      return res
        .status(400)
        .json({ success: false, message: "version e title são obrigatórios" });
    }
    const doc = await Changelog.create({
      version: version.trim(),
      title: title.trim(),
      description: description?.trim() || "",
      items: items || [],
      webhookConfig: webhookConfig || {},
      createdBy: req.user?._id,
    });
    return res.status(201).json({ success: true, data: doc });
  } catch (e) {
    return res.status(500).json({ success: false, message: e.message });
  }
});

// PUT /admin/changelogs/:id
router.put("/:id", async (req, res) => {
  try {
    const { version, title, description, items, published, webhookConfig } =
      req.body;
    const update = { updatedBy: req.user?._id };

    if (version !== undefined) update.version = version.trim?.() || version;
    if (title !== undefined) update.title = title.trim?.() || title;
    if (description !== undefined)
      update.description = description.trim?.() || description;
    if (items !== undefined) update.items = items;
    if (webhookConfig !== undefined) update.webhookConfig = webhookConfig;
    if (published !== undefined) {
      update.published = published;
      if (published) update.publishedAt = new Date();
    }

    const doc = await Changelog.findByIdAndUpdate(
      req.params.id,
      { $set: update },
      { new: true }
    );
    if (!doc)
      return res.status(404).json({ success: false, message: "Não encontrado" });
    return res.json({ success: true, data: doc });
  } catch (e) {
    return res.status(500).json({ success: false, message: e.message });
  }
});

// DELETE /admin/changelogs/:id
router.delete("/:id", async (req, res) => {
  try {
    const doc = await Changelog.findByIdAndDelete(req.params.id);
    if (!doc)
      return res.status(404).json({ success: false, message: "Não encontrado" });
    return res.json({ success: true, message: "Changelog deletado" });
  } catch (e) {
    return res.status(500).json({ success: false, message: e.message });
  }
});

// POST /admin/changelogs/:id/publish — toggle published
router.post("/:id/publish", async (req, res) => {
  try {
    const doc = await Changelog.findById(req.params.id);
    if (!doc)
      return res.status(404).json({ success: false, message: "Não encontrado" });
    doc.published = !doc.published;
    if (doc.published && !doc.publishedAt) doc.publishedAt = new Date();
    doc.updatedBy = req.user?._id;
    await doc.save();
    return res.json({ success: true, data: doc });
  } catch (e) {
    return res.status(500).json({ success: false, message: e.message });
  }
});

// POST /admin/changelogs/:id/webhook — build Components V2 and send to Discord
router.post("/:id/webhook", async (req, res) => {
  try {
    const doc = await Changelog.findById(req.params.id).lean();
    if (!doc)
      return res.status(404).json({ success: false, message: "Não encontrado" });

    // Merge stored config with any overrides in request body
    const cfg = Object.assign({}, doc.webhookConfig || {}, req.body || {});
    const webhookUrl = cfg.webhookUrl;

    if (!webhookUrl) {
      return res
        .status(400)
        .json({ success: false, message: "webhookUrl não configurada" });
    }

    // ── Build emoji map ────────────────────────────────────────────────────────
    const emojiMap = {
      new: cfg.emojiNew || "🆕",
      improved: cfg.emojiImproved || "⬆️",
      fixed: cfg.emojiFixed || "🔧",
    };

    // ── Build items text block ─────────────────────────────────────────────────
    let itemsContent = "";
    for (const item of doc.items || []) {
      const emoji = emojiMap[item.type] || "\u2022";
      const safeTitle = (item.title || "").trim();
      const safeDesc = (item.description || "").trim();
      if (safeTitle) {
        itemsContent += `### ${emoji} ${safeTitle}\n> -# \u2570 ${safeDesc}\n\n`;
      }
    }
    itemsContent = itemsContent.trim();

    // ── Main container components ──────────────────────────────────────────────
    const mainComponents = [];

    // Cover image (type 12 = media gallery)
    if (cfg.coverImageUrl) {
      mainComponents.push({
        type: 12,
        items: [
          {
            media: { url: cfg.coverImageUrl },
            description: null,
            spoiler: false,
          },
        ],
      });
      mainComponents.push({ type: 14, divider: true, spacing: 1 });
    }

    // Header text (type 10 = text display)
    const headerContent = [
      `# <:a1:1489828733937520840><:b2:1489828744809021591><:c3:1489828765222703114><:d4:1489828779827269813><:e5:1489828787334942850> Atualização`,
      `${doc.description ? `- ${doc.description}` : "- Nova atualização na Amethys Applications, as modificações foram as seguintes:"}`,
    ].join("\n");

    if (headerContent.trim()) {
      mainComponents.push({ type: 10, content: headerContent.trim() });
    }

    // Items
    if (itemsContent) {
      mainComponents.push({ type: 14, divider: true, spacing: 1 });
      mainComponents.push({ type: 10, content: itemsContent });
    }

    // ── Containers array ───────────────────────────────────────────────────────
    const containers = [
      {
        type: 17,
        accent_color: Number(cfg.accentColorMain) || 0xc400c4,
        spoiler: false,
        components: mainComponents,
      },
    ];

    // Promo container (optional) — text inside container, button action row outside
    if (cfg.promoText || cfg.promoButtonUrl) {
      if (cfg.promoText?.trim()) {
        containers.push({
          type: 17,
          accent_color: Number(cfg.accentColorPromo) || 0xa61fe3,
          spoiler: false,
          components: [
            { type: 10, content: `-# ${cfg.promoText.trim()}` },
          ],
        });
      }

      if (cfg.promoButtonUrl) {
        // Action Row must be top-level, not inside a Container (type 17)
        containers.push({
          type: 1,
          components: [
            {
              type: 2,
              style: 5, // link button
              label: cfg.promoButtonLabel || "Saiba mais",
              disabled: false,
              url: cfg.promoButtonUrl,
            },
          ],
        });
      }
    }

    // ── Final payload ──────────────────────────────────────────────────────────
    const payload = {
      flags: 32768, // IS_COMPONENTS_V2
      components: containers,
    };

    console.log(
      `[CHANGELOGS WEBHOOK] Sending changelog ${doc._id} (${doc.version}) to Discord`
    );
    console.log(`[CHANGELOGS WEBHOOK] Payload:`, JSON.stringify(payload, null, 2));

    const webhookResUrl = webhookUrl.includes("?") ? `${webhookUrl}&with_components=true` : `${webhookUrl}?with_components=true`;
    const webhookRes = await fetch(webhookResUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    console.log(`[CHANGELOGS WEBHOOK] Discord status: ${webhookRes.status}`);

    if (!webhookRes.ok) {
      const errBody = await webhookRes.text().catch(() => "");
      console.error(
        `[CHANGELOGS WEBHOOK] Discord returned ${webhookRes.status}:`,
        errBody.slice(0, 300)
      );
      return res.status(400).json({
        success: false,
        message: `Discord retornou ${webhookRes.status}`,
        details: errBody.slice(0, 300),
      });
    }

    // Persist sentAt
    await Changelog.findByIdAndUpdate(req.params.id, {
      $set: {
        "webhookConfig.sentAt": new Date(),
        "webhookConfig.webhookUrl": webhookUrl,
      },
    });

    return res.json({
      success: true,
      message: "Enviado com sucesso para o Discord!",
    });
  } catch (e) {
    console.error("[CHANGELOGS WEBHOOK]", e);
    return res.status(500).json({ success: false, message: e.message });
  }
});

export default router;
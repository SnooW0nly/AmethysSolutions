// src/routes/info/changelogs.js
import express from "express";
import Changelog from "../../database/models/Changelog.js";

const router = express.Router();

// GET /info/changelogs
router.get("/", async (req, res) => {
  try {
    const { limit = 20, page = 1 } = req.query;
    const skip = (parseInt(page) - 1) * parseInt(limit);

    const [items, total] = await Promise.all([
      Changelog.find({ published: true })
        .sort({ publishedAt: -1, createdAt: -1 })
        .limit(parseInt(limit))
        .skip(skip)
        .select("-webhookConfig -createdBy -updatedBy -__v")
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
  } catch (err) {
    console.error("[INFO CHANGELOGS]", err);
    return res.status(500).json({ success: false, error: "Erro ao buscar changelogs" });
  }
});

// GET /info/changelogs/:id
router.get("/:id", async (req, res) => {
  try {
    const item = await Changelog.findOne({ _id: req.params.id, published: true })
      .select("-webhookConfig -createdBy -updatedBy -__v")
      .lean();

    if (!item) return res.status(404).json({ success: false, error: "Não encontrado" });

    return res.json({ success: true, data: item });
  } catch (err) {
    console.error("[INFO CHANGELOGS]", err);
    return res.status(500).json({ success: false, error: "Erro interno" });
  }
});

export default router;
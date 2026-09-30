import { Router } from "express";
import Partnership from "../../database/models/Partnership.js";

const router = Router();

// GET /api/info/partnerships
router.get("/", async (req, res) => {
  try {
    const { category = "", featured = "" } = req.query;

    const query = { active: true };
    if (category) query.category = category;
    if (featured === "true") query.featured = true;

    const partnerships = await Partnership.find(query)
      .select("-createdBy -updatedBy -__v")
      .sort({ featured: -1, order: 1, createdAt: -1 })
      .lean();

    const grouped = partnerships.reduce((acc, p) => {
      const cat = p.category || "other";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(p);
      return acc;
    }, {});

    res.json({
      success: true,
      partnerships,
      grouped,
      featured: partnerships.filter((p) => p.featured),
      total: partnerships.length,
    });
  } catch (error) {
    console.error("[INFO PARTNERSHIPS] Erro:", error);
    res.status(500).json({ error: "Erro ao buscar parcerias" });
  }
});

// GET /api/info/partnerships/:slug
router.get("/:slug", async (req, res) => {
  try {
    const partnership = await Partnership.findOne({
      slug: req.params.slug,
      active: true,
    })
      .select("-createdBy -updatedBy -__v")
      .lean();

    if (!partnership)
      return res.status(404).json({ error: "Parceria não encontrada" });

    res.json({ success: true, partnership });
  } catch (error) {
    console.error("[INFO PARTNERSHIPS] Erro:", error);
    res.status(500).json({ error: "Erro ao buscar parceria" });
  }
});

export default router;
import express from "express";
import Plan from "../../database/models/Plan.js";

const router = express.Router();

router.get("/", async (req, res) => {
  try {
    const items = await Plan.find(
      { active: { $ne: false } }, // Filtra planos inativos
      {
        _id: 0,
        name: 1,
        id: 1,
        description: 1,
        primary: 1,
        isFree: 1,
        features: 1,
        "plans.id": 1,
        "plans.name": 1,
        "plans.value": 1,
        "plans.discount": 1,
        "plans.months": 1,
        "plans.description": 1,
      }
    )
      .sort({ primary: -1, name: 1 })
      .lean();
    console.log('[INFO PLANS] Retornando planos ativos:', items.map(p => ({ id: p.id, name: p.name, isFree: p.isFree })));
    return res.json({ plans: items });
  } catch (err) {
    return res.status(500).json({ error: "Erro ao buscar planos" });
  }
});

export default router;



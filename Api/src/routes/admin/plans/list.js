import express from "express";
import Plan from "../../../database/models/Plan.js";
import Payment from "../../../database/models/Payment.js";

const router = express.Router();

router.get("/", async (req, res) => {
  try {
    const [items, counts] = await Promise.all([
      Plan.find({}).sort({ primary: -1, name: 1 }).lean(),
      Payment.aggregate([
        { $match: { status: "approved" } },
        { $group: { _id: "$plan.id", count: { $sum: 1 } } },
      ])
    ]);
    const countMap = Object.fromEntries(counts.map((c) => [c._id, c.count]));
    const withCounts = items.map((p) => ({ ...p, purchasedCount: countMap[p.id] || 0 }));
    return res.json({ success: true, data: withCounts });
  } catch (err) {
    console.error("[ADMIN PLANS] Erro ao listar planos:", err);
    return res.status(500).json({ success: false, error: "Erro ao listar planos" });
  }
});

export default router;



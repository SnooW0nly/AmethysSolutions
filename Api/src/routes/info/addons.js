import express from "express";
import PlanAddon from "../../database/models/PlanAddon.js";

const router = express.Router();

/**
 * GET /info/addons?planId=xxx
 * Retorna addons ativos para um plano
 */
router.get("/", async (req, res) => {
  try {
    const { planId } = req.query;
    const query = { active: true };
    if (planId) {
      query.enabledForPlans = planId;
    }
    const addons = await PlanAddon.find(query)
      .select("id name shortDescription extraValue enabledForPlans")
      .lean();
    return res.json({ success: true, addons });
  } catch (err) {
    return res.status(500).json({ error: "Erro ao buscar addons" });
  }
});

export default router;
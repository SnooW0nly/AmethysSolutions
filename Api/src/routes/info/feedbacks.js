import express from "express";
import { getFeedbacks } from "../../services/discord/feedbacks.js";

const router = express.Router();

/**
 * GET /info/feedbacks
 * Retorna lista de feedbacks do canal do Discord
 */
router.get("/", async (req, res) => {
  try {
    const feedbacks = await getFeedbacks();
    return res.json({ success: true, data: feedbacks });
  } catch (err) {
    console.error("[ROUTE /info/feedbacks]", err);
    return res.status(500).json({ success: false, error: "Erro ao buscar feedbacks" });
  }
});

export default router;
import express from "express";
import Plan from "../../../database/models/Plan.js";

const router = express.Router();

router.post("/", async (req, res) => {
  try {
    const payload = req.body;
    const created = await Plan.create(payload);
    return res.status(201).json({ plan: created });
  } catch (err) {
    if (err?.code === 11000) {
      return res.status(409).json({ error: "ID do plano já existe" });
    }
    return res.status(400).json({ error: "Erro ao criar plano" });
  }
});

export default router;



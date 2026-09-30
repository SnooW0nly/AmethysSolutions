// src/routes/info/free-plan.js
// Endpoint público — retorna apenas os dados necessários para o frontend
// mostrar o botão "Teste grátis" nos cards de plano.
import express from "express";
import FreePlanConfig from "../../database/models/FreePlanConfig.js";

const router = express.Router();

router.get("/", async (req, res) => {
  try {
    const config = await FreePlanConfig.findOne({}).lean();

    if (!config || !config.active) {
      return res.json({ active: false });
    }

    // Expõe só o necessário — sem dados sensíveis de risco/segurança
    return res.json({
      active: true,
      sourcePlanId: config.sourcePlanId,
      durationDays: config.durationDays ?? null,
    });
  } catch (err) {
    console.error("[INFO FREE-PLAN] Erro:", err);
    return res.status(500).json({ active: false });
  }
});

export default router;
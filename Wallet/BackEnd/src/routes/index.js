import express from "express";
import authRoutes from "./auth.js";
import profileRoutes from "./profile.js";
import apiRoutes from "./api/index.js";
import affiliateRoutes from "./affiliates.js";
import ticketRoutes from "./tickets.js";
import authPlanRoutes from "./auth-plan.js"; // ← ADICIONAR

const router = express.Router();

// Health check
router.get("/health", (req, res) => {
  res.json({
    success: true,
    message: "API está funcionando",
    timestamp: new Date().toISOString(),
  });
});

// Rotas de autenticação
router.use("/auth", authRoutes);
router.use("/auth", authPlanRoutes); // ← ADICIONAR (mesmo prefixo /auth)

// Rotas de perfil
router.use("/profile", profileRoutes);

// Rotas de afiliados
router.use("/affiliates", affiliateRoutes);

// Rotas de tickets (solicitações)
router.use("/tickets", ticketRoutes);

// Rotas da API (Amethys Wallet API)
// app.js monta isso em /api, então /api/v1/... funcionará
router.use("/v1", apiRoutes);

export default router;


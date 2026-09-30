import express from "express";
import createRoute from "./create.js";
import statusRoute from "./status.js";
import webhookRoute from "./webhook.js";
import authMiddleware from "../../middlewares/authMiddleware.js";

const router = express.Router();

// Webhook não precisa de autenticação (usa assinatura da Woovi)
router.use("/webhook", webhookRoute);

// Rotas protegidas por autenticação
router.use(authMiddleware);
router.use("/", createRoute);
router.use("/", statusRoute);

export default router;
import { Router } from "express";
import authMiddleware from "../../middlewares/authMiddleware.js";
import chargeFloodProtection from "../../middlewares/chargeFloodProtection.js";
import createRenewalInvoice from "./create.js";
import listInvoices from "./list.js";

const router = Router();

// Todas as rotas exigem autenticação
router.use(authMiddleware);

// Rotas de faturas/renovação
router.post("/create", chargeFloodProtection, createRenewalInvoice);
router.get("/list", listInvoices);

export default router;

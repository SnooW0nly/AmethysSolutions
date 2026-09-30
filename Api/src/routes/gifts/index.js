import { Router } from "express";
import authMiddleware from "../../middlewares/authMiddleware.js";
import redeemGift from "./redeem.js";
import validateGift from "./validate.js";

const router = Router();

// Todas as rotas exigem autenticação
router.use(authMiddleware);

// Rotas para gifts
router.post("/redeem", redeemGift);
router.post("/validate", validateGift);

export default router;

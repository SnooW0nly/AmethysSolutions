import { Router } from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import createGifts from "./create.js";
import listGifts from "./list.js";
import deleteGift from "./delete.js";
import deleteBatch from "./deleteBatch.js";
import getGiftStats from "./stats.js";

const router = Router();

// Todas as rotas abaixo exigem autenticação + admin
router.use(authMiddleware, requireAdmin);

// Rotas de administração de gifts
router.post("/create", createGifts);
router.get("/list", listGifts);
router.get("/stats", getGiftStats);
router.delete("/delete/:id", deleteGift);
router.delete("/batch/:batchId", deleteBatch);

export default router;

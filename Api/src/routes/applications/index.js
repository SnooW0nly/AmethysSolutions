import { Router } from "express";
import authMiddleware from "../../middlewares/authMiddleware.js";
import getApplication from "./get.js";
import getExpiringApplications from "./expiring.js";

const router = Router();

// Todas as rotas exigem autenticação
router.use(authMiddleware);

// Rotas
router.get("/expiring", getExpiringApplications);
router.get("/:id", getApplication);

export default router;

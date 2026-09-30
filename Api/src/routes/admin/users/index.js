import express from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import listRoute from "./list.js";
import adminRoute from "./admin.js";

const router = express.Router();

// Todas as rotas abaixo exigem autenticação + admin
router.use(authMiddleware, requireAdmin);

router.use("/", listRoute);
router.use("/", adminRoute);

export default router;



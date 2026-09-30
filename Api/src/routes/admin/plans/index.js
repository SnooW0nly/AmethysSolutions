import express from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import listRoute from "./list.js";
import createRoute from "./create.js";
import updateRoute from "./update.js";
import removeRoute from "./remove.js";
import uploadRoute from "./upload.js";
import downloadRoute from "./download.js";

const router = express.Router();

// Todas as rotas abaixo exigem autenticação + admin
router.use(authMiddleware, requireAdmin);

router.use("/list", listRoute);
router.use("/create", createRoute);
router.use("/update", updateRoute);
router.use("/remove", removeRoute);
router.use("/upload", uploadRoute);
router.use("/download", downloadRoute);

export default router;



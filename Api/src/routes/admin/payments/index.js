import express from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import listRoute from "./list.js";
import manualApproveRoute from "./manualApprove.js";
import statsRoute from "./stats.js";

const router = express.Router();
router.use(authMiddleware, requireAdmin);

router.use("/stats", statsRoute);
router.use("/", listRoute);
router.use("/", manualApproveRoute);

export default router;



// src/routes/admin/bot/index.js
import express from "express";
import redeployRoute from "./redeploy.js";
import bioRoute from "./bio.js";
import requirementsRoute from "./requirements.js";

const router = express.Router();

router.use("/", redeployRoute);
router.use("/bio", bioRoute);
router.use("/requirements", requirementsRoute);

export default router;
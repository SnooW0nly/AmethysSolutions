import express from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import listRoute from "./list.js";
import createRoute from "./create.js";
import updateRoute from "./update.js";
import archiveRoute from "./archive.js";
import restoreRoute from "./restore.js";
import auditRoute from "./audit.js";
import removeRoute from "./remove.js";

const router = express.Router();
router.use(authMiddleware, requireAdmin);

router.use("/", listRoute);
router.use("/", createRoute);
router.use("/", updateRoute);
router.use("/", archiveRoute);
router.use("/", restoreRoute);
router.use("/", auditRoute);
router.use("/", removeRoute);

export default router;



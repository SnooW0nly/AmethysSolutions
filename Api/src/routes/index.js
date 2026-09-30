import express from "express";
import authRoutes from "./auth/index.js";
import infoRoutes from "./info/index.js";
import adminRoutes from "./admin/index.js";
import paymentRoutes from "./payment/index.js";
import appsRoutes from "./apps/index.js";
import botRoutes from "./bot/index.js";
import giftsRoutes from "./gifts/index.js";
import invoicesRoutes from "./invoices/index.js";
import applicationsRoutes from "./applications/index.js";
import builderRoute from "./builder/index.js";
import affiliateRoutes from "./affiliates/index.js";
import transcriptRoutes from "./transcripts/index.js";
import membersRoutes from "./members/index.js";

const router = express.Router();
router.use("/auth", authRoutes);
router.use("/info", infoRoutes);
router.use("/admin", adminRoutes);
router.use("/payment", paymentRoutes);
router.use("/apps", appsRoutes);
router.use("/bot", botRoutes);
router.use("/gifts", giftsRoutes);
router.use("/invoices", invoicesRoutes);
router.use("/applications", applicationsRoutes);
router.use("/builder", builderRoute)
router.use("/affiliates", affiliateRoutes);
router.use("/v1/transcript", transcriptRoutes);
router.use("/members", membersRoutes);

export default router;
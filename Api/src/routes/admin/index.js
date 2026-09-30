import express from "express";
import plansAdminRoute from "./plans/index.js";
import couponsAdminRoute from "./coupons/index.js";
import usersAdminRoute from "./users/index.js";
import paymentsAdminRoute from "./payments/index.js";
import botAdminRoute from "./bot/index.js";
import giftsAdminRoute from "./gifts/index.js";
import updatesAdminRoute from "./updates/index.js";
import applicationsAdminRoute from "./applications/index.js";
import cacheAdminRoute from "./cache.js";
import partnershipsAdminRoute from "./partnerships/index.js";
import monitorAdminRoute from "./monitor/index.js";
import aiMonitorRoute from "./ai-monitor/index.js";
import changelogsAdminRoute from "./changelogs/index.js";
import discordAdminRoute from "./discord/index.js";
import divulgacaoAdminRoute from "./divulgacao/index.js";
import plansConfigAdminRoute from "./plans-config/index.js";
import avisosAdminRoute from "./avisos/index.js";
import membersAdminRoute from "./members/index.js";

const router = express.Router();

router.use("/plans", plansAdminRoute);
router.use("/coupons", couponsAdminRoute);
router.use("/users", usersAdminRoute);
router.use("/payments", paymentsAdminRoute);
router.use("/bot", botAdminRoute);
router.use("/gifts", giftsAdminRoute);
router.use("/updates", updatesAdminRoute);
router.use("/applications", applicationsAdminRoute);
router.use("/cache", cacheAdminRoute);
router.use("/partnerships", partnershipsAdminRoute);
router.use("/monitor", monitorAdminRoute);
router.use("/ai-monitor", aiMonitorRoute);
router.use("/changelogs", changelogsAdminRoute);
router.use("/discord-config", discordAdminRoute);
router.use("/divulgacao", divulgacaoAdminRoute);
router.use("/plans-config", plansConfigAdminRoute);
router.use("/avisos", avisosAdminRoute);
router.use("/members", membersAdminRoute);

export default router;



import express from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import startRoute from "./start.js";
import startFromPathRoute from "./start-from-path.js";
import progressRoute from "./progress.js";
import listRoute from "./list.js";
import exportRoute from "./export.js";
import foldersRoute from "./folders.js";
import analyzeRoute from "./analyze.js";
import commitSingleRoute from "./commit-single.js";
import githubWebhookRoute from "./github-webhook.js";

const router = express.Router();

// ─── Rota pública (autenticação via HMAC do GitHub, não via JWT) ──────────────
// DEVE ficar antes do authMiddleware para não exigir login de admin
router.use("/github-webhook", githubWebhookRoute);

// ─── Rotas protegidas (requerem admin autenticado) ────────────────────────────
router.use(authMiddleware, requireAdmin);

router.use("/start", startRoute);
router.use("/start-from-path", startFromPathRoute);
router.use("/progress", progressRoute);
router.use("/list", listRoute);
router.use("/export", exportRoute);
router.use("/folders", foldersRoute);
router.use("/analyze", analyzeRoute);
router.use("/commit-single", commitSingleRoute);

export default router;
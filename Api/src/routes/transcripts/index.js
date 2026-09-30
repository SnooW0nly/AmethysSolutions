import { Router } from "express";
import uploadRoute from "./upload.js";
import viewRoute from "./view.js";
import adminRoute from "./admin.js";

const router = Router();

/**
 * Rotas de Transcript
 *
 * POST   /api/v1/transcript/upload          → Upload pelo bot (multipart/form-data)
 * GET    /api/v1/transcript/:id             → Metadados do transcript (JSON)
 * GET    /api/v1/transcript/:id/html        → HTML bruto do transcript
 * GET    /api/v1/transcript/admin/list      → Lista admin (auth + admin)
 * DELETE /api/v1/transcript/admin/:id       → Delete admin
 * GET    /api/v1/transcript/admin/stats     → Estatísticas admin
 */

router.use("/", uploadRoute);
router.use("/admin", adminRoute);
router.use("/", viewRoute); // viewRoute por último pois captura /:id

export default router;
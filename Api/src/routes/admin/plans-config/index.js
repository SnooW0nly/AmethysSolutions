import { Router } from "express";
import FreePlanConfig from "../../../database/models/FreePlanConfig.js";
import PlanAddon from "../../../database/models/PlanAddon.js";
import Plan from "../../../database/models/Plan.js";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";

const router = Router();
router.use(authMiddleware, requireAdmin);

// ════════════════════════════════════════════════════════════════════════════
// FREE PLAN CONFIG
// ════════════════════════════════════════════════════════════════════════════

/**
 * GET /admin/plans-config/free
 * Retorna configuração atual do Bot Free
 */
router.get("/free", async (req, res) => {
  try {
    const config = await FreePlanConfig.findOne({}).lean();
    const plans = await Plan.find({ active: { $ne: false } })
      .select("id name zipFilename")
      .lean();

    return res.json({ success: true, config: config || null, plans });
  } catch (err) {
    console.error("[ADMIN PLANS-CONFIG] Erro ao buscar config free:", err);
    return res.status(500).json({ error: "Erro ao buscar configuração" });
  }
});

/**
 * PUT /admin/plans-config/free
 * Cria ou atualiza configuração do Bot Free
 * Body: { sourcePlanId, durationDays, active, minAccountAgeDays, maxRiskScore }
 */
router.put("/free", async (req, res) => {
  try {
    const { sourcePlanId, durationDays, active, minAccountAgeDays, maxRiskScore } = req.body;
    const adminId = String(req.user?._id || "");

    if (!sourcePlanId) {
      return res.status(400).json({ error: "sourcePlanId é obrigatório" });
    }

    const planExists = await Plan.findOne({ id: sourcePlanId }).lean();
    if (!planExists) {
      return res.status(404).json({ error: "Plano de origem não encontrado" });
    }
    if (!planExists.zipFilename) {
      return res.status(400).json({ error: "O plano selecionado não tem arquivo ZIP cadastrado" });
    }

    if (durationDays !== undefined && (isNaN(durationDays) || durationDays < 0)) {
      return res.status(400).json({ error: "durationDays inválido" });
    }
    if (minAccountAgeDays !== undefined && (isNaN(minAccountAgeDays) || minAccountAgeDays < 0)) {
      return res.status(400).json({ error: "minAccountAgeDays inválido" });
    }
    if (maxRiskScore !== undefined && (isNaN(maxRiskScore) || maxRiskScore < 0 || maxRiskScore > 100)) {
      return res.status(400).json({ error: "maxRiskScore deve ser entre 0 e 100" });
    }

    const payload = {
      sourcePlanId,
      ...(durationDays !== undefined && { durationDays: Number(durationDays) }),
      ...(active !== undefined && { active: Boolean(active) }),
      ...(minAccountAgeDays !== undefined && { minAccountAgeDays: Number(minAccountAgeDays) }),
      ...(maxRiskScore !== undefined && { maxRiskScore: Number(maxRiskScore) }),
      updatedBy: adminId,
    };

    const updated = await FreePlanConfig.findOneAndUpdate(
      {},
      { $set: payload },
      { upsert: true, new: true }
    );

    return res.json({ success: true, config: updated });
  } catch (err) {
    console.error("[ADMIN PLANS-CONFIG] Erro ao atualizar config free:", err);
    return res.status(500).json({ error: "Erro ao atualizar configuração" });
  }
});

// ════════════════════════════════════════════════════════════════════════════
// ADDONS (Bot Black, etc.)
// ════════════════════════════════════════════════════════════════════════════

/**
 * GET /admin/plans-config/addons
 * Lista todos os addons
 */
router.get("/addons", async (req, res) => {
  try {
    const addons = await PlanAddon.find({}).sort({ createdAt: -1 }).lean();
    return res.json({ success: true, addons });
  } catch (err) {
    return res.status(500).json({ error: "Erro ao listar addons" });
  }
});

/**
 * POST /admin/plans-config/addons
 * Cria um novo addon
 * Body: { id, name, shortDescription, extraValue, active, enabledForPlans }
 */
router.post("/addons", async (req, res) => {
  try {
    const { id, name, shortDescription, extraValue, active, enabledForPlans } = req.body;
    const adminId = String(req.user?._id || "");

    if (!id || !name) return res.status(400).json({ error: "id e name são obrigatórios" });
    if (typeof extraValue !== "number" || extraValue < 0) {
      return res.status(400).json({ error: "extraValue deve ser um número >= 0" });
    }

    const slug = id.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
    if (!slug) return res.status(400).json({ error: "ID inválido" });

    const existing = await PlanAddon.findOne({ id: slug }).lean();
    if (existing) return res.status(409).json({ error: "ID já existe" });

    const addon = await PlanAddon.create({
      id: slug,
      name,
      shortDescription: shortDescription || "",
      extraValue,
      active: active !== false,
      enabledForPlans: Array.isArray(enabledForPlans) ? enabledForPlans : [],
      updatedBy: adminId,
    });

    return res.status(201).json({ success: true, addon });
  } catch (err) {
    console.error("[ADMIN ADDONS] Erro ao criar addon:", err);
    return res.status(500).json({ error: "Erro ao criar addon" });
  }
});

/**
 * PUT /admin/plans-config/addons/:id
 * Atualiza addon
 */
router.put("/addons/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const { name, shortDescription, extraValue, active, enabledForPlans } = req.body;
    const adminId = String(req.user?._id || "");

    const update = { updatedBy: adminId };
    if (name !== undefined) update.name = name;
    if (shortDescription !== undefined) update.shortDescription = shortDescription;
    if (extraValue !== undefined) {
      if (typeof extraValue !== "number" || extraValue < 0) {
        return res.status(400).json({ error: "extraValue deve ser um número >= 0" });
      }
      update.extraValue = extraValue;
    }
    if (active !== undefined) update.active = Boolean(active);
    if (Array.isArray(enabledForPlans)) update.enabledForPlans = enabledForPlans;

    const updated = await PlanAddon.findOneAndUpdate({ id }, { $set: update }, { new: true });
    if (!updated) return res.status(404).json({ error: "Addon não encontrado" });

    return res.json({ success: true, addon: updated });
  } catch (err) {
    return res.status(500).json({ error: "Erro ao atualizar addon" });
  }
});

/**
 * DELETE /admin/plans-config/addons/:id
 */
router.delete("/addons/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const deleted = await PlanAddon.findOneAndDelete({ id });
    if (!deleted) return res.status(404).json({ error: "Addon não encontrado" });
    return res.json({ success: true });
  } catch (err) {
    return res.status(500).json({ error: "Erro ao remover addon" });
  }
});

/**
 * GET /admin/plans-config/addons/:id/toggle-plan/:planId
 * Ativa/desativa addon para um plano específico
 */
router.post("/addons/:id/toggle-plan/:planId", async (req, res) => {
  try {
    const { id, planId } = req.params;
    const addon = await PlanAddon.findOne({ id });
    if (!addon) return res.status(404).json({ error: "Addon não encontrado" });

    const idx = addon.enabledForPlans.indexOf(planId);
    if (idx >= 0) {
      addon.enabledForPlans.splice(idx, 1);
    } else {
      addon.enabledForPlans.push(planId);
    }
    await addon.save();

    return res.json({ success: true, enabled: idx < 0, enabledForPlans: addon.enabledForPlans });
  } catch (err) {
    return res.status(500).json({ error: "Erro ao alternar addon" });
  }
});

export default router;
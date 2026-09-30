import { Router } from "express";
import mongoose from "mongoose";
import Partnership from "../../../database/models/Partnership.js";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";

const router = Router();

router.use(authMiddleware, requireAdmin);

/**
 * GET /api/admin/partnerships
 * Lista todas as parcerias com filtros
 */
router.get("/", async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      search = "",
      category = "",
      active = "",
      featured = "",
      sortBy = "order",
      sortOrder = "asc",
    } = req.query;

    const query = {};

    if (search) {
      query.$or = [
        { name: new RegExp(search, "i") },
        { description: new RegExp(search, "i") },
        { tags: { $in: [new RegExp(search, "i")] } },
      ];
    }

    if (category) query.category = category;
    if (active === "true") query.active = true;
    else if (active === "false") query.active = false;
    if (featured === "true") query.featured = true;

    const skip = (Number(page) - 1) * Number(limit);
    const sort = { [sortBy]: sortOrder === "asc" ? 1 : -1 };

    const [partnerships, total] = await Promise.all([
      Partnership.find(query)
        .populate("createdBy", "username globalName")
        .populate("updatedBy", "username globalName")
        .sort(sort)
        .skip(skip)
        .limit(Number(limit))
        .lean(),
      Partnership.countDocuments(query),
    ]);

    res.json({
      success: true,
      partnerships,
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total,
        totalPages: Math.ceil(total / Number(limit)),
      },
    });
  } catch (error) {
    console.error("[ADMIN PARTNERSHIPS] Erro ao listar:", error);
    res.status(500).json({ error: "Erro ao listar parcerias" });
  }
});

/**
 * GET /api/admin/partnerships/:id
 */
router.get("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const partnership = await Partnership.findById(id)
      .populate("createdBy", "username globalName avatar")
      .populate("updatedBy", "username globalName avatar")
      .lean();

    if (!partnership) {
      return res.status(404).json({ error: "Parceria não encontrada" });
    }

    res.json({ success: true, partnership });
  } catch (error) {
    console.error("[ADMIN PARTNERSHIPS] Erro ao buscar:", error);
    res.status(500).json({ error: "Erro ao buscar parceria" });
  }
});

/**
 * POST /api/admin/partnerships
 * Cria uma nova parceria
 */
router.post("/", async (req, res) => {
  try {
    const adminId = req.user?._id;
    const {
      name,
      description,
      shortDescription,
      logoUrl,
      bannerUrl,
      websiteUrl,
      discordUrl,
      discordServerId,
      category,
      tags,
      benefits,
      couponCode,
      couponDiscount,
      featured,
      active,
      order,
    } = req.body;

    if (!name?.trim()) {
      return res.status(400).json({ error: "Nome é obrigatório" });
    }
    if (!description?.trim()) {
      return res.status(400).json({ error: "Descrição é obrigatória" });
    }

    const partnership = await Partnership.create({
      name: name.trim(),
      description: description.trim(),
      shortDescription: shortDescription?.trim(),
      logoUrl: logoUrl?.trim(),
      bannerUrl: bannerUrl?.trim(),
      websiteUrl: websiteUrl?.trim(),
      discordUrl: discordUrl?.trim(),
      discordServerId: discordServerId?.trim(),
      category: category || "other",
      tags: Array.isArray(tags) ? tags.filter(Boolean) : [],
      benefits: Array.isArray(benefits) ? benefits.filter(Boolean) : [],
      couponCode: couponCode?.trim()?.toUpperCase(),
      couponDiscount: couponDiscount?.trim(),
      featured: Boolean(featured),
      active: active !== undefined ? Boolean(active) : true,
      order: Number(order) || 0,
      createdBy: adminId,
      updatedBy: adminId,
    });

    res.status(201).json({
      success: true,
      message: "Parceria criada com sucesso",
      partnership,
    });
  } catch (error) {
    if (error?.code === 11000) {
      return res.status(409).json({ error: "Parceria com esse nome já existe" });
    }
    console.error("[ADMIN PARTNERSHIPS] Erro ao criar:", error);
    res.status(500).json({ error: "Erro ao criar parceria" });
  }
});

/**
 * PUT /api/admin/partnerships/:id
 * Atualiza uma parceria
 */
router.put("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const adminId = req.user?._id;

    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const allowed = [
      "name", "description", "shortDescription", "logoUrl", "bannerUrl",
      "websiteUrl", "discordUrl", "discordServerId", "category", "tags",
      "benefits", "couponCode", "couponDiscount", "featured", "active", "order",
    ];

    const updateData = { updatedBy: adminId };
    for (const field of allowed) {
      if (req.body[field] !== undefined) {
        if (field === "couponCode" && req.body[field]) {
          updateData[field] = String(req.body[field]).trim().toUpperCase();
        } else if (field === "tags" || field === "benefits") {
          updateData[field] = Array.isArray(req.body[field])
            ? req.body[field].filter(Boolean)
            : [];
        } else if (field === "featured" || field === "active") {
          updateData[field] = Boolean(req.body[field]);
        } else if (field === "order") {
          updateData[field] = Number(req.body[field]) || 0;
        } else {
          updateData[field] =
            typeof req.body[field] === "string"
              ? req.body[field].trim()
              : req.body[field];
        }
      }
    }

    const partnership = await Partnership.findByIdAndUpdate(
      id,
      { $set: updateData },
      { new: true, runValidators: true }
    ).lean();

    if (!partnership) {
      return res.status(404).json({ error: "Parceria não encontrada" });
    }

    res.json({
      success: true,
      message: "Parceria atualizada com sucesso",
      partnership,
    });
  } catch (error) {
    console.error("[ADMIN PARTNERSHIPS] Erro ao atualizar:", error);
    res.status(500).json({ error: "Erro ao atualizar parceria" });
  }
});

/**
 * DELETE /api/admin/partnerships/:id
 */
router.delete("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const partnership = await Partnership.findByIdAndDelete(id).lean();
    if (!partnership) {
      return res.status(404).json({ error: "Parceria não encontrada" });
    }

    res.json({ success: true, message: "Parceria removida com sucesso" });
  } catch (error) {
    console.error("[ADMIN PARTNERSHIPS] Erro ao deletar:", error);
    res.status(500).json({ error: "Erro ao deletar parceria" });
  }
});

/**
 * PATCH /api/admin/partnerships/:id/toggle
 * Alterna active
 */
router.patch("/:id/toggle", async (req, res) => {
  try {
    const { id } = req.params;
    const adminId = req.user?._id;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const partnership = await Partnership.findById(id);
    if (!partnership) {
      return res.status(404).json({ error: "Parceria não encontrada" });
    }

    partnership.active = !partnership.active;
    partnership.updatedBy = adminId;
    await partnership.save();

    res.json({
      success: true,
      message: `Parceria ${partnership.active ? "ativada" : "desativada"} com sucesso`,
      active: partnership.active,
    });
  } catch (error) {
    console.error("[ADMIN PARTNERSHIPS] Erro ao alternar:", error);
    res.status(500).json({ error: "Erro ao alternar status" });
  }
});

/**
 * PATCH /api/admin/partnerships/reorder
 * Reordena parcerias
 */
router.patch("/reorder", async (req, res) => {
  try {
    const { items } = req.body; // [{ id, order }]
    if (!Array.isArray(items)) {
      return res.status(400).json({ error: "items deve ser um array" });
    }

    const updates = items.map(({ id, order }) =>
      Partnership.findByIdAndUpdate(id, { $set: { order: Number(order) } })
    );
    await Promise.all(updates);

    res.json({ success: true, message: "Ordem atualizada com sucesso" });
  } catch (error) {
    console.error("[ADMIN PARTNERSHIPS] Erro ao reordenar:", error);
    res.status(500).json({ error: "Erro ao reordenar parcerias" });
  }
});

export default router;
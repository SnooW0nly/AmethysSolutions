import express from "express";
import AuditLog from "../../../database/models/AuditLog.js";

const router = express.Router();

router.get("/audit", async (req, res) => {
  try {
    const { action, name, from, to, page = "1", limit = "20" } = req.query;
    const filter = { entity: "coupon" };
    if (action) filter.action = String(action);
    if (name) filter.targetId = String(name);
    const dateFilter = {};
    if (from) dateFilter.$gte = new Date(String(from));
    if (to) dateFilter.$lte = new Date(String(to));
    if (Object.keys(dateFilter).length) filter.createdAt = dateFilter;

    const pageNum = Math.max(parseInt(String(page), 10) || 1, 1);
    const limitNum = Math.min(Math.max(parseInt(String(limit), 10) || 20, 1), 100);
    const skip = (pageNum - 1) * limitNum;

    const [logs, total] = await Promise.all([
      AuditLog.find(filter).sort({ createdAt: -1 }).skip(skip).limit(limitNum).lean(),
      AuditLog.countDocuments(filter),
    ]);
    res.json({ logs, total, page: pageNum, limit: limitNum });
  } catch (e) {
    res.status(400).json({ error: "Erro ao listar auditoria" });
  }
});

export default router;



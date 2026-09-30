import express from "express";
import Coupon from "../../../database/models/Coupon.js";
import AuditLog from "../../../database/models/AuditLog.js";

const router = express.Router();

router.post("/", async (req, res) => {
  try {
    const payload = req.body;
    const created = await Coupon.create(payload);
    await AuditLog.create({ entity: "coupon", action: "create", actorId: req.user?._id, targetId: created.name, metadata: payload });
    res.status(201).json({ coupon: created });
  } catch (e) {
    if (e?.code === 11000) return res.status(409).json({ error: "Cupom já existe" });
    res.status(400).json({ error: "Erro ao criar cupom" });
  }
});

export default router;



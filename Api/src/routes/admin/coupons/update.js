import express from "express";
import Coupon from "../../../database/models/Coupon.js";
import AuditLog from "../../../database/models/AuditLog.js";

const router = express.Router();

router.put("/:name", async (req, res) => {
  try {
    const { name } = req.params;
    const payload = req.body;
    const updated = await Coupon.findOneAndUpdate({ name }, payload, { new: true });
    if (!updated) return res.status(404).json({ error: "Cupom não encontrado" });
    await AuditLog.create({ entity: "coupon", action: "update", actorId: req.user?._id, targetId: name, metadata: payload });
    res.json({ coupon: updated });
  } catch (e) {
    res.status(400).json({ error: "Erro ao atualizar cupom" });
  }
});

export default router;



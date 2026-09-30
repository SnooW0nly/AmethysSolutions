import express from "express";
import Coupon from "../../../database/models/Coupon.js";
import AuditLog from "../../../database/models/AuditLog.js";

const router = express.Router();

router.post("/:name/archive", async (req, res) => {
  try {
    const { name } = req.params;
    const updated = await Coupon.findOneAndUpdate({ name }, { archived: true }, { new: true });
    if (!updated) return res.status(404).json({ error: "Cupom não encontrado" });
    await AuditLog.create({ entity: "coupon", action: "archive", actorId: req.user?._id, targetId: name });
    res.json({ coupon: updated });
  } catch {
    res.status(400).json({ error: "Erro ao arquivar cupom" });
  }
});

export default router;



import express from "express";
import Coupon from "../../../database/models/Coupon.js";
import AuditLog from "../../../database/models/AuditLog.js";

const router = express.Router();

router.delete("/:name", async (req, res) => {
  try {
    const { name } = req.params;
    const removed = await Coupon.findOneAndDelete({ name });
    if (!removed) return res.status(404).json({ error: "Cupom não encontrado" });
    await AuditLog.create({ entity: "coupon", action: "delete", actorId: req.user?._id, targetId: name });
    res.json({ ok: true });
  } catch (e) {
    res.status(400).json({ error: "Erro ao remover cupom" });
  }
});

export default router;



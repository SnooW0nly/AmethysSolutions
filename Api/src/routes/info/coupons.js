import express from "express";
import Coupon from "../../database/models/Coupon.js";
import AuditLog from "../../database/models/AuditLog.js";
import { verifyToken } from "../../database/auth.js";

const router = express.Router();

function isExpired(c) {
  if (!c.availableDays) return false;
  const created = new Date(c.createdAt).getTime();
  const now = Date.now();
  return now > created + c.availableDays * 24 * 60 * 60 * 1000;
}

router.post("/validate", async (req, res) => {
  try {
    const { name, cartTotal } = req.body || {};
    const c = await Coupon.findOne({ name }).select("name percent archived availableDays createdAt maxUses usedCount minCart").lean();
    if (!c) return res.status(404).json({ valid: false, reason: "not_found" });
    if (c.archived) return res.json({ valid: false, reason: "archived" });
    if (isExpired(c)) return res.json({ valid: false, reason: "expired" });
    if (typeof c.maxUses === "number" && c.usedCount >= c.maxUses) return res.json({ valid: false, reason: "max_uses" });
    if (typeof c.minCart === "number" && Number(cartTotal || 0) < c.minCart) return res.json({ valid: false, reason: "min_cart" });
    let actorId = null;
    try {
      const auth = req.headers["authorization"]; const bearer = auth?.startsWith("Bearer ") ? auth.split(" ")[1] : null;
      const token = bearer || req.cookies?.token;
      if (token) {
        const decoded = verifyToken(token);
        if (decoded?.id) actorId = String(decoded.id);
      }
    } catch {}
    await AuditLog.create({ entity: "coupon", action: "validate", actorId, targetId: name, metadata: { cartTotal } });
    return res.json({ valid: true, coupon: { name: c.name, percent: c.percent } });
  } catch {
    return res.status(400).json({ valid: false, reason: "error" });
  }
});

router.post("/redeem", async (req, res) => {
  try {
    const { name, cartTotal, actorId: bodyActor } = req.body || {};
    const c = await Coupon.findOne({ name });
    if (!c) return res.status(404).json({ ok: false, reason: "not_found" });
    if (c.archived || isExpired(c)) return res.json({ ok: false, reason: "unavailable" });
    if (typeof c.maxUses === "number" && c.usedCount >= c.maxUses) return res.json({ ok: false, reason: "max_uses" });
    if (typeof c.minCart === "number" && Number(cartTotal || 0) < c.minCart) return res.json({ ok: false, reason: "min_cart" });
    c.usedCount = (c.usedCount || 0) + 1;
    await c.save();
    let actorId = bodyActor || null;
    if (!actorId) {
      try {
        const auth = req.headers["authorization"]; const bearer = auth?.startsWith("Bearer ") ? auth.split(" ")[1] : null;
        const token = bearer || req.cookies?.token;
        if (token) {
          const decoded = verifyToken(token);
          if (decoded?.id) actorId = String(decoded.id);
        }
      } catch {}
    }
    await AuditLog.create({ entity: "coupon", action: "redeem", actorId, targetId: name, metadata: { cartTotal } });
    return res.json({ ok: true });
  } catch {
    return res.status(400).json({ ok: false, reason: "error" });
  }
});

export default router;



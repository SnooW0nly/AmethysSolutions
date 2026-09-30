import express from "express";
import Coupon from "../../../database/models/Coupon.js";

const router = express.Router();

router.get("/", async (_req, res) => {
  try {
    const items = await Coupon.find({}).sort({ archived: 1, createdAt: -1 }).lean();
    res.json({ coupons: items });
  } catch (e) {
    res.status(500).json({ error: "Erro ao listar cupons" });
  }
});

export default router;



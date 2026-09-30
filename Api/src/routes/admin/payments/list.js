import express from "express";
import Payment from "../../../database/models/Payment.js";
import User from "../../../database/models/User.js";
import mongoose from "mongoose";

const router = express.Router();

router.get("/", async (req, res) => {
  try {
    const { page = "1", limit = "20", planId, coupon, user: userQuery, from, to } = req.query;
    const p = Math.max(parseInt(String(page), 10) || 1, 1);
    const l = Math.min(Math.max(parseInt(String(limit), 10) || 20, 1), 100);
    const skip = (p - 1) * l;

    // Build filter
    const filter = { status: "approved" };
    if (planId) filter["plan.id"] = String(planId);
    if (coupon) filter["coupon.code"] = String(coupon);
    if (from || to) {
      filter.createdAt = {};
      if (from) filter.createdAt.$gte = new Date(String(from));
      if (to) filter.createdAt.$lte = new Date(String(to));
    }

    // If user query provided, resolve user IDs first
    let userIdFilter = null;
    if (userQuery) {
      const regex = new RegExp(String(userQuery), "i");
      const matchedUsers = await User.find({ $or: [ { username: regex }, { globalName: regex }, { email: regex } ] }).select({ _id: 1 }).lean();
      userIdFilter = matchedUsers.map((u) => new mongoose.Types.ObjectId(String(u._id)));
      if (userIdFilter.length === 0) {
        return res.json({ payments: [], total: 0, page: p, limit: l, totalPages: 0 });
      }
      filter.userId = { $in: userIdFilter };
    }

    const [items, total] = await Promise.all([
      Payment.find(filter)
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(l)
        .lean(),
      Payment.countDocuments(filter),
    ]);

    const userIds = [...new Set(items.map((i) => String(i.userId)))].filter((v) => mongoose.Types.ObjectId.isValid(v));
    const users = await User.find({ _id: { $in: userIds.map((v) => new mongoose.Types.ObjectId(v)) } })
      .select({ _id: 1, username: 1, globalName: 1, email: 1, avatar: 1, discordId: 1 })
      .lean();
    const userMap = Object.fromEntries(users.map((u) => [String(u._id), u]));
    const enriched = items.map((i) => ({ ...i, user: userMap[String(i.userId)] || null }));

    res.json({ payments: enriched, total, page: p, limit: l, totalPages: Math.ceil(total / l) });
  } catch (e) {
    res.status(400).json({ error: "Erro ao listar pagamentos" });
  }
});

export default router;



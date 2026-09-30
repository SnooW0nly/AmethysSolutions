import express from "express";
import User from "../../../database/models/User.js";
import mongoose from "mongoose";

const router = express.Router();

// Lista usuários com paginação e busca simples (username/globalName/email/discordId)
router.get("/", async (req, res) => {
  try {
    const { page = "1", limit = "10", search = "", admin = "", from = "", to = "", sort = "createdAt_desc" } = req.query;
    const pageNum = Math.max(parseInt(String(page), 10) || 1, 1);
    const limitNum = Math.min(Math.max(parseInt(String(limit), 10) || 10, 1), 50);
    const skip = (pageNum - 1) * limitNum;

    const q = String(search || "").trim();
    const filter = {};
    if (q) {
      const or = [
        { username: { $regex: q, $options: "i" } },
        { globalName: { $regex: q, $options: "i" } },
        { email: { $regex: q, $options: "i" } },
        { discordId: { $regex: q, $options: "i" } },
      ];
      if (mongoose.Types.ObjectId.isValid(q)) {
        or.push({ _id: new mongoose.Types.ObjectId(q) });
      }
      Object.assign(filter, { $or: or });
    }
    if (admin === "true") Object.assign(filter, { admin: true });
    if (admin === "false") Object.assign(filter, { admin: false });
    if (from || to) {
      const dt = {};
      if (from) dt.$gte = new Date(String(from));
      if (to) dt.$lte = new Date(String(to));
      Object.assign(filter, { createdAt: dt });
    }

    const sortMap = {
      createdAt_desc: { createdAt: -1 },
      createdAt_asc: { createdAt: 1 },
      name_asc: { globalName: 1 },
      name_desc: { globalName: -1 },
    };
    const sortBy = sortMap[String(sort)] || sortMap.createdAt_desc;

    const projection = "discordId username globalName email avatar admin createdAt";
    const [items, total] = await Promise.all([
      User.find(filter).select(projection).sort(sortBy).skip(skip).limit(limitNum).lean(),
      User.countDocuments(filter),
    ]);

    return res.json({ users: items, total, page: pageNum, limit: limitNum });
  } catch (e) {
    return res.status(500).json({ error: "Erro ao listar usuários" });
  }
});

export default router;




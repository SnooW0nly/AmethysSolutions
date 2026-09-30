import express from "express";
import authMiddleware from "../../middlewares/authMiddleware.js";
import User from "../../database/models/User.js";

const router = express.Router();

router.get("/", authMiddleware, async (req, res) => {
  try {
    const userId = req.user._id || req.user._id;
    console.log("[session] Buscando sessão para user:", userId);
    
    const user = await User.findById(userId).lean();
    if (!user) {
      console.error("[session] Usuário não encontrado:", userId);
      return res.status(404).json({ error: "Erro ao buscar sessão" });
    }

    const normalized = {
      id: user.discordId,
      username: user.username,
      globalName: user.globalName,
      email: user.email,
      avatar: user.avatar || undefined,
    };
    if (user.admin) normalized.admin = true;

    return res.json({ user: normalized });
  } catch (err) {
    return res.status(500).json({ error: "Erro ao buscar sessão" });
  }
});

export default router;

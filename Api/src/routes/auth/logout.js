import express from "express";
import authMiddleware from "../../middlewares/authMiddleware.js";
import User from "../../database/models/User.js";

const router = express.Router();

router.post("/", authMiddleware, async (req, res) => {
  try {
    // Incrementa tokenVersion para invalidar todos os tokens existentes
    await User.findByIdAndUpdate(req.user._id, { $inc: { tokenVersion: 1 } });
  } catch {}

  const isProd = process.env.NODE_ENV === "production";

  res.clearCookie("token", {
    httpOnly: true,
    sameSite: isProd ? "none" : "lax",
    secure: isProd,
    path: "/",
    domain: isProd ? process.env.COOKIE_DOMAIN : undefined,
  });

  return res.json({ ok: true });
});

export default router;
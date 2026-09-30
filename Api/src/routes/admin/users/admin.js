import express from "express";
import User from "../../../database/models/User.js";
import Application from "../../../database/models/Application.js";

const router = express.Router();

// Atualiza flag admin
router.put("/:id/admin", async (req, res) => {
  try {
    const { id } = req.params; // Mongo _id
    const { admin } = req.body || {};
    const updated = await User.findByIdAndUpdate(id, { admin: !!admin }, { new: true }).select(
      "discordId username globalName email avatar admin createdAt"
    );
    if (!updated) return res.status(404).json({ error: "Usuário não encontrado" });
    return res.json({ user: updated });
  } catch (e) {
    return res.status(400).json({ error: "Erro ao atualizar usuário" });
  }
});

// Bloqueia/Desbloqueia usuário
router.put("/:id/block", async (req, res) => {
  try {
    const { id } = req.params; // Mongo _id
    const { blocked } = req.body || {};
    const updated = await User.findByIdAndUpdate(
      id,
      { blocked: !!blocked, $inc: { tokenVersion: 1 } },
      { new: true }
    ).select("discordId username globalName email avatar admin blocked createdAt");
    if (!updated) return res.status(404).json({ error: "Usuário não encontrado" });
    return res.json({ user: updated });
  } catch (e) {
    return res.status(400).json({ error: "Erro ao atualizar usuário" });
  }
});

// Obter token OAuth atual (se existir) - apenas admins
router.get("/:id/token", async (req, res) => {
  try {
    const { id } = req.params; // Mongo _id
    const user = await User.findById(id).select("oauth").lean();
    if (!user) return res.status(404).json({ error: "Usuário não encontrado" });
    // retorna somente metadados e accessToken (já que pedido é explícito por admin)
    return res.json({ oauth: user.oauth || null });
  } catch (e) {
    return res.status(400).json({ error: "Erro ao buscar token" });
  }
});

// Listar aplicações do usuário
router.get("/:id/apps", async (req, res) => {
  try {
    const { id } = req.params; // Mongo _id
    const apps = await Application.find({ userId: id }).select("_id plan.id plan.name hosting.appId name").lean();
    return res.json({ apps: (apps || []).map((a) => ({ id: a._id, planId: a.plan?.id, planName: a.plan?.name, hostingAppId: a.hosting?.appId, name: a.name })) });
  } catch (e) {
    return res.status(400).json({ error: "Erro ao listar apps" });
  }
});

// Puxar usuário para o servidor principal
router.post("/:id/puxar", async (req, res) => {
  try {
    const { id } = req.params; // Mongo _id do usuário
    const user = await User.findById(id).select("discordId oauth globalName").lean();
    if (!user) return res.status(404).json({ error: "Usuário não encontrado" });
    if (!user.discordId) return res.status(400).json({ error: "Usuário sem discordId" });
    if (!user.oauth?.accessToken) return res.status(400).json({ error: "Usuário sem accessToken OAuth" });

    const { addUserToGuild } = await import("../../../services/discord/puxarDiscord.js");
    await addUserToGuild({ userId: user.discordId, accessToken: user.oauth.accessToken, guildId: process.env.DISCORD_GUILD_ID, nickname: user.globalName });
    return res.json({ ok: true });
  } catch (e) {
    return res.status(400).json({ error: e?.message || "Erro ao puxar usuário" });
  }
});

export default router;




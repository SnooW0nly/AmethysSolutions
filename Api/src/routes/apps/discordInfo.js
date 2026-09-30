import express from "express";
import Application from "../../database/models/Application.js";
import { getUserInfo, getGuildInfo, getAvatarUrl, getGuildIconUrl } from "../../services/discordService.js";
import fetch from "node-fetch";

const router = express.Router();

/**
 * GET /apps/:id/discord/info
 * Busca informações do próprio bot
 */
router.get("/:id/discord/info", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.token": 1, "bot.id": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const token = app.bot?.token;
    if (!token) {
      return res.status(400).json({ error: "Token não configurado" });
    }

    // Busca info do bot via Discord API
    const response = await fetch("https://discord.com/api/v10/users/@me", {
      headers: { Authorization: `Bot ${token}` },
    });

    if (!response.ok) {
      return res.status(400).json({ error: "Erro ao buscar informações do bot" });
    }

    const botData = await response.json();

    return res.json({
      id: botData.id,
      username: botData.username,
      discriminator: botData.discriminator,
      avatar: botData.avatar 
        ? `https://cdn.discordapp.com/avatars/${botData.id}/${botData.avatar}.png?size=128`
        : null,
    });
  } catch (err) {
    console.error("[DISCORD BOT INFO]", err);
    return res.status(500).json({ error: "Erro ao buscar informações do bot" });
  }
});

/**
 * GET /apps/:id/discord/user/:userId
 * Busca informações de um usuário Discord
 */
router.get("/:id/discord/user/:userId", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id, userId: targetUserId } = req.params;

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.token": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const token = app.bot?.token;
    if (!token) {
      return res.status(400).json({ error: "Token não configurado" });
    }

    const userInfo = await getUserInfo(token, targetUserId);
    if (!userInfo) {
      return res.status(404).json({ error: "Usuário não encontrado" });
    }

    return res.json({
      id: userInfo.id,
      username: userInfo.username,
      discriminator: userInfo.discriminator,
      global_name: userInfo.global_name,
      avatar: getAvatarUrl(userInfo.id, userInfo.avatar),
    });
  } catch (err) {
    console.error("[DISCORD USER INFO]", err);
    return res.status(500).json({ error: "Erro ao buscar informações do usuário" });
  }
});

/**
 * GET /apps/:id/discord/guild/:guildId
 * Busca informações de um servidor Discord
 */
router.get("/:id/discord/guild/:guildId", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id, guildId } = req.params;

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.token": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const token = app.bot?.token;
    if (!token) {
      return res.status(400).json({ error: "Token não configurado" });
    }

    const guildInfo = await getGuildInfo(token, guildId);
    if (!guildInfo) {
      return res.status(404).json({ error: "Servidor não encontrado ou bot não está no servidor" });
    }

    return res.json({
      id: guildInfo.id,
      name: guildInfo.name,
      icon: getGuildIconUrl(guildInfo.id, guildInfo.icon),
      member_count: guildInfo.member_count,
      owner_id: guildInfo.owner_id,
    });
  } catch (err) {
    console.error("[DISCORD GUILD INFO]", err);
    return res.status(500).json({ error: "Erro ao buscar informações do servidor" });
  }
});

/**
 * GET /apps/:id/discord/users
 * Busca informações de múltiplos usuários
 */
router.post("/:id/discord/users", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;
    const { userIds } = req.body;

    if (!Array.isArray(userIds) || userIds.length === 0) {
      return res.status(400).json({ error: "userIds deve ser um array não vazio" });
    }

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.token": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const token = app.bot?.token;
    if (!token) {
      return res.status(400).json({ error: "Token não configurado" });
    }

    // Busca info de todos os usuários
    const usersPromises = userIds.map(uid => getUserInfo(token, uid));
    const usersData = await Promise.all(usersPromises);

    const users = usersData
      .filter(u => u !== null)
      .map(u => ({
        id: u.id,
        username: u.username,
        discriminator: u.discriminator,
        global_name: u.global_name,
        avatar: getAvatarUrl(u.id, u.avatar),
      }));

    return res.json({ users });
  } catch (err) {
    console.error("[DISCORD USERS INFO]", err);
    return res.status(500).json({ error: "Erro ao buscar informações dos usuários" });
  }
});

export default router;

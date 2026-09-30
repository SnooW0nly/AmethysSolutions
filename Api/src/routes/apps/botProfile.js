import express from "express";
import Application from "../../database/models/Application.js";
import fetch from "node-fetch";

const router = express.Router();

/**
 * GET /apps/:id/bot/profile
 * Busca perfil do bot (username, avatar, banner)
 */
router.get("/:id/bot/profile", async (req, res) => {
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

    // Busca info do bot no Discord
    const response = await fetch("https://discord.com/api/v10/users/@me", {
      headers: {
        Authorization: `Bot ${token}`,
      },
    });

    if (!response.ok) {
      return res.status(400).json({ error: "Erro ao buscar perfil do bot" });
    }

    const botData = await response.json();

    return res.json({
      username: botData.username,
      discriminator: botData.discriminator,
      avatar: botData.avatar 
        ? `https://cdn.discordapp.com/avatars/${botData.id}/${botData.avatar}.png?size=256`
        : null,
      banner: botData.banner
        ? `https://cdn.discordapp.com/banners/${botData.id}/${botData.banner}.png?size=600`
        : null,
    });
  } catch (err) {
    console.error("[BOT PROFILE GET]", err);
    return res.status(500).json({ error: "Erro ao buscar perfil" });
  }
});

/**
 * PATCH /apps/:id/bot/profile
 * Atualiza perfil do bot (username, avatar, banner)
 */
router.patch("/:id/bot/profile", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;
    const { username, avatar, banner } = req.body;

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

    // Prepara body para atualização
    const updateBody = {};
    if (username !== undefined) updateBody.username = username;
    if (avatar !== undefined) updateBody.avatar = avatar;
    if (banner !== undefined) updateBody.banner = banner;

    if (Object.keys(updateBody).length === 0) {
      return res.status(400).json({ error: "Nenhuma alteração fornecida" });
    }

    // Atualiza perfil no Discord
    const response = await fetch("https://discord.com/api/v10/users/@me", {
      method: "PATCH",
      headers: {
        Authorization: `Bot ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updateBody),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("[BOT PROFILE UPDATE ERROR]", errorData);
      
      // Trata erros específicos do Discord
      if (errorData.code === 50035) {
        return res.status(400).json({ 
          error: "Dados inválidos. Verifique o formato das imagens e tente novamente." 
        });
      }
      
      if (errorData.code === 30002) {
        return res.status(429).json({ 
          error: "Limite de alterações atingido. Aguarde antes de tentar novamente." 
        });
      }

      return res.status(400).json({ 
        error: errorData.message || "Erro ao atualizar perfil no Discord" 
      });
    }

    const botData = await response.json();

    return res.json({
      username: botData.username,
      discriminator: botData.discriminator,
      avatar: botData.avatar 
        ? `https://cdn.discordapp.com/avatars/${botData.id}/${botData.avatar}.png?size=256`
        : null,
      banner: botData.banner
        ? `https://cdn.discordapp.com/banners/${botData.id}/${botData.banner}.png?size=600`
        : null,
    });
  } catch (err) {
    console.error("[BOT PROFILE PATCH]", err);
    return res.status(500).json({ error: "Erro ao atualizar perfil" });
  }
});

export default router;

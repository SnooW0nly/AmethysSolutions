import express from "express";
import Application from "../../database/models/Application.js";
import BotConfig from "../../database/models/BotConfig.js";
import { getBotInfo } from "../../services/discordService.js";
import { assertRestricted } from "../../utils/authz.js";

const router = express.Router();

/**
 * PUT /apps/:id/bot
 * Atualiza configurações do bot (token, owner, perms, server)
 * SINCRONIZA Application E BotConfig
 */
router.put("/:id/bot", async (req, res) => {
  try {
    const userId = req.user?._id;
    const userDiscordId = req.user?.discordId;
    const { id } = req.params;
    const { token, owner, perms, server } = req.body;

    // 1. Busca aplicação — aceita dono (userId) OU usuário com permissão (bot.perms)
    //    Mesmo padrão usado em info.js para não dar 404 a quem tem acesso via perms
    const app = await Application.findOne({
      _id: id,
      $or: [
        { userId },
        { "bot.perms": userDiscordId || "__none__" },
      ],
    });

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    // 1.1. assertRestricted só é chamado quando campos sensíveis estão sendo alterados
    //      (token ou owner). perms e server podem ser alterados por qualquer um em bot.perms.
    const isChangingRestrictedFields = token !== undefined || owner !== undefined;
    if (isChangingRestrictedFields) {
      try {
        assertRestricted(app, req.user);
      } catch (e) {
        const status = e?.status || 403;
        return res.status(status).json({ error: "Acesso negado. Apenas o dono da conta pode alterar token ou owner." });
      }
    }

    const botID = app.botID;
    if (!botID) {
      return res.status(400).json({ error: "Aplicação sem botID vinculado" });
    }

    // 2. Valida dados
    if (token !== undefined && typeof token !== "string") {
      return res.status(400).json({ error: "Token inválido" });
    }

    if (owner !== undefined && typeof owner !== "string") {
      return res.status(400).json({ error: "Owner inválido" });
    }

    if (perms !== undefined && !Array.isArray(perms)) {
      return res.status(400).json({ error: "Perms deve ser um array" });
    }

    if (server !== undefined && typeof server !== "string") {
      return res.status(400).json({ error: "Server inválido" });
    }

    // 3. Se token foi fornecido, busca ID do bot no Discord
    let botInfo = null;
    if (token !== undefined) {
      try {
        botInfo = await getBotInfo(token);
        if (!botInfo.bot) {
          return res.status(400).json({ error: "Token fornecido não é de um bot" });
        }
      } catch (err) {
        return res.status(400).json({ error: "Token inválido ou bot não encontrado no Discord" });
      }
    }

    // 4. Atualiza Application.bot
    const updates = {};
    if (token !== undefined) updates["bot.token"] = token;
    if (botInfo) updates["bot.id"] = botInfo.id;
    if (owner !== undefined) updates["bot.owner"] = owner;
    // Garante owner imutável em perms
    if (perms !== undefined) {
      const targetOwner = owner !== undefined ? owner : (app.bot?.owner || null);
      const incoming = Array.isArray(perms) ? perms : [];
      const unique = Array.from(new Set(incoming));
      if (targetOwner && !unique.includes(targetOwner)) unique.push(targetOwner);
      updates["bot.perms"] = unique;
    }
    if (server !== undefined) updates["bot.server"] = server;

    if (Object.keys(updates).length === 0) {
      return res.status(400).json({ error: "Nenhum campo para atualizar" });
    }

    await Application.updateOne({ _id: id }, { $set: updates });

    // 5. Sincroniza com BotConfig
    const botConfig = await BotConfig.findOne({ botID });
    if (botConfig) {
      if (token !== undefined) botConfig.bot.token = token;
      if (botInfo) botConfig.bot.id = botInfo.id;
      if (owner !== undefined) {
        botConfig.bot.owner = owner;
        if (perms === undefined) {
          const currentPerms = botConfig.bot.perms || [];
          if (!currentPerms.includes(owner)) {
            botConfig.bot.perms = [...currentPerms, owner];
          }
        }
      }
      if (perms !== undefined) {
        const targetOwner = owner !== undefined ? owner : (app.bot?.owner || null);
        const incoming = Array.isArray(perms) ? perms : [];
        const unique = Array.from(new Set(incoming));
        if (targetOwner && !unique.includes(targetOwner)) unique.push(targetOwner);
        botConfig.bot.perms = unique;
      }
      if (server !== undefined) botConfig.bot.server = server;

      await botConfig.save();
    }

    // 6. Busca dados atualizados
    const updatedApp = await Application.findById(id)
      .select({ bot: 1 })
      .lean();

    return res.json({
      success: true,
      bot: {
        id: updatedApp.bot?.id || null,
        owner: updatedApp.bot?.owner || null,
        server: updatedApp.bot?.server || null,
        perms: Array.isArray(updatedApp.bot?.perms) ? updatedApp.bot.perms : [],
        configured: Boolean(updatedApp.bot?.token || ""),
      },
      botInfo: botInfo ? {
        id: botInfo.id,
        username: botInfo.username,
        discriminator: botInfo.discriminator,
      } : null,
      needsRestart: true,
      message: "Configurações atualizadas. Reinicie o bot para aplicar as mudanças.",
    });
  } catch (err) {
    console.error("[UPDATE BOT]", err);
    return res.status(500).json({ error: "Erro ao atualizar configurações" });
  }
});

export default router;
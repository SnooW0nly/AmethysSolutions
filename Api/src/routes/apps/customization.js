import express from "express";
import Application from "../../database/models/Application.js";
import { getBotDocument, saveBotDocument } from "../../services/botDatabaseService.js";
import fetch from "node-fetch";

const router = express.Router();

/**
 * Helper: Converte URL de imagem para base64
 */
async function imageUrlToBase64(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Erro ao baixar imagem");
    
    const buffer = await response.buffer();
    const base64 = buffer.toString('base64');
    
    // Detecta tipo de imagem pela URL ou content-type
    const contentType = response.headers.get('content-type') || 'image/png';
    const imageType = contentType.split('/')[1] || 'png';
    
    return `data:image/${imageType};base64,${base64}`;
  } catch (err) {
    console.error('[IMAGE URL TO BASE64]', err);
    throw new Error('Erro ao processar imagem');
  }
}

/**
 * GET /apps/:id/customization
 * Busca todas as configurações de personalização do bot
 */
router.get("/:id/customization", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.id": 1, "bot.token": 1, "bot.configured": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const botId = app.bot?.id;
    const token = app.bot?.token;
    
    if (!botId || !token) {
      return res.status(400).json({ error: "Bot não configurado" });
    }

    // Busca configurações do bot no MongoDB
    const [colorsDoc, statusDoc, modeDoc] = await Promise.all([
      getBotDocument(botId, "custom_colors", {}),
      getBotDocument(botId, "custom_status", {}),
      getBotDocument(botId, "custom_mode", {}),
    ]);

    // Busca perfil do Discord
    const profile = await fetchBotProfile(token);

    return res.json({
      colors: colorsDoc || {
        primary: "",
        secondary: "",
        success: "",
        danger: "",
        warning: "",
      },
      status: statusDoc || {
        type: "online",
        names: [],
      },
      mode: modeDoc?.mode || "components",
      profile: profile || null,
    });
  } catch (err) {
    console.error("[CUSTOMIZATION GET]", err);
    return res.status(500).json({ error: "Erro ao buscar personalização" });
  }
});

/**
 * PATCH /apps/:id/customization/colors
 * Atualiza cores do bot
 */
router.patch("/:id/customization/colors", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;
    const { primary, secondary, success, danger, warning } = req.body;

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.id": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const botId = app.bot?.id;
    if (!botId) {
      return res.status(400).json({ error: "Bot ID não configurado" });
    }

    // Valida cores hexadecimais
    const hexPattern = /^#?([0-9a-fA-F]{6})$/;
    const colors = { primary, secondary, success, danger, warning };
    
    for (const [key, value] of Object.entries(colors)) {
      if (value && !hexPattern.test(value)) {
        return res.status(400).json({ 
          error: `Cor ${key} inválida. Use formato hexadecimal (#RRGGBB)` 
        });
      }
      // Garante que começa com #
      if (value && !value.startsWith("#")) {
        colors[key] = `#${value}`;
      }
    }

    // Salva no MongoDB do bot
    const saved = await saveBotDocument(botId, "custom_colors", {}, colors);
    
    if (!saved) {
      return res.status(500).json({ error: "Erro ao salvar cores" });
    }

    return res.json({ colors });
  } catch (err) {
    console.error("[CUSTOMIZATION COLORS]", err);
    return res.status(500).json({ error: "Erro ao atualizar cores" });
  }
});

/**
 * PATCH /apps/:id/customization/status
 * Atualiza status do bot
 */
router.patch("/:id/customization/status", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;
    const { type, names } = req.body;

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.id": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const botId = app.bot?.id;
    if (!botId) {
      return res.status(400).json({ error: "Bot ID não configurado" });
    }

    // Valida tipo de status
    const validTypes = ["online", "idle", "dnd", "streaming", "offline"];
    if (type && !validTypes.includes(type)) {
      return res.status(400).json({ 
        error: "Tipo de status inválido. Use: online, idle, dnd, streaming ou offline" 
      });
    }

    // Valida nomes
    if (names && !Array.isArray(names)) {
      return res.status(400).json({ error: "Names deve ser um array" });
    }

    const statusData = {};
    if (type) statusData.type = type;
    if (names !== undefined) statusData.names = names.filter(n => n && n.trim());

    // Busca status atual e mescla
    const currentStatus = await getBotDocument(botId, "custom_status") || {};
    const updatedStatus = { ...currentStatus, ...statusData };

    // Salva no MongoDB do bot
    const saved = await saveBotDocument(botId, "custom_status", {}, updatedStatus);
    
    if (!saved) {
      return res.status(500).json({ error: "Erro ao salvar status" });
    }

    return res.json({ status: updatedStatus });
  } catch (err) {
    console.error("[CUSTOMIZATION STATUS]", err);
    return res.status(500).json({ error: "Erro ao atualizar status" });
  }
});

/**
 * PATCH /apps/:id/customization/mode
 * Atualiza modo de exibição do bot
 */
router.patch("/:id/customization/mode", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id } = req.params;
    const { mode } = req.body;

    const app = await Application.findOne({ _id: id, userId })
      .select({ "bot.id": 1 })
      .lean();

    if (!app) {
      return res.status(404).json({ error: "Aplicação não encontrada" });
    }

    const botId = app.bot?.id;
    if (!botId) {
      return res.status(400).json({ error: "Bot ID não configurado" });
    }

    // Valida modo
    const validModes = ["embed", "components"];
    if (!validModes.includes(mode)) {
      return res.status(400).json({ 
        error: "Modo inválido. Use: embed ou components" 
      });
    }

    // Salva no MongoDB do bot
    const saved = await saveBotDocument(botId, "custom_mode", {}, { mode });
    
    if (!saved) {
      return res.status(500).json({ error: "Erro ao salvar modo" });
    }

    return res.json({ mode });
  } catch (err) {
    console.error("[CUSTOMIZATION MODE]", err);
    return res.status(500).json({ error: "Erro ao atualizar modo" });
  }
});

/**
 * PATCH /apps/:id/customization/profile
 * Atualiza perfil do bot (nome, avatar, banner) via Discord API
 */
router.patch("/:id/customization/profile", async (req, res) => {
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
    
    if (username !== undefined && username.trim()) {
      updateBody.username = username;
    }
    
    // Se avatar é uma URL, converte para base64
    if (avatar !== undefined && avatar) {
      if (avatar.startsWith('http://') || avatar.startsWith('https://')) {
        updateBody.avatar = await imageUrlToBase64(avatar);
      } else if (avatar.startsWith('data:image')) {
        updateBody.avatar = avatar;
      }
    }
    
    // Se banner é uma URL, converte para base64
    if (banner !== undefined && banner) {
      if (banner.startsWith('http://') || banner.startsWith('https://')) {
        updateBody.banner = await imageUrlToBase64(banner);
      } else if (banner.startsWith('data:image')) {
        updateBody.banner = banner;
      }
    }

    if (Object.keys(updateBody).length === 0) {
      return res.status(400).json({ error: "Nenhuma alteração fornecida" });
    }

    console.log('[CUSTOMIZATION PROFILE] Atualizando:', Object.keys(updateBody));

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
      const errorText = await response.text();
      let errorData;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { message: errorText };
      }
      
      console.error("[CUSTOMIZATION PROFILE ERROR]", errorData);
      
      if (errorData.code === 50035) {
        return res.status(400).json({ 
          error: "Dados inválidos. Verifique o formato das imagens." 
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
      profile: {
        username: botData.username,
        discriminator: botData.discriminator,
        avatar: botData.avatar 
          ? `https://cdn.discordapp.com/avatars/${botData.id}/${botData.avatar}.png?size=256`
          : null,
        banner: botData.banner
          ? `https://cdn.discordapp.com/banners/${botData.id}/${botData.banner}.png?size=600`
          : null,
      }
    });
  } catch (err) {
    console.error("[CUSTOMIZATION PROFILE]", err);
    return res.status(500).json({ error: err.message || "Erro ao atualizar perfil" });
  }
});

/**
 * Helper: Busca perfil do bot no Discord
 */
async function fetchBotProfile(token) {
  if (!token) return null;
  
  try {
    const response = await fetch("https://discord.com/api/v10/users/@me", {
      headers: { Authorization: `Bot ${token}` },
    });

    if (!response.ok) return null;

    const data = await response.json();
    
    return {
      username: data.username,
      discriminator: data.discriminator,
      avatar: data.avatar 
        ? `https://cdn.discordapp.com/avatars/${data.id}/${data.avatar}.png?size=256`
        : null,
      banner: data.banner
        ? `https://cdn.discordapp.com/banners/${data.id}/${data.banner}.png?size=600`
        : null,
    };
  } catch (err) {
    return null;
  }
}

export default router;

/**
 * src/routes/admin/discord-config.js
 * Gerencia configurações do Discord armazenadas no MongoDB (GlobalConfig)
 * em vez de depender apenas de variáveis de ambiente.
 */
import { Router } from "express";
import GlobalConfig from "../../../database/models/GlobalConfig.js";
import AuditLog from "../../../database/models/AuditLog.js";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";

const router = Router();

// Todas as rotas deste router exigem token válido + flag admin
router.use(authMiddleware, requireAdmin);

// ─── Chaves gerenciadas ────────────────────────────────────────────────────────

const DISCORD_CONFIG_KEYS = [
  "discord_guild_id",
  "discord_bot_token",
  "discord_counter_channel_id",
  "discord_feedback_channel_id",
  "discord_sales_channel_id",
  "discord_default_role_id",
];

// Quais campos são sensíveis (mascarados no GET)
const SENSITIVE_KEYS = ["discord_bot_token"];

function maskSensitive(key, value) {
  if (!value || typeof value !== "string") return value;
  if (SENSITIVE_KEYS.includes(key)) {
    if (value.length <= 8) return "***";
    return value.slice(0, 6) + "..." + value.slice(-4);
  }
  return value;
}

// ─── GET /api/admin/discord-config ────────────────────────────────────────────

router.get("/", async (req, res) => {
  try {
    const docs = await GlobalConfig.find({
      key: { $in: DISCORD_CONFIG_KEYS },
    }).lean();

    const config = {};
    for (const key of DISCORD_CONFIG_KEYS) {
      const doc = docs.find((d) => d.key === key);
      config[key] = {
        value: doc ? maskSensitive(key, String(doc.value ?? "")) : "",
        updatedAt: doc?.updatedAt ?? null,
        updatedBy: doc?.updatedBy ?? null,
        fromEnv: Boolean(
          !doc &&
            process.env[key.toUpperCase().replace("discord_", "DISCORD_")]
        ),
      };
    }

    return res.json({ success: true, config });
  } catch (err) {
    console.error("[DISCORD CONFIG GET]", err);
    return res.status(500).json({ success: false, error: "Erro interno" });
  }
});

// ─── PUT /api/admin/discord-config ────────────────────────────────────────────

router.put("/", async (req, res) => {
  try {
    const actorId = String(req.user._id);
    const updates = req.body;

    if (!updates || typeof updates !== "object" || Array.isArray(updates)) {
      return res.status(400).json({ success: false, error: "Body inválido" });
    }

    const allowedKeys = Object.keys(updates).filter((k) =>
      DISCORD_CONFIG_KEYS.includes(k)
    );

    if (allowedKeys.length === 0) {
      return res
        .status(400)
        .json({ success: false, error: "Nenhuma chave válida fornecida" });
    }

    const results = {};

    for (const key of allowedKeys) {
      const value = updates[key];
      const finalValue =
        value === null || value === undefined ? "" : String(value).trim();

      const doc = await GlobalConfig.findOneAndUpdate(
        { key },
        {
          $set: {
            value: finalValue,
            updatedBy: actorId,
          },
        },
        { new: true, upsert: true }
      );

      results[key] = {
        value: maskSensitive(key, finalValue),
        updatedAt: doc.updatedAt,
      };
    }

    // Audit log
    await AuditLog.create({
      entity: "discord_config",
      action: "update",
      actorId,
      targetId: allowedKeys.join(","),
      metadata: {
        keys: allowedKeys,
        values: Object.fromEntries(
          allowedKeys.map((k) => [
            k,
            SENSITIVE_KEYS.includes(k) ? "***" : updates[k],
          ])
        ),
      },
    }).catch((e) => console.warn("[DISCORD CONFIG AUDIT]", e));

    await invalidateServiceCaches(allowedKeys);

    return res.json({ success: true, results });
  } catch (err) {
    console.error("[DISCORD CONFIG PUT]", err);
    return res.status(500).json({ success: false, error: "Erro interno" });
  }
});

// ─── POST /api/admin/discord-config/test ──────────────────────────────────────
// Testa conexão com o Discord usando as configurações salvas

router.post("/test", async (req, res) => {
  try {
    const token = await getDiscordConfig("discord_bot_token");
    const guildId = await getDiscordConfig("discord_guild_id");

    if (!token) {
      return res
        .status(400)
        .json({ success: false, error: "Token do bot não configurado" });
    }

    // ── Valida o bot token (/users/@me) ──────────────────────────────────────
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    let botResp;
    try {
      botResp = await fetch("https://discord.com/api/v10/users/@me", {
        method: "GET",
        headers: {
          Authorization: `Bot ${token}`,
          "Content-Type": "application/json",
        },
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeout);
    }

    if (!botResp.ok) {
      const body = await botResp.json().catch(() => ({}));
      return res.status(200).json({
        success: false,
        error: `Token inválido — Discord retornou ${botResp.status}`,
        discord_error: body,
      });
    }

    const botUser = await botResp.json();

    // ── Valida a guild (se configurada) ──────────────────────────────────────
    let guildInfo = null;
    if (guildId) {
      const guildController = new AbortController();
      const guildTimeout = setTimeout(() => guildController.abort(), 8000);

      let gr;
      try {
        gr = await fetch(
          `https://discord.com/api/v10/guilds/${guildId}?with_counts=true`,
          {
            method: "GET",
            headers: {
              Authorization: `Bot ${token}`,
              "Content-Type": "application/json",
            },
            signal: guildController.signal,
          }
        );
      } finally {
        clearTimeout(guildTimeout);
      }

      if (gr.ok) {
        const g = await gr.json();
        guildInfo = {
          id: g.id,
          name: g.name,
          memberCount: g.approximate_member_count,
        };
      } else {
        const guildErr = await gr.json().catch(() => ({}));
        guildInfo = {
          error: `Guild inacessível — Discord retornou ${gr.status}`,
          discord_error: guildErr,
        };
      }
    }

    return res.json({
      success: true,
      bot: {
        id: botUser.id,
        username: botUser.username,
        avatar: botUser.avatar
          ? `https://cdn.discordapp.com/avatars/${botUser.id}/${botUser.avatar}.png?size=128`
          : null,
      },
      guild: guildInfo,
    });
  } catch (err) {
    // AbortError = timeout
    if (err.name === "AbortError") {
      return res
        .status(504)
        .json({ success: false, error: "Timeout ao conectar com o Discord" });
    }
    console.error("[DISCORD CONFIG TEST]", err);
    return res
      .status(500)
      .json({ success: false, error: err.message || "Erro ao testar conexão" });
  }
});

// ─── Helpers públicos ──────────────────────────────────────────────────────────

/**
 * Busca valor de uma chave de config, com fallback para env.
 * Exportado para uso em outros serviços.
 */
export async function getDiscordConfig(key) {
  try {
    const doc = await GlobalConfig.findOne({ key }).lean();
    if (doc?.value && String(doc.value).trim()) {
      return String(doc.value).trim();
    }
  } catch {
    // silencioso — cai para env
  }

  const envKey = key.toUpperCase();
  return process.env[envKey] || null;
}

async function invalidateServiceCaches(keys) {
  if (
    keys.includes("discord_bot_token") ||
    keys.includes("discord_feedback_channel_id")
  ) {
    try {
      const { invalidateFeedbackCache } = await import(
        "../../../services/discord/feedbacks.js"
      );
      invalidateFeedbackCache();
    } catch {}
  }

  if (
    keys.includes("discord_counter_channel_id") ||
    keys.includes("discord_bot_token") ||
    keys.includes("discord_guild_id")
  ) {
    try {
      const { invalidateCounterCache } = await import(
        "../../../services/discord/botCounter.js"
      );
      if (typeof invalidateCounterCache === "function") invalidateCounterCache();
    } catch {}
  }
}

export default router;
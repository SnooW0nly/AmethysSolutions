/**
 * Rotas do Monitor de Usuários — banco MongoDB separado.
 *
 * Variáveis de ambiente obrigatórias (.env):
 *   MONITOR_MONGO_URL  — connection string do MongoDB do monitor
 *   MONITOR_DB_NAME    — nome do banco (default: amethys_monitor)
 *
 * GET  /api/admin/monitor/users
 *   q, page, limit, sort (last_seen|total_messages|first_seen|total_voice), order (asc|desc)
 *
 * GET  /api/admin/monitor/users/:discordId
 *   Perfil completo do usuário.
 *
 * GET  /api/admin/monitor/stats
 *   Totais gerais (usuários, mensagens, eventos de voz).
 */

import { Router } from "express";
import { MongoClient } from "mongodb";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";

const router = Router();
router.use(authMiddleware, requireAdmin);

// ── Conexão lazy com o MongoDB do monitor ────────────────────────────────────

let _client = null;
let _col = null;

async function getMonitorCollection() {
  if (_col) return _col;

  const mongoURL = process.env.MONITOR_MONGO_URL;
  const dbName   = process.env.MONITOR_DB_NAME || "amethys_monitor";

  if (!mongoURL) {
    throw new Error(
      "MONITOR_MONGO_URL não definido no .env"
    );
  }

  _client = new MongoClient(mongoURL, {
    serverSelectionTimeoutMS: 5_000,
    connectTimeoutMS: 5_000,
    socketTimeoutMS: 10_000,
    maxPoolSize: 5,
  });

  await _client.connect();
  _col = _client.db(dbName).collection("users");
  console.log("[Monitor Route] Conectado →", dbName);
  return _col;
}

// ── Lista / busca usuários ────────────────────────────────────────────────────

router.get("/users", async (req, res) => {
  try {
    const col = await getMonitorCollection();

    const {
      q = "",
      page = "1",
      limit = "20",
      sort = "last_seen",
      order = "desc",
    } = req.query;

    const pageNum = Math.max(parseInt(page) || 1, 1);
    const limitNum = Math.min(Math.max(parseInt(limit) || 20, 1), 100);
    const skip = (pageNum - 1) * limitNum;
    const sortDir = order === "asc" ? 1 : -1;

    // Campos válidos de ordenação
    const sortFieldMap = {
      last_seen: "meta.last_seen",
      first_seen: "meta.first_seen",
      total_messages: "meta.total_messages",
      total_voice: "meta.total_voice_events",
    };
    const sortField = sortFieldMap[sort] || "meta.last_seen";

    // Filtro de busca
    let filter = {};
    if (q.trim()) {
      const regex = new RegExp(q.trim(), "i");
      filter = {
        $or: [
          { _id: q.trim() }, // Discord ID exato
          { "profile.current_username": regex },
          { "profile.current_display_name": regex },
          // Busca também no histórico de usernames
          { "history.usernames.value": regex },
        ],
      };
    }

    const [users, total] = await Promise.all([
      col
        .find(filter, {
          projection: {
            _id: 1,
            "profile.current_username": 1,
            "profile.current_display_name": 1,
            "profile.current_avatar_url": 1,
            "meta.first_seen": 1,
            "meta.last_seen": 1,
            "meta.total_messages": 1,
            "meta.total_voice_events": 1,
            "meta.seen_by_bots": 1,
            "activity.guilds_seen": 1,
            // Não retorna arrays pesados na listagem
          },
        })
        .sort({ [sortField]: sortDir })
        .skip(skip)
        .limit(limitNum)
        .toArray(),
      col.countDocuments(filter),
    ]);

    return res.json({
      success: true,
      users,
      total,
      page: pageNum,
      limit: limitNum,
      pages: Math.ceil(total / limitNum),
    });
  } catch (err) {
    console.error("[Monitor Route] Erro ao buscar usuários:", err.message);
    return res.status(500).json({
      success: false,
      error: err.message || "Erro ao conectar ao banco de dados do monitor",
    });
  }
});

// ── Perfil completo de um usuário ─────────────────────────────────────────────

router.get("/users/:discordId", async (req, res) => {
  try {
    const col = await getMonitorCollection();
    const { discordId } = req.params;

    const user = await col.findOne({ _id: discordId });

    if (!user) {
      return res.status(404).json({ success: false, error: "Usuário não encontrado" });
    }

    // Remove campos internos de deduplicação
    delete user._recent_hashes;

    return res.json({ success: true, user });
  } catch (err) {
    console.error("[Monitor Route] Erro ao buscar usuário:", err.message);
    return res.status(500).json({
      success: false,
      error: err.message || "Erro ao conectar ao banco de dados do monitor",
    });
  }
});

// ── Stats gerais do monitor ───────────────────────────────────────────────────

router.get("/stats", async (req, res) => {
  try {
    const col = await getMonitorCollection();

    const [totalUsers, stats] = await Promise.all([
      col.countDocuments(),
      col
        .aggregate([
          {
            $group: {
              _id: null,
              totalMessages: { $sum: "$meta.total_messages" },
              totalVoiceEvents: { $sum: "$meta.total_voice_events" },
              lastSeen: { $max: "$meta.last_seen" },
            },
          },
        ])
        .toArray(),
    ]);

    const s = stats[0] || {};

    return res.json({
      success: true,
      stats: {
        totalUsers,
        totalMessages: s.totalMessages || 0,
        totalVoiceEvents: s.totalVoiceEvents || 0,
        lastActivity: s.lastSeen || null,
      },
    });
  } catch (err) {
    console.error("[Monitor Route] Erro ao buscar stats:", err.message);
    return res.status(500).json({
      success: false,
      error: err.message || "Erro ao conectar ao banco de dados do monitor",
    });
  }
});

export default router;
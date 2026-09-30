import Gift from "../../../database/models/Gift.js";

/**
 * GET /admin/gifts/stats
 * Retorna estatísticas detalhadas sobre os gifts
 */
export default async function getGiftStats(req, res) {
  try {
    const now = new Date();

    // Estatísticas gerais
    const [generalStats, planStats, recentActivity] = await Promise.all([
      // Estatísticas gerais
      Gift.aggregate([
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            used: { $sum: { $cond: ["$isUsed", 1, 0] } },
            available: { $sum: { $cond: ["$isUsed", 0, 1] } },
            expired: {
              $sum: {
                $cond: [
                  {
                    $and: [
                      { $ne: ["$expiresAt", null] },
                      { $lt: ["$expiresAt", now] },
                      { $eq: ["$isUsed", false] },
                    ],
                  },
                  1,
                  0,
                ],
              },
            },
          },
        },
      ]),

      // Estatísticas por plano
      Gift.aggregate([
        {
          $group: {
            _id: "$planId",
            planName: { $first: "$planName" },
            total: { $sum: 1 },
            used: { $sum: { $cond: ["$isUsed", 1, 0] } },
            available: { $sum: { $cond: ["$isUsed", 0, 1] } },
          },
        },
        { $sort: { total: -1 } },
      ]),

      // Atividade recente (últimos 30 dias)
      Gift.aggregate([
        {
          $match: {
            isUsed: true,
            usedAt: { $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) },
          },
        },
        {
          $group: {
            _id: {
              $dateToString: { format: "%Y-%m-%d", date: "$usedAt" },
            },
            count: { $sum: 1 },
          },
        },
        { $sort: { _id: 1 } },
        { $limit: 30 },
      ]),
    ]);

    // Lotes mais recentes
    const recentBatches = await Gift.aggregate([
      {
        $match: {
          batchId: { $ne: null },
        },
      },
      {
        $group: {
          _id: "$batchId",
          planName: { $first: "$planName" },
          total: { $sum: 1 },
          used: { $sum: { $cond: ["$isUsed", 1, 0] } },
          createdAt: { $first: "$createdAt" },
        },
      },
      { $sort: { createdAt: -1 } },
      { $limit: 10 },
    ]);

    return res.status(200).json({
      success: true,
      data: {
        general: generalStats[0] || { total: 0, used: 0, available: 0, expired: 0 },
        byPlan: planStats,
        recentActivity,
        recentBatches,
      },
    });
  } catch (error) {
    console.error("[ADMIN GIFTS STATS ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao obter estatísticas",
      error: error.message,
    });
  }
}

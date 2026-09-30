import Gift from "../../../database/models/Gift.js";

/**
 * GET /admin/gifts/list
 * Lista todos os gifts com filtros e paginação
 */
export default async function listGifts(req, res) {
  try {
    const {
      page = 1,
      limit = 50,
      planId,
      isUsed,
      batchId,
      search,
      sortBy = "createdAt",
      sortOrder = "desc",
    } = req.query;

    // Constrói filtros
    const filters = {};

    if (planId) {
      filters.planId = planId;
    }

    if (isUsed !== undefined) {
      filters.isUsed = isUsed === "true";
    }

    if (batchId) {
      filters.batchId = batchId;
    }

    if (search) {
      filters.$or = [
        { code: { $regex: search, $options: "i" } },
        { description: { $regex: search, $options: "i" } },
        { planName: { $regex: search, $options: "i" } },
      ];
    }

    // Configuração de paginação
    const skip = (parseInt(page) - 1) * parseInt(limit);
    const sortOptions = { [sortBy]: sortOrder === "asc" ? 1 : -1 };

    // Busca gifts
    const [gifts, total] = await Promise.all([
      Gift.find(filters)
        .sort(sortOptions)
        .skip(skip)
        .limit(parseInt(limit))
        .populate("usedBy", "username globalName discordId")
        .populate("createdBy", "username globalName discordId")
        .lean(),
      Gift.countDocuments(filters),
    ]);

    // Estatísticas
    const stats = await Gift.aggregate([
      { $match: filters },
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
                    { $lt: ["$expiresAt", new Date()] },
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
    ]);

    return res.status(200).json({
      success: true,
      data: {
        gifts,
        pagination: {
          page: parseInt(page),
          limit: parseInt(limit),
          total,
          pages: Math.ceil(total / parseInt(limit)),
        },
        stats: stats[0] || { total: 0, used: 0, available: 0, expired: 0 },
      },
    });
  } catch (error) {
    console.error("[ADMIN GIFTS LIST ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao listar gifts",
      error: error.message,
    });
  }
}

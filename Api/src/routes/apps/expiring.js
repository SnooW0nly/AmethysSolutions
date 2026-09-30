import Application from "../../database/models/Application.js";

/**
 * GET /apps/expiring
 * Retorna aplicações do usuário que estão próximas do vencimento (7 dias)
 */
export default async function getExpiringApps(req, res) {
  try {
    const userId = req.user._id;
    const now = new Date();
    const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

    const expiringApps = await Application.find({
      userId,
      expiresAt: {
        $gte: now,
        $lte: sevenDaysFromNow,
      },
    })
      .select("name plan expiresAt _id")
      .lean();

    // Calcula dias restantes para cada aplicação
    const appsWithDaysLeft = expiringApps.map((app) => {
      const daysLeft = Math.ceil((new Date(app.expiresAt) - now) / (1000 * 60 * 60 * 24));
      return {
        ...app,
        daysLeft,
      };
    });

    return res.status(200).json({
      success: true,
      data: appsWithDaysLeft,
    });
  } catch (error) {
    console.error("[GET EXPIRING APPS ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao buscar aplicações expirando",
      error: error.message,
    });
  }
}

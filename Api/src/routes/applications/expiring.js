import Application from "../../database/models/Application.js";

/**
 * GET /applications/expiring
 * Lista aplicações do usuário que estão próximas do vencimento (7 dias ou menos)
 */
export default async function getExpiringApplications(req, res) {
  try {
    if (!req.user || !req.user._id) {
      console.error("[GET EXPIRING APPS] req.user não definido:", req.user);
      return res.status(401).json({
        success: false,
        message: "Usuário não autenticado",
      });
    }

    const userId = req.user._id;

    const now = new Date();
    const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

    console.log("[GET EXPIRING APPS] Buscando apps expirando para user:", userId);

    // Busca aplicações que vão vencer nos próximos 7 dias
    const expiringApps = await Application.find({
      userId,
      isDeleted: { $ne: true },
      isBlocked: { $ne: true },
      expiresAt: {
        $gte: now,
        $lte: sevenDaysFromNow,
      },
    })
      .sort({ expiresAt: 1 }) // Ordena por data de vencimento (mais próximo primeiro)
      .lean();

    console.log("[GET EXPIRING APPS] Encontradas", expiringApps.length, "aplicações expirando");

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

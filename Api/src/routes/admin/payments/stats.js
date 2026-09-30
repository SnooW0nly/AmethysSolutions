import express from "express";
import Payment from "../../../database/models/Payment.js";
import Application from "../../../database/models/Application.js";

const router = express.Router();

/**
 * GET /admin/payments/stats
 * Retorna estatísticas de pagamentos e vendas
 */
router.get("/", async (req, res) => {
  try {
    const { period = "all" } = req.query;

    // Define o filtro de data baseado no período
    let dateFilter = {};
    const now = new Date();

    switch (period) {
      case "today":
        dateFilter = {
          createdAt: {
            $gte: new Date(now.setHours(0, 0, 0, 0)),
          },
        };
        break;
      case "week":
        const weekAgo = new Date(now.setDate(now.getDate() - 7));
        dateFilter = {
          createdAt: { $gte: weekAgo },
        };
        break;
      case "month":
        const monthAgo = new Date(now.setMonth(now.getMonth() - 1));
        dateFilter = {
          createdAt: { $gte: monthAgo },
        };
        break;
      case "year":
        const yearAgo = new Date(now.setFullYear(now.getFullYear() - 1));
        dateFilter = {
          createdAt: { $gte: yearAgo },
        };
        break;
      default:
        // "all" - sem filtro de data
        break;
    }

    // Busca pagamentos aprovados
    const payments = await Payment.find({
      status: "approved",
      ...dateFilter,
    }).lean();

    // Calcula estatísticas
    const totalRevenue = payments.reduce((sum, payment) => sum + (payment.priceFinal || 0), 0);
    const totalPayments = payments.length;

    // Busca total de bots criados (applications) no período
    const totalBots = await Application.countDocuments({
      isDeleted: { $ne: true },
      ...dateFilter,
    });

    // Ticket médio
    const averageTicket = totalPayments > 0 ? totalRevenue / totalPayments : 0;

    // Agrupa por método de pagamento
    const paymentsByMethod = payments.reduce((acc, payment) => {
      const method = payment.method || "pix";
      if (!acc[method]) {
        acc[method] = { count: 0, revenue: 0 };
      }
      acc[method].count++;
      acc[method].revenue += payment.priceFinal || 0;
      return acc;
    }, {});

    // Agrupa por plano
    const paymentsByPlan = payments.reduce((acc, payment) => {
      const planName = payment.plan?.name || "Sem plano";
      if (!acc[planName]) {
        acc[planName] = { count: 0, revenue: 0 };
      }
      acc[planName].count++;
      acc[planName].revenue += payment.priceFinal || 0;
      return acc;
    }, {});

    // Receita por dia (últimos 30 dias)
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const revenueByDay = await Payment.aggregate([
      {
        $match: {
          status: "approved",
          createdAt: { $gte: thirtyDaysAgo },
        },
      },
      {
        $group: {
          _id: {
            $dateToString: { format: "%Y-%m-%d", date: "$createdAt" },
          },
          revenue: { $sum: "$priceFinal" },
          count: { $sum: 1 },
        },
      },
      {
        $sort: { _id: 1 },
      },
    ]);

    return res.status(200).json({
      success: true,
      data: {
        summary: {
          totalRevenue: totalRevenue.toFixed(2),
          totalPayments,
          totalBots,
          averageTicket: averageTicket.toFixed(2),
        },
        byMethod: paymentsByMethod,
        byPlan: paymentsByPlan,
        revenueByDay,
        period,
      },
    });
  } catch (error) {
    console.error("[ADMIN PAYMENTS STATS] Erro:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao buscar estatísticas",
      error: error.message,
    });
  }
});

export default router;

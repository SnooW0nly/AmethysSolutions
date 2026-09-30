import Payment from "../../database/models/Payment.js";

/**
 * GET /invoices/list
 * Lista todas as faturas (pagamentos) do usuário
 */
export default async function listInvoices(req, res) {
  try {
    const userId = req.user._id;
    const { status, page = 1, limit = 20 } = req.query;

    // Constrói filtros
    const filters = { userId };
    if (status) {
      filters.status = status;
    }

    // Paginação
    const skip = (parseInt(page) - 1) * parseInt(limit);

    // Busca pagamentos
    const [payments, total] = await Promise.all([
      Payment.find(filters)
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(parseInt(limit))
        .lean(),
      Payment.countDocuments(filters),
    ]);

    return res.status(200).json({
      success: true,
      data: {
        payments,
        pagination: {
          page: parseInt(page),
          limit: parseInt(limit),
          total,
          pages: Math.ceil(total / parseInt(limit)),
        },
      },
    });
  } catch (error) {
    console.error("[LIST INVOICES ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao listar faturas",
      error: error.message,
    });
  }
}

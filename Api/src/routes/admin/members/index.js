/**
 * src/routes/admin/members/index.js
 *
 * Painel admin completo para gerenciar:
 *  - Cookie da RevisionSMM (adicionar, atualizar, validar)
 *  - CPF de pagamento
 *  - Serviços cadastrados (preços, IDs)
 *  - Pedidos de membros (listar, ver detalhes, forçar reprocessamento, notas)
 */

import { Router } from "express";
import authMiddleware from "../../../middlewares/authMiddleware.js";
import requireAdmin from "../../../middlewares/requireAdmin.js";
import RevisionConfig from "../../../database/models/RevisionConfig.js";
import MemberOrder from "../../../database/models/MemberOrder.js";
import {
  validateCookie,
  getBalance,
  listServices,
  checkOrderStatus,
  addFunds,
  placeOrder,
} from "../../../services/revision/index.js";

const router = Router();
router.use(authMiddleware, requireAdmin);

// ─────────────────────────────────────────────────────────────────────────────
// SEÇÃO 1: Configurações da conta RevisionSMM
// ─────────────────────────────────────────────────────────────────────────────

/**
 * GET /api/admin/members/config
 * Retorna todas as configs (cookie mascarado, CPF mascarado, etc)
 */
router.get("/config", async (req, res) => {
  try {
    const docs = await RevisionConfig.find().lean();

    const config = {};
    for (const doc of docs) {
      config[doc.key] = {
        value:
          doc.key === "revision_cookie"
            ? maskCookie(doc.value)
            : doc.key === "revision_cpf"
            ? maskCpf(doc.value)
            : doc.value,
        rawLength: doc.value?.length || 0,
        label: doc.label,
        updatedAt: doc.updatedAt,
      };
    }

    return res.json({ success: true, config });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * PUT /api/admin/members/config
 * Atualiza uma ou mais configs
 * Body: { revision_cookie: "...", revision_cpf: "..." }
 */
router.put("/config", async (req, res) => {
  try {
    const actorId = String(req.user._id);
    const allowed = ["revision_cookie", "revision_cpf"];
    const labels = {
      revision_cookie: "Cookie da RevisionSMM",
      revision_cpf: "CPF para pagamentos PIX",
    };

    const keys = Object.keys(req.body).filter((k) => allowed.includes(k));
    if (!keys.length) {
      return res.status(400).json({ success: false, error: "Nenhuma chave válida fornecida" });
    }

    const results = {};
    for (const key of keys) {
      const value = String(req.body[key] || "").trim();
      await RevisionConfig.findOneAndUpdate(
        { key },
        { $set: { value, label: labels[key], updatedBy: actorId } },
        { upsert: true, new: true }
      );
      results[key] = { updated: true, rawLength: value.length };
    }

    return res.json({ success: true, results });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * POST /api/admin/members/config/validate
 * Valida o cookie atual tentando acessar o RevisionSMM
 */
router.post("/config/validate", async (req, res) => {
  try {
    const result = await validateCookie();
    return res.json({ success: true, ...result });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * GET /api/admin/members/config/balance
 * Retorna o saldo atual da conta RevisionSMM
 */
router.get("/config/balance", async (req, res) => {
  try {
    const result = await getBalance();
    return res.json({ success: true, ...result });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * GET /api/admin/members/config/services
 * Lista os serviços disponíveis na RevisionSMM
 */
router.get("/config/services", async (req, res) => {
  try {
    const result = await listServices();
    return res.json({ success: true, ...result });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// SEÇÃO 2: Serviços cadastrados (para o frontend de pedidos)
// Permite ao admin cadastrar os serviços com preço, ID Revision, min/max qty
// ─────────────────────────────────────────────────────────────────────────────

/**
 * GET /api/admin/members/services
 * Lista serviços cadastrados no banco (que aparecem pro usuário)
 */
router.get("/services", async (req, res) => {
  try {
    const doc = await RevisionConfig.findOne({ key: "revision_services" }).lean();
    const services = doc?.value ? JSON.parse(doc.value) : [];
    return res.json({ success: true, services });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * PUT /api/admin/members/services
 * Salva/substitui lista de serviços
 * Body: { services: [ { id, name, minQty, maxQty, pricePerUnit, category } ] }
 *
 * pricePerUnit = preço por membro em R$ (ex: 0.013 para 1000 membros = R$13)
 */
router.put("/services", async (req, res) => {
  try {
    const actorId = String(req.user._id);
    const { services } = req.body;

    if (!Array.isArray(services)) {
      return res.status(400).json({ success: false, error: "services deve ser um array" });
    }

    // Valida campos obrigatórios de cada serviço
    for (const s of services) {
      if (!s.id || !s.name || s.pricePerUnit == null || !s.minQty || !s.maxQty) {
        return res.status(400).json({
          success: false,
          error: `Serviço inválido: ${JSON.stringify(s)}. Campos obrigatórios: id, name, pricePerUnit, minQty, maxQty`,
        });
      }
    }

    await RevisionConfig.findOneAndUpdate(
      { key: "revision_services" },
      {
        $set: {
          value: JSON.stringify(services),
          label: "Serviços de membros",
          updatedBy: actorId,
        },
      },
      { upsert: true }
    );

    return res.json({ success: true, count: services.length });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// SEÇÃO 3: Pedidos (gerenciamento admin)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * GET /api/admin/members/orders
 * Lista todos os pedidos com paginação e filtros
 * Query: ?page=1&limit=20&status=&userId=
 */
router.get("/orders", async (req, res) => {
  try {
    const page = Math.max(1, Number(req.query.page) || 1);
    const limit = Math.min(100, Number(req.query.limit) || 20);
    const skip = (page - 1) * limit;

    const query = {};
    if (req.query.status) query.status = req.query.status;
    if (req.query.userId) query.userId = req.query.userId;
    if (req.query.misticId) query["payment.misticId"] = req.query.misticId;

    const [orders, total] = await Promise.all([
      MemberOrder.find(query)
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(limit)
        .populate("userId", "username email discordId")
        .lean(),
      MemberOrder.countDocuments(query),
    ]);

    return res.json({
      success: true,
      orders,
      total,
      page,
      pages: Math.ceil(total / limit),
    });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * GET /api/admin/members/orders/:id
 * Detalhes completos de um pedido
 */
router.get("/orders/:id", async (req, res) => {
  try {
    const order = await MemberOrder.findById(req.params.id)
      .populate("userId", "username email discordId")
      .lean();
    if (!order) return res.status(404).json({ success: false, error: "Pedido não encontrado" });
    return res.json({ success: true, order });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * PATCH /api/admin/members/orders/:id
 * Atualiza campos editáveis pelo admin (notes, status manual, etc.)
 */
router.patch("/orders/:id", async (req, res) => {
  try {
    const allowed = ["notes", "status", "failReason"];
    const update = {};
    for (const k of allowed) {
      if (req.body[k] !== undefined) update[k] = req.body[k];
    }

    const order = await MemberOrder.findByIdAndUpdate(
      req.params.id,
      { $set: update },
      { new: true }
    );
    if (!order) return res.status(404).json({ success: false, error: "Pedido não encontrado" });
    return res.json({ success: true, order });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * POST /api/admin/members/orders/:id/check-revision
 * Verifica status do pedido diretamente na RevisionSMM
 */
router.post("/orders/:id/check-revision", async (req, res) => {
  try {
    const order = await MemberOrder.findById(req.params.id);
    if (!order) return res.status(404).json({ success: false, error: "Pedido não encontrado" });
    if (!order.revision.orderId) {
      return res.status(400).json({ success: false, error: "Pedido ainda não foi enviado para a RevisionSMM" });
    }

    const result = await checkOrderStatus(order.revision.orderId);

    if (result.success) {
      order.revision.orderStatus = result.data?.status || order.revision.orderStatus;
      order.revision.lastCheckedAt = new Date();

      // Atualiza status geral se Revision reportar completo
      if (result.data?.status === "Completed" || result.data?.status === "Partial") {
        order.status = "completed";
      } else if (result.data?.status === "Canceled") {
        order.status = "failed";
        order.failReason = "Pedido cancelado pela RevisionSMM";
      }

      await order.save();
    }

    return res.json({ success: true, revisionData: result.data, order });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * POST /api/admin/members/orders/:id/retry
 * Tenta reprocessar um pedido que falhou (add funds + order)
 */
router.post("/orders/:id/retry", async (req, res) => {
  try {
    const order = await MemberOrder.findById(req.params.id);
    if (!order) return res.status(404).json({ success: false, error: "Pedido não encontrado" });

    if (!["failed", "payment_confirmed", "adding_funds", "ordering"].includes(order.status)) {
      return res.status(400).json({
        success: false,
        error: `Não é possível retentar um pedido com status "${order.status}"`,
      });
    }

    if (order.payment.status !== "approved") {
      return res.status(400).json({ success: false, error: "Pagamento ainda não foi confirmado" });
    }

    // Reprocessa a partir de onde parou
    await processApprovedOrder(order);

    return res.json({ success: true, order: await MemberOrder.findById(order._id).lean() });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * GET /api/admin/members/stats
 * Estatísticas gerais de pedidos
 */
router.get("/stats", async (req, res) => {
  try {
    const [statusCounts, totalRevenue, recentOrders] = await Promise.all([
      MemberOrder.aggregate([
        { $group: { _id: "$status", count: { $sum: 1 } } },
      ]),
      MemberOrder.aggregate([
        { $match: { "payment.status": "approved" } },
        { $group: { _id: null, total: { $sum: "$totalCharged" }, fees: { $sum: "$ourFee" } } },
      ]),
      MemberOrder.countDocuments({
        createdAt: { $gte: new Date(Date.now() - 24 * 60 * 60 * 1000) },
      }),
    ]);

    const counts = {};
    for (const s of statusCounts) counts[s._id] = s.count;

    return res.json({
      success: true,
      stats: {
        byStatus: counts,
        totalRevenue: totalRevenue[0]?.total || 0,
        totalOurFees: totalRevenue[0]?.fees || 0,
        ordersLast24h: recentOrders,
      },
    });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function maskCookie(cookie) {
  if (!cookie || cookie.length < 20) return "***";
  return cookie.slice(0, 12) + "..." + cookie.slice(-8);
}

function maskCpf(cpf) {
  if (!cpf) return "";
  return cpf.replace(/(\d{3})\.\d{3}\.\d{3}-(\d{2})/, "$1.***.***-$2");
}

// Exporta para reuso no webhook de pagamento
export async function processApprovedOrder(order) {
  try {
    // 1. Adicionar saldo na Revision (valor do serviço, sem as taxas)
    if (order.revision.addFundsStatus !== "success") {
      order.status = "adding_funds";
      await order.save();

      const fundsResult = await addFunds(order.servicePrice);
      if (!fundsResult.success) {
        order.revision.addFundsStatus = "failed";
        order.status = "failed";
        order.failReason = `Falha ao adicionar saldo: ${JSON.stringify(fundsResult.data)}`;
        await order.save();
        return;
      }

      order.revision.addFundsStatus = "success";
      order.revision.addFundsAt = new Date();
      await order.save();
    }

    // 2. Fazer o pedido na Revision
    order.status = "ordering";
    await order.save();

    const orderResult = await placeOrder({
      serviceId: order.serviceId,
      link: order.serverLink,
      quantity: order.quantity,
    });

    if (!orderResult.success) {
      order.status = "failed";
      order.failReason = `Falha ao criar pedido: ${orderResult.error}`;
      await order.save();
      return;
    }

    order.revision.orderId = orderResult.orderId;
    order.revision.orderStatus = "Pending";
    order.revision.orderPlacedAt = new Date();
    order.status = "in_progress";
    await order.save();
  } catch (err) {
    order.status = "failed";
    order.failReason = `Erro interno: ${err.message}`;
    await order.save();
  }
}

export default router;
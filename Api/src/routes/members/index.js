/**
 * src/routes/members/index.js
 *
 * Rotas públicas (autenticadas com usuário logado) para o fluxo de pedido de membros:
 *
 *  GET  /members/services         → lista serviços disponíveis com preços calculados
 *  POST /members/orders           → cria pedido + gera PIX Mistic
 *  GET  /members/orders           → histórico de pedidos do usuário
 *  GET  /members/orders/:id       → detalhes de um pedido
 *  POST /members/orders/:id/verify-bot  → verifica se bot está no servidor
 *  GET  /members/orders/:id/status     → status do pedido (polling frontend)
 *  POST /members/webhook/mistic        → webhook de confirmação de pagamento
 */

import { Router } from "express";
import authMiddleware from "../../middlewares/authMiddleware.js";
import RevisionConfig from "../../database/models/RevisionConfig.js";
import MemberOrder from "../../database/models/MemberOrder.js";
import { createPixPayment, checkPixPayment } from "../../services/mistic/index.js";
import { processApprovedOrder } from "../admin/members/index.js";

const router = Router();

const OUR_FEE = 1.50;    // nossa taxa fixa por pedido
const MISTIC_FEE = 0.50; // taxa da Mistic

const REVISION_BOT_INVITE_URL = "https://discord.com/oauth2/authorize?client_id=SEU_CLIENT_ID_AQUI&permissions=8&scope=bot";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

async function getServices() {
  const doc = await RevisionConfig.findOne({ key: "revision_services" }).lean();
  return doc?.value ? JSON.parse(doc.value) : [];
}

/**
 * Calcula o total cobrado do cliente.
 * preço = (pricePerUnit * quantity) + ourFee + misticFee
 */
function calcTotal(pricePerUnit, quantity) {
  const servicePrice = parseFloat((pricePerUnit * quantity).toFixed(2));
  const total = parseFloat((servicePrice + OUR_FEE + MISTIC_FEE).toFixed(2));
  return { servicePrice, total };
}

/**
 * Extrai o Guild ID de um link do Discord.
 * Formatos aceitos:
 *  - discord.gg/invite/CODE
 *  - discord.com/invite/CODE
 *  - discord.gg/CODE
 *  - https://discord.com/channels/GUILD_ID/...
 */
function extractGuildOrInvite(link) {
  // Link direto com guild ID
  const channelMatch = link.match(/discord\.com\/channels\/(\d+)/);
  if (channelMatch) return { type: "guild_id", value: channelMatch[1] };

  // Link de convite
  const inviteMatch = link.match(/discord(?:\.gg|\.com\/invite)\/([a-zA-Z0-9-]+)/);
  if (inviteMatch) return { type: "invite", value: inviteMatch[1] };

  return null;
}



// ─────────────────────────────────────────────────────────────────────────────
// GET /members/services
// Lista serviços com preços já calculados para o frontend exibir
// ─────────────────────────────────────────────────────────────────────────────

router.get("/services", authMiddleware, async (req, res) => {
  try {
    const services = await getServices();

    // Adiciona exemplos de preço calculado
    const enriched = services.map((s) => {
      const exampleQty = s.minQty;
      const { servicePrice, total } = calcTotal(s.pricePerUnit, exampleQty);
      return {
        ...s,
        example: {
          quantity: exampleQty,
          servicePrice,
          ourFee: OUR_FEE,
          misticFee: MISTIC_FEE,
          total,
        },
      };
    });

    return res.json({ success: true, services: enriched, fees: { ourFee: OUR_FEE, misticFee: MISTIC_FEE } });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /members/services/calculate
// Calcula o total para uma combinação serviço + quantidade
// ─────────────────────────────────────────────────────────────────────────────

router.post("/services/calculate", authMiddleware, async (req, res) => {
  try {
    const { serviceId, quantity } = req.body;
    if (!serviceId || !quantity) {
      return res.status(400).json({ success: false, error: "serviceId e quantity são obrigatórios" });
    }

    const services = await getServices();
    const service = services.find((s) => s.id === String(serviceId));
    if (!service) return res.status(404).json({ success: false, error: "Serviço não encontrado" });

    const qty = Number(quantity);
    if (qty < service.minQty || qty > service.maxQty) {
      return res.status(400).json({
        success: false,
        error: `Quantidade deve ser entre ${service.minQty} e ${service.maxQty}`,
      });
    }

    const { servicePrice, total } = calcTotal(service.pricePerUnit, qty);

    return res.json({
      success: true,
      breakdown: {
        service: service.name,
        quantity: qty,
        servicePrice,
        ourFee: OUR_FEE,
        misticFee: MISTIC_FEE,
        total,
      },
    });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /members/orders
// Cria o pedido e gera o PIX Mistic
// ─────────────────────────────────────────────────────────────────────────────

router.post("/orders", authMiddleware, async (req, res) => {
  try {
    const { serviceId, quantity, serverLink } = req.body;
    const userId = req.user._id;

    if (!serviceId || !quantity || !serverLink) {
      return res.status(400).json({ success: false, error: "serviceId, quantity e serverLink são obrigatórios" });
    }

    // 1. Valida serviço
    const services = await getServices();
    const service = services.find((s) => s.id === String(serviceId));
    if (!service) return res.status(404).json({ success: false, error: "Serviço não encontrado" });

    const qty = Number(quantity);
    if (qty < service.minQty || qty > service.maxQty) {
      return res.status(400).json({
        success: false,
        error: `Quantidade deve ser entre ${service.minQty} e ${service.maxQty}`,
      });
    }

    // 2. Extrai guildId do link (a Revision rejeita se o bot não estiver no servidor)
    const parsed = extractGuildOrInvite(serverLink);
    if (!parsed) {
      return res.status(400).json({ success: false, error: "Link de servidor inválido" });
    }

    let guildId = null;
    if (parsed.type === "guild_id") {
      guildId = parsed.value;
    } else {
      try {
        const inviteRes = await fetch(`https://discord.com/api/v10/invites/${parsed.value}`);
        if (!inviteRes.ok) {
          return res.status(400).json({ success: false, error: "Convite inválido ou expirado" });
        }
        const inviteData = await inviteRes.json();
        guildId = inviteData.guild?.id ?? null;
      } catch {
        return res.status(400).json({ success: false, error: "Erro ao resolver convite do Discord" });
      }
    }

    if (!guildId) {
      return res.status(400).json({ success: false, error: "Não foi possível identificar o servidor" });
    }

    // 3. Calcula preços
    const { servicePrice, total } = calcTotal(service.pricePerUnit, qty);

    // 4. Cria pedido no banco (status: awaiting_payment)
    const order = await MemberOrder.create({
      userId,
      serviceId: service.id,
      serviceName: service.name,
      quantity: qty,
      serverLink,
      guildId,
      servicePrice,
      ourFee: OUR_FEE,
      misticFee: MISTIC_FEE,
      totalCharged: total,
      status: "awaiting_payment",
    });

    // 5. Gera PIX via Mistic
    const pixResult = await createPixPayment({
      price: total,
      description: `${qty}x ${service.name} — Pedido #${order._id}`,
      transactionId: `members-${order._id}`,
    });

    const expiresAt = new Date(Date.now() + 30 * 60 * 1000); // 30 min

    // 6. Atualiza pedido com dados do PIX
    order.payment.misticId = pixResult.misticId;
    order.payment.emv = pixResult.emv;
    order.payment.qrCodeBase64 = pixResult.qrBase64;
    order.payment.expiresAt = expiresAt;
    await order.save();

    return res.status(201).json({
      success: true,
      order: {
        _id: order._id,
        status: order.status,
        serviceName: order.serviceName,
        quantity: order.quantity,
        serverLink: order.serverLink,
        breakdown: {
          servicePrice,
          ourFee: OUR_FEE,
          misticFee: MISTIC_FEE,
          total,
        },
      },
      payment: {
        misticId: pixResult.misticId,
        emv: pixResult.emv,
        qrCodeBase64: pixResult.qrBase64,
        expiresAt,
        total,
      },
    });
  } catch (err) {
    console.error("[MEMBERS] Erro ao criar pedido:", err.message);
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /members/orders
// Histórico de pedidos do usuário autenticado
// ─────────────────────────────────────────────────────────────────────────────

router.get("/orders", authMiddleware, async (req, res) => {
  try {
    const page = Math.max(1, Number(req.query.page) || 1);
    const limit = Math.min(50, Number(req.query.limit) || 10);
    const skip = (page - 1) * limit;

    const [orders, total] = await Promise.all([
      MemberOrder.find({ userId: req.user._id })
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(limit)
        .select("-payment.qrCodeBase64") // não retorna o base64 na listagem
        .lean(),
      MemberOrder.countDocuments({ userId: req.user._id }),
    ]);

    return res.json({ success: true, orders, total, page, pages: Math.ceil(total / limit) });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /members/orders/:id
// Detalhes de um pedido específico (só do próprio usuário)
// ─────────────────────────────────────────────────────────────────────────────

router.get("/orders/:id", authMiddleware, async (req, res) => {
  try {
    const order = await MemberOrder.findOne({
      _id: req.params.id,
      userId: req.user._id,
    }).lean();

    if (!order) return res.status(404).json({ success: false, error: "Pedido não encontrado" });

    return res.json({ success: true, order });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /members/orders/:id/status
// Polling de status — frontend chama a cada 5s enquanto awaiting_payment
// Também verifica o status no Mistic se ainda pendente
// ─────────────────────────────────────────────────────────────────────────────

router.get("/orders/:id/status", authMiddleware, async (req, res) => {
  try {
    const order = await MemberOrder.findOne({
      _id: req.params.id,
      userId: req.user._id,
    });

    if (!order) return res.status(404).json({ success: false, error: "Pedido não encontrado" });

    // Se ainda aguardando pagamento, verifica na Mistic
    if (order.status === "awaiting_payment" && order.payment.misticId) {
      // Verifica se expirou
      if (order.payment.expiresAt && new Date() > order.payment.expiresAt) {
        order.payment.status = "expired";
        order.status = "cancelled";
        order.failReason = "PIX expirado sem pagamento";
        await order.save();
      } else {
        try {
          const pixStatus = await checkPixPayment({ payment_id: order.payment.misticId });

          if (pixStatus.status === "approved" && order.payment.status !== "approved") {
            order.payment.status = "approved";
            order.payment.paidAt = new Date();
            order.status = "payment_confirmed";
            await order.save();

            // Dispara processamento em background
            setImmediate(() => processApprovedOrder(order).catch(console.error));
          } else if (pixStatus.status === "cancelled") {
            order.payment.status = "cancelled";
            order.status = "cancelled";
            await order.save();
          }
        } catch {
          // ignora erro de verificação — retorna status atual
        }
      }
    }

    return res.json({
      success: true,
      status: order.status,
      paymentStatus: order.payment.status,
      revisionOrderId: order.revision.orderId,
      revisionOrderStatus: order.revision.orderStatus,
      paidAt: order.payment.paidAt,
      failReason: order.failReason,
    });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /members/webhook/mistic
// Webhook recebido da Mistic quando pagamento é aprovado
// ─────────────────────────────────────────────────────────────────────────────

router.post("/webhook/mistic", async (req, res) => {
  try {
    const { transactionId, status } = req.body;

    if (!transactionId) {
      return res.status(400).json({ error: "transactionId ausente" });
    }

    // Ack imediato pra Mistic não retentar
    res.json({ received: true });

    const mappedStatus = mapMisticStatus(status);
    if (mappedStatus !== "approved") return;

    // Busca o pedido pelo misticId
    const order = await MemberOrder.findOne({ "payment.misticId": transactionId });
    if (!order) {
      console.warn(`[MEMBERS WEBHOOK] Pedido não encontrado para misticId: ${transactionId}`);
      return;
    }

    if (order.payment.status === "approved") return; // já processado

    order.payment.status = "approved";
    order.payment.paidAt = new Date();
    order.status = "payment_confirmed";
    await order.save();

    // Processa em background
    processApprovedOrder(order).catch((err) =>
      console.error("[MEMBERS WEBHOOK] Erro ao processar pedido:", err.message)
    );
  } catch (err) {
    console.error("[MEMBERS WEBHOOK] Erro:", err.message);
  }
});

function mapMisticStatus(s) {
  if (!s) return "pending";
  const u = String(s).toUpperCase();
  if (["COMPLETO", "COMPLETED", "APPROVED", "PAID", "FINISHED"].includes(u)) return "approved";
  if (["FALHA", "FAILED", "CANCELLED", "CANCELED"].includes(u)) return "cancelled";
  return "pending";
}

export default router;
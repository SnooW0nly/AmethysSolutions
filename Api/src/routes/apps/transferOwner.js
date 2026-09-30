import express from "express";
import {
  initiateOwnerTransfer,
  confirmOwnerTransfer,
  cancelOwnerTransfer,
} from "../../services/ownerTransferService.js";

const router = express.Router();

/**
 * POST /apps/:id/transfer-owner/initiate
 * Inicia processo de transferência de posse
 */
router.post("/:id/transfer-owner/initiate", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { id: applicationId } = req.params;
    const { newOwnerDiscordId } = req.body;

    if (!newOwnerDiscordId) {
      return res.status(400).json({ error: "Discord ID do novo dono é obrigatório" });
    }

    // Pega IP e User Agent
    const ip = req.headers["x-forwarded-for"] || req.connection.remoteAddress;
    const userAgent = req.headers["user-agent"];

    const result = await initiateOwnerTransfer(
      applicationId,
      userId,
      newOwnerDiscordId,
      ip,
      userAgent
    );

    if (!result.success) {
      return res.status(400).json({ error: result.message });
    }

    return res.json({
      success: true,
      transferId: result.transferId,
      message: result.message,
    });
  } catch (err) {
    console.error("[TRANSFER OWNER - INITIATE]", err);
    return res.status(500).json({ error: "Erro ao iniciar transferência" });
  }
});

/**
 * POST /apps/:id/transfer-owner/confirm
 * Confirma transferência com código
 */
router.post("/:id/transfer-owner/confirm", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { transferId, code } = req.body;

    if (!transferId || !code) {
      return res.status(400).json({ error: "ID da transferência e código são obrigatórios" });
    }

    const result = await confirmOwnerTransfer(transferId, code, userId);

    if (!result.success) {
      return res.status(400).json({ error: result.message });
    }

    return res.json({
      success: true,
      message: result.message,
      newOwner: result.newOwner,
      redirectTo: "/dashboard", // Redireciona para dashboard após sucesso
    });
  } catch (err) {
    console.error("[TRANSFER OWNER - CONFIRM]", err);
    return res.status(500).json({ error: "Erro ao confirmar transferência" });
  }
});

/**
 * POST /apps/:id/transfer-owner/cancel
 * Cancela transferência pendente
 */
router.post("/:id/transfer-owner/cancel", async (req, res) => {
  try {
    const userId = req.user?._id;
    const { transferId } = req.body;

    if (!transferId) {
      return res.status(400).json({ error: "ID da transferência é obrigatório" });
    }

    const result = await cancelOwnerTransfer(transferId, userId);

    if (!result.success) {
      return res.status(400).json({ error: result.message });
    }

    return res.json({
      success: true,
      message: result.message,
    });
  } catch (err) {
    console.error("[TRANSFER OWNER - CANCEL]", err);
    return res.status(500).json({ error: "Erro ao cancelar transferência" });
  }
});

export default router;

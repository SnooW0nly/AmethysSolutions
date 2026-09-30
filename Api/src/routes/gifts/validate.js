import Gift from "../../database/models/Gift.js";

/**
 * POST /gifts/validate
 * Valida um gift code sem resgatá-lo
 */
export default async function validateGift(req, res) {
  try {
    const { code } = req.body;

    if (!code || typeof code !== "string") {
      return res.status(400).json({
        success: false,
        message: "Código do gift é obrigatório",
      });
    }

    // Normaliza o código
    const normalizedCode = code.trim().toUpperCase();

    // Busca o gift
    const gift = await Gift.findOne({ code: normalizedCode })
      .select("-createdBy -batchId")
      .lean();

    if (!gift) {
      return res.status(404).json({
        success: false,
        valid: false,
        message: "Gift não encontrado",
      });
    }

    // Verifica se já foi usado
    if (gift.isUsed) {
      return res.status(200).json({
        success: true,
        valid: false,
        message: "Este gift já foi resgatado",
        data: {
          isUsed: true,
          usedAt: gift.usedAt,
        },
      });
    }

    // Verifica se expirou
    if (gift.expiresAt && new Date() > gift.expiresAt) {
      return res.status(200).json({
        success: true,
        valid: false,
        message: "Este gift expirou",
        data: {
          expired: true,
          expiresAt: gift.expiresAt,
        },
      });
    }

    // Gift válido
    return res.status(200).json({
      success: true,
      valid: true,
      message: "Gift válido!",
      data: {
        planName: gift.planName,
        months: gift.months,
        description: gift.description,
        expiresAt: gift.expiresAt,
      },
    });
  } catch (error) {
    console.error("[GIFT VALIDATE ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao validar gift",
      error: error.message,
    });
  }
}

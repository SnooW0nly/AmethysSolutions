import Gift from "../../../database/models/Gift.js";

/**
 * DELETE /admin/gifts/batch/:batchId
 * Deleta todos os gifts de um lote (apenas os não usados)
 */
export default async function deleteBatch(req, res) {
  try {
    const { batchId } = req.params;

    // Verifica quantos gifts existem no lote
    const totalGifts = await Gift.countDocuments({ batchId });

    if (totalGifts === 0) {
      return res.status(404).json({
        success: false,
        message: "Lote não encontrado",
      });
    }

    // Deleta apenas os gifts não usados
    const result = await Gift.deleteMany({
      batchId,
      isUsed: false,
    });

    const usedCount = totalGifts - result.deletedCount;

    return res.status(200).json({
      success: true,
      message: `${result.deletedCount} gift(s) deletado(s) com sucesso`,
      data: {
        deleted: result.deletedCount,
        kept: usedCount,
        total: totalGifts,
      },
    });
  } catch (error) {
    console.error("[ADMIN GIFTS DELETE BATCH ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao deletar lote de gifts",
      error: error.message,
    });
  }
}

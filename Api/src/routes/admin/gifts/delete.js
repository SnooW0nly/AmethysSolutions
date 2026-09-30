import Gift from "../../../database/models/Gift.js";

/**
 * DELETE /admin/gifts/delete/:id
 * Deleta um gift específico (apenas se não foi usado)
 */
export default async function deleteGift(req, res) {
  try {
    const { id } = req.params;

    const gift = await Gift.findById(id);

    if (!gift) {
      return res.status(404).json({
        success: false,
        message: "Gift não encontrado",
      });
    }

    if (gift.isUsed) {
      return res.status(400).json({
        success: false,
        message: "Não é possível deletar um gift que já foi usado",
      });
    }

    await Gift.findByIdAndDelete(id);

    return res.status(200).json({
      success: true,
      message: "Gift deletado com sucesso",
    });
  } catch (error) {
    console.error("[ADMIN GIFTS DELETE ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao deletar gift",
      error: error.message,
    });
  }
}

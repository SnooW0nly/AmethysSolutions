import Application from "../../database/models/Application.js";
import mongoose from "mongoose";

/**
 * GET /applications/:id
 * Busca uma aplicação específica do usuário
 */
export default async function getApplication(req, res) {
  try {
    if (!req.user || !req.user._id) {
      console.error("[GET APPLICATION] req.user não definido:", req.user);
      return res.status(401).json({
        success: false,
        message: "Usuário não autenticado",
      });
    }

    const userId = req.user._id;
    const { id } = req.params;

    // Valida se o ID é um ObjectId válido
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(400).json({
        success: false,
        message: "ID de aplicação inválido",
      });
    }

    // Busca a aplicação
    const existingApp = await Application.findOne({ _id: id }).lean();
    
    if (!existingApp) {
      return res.status(404).json({
        success: false,
        message: "Aplicação não encontrada",
      });
    }

    // Verifica se pertence ao usuário
    if (existingApp.userId.toString() !== userId.toString()) {
      return res.status(403).json({
        success: false,
        message: "Você não tem permissão para acessar esta aplicação",
      });
    }

    // Verifica se está deletado
    if (existingApp.isDeleted) {
      return res.status(404).json({
        success: false,
        message: "Aplicação não encontrada",
      });
    }

    const application = existingApp;

    return res.status(200).json({
      success: true,
      data: application,
    });
  } catch (error) {
    console.error("[GET APPLICATION ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao buscar aplicação",
      error: error.message,
    });
  }
}

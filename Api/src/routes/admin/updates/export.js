import express from "express";
import UpdateLog from "../../../database/models/UpdateLog.js";

const router = express.Router();

/**
 * GET /admin/updates/export/:updateId
 * Exporta os logs de uma atualização em formato TXT
 */
router.get("/:updateId", async (req, res) => {
  try {
    const { updateId } = req.params;

    const updateLog = await UpdateLog.findOne({ updateId })
      .populate("adminUserId", "name email")
      .lean();

    if (!updateLog) {
      return res.status(404).json({
        success: false,
        message: "Atualização não encontrada",
      });
    }

    // Gera o conteúdo do arquivo TXT
    let txtContent = "";
    txtContent += "=".repeat(80) + "\n";
    txtContent += "RELATÓRIO DE ATUALIZAÇÃO EM MASSA\n";
    txtContent += "=".repeat(80) + "\n\n";
    
    txtContent += `ID da Atualização: ${updateLog.updateId}\n`;
    txtContent += `Plano: ${updateLog.planId}\n`;
    txtContent += `Versão: ${updateLog.updateVersion}\n`;
    txtContent += `Admin: ${updateLog.adminUserId?.name || updateLog.adminUserId?.email || "N/A"}\n`;
    txtContent += `Status: ${updateLog.status}\n`;
    txtContent += `Iniciado em: ${new Date(updateLog.startedAt).toLocaleString("pt-BR")}\n`;
    
    if (updateLog.finishedAt) {
      txtContent += `Finalizado em: ${new Date(updateLog.finishedAt).toLocaleString("pt-BR")}\n`;
      const duration = Math.round((new Date(updateLog.finishedAt) - new Date(updateLog.startedAt)) / 1000);
      txtContent += `Duração: ${duration}s\n`;
    }
    
    txtContent += "\n" + "-".repeat(80) + "\n";
    txtContent += "ESTATÍSTICAS\n";
    txtContent += "-".repeat(80) + "\n\n";
    
    txtContent += `Total de bots: ${updateLog.stats.total}\n`;
    txtContent += `Processados: ${updateLog.stats.processed}\n`;
    txtContent += `Sucesso: ${updateLog.stats.successful}\n`;
    txtContent += `Falhas: ${updateLog.stats.failed}\n`;
    txtContent += `Pulados: ${updateLog.stats.skipped}\n`;
    
    if (updateLog.errors && updateLog.errors.length > 0) {
      txtContent += "\n" + "-".repeat(80) + "\n";
      txtContent += "ERROS\n";
      txtContent += "-".repeat(80) + "\n\n";
      
      updateLog.errors.forEach((error, index) => {
        txtContent += `${index + 1}. ${error.appName} (${error.appId})\n`;
        txtContent += `   Erro: ${error.error}\n\n`;
      });
    }
    
    txtContent += "\n" + "-".repeat(80) + "\n";
    txtContent += "LOGS DETALHADOS\n";
    txtContent += "-".repeat(80) + "\n\n";
    
    updateLog.logs.forEach((log) => {
      const timestamp = new Date(log.timestamp).toLocaleTimeString("pt-BR");
      const icon = {
        info: "ℹ️",
        success: "✓",
        error: "✗",
        warning: "⚠️",
      }[log.type] || "•";
      
      txtContent += `[${timestamp}] ${icon} ${log.message}\n`;
    });
    
    txtContent += "\n" + "=".repeat(80) + "\n";
    txtContent += "FIM DO RELATÓRIO\n";
    txtContent += "=".repeat(80) + "\n";

    // Define headers para download
    const filename = `update-${updateLog.planId}-${updateLog.updateVersion}.txt`;
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
    
    return res.send(txtContent);
  } catch (error) {
    console.error("[ADMIN UPDATES EXPORT] Erro ao exportar:", error);
    return res.status(500).json({
      success: false,
      message: "Erro ao exportar logs",
      error: error.message,
    });
  }
});

export default router;

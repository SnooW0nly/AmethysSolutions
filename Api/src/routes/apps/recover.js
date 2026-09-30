import Application from "../../database/models/Application.js";
import discloudService from "../../services/discloudService.js";

export default async function recoverApplication(req, res) {
  try {
    const { id } = req.params;
    const userId = req.user._id;

    const application = await Application.findOne({ _id: id, userId });

    if (!application) {
      return res.status(404).json({ success: false, message: "Aplicação não encontrada" });
    }

    if (!application.canRecover) {
      return res.status(400).json({ success: false, message: "Esta aplicação não pode ser recuperada" });
    }

    if (new Date() > new Date(application.expiresAt)) {
      return res.status(400).json({ success: false, message: "Aplicação ainda está vencida. Renove primeiro." });
    }

    if (application.isDeleted) {
      return res.status(400).json({
        success: false,
        message: "Aplicação foi deletada. Entre em contato com o suporte para redeploy.",
        needsRedeploy: true,
      });
    }

    const appId = application.hosting?.appId;
    const isDiscloud = application.hosting?.provider === "discloud";

    if (application.isBlocked && appId && isDiscloud) {
      try {
        const result = await discloudService.startApp(appId);

        if (!result.success) {
          console.error(`[RECOVER] Erro ao iniciar app ${appId}:`, result.error);
          return res.status(500).json({ success: false, message: "Erro ao iniciar aplicação na Discloud", error: result.error });
        }

        application.isBlocked = false;
        application.blockedAt = null;
        await application.save();

        console.log(`[RECOVER] Aplicação ${id} recuperada com sucesso`);

        return res.status(200).json({
          success: true,
          message: "Aplicação recuperada com sucesso!",
          data: {
            application: {
              id: application._id,
              name: application.name,
              isBlocked: application.isBlocked,
              expiresAt: application.expiresAt,
            },
          },
        });
      } catch (error) {
        console.error(`[RECOVER] Erro ao recuperar aplicação ${id}:`, error);
        return res.status(500).json({ success: false, message: "Erro ao recuperar aplicação", error: error.message });
      }
    }

    return res.status(400).json({ success: false, message: "Aplicação não está bloqueada" });
  } catch (error) {
    console.error("[RECOVER ERROR]", error);
    return res.status(500).json({ success: false, message: "Erro ao recuperar aplicação", error: error.message });
  }
}
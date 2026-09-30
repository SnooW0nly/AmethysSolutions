import { Router } from "express";
import Transcript from "../../database/models/Transcript.js";

const router = Router();

/**
 * GET /api/v1/transcript/:id
 * Retorna os dados do transcript para o frontend exibir
 * Rota pública — sem autenticação necessária
 */
router.get("/:id", async (req, res) => {
  try {
    const { id } = req.params;

    if (!id || id.length < 4) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const transcript = await Transcript.findOne({
      publicId: id,
      isDeleted: false,
    })
      .select("-htmlContent -__v") // não retorna o HTML aqui (retorna na rota /html)
      .lean();

    if (!transcript) {
      return res.status(404).json({ error: "Transcript não encontrado ou expirado" });
    }

    // Incrementa views (fire & forget)
    Transcript.updateOne({ _id: transcript._id }, { $inc: { views: 1 } }).catch(() => {});

    return res.json({
      success: true,
      transcript: {
        publicId: transcript.publicId,
        channelName: transcript.channelName,
        channelId: transcript.channelId,
        guildName: transcript.guildName,
        guildId: transcript.guildId,
        ticketId: transcript.ticketId,
        messageCount: transcript.messageCount,
        participantCount: transcript.participantCount,
        generatedBy: transcript.generatedBy,
        views: transcript.views,
        createdAt: transcript.createdAt,
        expiresAt: transcript.expiresAt,
      },
    });
  } catch (err) {
    console.error("[TRANSCRIPT GET]", err);
    return res.status(500).json({ error: "Erro ao buscar transcript" });
  }
});

/**
 * GET /api/v1/transcript/:id/html
 * Retorna o HTML bruto do transcript para renderização inline
 * Rota pública
 */
router.get("/:id/html", async (req, res) => {
  try {
    const { id } = req.params;

    if (!id || id.length < 4) {
      return res.status(400).json({ error: "ID inválido" });
    }

    const transcript = await Transcript.findOne({
      publicId: id,
      isDeleted: false,
    })
      .select("htmlContent expiresAt isDeleted")
      .lean();

    if (!transcript) {
      return res.status(404).send("<html><body><h2>Transcript não encontrado ou expirado.</h2></body></html>");
    }

    // Retorna HTML com headers corretos
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.setHeader("Cache-Control", "public, max-age=300"); // cache 5 min
    return res.send(transcript.htmlContent);
  } catch (err) {
    console.error("[TRANSCRIPT HTML]", err);
    return res.status(500).send("<html><body><h2>Erro interno.</h2></body></html>");
  }
});

export default router;
import { Router } from "express";
import multer from "multer";
import Transcript from "../../database/models/Transcript.js";
import { generatePublicId, getExpirationDate, extractTranscriptMeta } from "../../utils/transcriptUtils.js";

const router = Router();

// Multer em memória (sem salvar em disco)
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB máximo
  fileFilter: (_req, file, cb) => {
    if (
      file.mimetype === "text/html" ||
      file.originalname.endsWith(".html")
    ) {
      cb(null, true);
    } else {
      cb(new Error("Apenas arquivos HTML são aceitos"));
    }
  },
});

/**
 * POST /api/v1/transcript/upload
 * Chamado pelo bot Python para hospedar o transcript
 *
 * Body (multipart/form-data):
 *   - file: arquivo HTML do transcript
 *   - filename: nome do arquivo (ex: "transcript-ticket-123.html")
 *   - channel_name: nome do canal
 *   - channel_id: (opcional) ID do canal Discord
 *   - guild_id: (opcional) ID do servidor Discord
 *   - guild_name: (opcional) nome do servidor Discord
 *   - ticket_id: (opcional) ID do ticket
 *   - panel_id: (opcional) ID do painel
 *   - generated_by_id: (opcional) ID do usuário que gerou
 *   - generated_by_username: (opcional) username de quem gerou
 *   - ttl_days: (opcional) dias até expirar (padrão: 3)
 *
 * Headers:
 *   - X-API-Key: chave da API configurada no .env (CYM_API_KEY ou TRANSCRIPT_API_KEY)
 */
router.post("/upload", upload.single("file"), async (req, res) => {
  try {
    // Validação da API Key
    const apiKey = req.headers["x-api-key"] || req.headers["authorization"]?.replace("Bearer ", "");
    const validKey = process.env.TRANSCRIPT_API_KEY || process.env.CYM_API_KEY;

    if (validKey && apiKey !== validKey) {
      return res.status(401).json({ success: false, error: "API Key inválida" });
    }

    // Valida arquivo
    if (!req.file || !req.file.buffer) {
      return res.status(400).json({ success: false, error: "Arquivo HTML não enviado" });
    }

    const htmlContent = req.file.buffer.toString("utf-8");

    if (!htmlContent || htmlContent.trim().length < 10) {
      return res.status(400).json({ success: false, error: "Conteúdo HTML inválido ou vazio" });
    }

    // Extrai campos do body
    const {
      filename,
      channel_name,
      channel_id,
      guild_id,
      guild_name,
      ticket_id,
      panel_id,
      generated_by_id,
      generated_by_username,
      generated_by_avatar,
      ttl_days,
    } = req.body;

    const channelName = channel_name || (filename ? filename.replace(/^transcript-/, "").replace(/\.html$/, "") : "unknown");

    // Gera ID público único (garante unicidade)
    let publicId;
    let attempts = 0;
    do {
      publicId = generatePublicId(8);
      const existing = await Transcript.findOne({ publicId }).select("_id").lean();
      if (!existing) break;
      attempts++;
    } while (attempts < 5);

    if (attempts >= 5) {
      return res.status(500).json({ success: false, error: "Erro ao gerar ID único" });
    }

    // Calcula expiração
    const ttl = parseInt(ttl_days) || 3;
    const expiresAt = getExpirationDate(Math.min(ttl, 30)); // máximo 30 dias

    // Extrai metadados do HTML
    const { messageCount, participantCount } = extractTranscriptMeta(htmlContent);

    // Salva no banco
    const transcript = await Transcript.create({
      publicId,
      channelId: channel_id || "unknown",
      channelName,
      guildId: guild_id || null,
      guildName: guild_name || null,
      ticketId: ticket_id || null,
      panelId: panel_id || null,
      htmlContent,
      messageCount,
      participantCount,
      generatedBy: {
        userId: generated_by_id || null,
        username: generated_by_username || null,
        avatar: generated_by_avatar || null,
      },
      expiresAt,
      views: 0,
      isDeleted: false,
    });

    // Monta URL pública
    const baseUrl = process.env.NEXT_PUBLIC_URL || process.env.BASE_URL || "https://amethys.solutions";
    const fullUrl = `${baseUrl}/transcript/${publicId}`;

    console.log(`[TRANSCRIPT] Upload bem-sucedido — ID: ${publicId} | Canal: ${channelName} | Expira: ${expiresAt.toISOString()}`);

    return res.status(200).json({
      success: true,
      publicId,
      url: `/transcript/${publicId}`,
      fullUrl,
      expiresAt: expiresAt.toISOString(),
      ttlDays: ttl,
    });
  } catch (err) {
    console.error("[TRANSCRIPT UPLOAD] Erro:", err);
    return res.status(500).json({ success: false, error: "Erro interno ao salvar transcript" });
  }
});

export default router;
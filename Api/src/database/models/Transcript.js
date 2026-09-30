import mongoose from "mongoose";

const transcriptSchema = new mongoose.Schema(
  {
    // ID público para acesso via URL (ex: /transcript/abc123)
    publicId: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },

    // Dados do canal Discord
    channelId: {
      type: String,
      required: true,
    },
    channelName: {
      type: String,
      required: true,
    },

    // Dados do servidor
    guildId: {
      type: String,
      default: null,
    },
    guildName: {
      type: String,
      default: null,
    },

    // Dados do ticket
    ticketId: {
      type: String,
      default: null,
    },
    panelId: {
      type: String,
      default: null,
    },

    // Conteúdo HTML do transcript
    htmlContent: {
      type: String,
      required: true,
    },

    // Metadados extraídos do HTML
    messageCount: {
      type: Number,
      default: 0,
    },
    participantCount: {
      type: Number,
      default: 0,
    },

    // Quem gerou o transcript
    generatedBy: {
      userId: { type: String, default: null },
      username: { type: String, default: null },
      avatar: { type: String, default: null },
    },

    // Expiração automática
    expiresAt: {
      type: Date,
      required: true,
      index: { expireAfterSeconds: 0 }, // TTL index do MongoDB
    },

    // Views / acessos
    views: {
      type: Number,
      default: 0,
    },

    // Status
    isDeleted: {
      type: Boolean,
      default: false,
    },
  },
  {
    timestamps: true,
  }
);

// Index para busca por channelId
transcriptSchema.index({ channelId: 1, createdAt: -1 });

// Index para busca por guildId
transcriptSchema.index({ guildId: 1, createdAt: -1 });

const Transcript = mongoose.model("Transcript", transcriptSchema);

export default Transcript;
import mongoose from "mongoose";

const ChannelConfigSchema = new mongoose.Schema(
  {
    channelId: { type: String, required: true },
    channelName: { type: String, default: "" },
    guildId: { type: String, default: "" },
    guildName: { type: String, default: "" },
    slowmode: { type: Number, default: 0 },
    lastSentAt: { type: Date, default: null },
    lastMessageId: { type: String, default: null },
    enabled: { type: Boolean, default: true },
  },
  { _id: false }
);

const TokenConfigSchema = new mongoose.Schema(
  {
    id: { type: String, required: true },
    label: { type: String, default: "" },
    token: { type: String, required: true }, // token de conta (user)
    isValid: { type: Boolean, default: null },
    lastValidatedAt: { type: Date, default: null },
    // Informações da conta
    userId: { type: String, default: null },
    username: { type: String, default: null },
    avatar: { type: String, default: null },
    discriminator: { type: String, default: null },
    channels: { type: [ChannelConfigSchema], default: [] },
    isActive: { type: Boolean, default: true },
  },
  { _id: false }
);

const DivulgacaoSchema = new mongoose.Schema(
  {
    message: { type: String, default: "" }, // apenas conteúdo textual
    tokens: { type: [TokenConfigSchema], default: [] },
    isRunning: { type: Boolean, default: false },
    startedAt: { type: Date, default: null },
    stoppedAt: { type: Date, default: null },
    totalSent: { type: Number, default: 0 },
    totalErrors: { type: Number, default: 0 },
    updatedBy: { type: mongoose.Schema.Types.ObjectId, ref: "User", default: null },
  },
  { timestamps: true }
);

export default mongoose.models.Divulgacao ||
  mongoose.model("Divulgacao", DivulgacaoSchema);
import mongoose from "mongoose";

const OwnerTransferSchema = new mongoose.Schema(
  {
    applicationId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Application",
      required: true,
      index: true,
    },
    botID: {
      type: String,
      required: true,
      index: true,
    },
    fromUserId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
    fromDiscordId: {
      type: String,
      required: true,
    },
    toDiscordId: {
      type: String,
      required: true,
    },
    verificationCode: {
      type: String,
      required: true,
    },
    status: {
      type: String,
      enum: ["pending", "confirmed", "completed", "cancelled", "expired"],
      default: "pending",
    },
    expiresAt: {
      type: Date,
      required: true,
      default: () => new Date(Date.now() + 30 * 60 * 1000), // 30 minutos
    },
    confirmedAt: {
      type: Date,
      default: null,
    },
    completedAt: {
      type: Date,
      default: null,
    },
    ip: {
      type: String,
      default: null,
    },
    userAgent: {
      type: String,
      default: null,
    },
    attempts: {
      type: Number,
      default: 0,
    },
  },
  { timestamps: true }
);

// Índice para expiração automática
OwnerTransferSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 3600 }); // Remove após 1 hora da expiração

export default mongoose.models.OwnerTransfer || mongoose.model("OwnerTransfer", OwnerTransferSchema);

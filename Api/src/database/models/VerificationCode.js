import mongoose from "mongoose";

const VerificationCodeSchema = new mongoose.Schema(
  {
    email: {
      type: String,
      required: true,
      lowercase: true,
      trim: true,
      index: true,
    },
    code: {
      type: String,
      required: true,
    },
    expiresAt: {
      type: Date,
      required: true,
      index: true,
    },
    attempts: {
      type: Number,
      default: 0,
    },
    verified: {
      type: Boolean,
      default: false,
    },
    ip: {
      type: String,
    },
    userAgent: {
      type: String,
    },
  },
  { timestamps: true }
);

// Índice para expiração automática
VerificationCodeSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

// Índice composto para busca rápida
VerificationCodeSchema.index({ email: 1, verified: 1 });

export default mongoose.models.VerificationCode || mongoose.model("VerificationCode", VerificationCodeSchema);

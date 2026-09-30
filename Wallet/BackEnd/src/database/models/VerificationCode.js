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
    type: {
      type: String,
      enum: ['login', 'signup', 'email-change', 'password-change', 'forgot-password', 'transfer'],
      default: 'login',
    },
    metadata: {
      type: mongoose.Schema.Types.Mixed,
    },
  },
  { timestamps: true }
);

// Índice para expiração automática (TTL)
VerificationCodeSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

// Índice composto para busca rápida
VerificationCodeSchema.index({ email: 1, verified: 1 });

export default mongoose.models.VerificationCode || mongoose.model("VerificationCode", VerificationCodeSchema);


import mongoose from "mongoose";
import crypto from "crypto";

const TrustedDeviceSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    deviceId: {
      type: String,
      required: true,
      index: true,
    },
    deviceName: {
      type: String,
      trim: true,
    },
    userAgent: {
      type: String,
    },
    ip: {
      type: String,
    },
    lastUsedAt: {
      type: Date,
      default: Date.now,
      index: true,
    },
  },
  { timestamps: true }
);

// Índice composto para busca rápida
TrustedDeviceSchema.index({ userId: 1, deviceId: 1 }, { unique: true });

// Gerar deviceId único baseado em userAgent e IP
TrustedDeviceSchema.statics.generateDeviceId = function(userAgent, ip) {
  const data = `${userAgent || ''}|${ip || ''}`;
  return crypto.createHash('sha256').update(data).digest('hex');
};

// Buscar dispositivo confiável por userId e deviceId
TrustedDeviceSchema.statics.findTrustedDevice = async function(userId, deviceId) {
  return await this.findOne({ userId, deviceId });
};

// Listar todos os dispositivos confiáveis de um usuário
TrustedDeviceSchema.statics.findByUserId = async function(userId) {
  return await this.find({ userId }).sort({ lastUsedAt: -1 });
};

// Atualizar último uso do dispositivo
TrustedDeviceSchema.methods.updateLastUsed = async function() {
  this.lastUsedAt = new Date();
  await this.save();
};

export default mongoose.models.TrustedDevice || mongoose.model("TrustedDevice", TrustedDeviceSchema);


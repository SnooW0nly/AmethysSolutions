import mongoose from "mongoose";
import jwt from "jsonwebtoken";
import { JWT_SECRET } from "../../config/env.js";

const SessionSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
    token: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    deviceInfo: {
      userAgent: {
        type: String,
      },
      ip: {
        type: String,
      },
      deviceName: {
        type: String,
      },
    },
    lastActivity: {
      type: Date,
      default: Date.now,
      index: true,
    },
    expiresAt: {
      type: Date,
      required: true,
    },
    revoked: {
      type: Boolean,
      default: false,
      index: true,
    },
    revokedAt: {
      type: Date,
    },
  },
  { timestamps: true }
);

// Índice composto para busca rápida
SessionSchema.index({ userId: 1, revoked: 1 });
SessionSchema.index({ token: 1, revoked: 1 });

// TTL index para remover sessões expiradas automaticamente
SessionSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

// Buscar sessões ativas de um usuário
SessionSchema.statics.findActiveByUserId = async function (userId) {
  return await this.find({
    userId,
    revoked: false,
    expiresAt: { $gt: new Date() },
  }).sort({ lastActivity: -1 });
};

// Buscar sessão por token
SessionSchema.statics.findByToken = async function (token) {
  return await this.findOne({ token, revoked: false });
};

// Revogar sessão
SessionSchema.methods.revoke = async function () {
  this.revoked = true;
  this.revokedAt = new Date();
  await this.save();
};

// Revogar todas as sessões de um usuário (exceto a atual)
SessionSchema.statics.revokeAllByUserId = async function (userId, excludeToken = null) {
  const query = {
    userId,
    revoked: false,
    expiresAt: { $gt: new Date() },
  };

  if (excludeToken) {
    query.token = { $ne: excludeToken };
  }

  return await this.updateMany(query, {
    $set: {
      revoked: true,
      revokedAt: new Date(),
    },
  });
};

// Atualizar última atividade
SessionSchema.methods.updateActivity = async function () {
  this.lastActivity = new Date();
  await this.save();
};

// Criar sessão a partir de token JWT
SessionSchema.statics.createFromToken = async function (token, userId, deviceInfo = {}) {
  try {
    // Decodificar token para obter expiração
    const decoded = jwt.verify(token, JWT_SECRET);
    const expiresAt = decoded.exp ? new Date(decoded.exp * 1000) : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 dias padrão

    return await this.create({
      userId,
      token,
      deviceInfo,
      expiresAt,
    });
  } catch (error) {
    throw new Error('Token inválido');
  }
};

export default mongoose.models.Session || mongoose.model("Session", SessionSchema);


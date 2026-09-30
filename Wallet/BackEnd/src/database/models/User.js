import mongoose from "mongoose";
import bcrypt from "bcryptjs";

const BCRYPT_ROUNDS = 12;

const UserSchema = new mongoose.Schema(
  {
    fullName: {
      type: String,
      required: true,
      trim: true,
    },
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
      index: true,
    },
    password: {
      type: String,
      required: true,
    },
    birthDate: {
      type: Date,
    },
    phone: {
      type: String,
    },
    avatar: {
      type: String,
    },
    emailVerified: {
      type: Boolean,
      default: false,
    },
    blocked: {
      type: Boolean,
      default: false,
    },
    lastLogin: {
      type: Date,
    },
    ipHistory: [
      {
        ip: { type: String, required: true },
        date: { type: Date, default: Date.now },
      },
    ],
    admin: {
      type: Boolean,
      default: false,
      index: true,
    },
    isAffiliate: {
      type: Boolean,
      default: false,
    },
    // Business Profile & Category
    category: {
      type: String,
      enum: ['WHITE', 'BLACK'],
      default: 'WHITE',
    },
    tier: {
      type: Number,
      default: 1,
    },
    categoryLockedByAdmin: {
      type: Boolean,
      default: false,
    },
    businessProfileCompleted: {
      type: Boolean,
      default: false,
    },
  },
  { timestamps: true }
);

// Hash de senha antes de salvar (apenas se foi modificada)
UserSchema.pre("save", async function (next) {
  if (!this.isModified("password")) return next();
  // Evitar duplo hash (plaintext nunca começa com $2a/$2b)
  if (this.password.startsWith("$2")) return next();
  this.password = await bcrypt.hash(this.password, BCRYPT_ROUNDS);
  next();
});

// Método para comparar senha
UserSchema.methods.comparePassword = async function (candidatePassword) {
  // Suporte a migração: se a senha ainda for plaintext (não começa com $2), comparar direto
  if (!this.password.startsWith("$2")) {
    return this.password === candidatePassword;
  }
  return bcrypt.compare(candidatePassword, this.password);
};

// Método para adicionar IP ao histórico
UserSchema.methods.addIpToHistory = function (ip) {
  const existingIp = this.ipHistory.find((entry) => entry.ip === ip);
  if (existingIp) {
    existingIp.date = new Date();
  } else {
    this.ipHistory.push({ ip, date: new Date() });
  }
};

export default mongoose.models.User || mongoose.model("User", UserSchema);

import mongoose from "mongoose";

const HostingSchema = new mongoose.Schema(
  {
    provider: { type: String, default: "discloud" },
    appId: { type: String },
    name: { type: String },
    ram: { type: Number },
    version: { type: String },
    main: { type: String },
    status: { type: String },
    url: { type: String },
    createdAt: { type: Date },
    updatedAt: { type: Date },
    lastDeployAt: { type: Date },
  },
  { _id: false }
);

const BotSchema = new mongoose.Schema(
  {
    token: { type: String, default: null },
    owner: { type: String, default: null },
    id: { type: String, default: null },
    perms: { type: [String], default: [] },
    server: { type: String, default: null },
  },
  { _id: false }
);

const InfoSchema = new mongoose.Schema(
  {
    name: { type: String, default: "Vision Pro" },
    imageUrl: { type: String, default: null },
    id: { type: String, default: null },
  },
  { _id: false }
);

const ApplicationSchema = new mongoose.Schema(
  {
    userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true, index: true },
    paymentId: { type: mongoose.Schema.Types.ObjectId, ref: "Payment", index: true },
    name: { type: String, required: true },

    // ID único do bot para vincular com BotConfig
    botID: { type: String, index: true },

    plan: {
      id: { type: String, required: true },
      name: { type: String },
      months: { type: Number },
      price: { type: Number },
      paymentId: { type: mongoose.Schema.Types.ObjectId, ref: "Payment" },
    },

    hosting: { type: HostingSchema, default: {} },
    bot: { type: BotSchema, default: {} },
    info: { type: InfoSchema, default: {} },

    expiresAt: { type: Date },
    lastChargeSent: { type: Date, default: null },

    // Controle de atualização em massa
    lastUpdate: { type: Date, default: null },
    lastUpdateBy: { type: mongoose.Schema.Types.ObjectId, ref: "User", default: null },
    updateVersion: { type: String, default: null },

    // Controle de bloqueio e deleção
    isBlocked: { type: Boolean, default: false },
    blockedAt: { type: Date, default: null },
    isDeleted: { type: Boolean, default: false },
    deletedAt: { type: Date, default: null },
    canRecover: { type: Boolean, default: true },

    // Controle de plano gratuito
    isFree: { type: Boolean, default: false },
    lastStartedAt: { type: Date, default: Date.now },
    inactivityWarningSentAt: { type: Date, default: null },

    // Indica que esta aplicação é uma recompensa do programa de afiliados
    // Criada automaticamente quando alguém compra usando o link de afiliado do usuário
    isAffiliateReward: { type: Boolean, default: false },
  },
  { timestamps: true }
);

// Garante que o owner do bot sempre esteja presente em bot.perms (imutável)
ApplicationSchema.pre("save", function (next) {
  try {
    const bot = this.get("bot");
    const owner = bot?.owner;
    if (owner && typeof owner === "string" && owner.trim().length > 0) {
      const perms = Array.isArray(bot?.perms) ? bot.perms.slice() : [];
      if (!perms.includes(owner)) {
        perms.push(owner);
      }
      this.set("bot.perms", perms);
    }
  } catch {
    // não bloqueia o fluxo em caso de erro não crítico
  }
  next();
});

// Garante em updates/upserts que bot.perms inclua o owner quando definido
ApplicationSchema.pre("findOneAndUpdate", function (next) {
  try {
    const update = this.getUpdate() || {};
    const set = update.$set || update;
    const owner =
      (set && (set["bot.owner"] ?? (set.bot && set.bot.owner))) ?? null;
    if (typeof owner === "string" && owner.trim().length > 0) {
      let perms =
        (set && (set["bot.perms"] ?? (set.bot && set.bot.perms))) ?? undefined;
      if (!Array.isArray(perms)) perms = [];
      if (!perms.includes(owner)) {
        const newPerms = perms.concat([owner]);
        if (!update.$set) update.$set = {};
        update.$set["bot.perms"] = newPerms;
        this.setUpdate(update);
      }
    }
  } catch {
    // não bloqueia o fluxo
  }
  next();
});

ApplicationSchema.index({ userId: 1, "plan.id": 1 });
ApplicationSchema.index(
  { userId: 1, isFree: 1 },
  {
    unique: true,
    partialFilterExpression: { isFree: true, isDeleted: false },
    background: true,
  }
);
ApplicationSchema.index({ userId: 1, isAffiliateReward: 1, isDeleted: 1 });

export default mongoose.models.Application || mongoose.model("Application", ApplicationSchema);
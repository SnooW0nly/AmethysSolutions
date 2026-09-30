import mongoose from "mongoose";

const BotSchema = new mongoose.Schema(
  {
    token: { type: String, default: "" },
    owner: { type: String, required: true },
    id: { type: String, default: "" },
    perms: { type: [String], default: [] },
    server: { type: String, default: "" },
  },
  { _id: false }
);

const BotConfigSchema = new mongoose.Schema(
  {
    botID: { type: String, required: true, index: true, unique: true },
    botToken: { type: String, required: true }, // token simples (ex: 5 dígitos)
    apiURL: { type: String, required: true, default: () => process.env.BACKEND_URL || "http://localhost" },
    version: { type: String, default: "Stable" },
    syncEmojis: { type: Boolean, default: true },
    saveConfig: { type: Boolean, default: true },
    startOnBackup: { type: Boolean, default: true },
    bot: { type: BotSchema, required: true },
  },
  { timestamps: true }
);

// Garante que o owner esteja em bot.perms ao salvar
BotConfigSchema.pre("save", function (next) {
  try {
    const bot = this.get("bot");
    const owner = bot?.owner;
    if (typeof owner === "string" && owner.trim().length > 0) {
      const perms = Array.isArray(bot?.perms) ? bot.perms.slice() : [];
      if (!perms.includes(owner)) {
        perms.push(owner);
      }
      this.set("bot.perms", perms);
    }
  } catch {
    // não bloqueia
  }
  next();
});

// Garante em updates/upserts que bot.perms inclua o owner
BotConfigSchema.pre("findOneAndUpdate", function (next) {
  try {
    const update = this.getUpdate() || {};
    const set = update.$set || update;
    const owner = (set && (set["bot.owner"] ?? (set.bot && set.bot.owner))) ?? null;
    if (typeof owner === "string" && owner.trim().length > 0) {
      let perms = (set && (set["bot.perms"] ?? (set.bot && set.bot.perms))) ?? undefined;
      if (!Array.isArray(perms)) perms = [];
      if (!perms.includes(owner)) {
        const newPerms = perms.concat([owner]);
        if (!update.$set) update.$set = {};
        update.$set["bot.perms"] = newPerms;
        this.setUpdate(update);
      }
    }
  } catch {
    // não bloqueia
  }
  next();
});

const BotConfig = mongoose.models.BotConfig || mongoose.model("BotConfig", BotConfigSchema);
export default BotConfig;

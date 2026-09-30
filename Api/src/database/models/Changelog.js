import mongoose from "mongoose";

const ChangelogItemSchema = new mongoose.Schema(
  {
    type: {
      type: String,
      enum: ["new", "improved", "fixed"],
      required: true,
    },
    title: { type: String, required: true, trim: true },
    description: { type: String, required: true, trim: true },
  },
  { _id: true }
);

const ChangelogSchema = new mongoose.Schema(
  {
    version: { type: String, required: true, trim: true },
    title: { type: String, required: true, trim: true },
    description: { type: String, default: "", trim: true },
    items: { type: [ChangelogItemSchema], default: [] },

    published: { type: Boolean, default: false, index: true },
    publishedAt: { type: Date, default: null },

    webhookConfig: {
      sentAt: { type: Date, default: null },
      webhookUrl: { type: String, default: null },
      coverImageUrl: { type: String, default: null },
      accentColorMain: { type: Number, default: 0xc400c4 },
      accentColorPromo: { type: Number, default: 0xa61fe3 },
      promoText: { type: String, default: "" },
      promoButtonLabel: { type: String, default: "Adquirir Pro" },
      promoButtonUrl: {
        type: String,
        default: "https://amethysapp.vercel.app/pricing",
      },
      // Discord custom emoji format: <:name:id> or unicode
      emojiNew: { type: String, default: "🆕" },
      emojiImproved: { type: String, default: "⬆️" },
      emojiFixed: { type: String, default: "🔧" },
    },

    createdBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      default: null,
    },
    updatedBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      default: null,
    },
  },
  { timestamps: true }
);

ChangelogSchema.index({ published: 1, createdAt: -1 });
ChangelogSchema.index({ version: 1 });

export default mongoose.models.Changelog ||
  mongoose.model("Changelog", ChangelogSchema);
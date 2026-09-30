import mongoose from "mongoose";

const PartnershipSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: true,
      trim: true,
      maxlength: 100,
    },
    slug: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
      index: true,
    },
    description: {
      type: String,
      required: true,
      trim: true,
      maxlength: 500,
    },
    shortDescription: {
      type: String,
      trim: true,
      maxlength: 150,
    },
    logoUrl: {
      type: String,
      trim: true,
      default: null,
    },
    bannerUrl: {
      type: String,
      trim: true,
      default: null,
    },
    websiteUrl: {
      type: String,
      trim: true,
      default: null,
    },
    discordUrl: {
      type: String,
      trim: true,
      default: null,
    },
    category: {
      type: String,
      enum: ["hosting", "bot", "community", "tool", "service", "other"],
      default: "other",
      index: true,
    },
    tags: {
      type: [String],
      default: [],
    },
    benefits: {
      type: [String],
      default: [],
    },
    couponCode: {
      type: String,
      trim: true,
      default: null,
    },
    couponDescription: {
      type: String,
      trim: true,
      default: null,
    },
    featured: {
      type: Boolean,
      default: false,
      index: true,
    },
    active: {
      type: Boolean,
      default: true,
      index: true,
    },
    order: {
      type: Number,
      default: 0,
      index: true,
    },
    createdBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
    updatedBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      default: null,
    },
  },
  { timestamps: true }
);

// Índice composto para listagem pública
PartnershipSchema.index({ active: 1, featured: -1, order: 1 });
PartnershipSchema.index({ active: 1, category: 1, order: 1 });

// Gera slug automaticamente a partir do nome se não fornecido
PartnershipSchema.pre("validate", function (next) {
  if (!this.slug && this.name) {
    this.slug = this.name
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9-]/g, "")
      .slice(0, 80);
  }
  next();
});

export default mongoose.models.Partnership ||
  mongoose.model("Partnership", PartnershipSchema);
import mongoose from "mongoose";

const CouponSchema = new mongoose.Schema(
  {
    name: { type: String, required: true, unique: true, trim: true, uppercase: true, maxlength: 20 }, // código
    percent: { type: Number, required: true, min: 0, max: 100 }, // desconto percentual

    archived: { type: Boolean, default: false },
    maxUses: { type: Number }, // total de usos permitidos
    usedCount: { type: Number, default: 0 },
    availableDays: { type: Number }, // dias a partir de createdAt
    minCart: { type: Number }, // valor mínimo do carrinho

    createdBy: { type: String },
    updatedBy: { type: String },
  },
  { timestamps: true }
);

export default mongoose.models.Coupon || mongoose.model("Coupon", CouponSchema);

// Normalize name: spaces to '-', keep uppercase and within 20 chars (maxlength enforces)
CouponSchema.pre("validate", function (next) {
  try {
    if (typeof this.name === "string") {
      const normalized = this.name.replace(/\s+/g, "-");
      this.name = normalized.toUpperCase();
    }
  } catch {}
  next();
});



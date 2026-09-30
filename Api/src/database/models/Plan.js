import mongoose from "mongoose";

const FeatureSchema = new mongoose.Schema(
  {
    title: { type: String, required: true },
  },
  { _id: false }
);

const PlanOptionSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    value: { type: Number, required: true },
    discount: { type: Number, default: 0 },
    months: { type: Number, required: true },
    id: { type: String, required: true },
    description: { type: String },
  },
  { _id: false }
);

const PlanSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    id: { type: String, required: true, unique: true }, // slug
    icon: { type: String }, // frontend deve mapear o nome do ícone
    description: { type: String },
    primary: { type: Boolean, default: false },
    isFree: { type: Boolean, default: false }, // Plano gratuito
    features: { type: [FeatureSchema], default: [] },
    plans: { type: [PlanOptionSchema], default: [] },
    zipFilename: { type: String },
    discordRoleId: { type: String },
    active: { type: Boolean, default: true }, // Se false, plano não aparece publicamente
  },
  { timestamps: true }
);

export default mongoose.models.Plan || mongoose.model("Plan", PlanSchema);



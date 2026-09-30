import mongoose from "mongoose";

// Representa um "adicional" que pode ser habilitado num plano
const PlanAddonSchema = new mongoose.Schema(
  {
    // ID legível: ex "bot-black"
    id: { type: String, required: true, unique: true },
    name: { type: String, required: true },
    shortDescription: { type: String, default: "" },
    // Valor adicional em R$ (somado ao plano base)
    extraValue: { type: Number, required: true, default: 0 },
    active: { type: Boolean, default: true },
    // Quais planos têm este addon habilitado
    enabledForPlans: { type: [String], default: [] },
    updatedBy: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
  },
  { timestamps: true }
);

export default mongoose.models.PlanAddon ||
  mongoose.model("PlanAddon", PlanAddonSchema);
import mongoose from "mongoose";

const FreePlanConfigSchema = new mongoose.Schema(
  {
    // Plano de referência (usa o ZIP deste plano)
    sourcePlanId: { type: String, required: true },
    // Duração em dias
    durationDays: { type: Number, required: true, default: 7 },
    // Ativo ou não
    active: { type: Boolean, default: true },
    // Limite de conta em dias para resgatar (ex: 15 dias)
    minAccountAgeDays: { type: Number, default: 15 },
    // Score máximo de risco para bloquear (0-100)
    maxRiskScore: { type: Number, default: 60 },
    updatedBy: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
  },
  { timestamps: true }
);

export default mongoose.models.FreePlanConfig ||
  mongoose.model("FreePlanConfig", FreePlanConfigSchema);
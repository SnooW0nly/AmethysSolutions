import mongoose from "mongoose";

const RevisionConfigSchema = new mongoose.Schema(
  {
    key: { type: String, required: true, unique: true, index: true },
    value: { type: String, default: "" },
    label: { type: String, default: "" },
    updatedBy: { type: String, default: null },
  },
  { timestamps: true }
);

export default mongoose.models.RevisionConfig ||
  mongoose.model("RevisionConfig", RevisionConfigSchema);
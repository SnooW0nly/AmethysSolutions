// src/database/models/GlobalConfig.js
// Model para configurações globais do sistema
import mongoose from "mongoose";

const GlobalConfigSchema = new mongoose.Schema(
  {
    key: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    value: {
      type: mongoose.Schema.Types.Mixed,
      required: true,
    },
    updatedBy: {
      type: String,
      default: null,
    },
  },
  { timestamps: true }
);

export default mongoose.models.GlobalConfig ||
  mongoose.model("GlobalConfig", GlobalConfigSchema);
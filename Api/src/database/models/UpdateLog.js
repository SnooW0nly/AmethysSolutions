import mongoose from "mongoose";

const UpdateLogSchema = new mongoose.Schema(
  {
    updateId: { type: String, required: true, index: true },
    planId: { type: String, required: true, index: true },
    updateVersion: { type: String, required: true },
    adminUserId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
    
    status: { 
      type: String, 
      enum: ["running", "completed", "error"], 
      default: "running",
      index: true 
    },
    
    startedAt: { type: Date, required: true },
    finishedAt: { type: Date, default: null },
    
    stats: {
      total: { type: Number, default: 0 },
      processed: { type: Number, default: 0 },
      successful: { type: Number, default: 0 },
      failed: { type: Number, default: 0 },
      skipped: { type: Number, default: 0 },
    },
    
    logs: [{
      timestamp: { type: Date, required: true },
      type: { 
        type: String, 
        enum: ["info", "success", "error", "warning"], 
        required: true 
      },
      message: { type: String, required: true },
    }],
    
    errors: [{
      appId: { type: String },
      appName: { type: String },
      error: { type: String },
    }],
  },
  { timestamps: true }
);

// Índice composto para buscar logs por plano e data
UpdateLogSchema.index({ planId: 1, startedAt: -1 });

// Índice para buscar por status e data
UpdateLogSchema.index({ status: 1, startedAt: -1 });

const UpdateLog = mongoose.models.UpdateLog || mongoose.model("UpdateLog", UpdateLogSchema);
export default UpdateLog;

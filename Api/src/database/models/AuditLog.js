import mongoose from "mongoose";

const AuditLogSchema = new mongoose.Schema(
  {
    entity: { type: String, required: true }, // coupon, plan, etc.
    action: { type: String, required: true }, // create, update, redeem, validate, archive, restore
    actorId: { type: String }, // user/admin id
    targetId: { type: String }, // coupon id/name
    metadata: { type: Object, default: {} },
  },
  { timestamps: true }
);

export default mongoose.models.AuditLog || mongoose.model("AuditLog", AuditLogSchema);



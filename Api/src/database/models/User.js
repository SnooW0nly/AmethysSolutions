import mongoose from "mongoose";

const UserSchema = new mongoose.Schema(
  {
    discordId: { type: String, required: true, unique: true },
    username: { type: String, required: true },
    globalName: { type: String, required: true },
    email: { type: String },
    avatar: { type: String },
    admin: { type: Boolean, default: false },
    blocked: { type: Boolean, default: false },
    freePlanRedeemed: { type: Boolean, default: false },
    tokenVersion: { type: Number, default: 0 },
    oauth: {
      accessToken: { type: String },
      refreshToken: { type: String },
      tokenType: { type: String },
      scope: { type: String },
      expiresAt: { type: Date },
      obtainedAt: { type: Date },
    },
    ipHistory: [
      new mongoose.Schema(
        {
          ip: { type: String, required: true },
          dates: { type: [Date], default: [] },
        },
        { _id: false }
      ),
    ],
  },
  { timestamps: true }
);

export default mongoose.models.User || mongoose.model("User", UserSchema);
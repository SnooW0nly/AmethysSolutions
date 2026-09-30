import mongoose from "mongoose";

const WebhookSchema = new mongoose.Schema(
  {
    id: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    userId: {
      type: String,
      required: true,
      index: true,
    },
    event: {
      type: String,
      required: true,
      index: true,
    },
    url: {
      type: String,
      required: true,
    },
    payload: {
      type: mongoose.Schema.Types.Mixed,
      required: true,
    },
    status: {
      type: String,
      enum: ['pending', 'success', 'failed'],
      default: 'pending',
      index: true,
    },
    attempts: {
      type: Number,
      default: 0,
    },
    maxAttempts: {
      type: Number,
      default: 5,
    },
    lastAttemptAt: {
      type: Date,
    },
    nextRetryAt: {
      type: Date,
      index: true,
    },
    responseStatus: {
      type: Number,
    },
    responseBody: {
      type: String,
    },
    error: {
      type: String,
    },
    signature: {
      type: String,
    },
  },
  {
    timestamps: true,
    collection: 'webhooks'
  }
);

// Índices compostos
WebhookSchema.index({ userId: 1, status: 1 });
WebhookSchema.index({ status: 1, nextRetryAt: 1 });
WebhookSchema.index({ event: 1, createdAt: -1 });

// Métodos estáticos
WebhookSchema.statics.getById = async function(id) {
  return await this.findOne({ id });
};

WebhookSchema.statics.getPending = async function() {
  const now = new Date();
  return await this.find({
    status: 'pending',
    attempts: { $lt: this.schema.path('maxAttempts').defaultValue || 5 },
    $or: [
      { nextRetryAt: { $lte: now } },
      { nextRetryAt: { $exists: false } }
    ]
  }).limit(50);
};

WebhookSchema.statics.getByUser = async function(userId, limit = 100) {
  return await this.find({ userId })
    .sort({ createdAt: -1 })
    .limit(limit);
};

WebhookSchema.statics.getByEvent = async function(event, limit = 100) {
  return await this.find({ event })
    .sort({ createdAt: -1 })
    .limit(limit);
};

export default mongoose.models.Webhook || mongoose.model("Webhook", WebhookSchema);


import mongoose from 'mongoose';

const PushSubscriptionSchema = new mongoose.Schema(
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
        endpoint: {
            type: String,
            required: true,
        },
        keys: {
            p256dh: {
                type: String,
                required: true,
            },
            auth: {
                type: String,
                required: true,
            },
        },
        userAgent: {
            type: String,
        },
        deviceType: {
            type: String,
            enum: ['desktop', 'mobile', 'tablet'],
            default: 'desktop',
        },
        active: {
            type: Boolean,
            default: true,
        },
        lastUsed: {
            type: Date,
            default: Date.now,
        },
    },
    {
        timestamps: true,
        collection: 'push_subscriptions',
    }
);

// Índices
PushSubscriptionSchema.index({ userId: 1, active: 1 });
PushSubscriptionSchema.index({ endpoint: 1 }, { unique: true });

// Métodos estáticos
PushSubscriptionSchema.statics.getByUserId = async function (userId) {
    return await this.find({ userId, active: true });
};

PushSubscriptionSchema.statics.getByEndpoint = async function (endpoint) {
    return await this.findOne({ endpoint });
};

PushSubscriptionSchema.statics.deactivate = async function (endpoint) {
    return await this.findOneAndUpdate(
        { endpoint },
        { $set: { active: false } }
    );
};

export default mongoose.models.PushSubscription || mongoose.model('PushSubscription', PushSubscriptionSchema);

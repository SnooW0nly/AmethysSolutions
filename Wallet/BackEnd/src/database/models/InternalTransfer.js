import mongoose from "mongoose";

const InternalTransferSchema = new mongoose.Schema(
    {
        id: {
            type: String,
            required: true,
            unique: true,
            index: true,
        },
        senderId: {
            type: String,
            required: true,
            index: true,
        },
        senderEmail: {
            type: String,
            required: true,
        },
        recipientId: {
            type: String,
            required: true,
            index: true,
        },
        recipientEmail: {
            type: String,
            required: true,
        },
        amount: {
            type: Number,
            required: true,
        },
        description: {
            type: String,
        },
        status: {
            type: String,
            enum: ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'],
            default: 'COMPLETED',
            index: true,
        },
        metadata: {
            type: mongoose.Schema.Types.Mixed,
        },
    },
    {
        timestamps: true,
        collection: 'internal_transfers'
    }
);

// Índices compostos
InternalTransferSchema.index({ senderId: 1, status: 1 });
InternalTransferSchema.index({ senderId: 1, createdAt: -1 });
InternalTransferSchema.index({ recipientId: 1, createdAt: -1 });

// Métodos estáticos
InternalTransferSchema.statics.getById = async function (id) {
    return await this.findOne({ id });
};

InternalTransferSchema.statics.getBySenderId = async function (senderId) {
    return await this.find({ senderId }).sort({ createdAt: -1 });
};

InternalTransferSchema.statics.getByRecipientId = async function (recipientId) {
    return await this.find({ recipientId }).sort({ createdAt: -1 });
};

InternalTransferSchema.statics.getPending = async function (senderId) {
    return await this.findOne({
        senderId,
        status: { $in: ['PENDING', 'PROCESSING'] }
    });
};

export default mongoose.models.InternalTransfer || mongoose.model("InternalTransfer", InternalTransferSchema);

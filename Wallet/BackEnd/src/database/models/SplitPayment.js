import mongoose from 'mongoose';

const SplitPaymentSchema = new mongoose.Schema({
    id: {
        type: String,
        required: true,
        unique: true,
        index: true,
    },
    originalPaymentId: {
        type: String,
        required: true,
        index: true,
    },
    senderId: {
        type: String,
        required: true,
        index: true,
    },
    senderEmail: {
        type: String,
    },
    recipientId: {
        type: String,
        required: true,
        index: true,
    },
    recipientEmail: {
        type: String,
    },
    amount: {
        type: Number,
        required: true,
    },
    splitPercentage: {
        type: Number,
        required: true,
    },
    originalAmount: {
        type: Number,
        required: true,
    },
    status: {
        type: String,
        enum: ['PENDING', 'COMPLETED', 'FAILED'],
        default: 'COMPLETED',
    },
    createdAt: {
        type: String,
    },
    processedAt: {
        type: String,
    },
});

// Índices compostos
SplitPaymentSchema.index({ recipientId: 1, status: 1 });
SplitPaymentSchema.index({ senderId: 1, status: 1 });
SplitPaymentSchema.index({ createdAt: -1 });

// Métodos estáticos
SplitPaymentSchema.statics.getByRecipient = async function (recipientId) {
    return await this.find({ recipientId }).sort({ createdAt: -1 });
};

SplitPaymentSchema.statics.getBySender = async function (senderId) {
    return await this.find({ senderId }).sort({ createdAt: -1 });
};

const SplitPayment = mongoose.model('SplitPayment', SplitPaymentSchema);

export default SplitPayment;

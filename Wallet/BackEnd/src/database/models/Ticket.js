import mongoose from "mongoose";

const TicketSchema = new mongoose.Schema(
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
        userEmail: {
            type: String,
            required: true,
        },
        type: {
            type: String,
            enum: ['CATEGORY_CHANGE', 'SUPPORT', 'OTHER'],
            required: true,
            index: true,
        },
        status: {
            type: String,
            enum: ['PENDING', 'APPROVED', 'REJECTED', 'CLOSED'],
            default: 'PENDING',
            index: true,
        },
        // Dados específicos do ticket
        data: {
            // Para CATEGORY_CHANGE
            currentCategory: String,
            currentTier: Number,
            requestedCategory: String, // WHITE ou BLACK
            requestedTier: Number,
            reason: String, // Justificativa do usuário

            // Dados preenchidos pelo admin na resolução
            resolvedCategory: String,
            resolvedTier: Number,
            adminNotes: String,
        },
        // Admin que resolveu
        resolvedBy: {
            type: String,
        },
        resolvedAt: {
            type: String, // ISO string
        },
    },
    {
        timestamps: true,
        collection: 'tickets'
    }
);

// Índices compostos
TicketSchema.index({ status: 1, type: 1 });
TicketSchema.index({ userId: 1, status: 1 });

// Métodos estáticos
TicketSchema.statics.getPending = async function (type = null) {
    const query = { status: 'PENDING' };
    if (type) query.type = type;
    return await this.find(query).sort({ createdAt: -1 }).lean();
};

TicketSchema.statics.getByUser = async function (userId) {
    return await this.find({ userId }).sort({ createdAt: -1 }).lean();
};

export default mongoose.models.Ticket || mongoose.model("Ticket", TicketSchema);

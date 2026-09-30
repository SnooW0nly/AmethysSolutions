import mongoose from "mongoose";

/**
 * Model para armazenar dados de categorização do negócio
 * Usado para determinar se o usuário é WHITE ou BLACK
 */
const BusinessProfileSchema = new mongoose.Schema(
    {
        // Identificação
        id: {
            type: String,
            required: true,
            unique: true,
            index: true,
        },
        userId: {
            type: String,
            required: true,
            unique: true,
            index: true,
        },

        // Dados do negócio
        businessName: {
            type: String,
            required: true,
            trim: true,
        },
        website: {
            type: String,
            trim: true,
        },
        description: {
            type: String,
            required: true,
            trim: true,
        },

        // Pergunta sobre MEDs
        medFrequency: {
            type: String,
            enum: ['NEVER', 'RARELY', 'FREQUENTLY', 'ALWAYS'],
            required: true,
        },

        // Categorização
        category: {
            type: String,
            enum: ['WHITE', 'BLACK'],
            required: true,
        },
        categorizedAt: {
            type: String, // ISO string
        },
        categorizedBy: {
            type: String,
            enum: ['SYSTEM', 'ADMIN', 'AI'],
            default: 'SYSTEM',
        },

        // Admin notes (opcional)
        adminNotes: {
            type: String,
            trim: true,
        },
    },
    {
        timestamps: true,
        collection: 'business_profiles'
    }
);

// Índices
BusinessProfileSchema.index({ category: 1 });

// Métodos estáticos
BusinessProfileSchema.statics.getByUserId = async function (userId) {
    return await this.findOne({ userId });
};

BusinessProfileSchema.statics.createProfile = async function (profileData) {
    return await this.create(profileData);
};

export default mongoose.models.BusinessProfile || mongoose.model("BusinessProfile", BusinessProfileSchema);

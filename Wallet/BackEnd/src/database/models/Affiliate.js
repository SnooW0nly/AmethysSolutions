import mongoose from "mongoose";

const AffiliateSchema = new mongoose.Schema(
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
            unique: true,
            index: true,
        },
        userEmail: {
            type: String,
            required: true,
        },
        userName: {
            type: String,
        },
        // Código personalizado do link (ex: /CODIGO)
        code: {
            type: String,
            required: true,
            unique: true,
            index: true,
            lowercase: true,
            trim: true,
        },
        // Estatísticas
        totalReferrals: {
            type: Number,
            default: 0,
        },
        totalEarnings: {
            type: Number,
            default: 0, // Em centavos
        },
        clicks: {
            type: Number,
            default: 0,
        },
        // Taxa de comissão por transação (em centavos)
        commissionRate: {
            type: Number,
            default: 5, // R$ 0,05
        },
        // Status do afiliado
        status: {
            type: String,
            enum: ['active', 'inactive', 'suspended'],
            default: 'active',
            index: true,
        },
    },
    {
        timestamps: true,
        collection: 'affiliates'
    }
);

// Índices compostos
AffiliateSchema.index({ status: 1, createdAt: -1 });

// Métodos estáticos
AffiliateSchema.statics.getById = async function (id) {
    return await this.findOne({ id, status: 'active' });
};

AffiliateSchema.statics.getByUserId = async function (userId) {
    return await this.findOne({ userId });
};

AffiliateSchema.statics.getByCode = async function (code) {
    return await this.findOne({ code: code.toLowerCase(), status: 'active' });
};

AffiliateSchema.statics.isCodeAvailable = async function (code) {
    const existing = await this.findOne({ code: code.toLowerCase() });
    return !existing;
};

AffiliateSchema.statics.getReferrals = async function (affiliateId) {
    const Register = mongoose.model('Register');
    return await Register.find({
        referredBy: affiliateId,
        status: 'active'
    }).select('id email name createdAt plan').sort({ createdAt: -1 });
};

export default mongoose.models.Affiliate || mongoose.model("Affiliate", AffiliateSchema);

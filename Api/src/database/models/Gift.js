import mongoose from "mongoose";

const GiftSchema = new mongoose.Schema(
  {
    code: { 
      type: String, 
      required: true, 
      unique: true, 
      uppercase: true,
      trim: true,
      index: true 
    },
    planId: { 
      type: String, 
      required: true,
      index: true 
    },
    planName: { 
      type: String, 
      required: true 
    },
    months: { 
      type: Number, 
      required: true,
      min: 1 
    },
    // Controle de uso
    isUsed: { 
      type: Boolean, 
      default: false,
      index: true 
    },
    usedBy: { 
      type: mongoose.Schema.Types.ObjectId, 
      ref: "User",
      default: null 
    },
    usedAt: { 
      type: Date, 
      default: null 
    },
    // Controle de validade
    expiresAt: { 
      type: Date, 
      default: null 
    },
    // Metadados
    createdBy: { 
      type: mongoose.Schema.Types.ObjectId, 
      ref: "User", 
      required: true 
    },
    description: { 
      type: String, 
      default: "" 
    },
    // Controle de lote (para criar múltiplos gifts)
    batchId: { 
      type: String,
      index: true 
    },
    // Aplicação gerada pelo gift
    applicationId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Application",
      default: null
    }
  },
  { timestamps: true }
);

// Índices compostos para queries otimizadas
GiftSchema.index({ isUsed: 1, expiresAt: 1 });
GiftSchema.index({ batchId: 1, createdAt: -1 });
GiftSchema.index({ planId: 1, isUsed: 1 });

// Método para verificar se o gift é válido
GiftSchema.methods.isValid = function() {
  if (this.isUsed) return false;
  if (this.expiresAt && new Date() > this.expiresAt) return false;
  return true;
};

// Método estático para gerar código único
GiftSchema.statics.generateUniqueCode = async function(length = 16) {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let code;
  let exists = true;
  
  while (exists) {
    code = '';
    for (let i = 0; i < length; i++) {
      code += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    // Adiciona hífens para melhor legibilidade (formato: XXXX-XXXX-XXXX-XXXX)
    code = code.match(/.{1,4}/g).join('-');
    
    exists = await this.findOne({ code });
  }
  
  return code;
};

export default mongoose.models.Gift || mongoose.model("Gift", GiftSchema);

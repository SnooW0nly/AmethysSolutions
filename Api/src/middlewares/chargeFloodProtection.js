/**
 * Middleware de proteção contra flood na criação de cobranças
 * Previne criação excessiva de cobranças PIX
 */

import Payment from "../database/models/Payment.js";

// Cache de última criação por usuário (para cooldown)
const lastChargeCreation = new Map();

// Limpa cache antigo periodicamente
setInterval(() => {
  const now = Date.now();
  for (const [userId, timestamp] of lastChargeCreation.entries()) {
    // Remove entradas com mais de 5 minutos
    if (now - timestamp > 5 * 60 * 1000) {
      lastChargeCreation.delete(userId);
    }
  }
}, 60000); // Limpa a cada 1 minuto

/**
 * Configurações de proteção contra flood
 */
const FLOOD_PROTECTION_CONFIG = {
  // Cooldown mínimo entre criações (30 segundos)
  cooldownMs: 30 * 1000,
  
  // Máximo de cobranças pendentes por usuário
  maxPendingCharges: 3,
  
  // Janela de tempo para verificar cobranças recentes (5 minutos)
  recentWindowMs: 5 * 60 * 1000,
  
  // Máximo de cobranças criadas na janela de tempo
  maxChargesInWindow: 5,
};

/**
 * Middleware de proteção contra flood na criação de cobranças
 */
export async function chargeFloodProtection(req, res, next) {
  try {
    const userId = req.user?._id;
    
    if (!userId) {
      return res.status(401).json({
        success: false,
        error: "Usuário não autenticado",
      });
    }

    const userIdStr = String(userId);
    const now = Date.now();

    // 1. Verifica cooldown (tempo mínimo entre criações)
    const lastCreation = lastChargeCreation.get(userIdStr);
    if (lastCreation) {
      const timeSinceLastCreation = now - lastCreation;
      if (timeSinceLastCreation < FLOOD_PROTECTION_CONFIG.cooldownMs) {
        const remainingSeconds = Math.ceil(
          (FLOOD_PROTECTION_CONFIG.cooldownMs - timeSinceLastCreation) / 1000
        );
        
        console.warn(
          `[FLOOD PROTECTION] Cooldown ativo para usuário ${userIdStr}. ` +
          `Aguarde ${remainingSeconds} segundos.`
        );
        
        return res.status(429).json({
          success: false,
          error: "Aguarde antes de criar uma nova cobrança",
          retryAfter: remainingSeconds,
          message: `Você pode criar uma nova cobrança em ${remainingSeconds} segundo(s)`,
        });
      }
    }

    // 2. Verifica número de cobranças pendentes
    const pendingCount = await Payment.countDocuments({
      userId,
      status: { $ne: "approved" },
    });

    if (pendingCount >= FLOOD_PROTECTION_CONFIG.maxPendingCharges) {
      console.warn(
        `[FLOOD PROTECTION] Usuário ${userIdStr} excedeu limite de cobranças pendentes (${pendingCount})`
      );
      
      return res.status(429).json({
        success: false,
        error: "Limite de cobranças pendentes atingido",
        message: `Você já possui ${pendingCount} cobrança(s) pendente(s). ` +
                 `Aguarde a aprovação ou cancele uma antes de criar nova.`,
        pendingCount,
        maxPending: FLOOD_PROTECTION_CONFIG.maxPendingCharges,
      });
    }

    // 3. Verifica número de cobranças criadas recentemente (na janela de tempo)
    const recentWindowStart = new Date(now - FLOOD_PROTECTION_CONFIG.recentWindowMs);
    const recentChargesCount = await Payment.countDocuments({
      userId,
      createdAt: { $gte: recentWindowStart },
    });

    if (recentChargesCount >= FLOOD_PROTECTION_CONFIG.maxChargesInWindow) {
      console.warn(
        `[FLOOD PROTECTION] Usuário ${userIdStr} excedeu limite de cobranças na janela ` +
        `(${recentChargesCount} em ${FLOOD_PROTECTION_CONFIG.recentWindowMs / 1000}s)`
      );
      
      return res.status(429).json({
        success: false,
        error: "Muitas cobranças criadas recentemente",
        message: `Você criou muitas cobranças recentemente. ` +
                 `Aguarde alguns minutos antes de criar uma nova.`,
        recentCount: recentChargesCount,
        maxInWindow: FLOOD_PROTECTION_CONFIG.maxChargesInWindow,
      });
    }

    // Todas as verificações passaram
    // Registra timestamp da criação (será atualizado após criação bem-sucedida)
    req._chargeFloodProtection = {
      userId: userIdStr,
      timestamp: now,
    };

    next();
  } catch (error) {
    console.error("[FLOOD PROTECTION] Erro ao verificar proteção:", error);
    // Em caso de erro, permite a requisição (fail-open para não bloquear usuários legítimos)
    next();
  }
}

/**
 * Middleware para registrar criação bem-sucedida de cobrança
 * Deve ser chamado após a criação bem-sucedida
 */
export function registerChargeCreation(req, res, next) {
  if (req._chargeFloodProtection) {
    const { userId, timestamp } = req._chargeFloodProtection;
    lastChargeCreation.set(userId, timestamp);
  }
  next();
}

export default chargeFloodProtection;


import Coupon from "../database/models/Coupon.js";

/**
 * Valida um cupom com base no schema real de Coupon.
 * @param {string} code - Código do cupom
 * @param {number} planPrice - Preço atual considerado para compra
 * @returns {Promise<{valid: boolean, error?: string, coupon?: object}>}
 */
export async function validateCoupon(code, planPrice) {
  if (!code) return { valid: false, error: "Cupom não informado" };

  // Normaliza o código como o schema faz (trim, espaços -> '-', uppercase)
  const normalized = String(code).trim().replace(/\s+/g, "-").toUpperCase();

  const coupon = await Coupon.findOne({ name: normalized }).lean();
  if (!coupon) return { valid: false, error: "Cupom inválido" };

  // 1) Arquivado = inválido
  if (coupon.archived) {
    return { valid: false, error: "Cupom inválido" };
  }

  // 2) Validade por dias a partir da criação
  if (coupon.availableDays && coupon.createdAt) {
    const expiresAt = new Date(new Date(coupon.createdAt).getTime() + coupon.availableDays * 24 * 60 * 60 * 1000);
    if (expiresAt < new Date()) {
      return { valid: false, error: "Cupom inválido" };
    }
  }

  // 3) Limite de usos
  if (coupon.maxUses && (coupon.usedCount ?? 0) >= coupon.maxUses) {
    return { valid: false, error: "Cupom inválido" };
  }

  // 4) Valor mínimo do carrinho
  if (coupon.minCart && Number(planPrice) < Number(coupon.minCart)) {
    return { valid: false, error: "Cupom inválido" };
  }

  return { valid: true, coupon };
}

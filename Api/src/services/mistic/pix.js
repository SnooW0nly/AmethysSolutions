/**
 * Funções auxiliares PIX para Mistic Pay
 */

/**
 * Mapeia o status da Mistic para o status interno
 * @param {string} misticStatus - Status retornado pela Mistic
 * @returns {string} - Status interno: 'pending', 'approved', 'cancelled'
 * 
 * Status Mistic:
 * - PENDENTE: Transação pendente, aguardando pagamento
 * - COMPLETO: Transação aprovada e concluída com sucesso
 * - FALHA: Transação falhou ou foi rejeitada
 */
export function mapStatus(misticStatus) {
    if (!misticStatus) return "pending";

    const statusUpper = String(misticStatus).toUpperCase();

    // Status aprovado/completo
    if (
        statusUpper === "COMPLETO" || 
        statusUpper === "COMPLETED" || 
        statusUpper === "APPROVED" || 
        statusUpper === "PAID" || 
        statusUpper === "FINISHED"
    ) {
        return "approved";
    }

    // Status falha/cancelado
    if (statusUpper === "FALHA" || statusUpper === "FAILED" || statusUpper === "CANCELLED" || statusUpper === "CANCELED") {
        return "cancelled";
    }

    // Status pendente (PENDENTE ou qualquer outro)
    return "pending";
}

import { randomBytes } from "crypto";

/**
 * Gera um ID público curto e único para o transcript
 * Formato: 8 caracteres alfanuméricos (ex: "a3f9bx2k")
 */
export function generatePublicId(length = 8) {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  const bytes = randomBytes(length);
  let result = "";
  for (let i = 0; i < length; i++) {
    result += chars[bytes[i] % chars.length];
  }
  return result;
}

/**
 * Calcula a data de expiração com base em dias
 * @param {number} days - Número de dias até expirar
 * @returns {Date}
 */
export function getExpirationDate(days = 3) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date;
}

/**
 * Extrai metadados básicos do HTML do transcript
 * @param {string} html - Conteúdo HTML do transcript
 * @returns {{ messageCount: number, participantCount: number }}
 */
export function extractTranscriptMeta(html) {
  let messageCount = 0;
  let participantCount = 0;

  try {
    // Tenta extrair contagem de mensagens
    const msgMatch = html.match(/(\d+)\s*mensagens?/i) || html.match(/(\d+)\s*messages?/i);
    if (msgMatch) messageCount = parseInt(msgMatch[1]);

    // Tenta extrair contagem de participantes
    const partMatch = html.match(/(\d+)\s*participantes?/i) || html.match(/(\d+)\s*participants?/i);
    if (partMatch) participantCount = parseInt(partMatch[1]);
  } catch {
    // silently fail
  }

  return { messageCount, participantCount };
}
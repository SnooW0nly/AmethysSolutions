/**
 * Serviço de email usando Nodemailer
 */

import nodemailer from "nodemailer";

function createTransporter() {
  const user = process.env.MAIL_USER;
  const pass = process.env.MAIL_PASS;

  if (!user || !pass) {
    throw new Error("MAIL_USER e MAIL_PASS são obrigatórios no .env");
  }

  return nodemailer.createTransport({
    service: "gmail",
    auth: { user, pass },
  });
}

/**
 * Envia email usando Nodemailer
 * @param {object} params
 * @param {string} params.to - Destinatário
 * @param {string} params.subject - Assunto
 * @param {string} params.html - Conteúdo HTML
 * @param {string} params.text - Conteúdo texto (opcional)
 * @param {string} params.replyTo - Reply-to (opcional)
 * @returns {Promise<{id: string}>}
 */
export async function sendMail({ to, subject, html, text, replyTo }) {
  if (!to || !subject || (!html && !text)) {
    throw new Error("Parâmetros inválidos: 'to', 'subject' e 'html' ou 'text' são obrigatórios");
  }

  const transporter = createTransporter();

  const fromName = process.env.EMAIL_FROM_NAME || "Vision Applications";
  const fromEmail = process.env.MAIL_USER;

  try {
    const info = await transporter.sendMail({
      from: `"${fromName}" <${fromEmail}>`,
      to: Array.isArray(to) ? to.join(", ") : to,
      subject,
      html,
      text,
      replyTo,
    });

    console.log(`[NODEMAILER] Email enviado com sucesso. ID: ${info.messageId}`);
    return { id: info.messageId };
  } catch (error) {
    console.error("[NODEMAILER] Erro ao enviar email:", error.message);
    throw error;
  }
}

/**
 * Verifica se a configuração do transporte está correta
 */
export async function verifyTransport() {
  const transporter = createTransporter();
  await transporter.verify();
  console.log("[NODEMAILER] Configuração verificada com sucesso.");
  return true;
}
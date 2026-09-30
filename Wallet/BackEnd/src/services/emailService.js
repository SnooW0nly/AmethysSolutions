import { Resend } from "resend";
import nodemailer from "nodemailer";
import {
  NODE_ENV,
  RESEND_API_KEY, RESEND_FROM_EMAIL, EMAIL_FROM_NAME,
  EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASS, EMAIL_SECURE, EMAIL_FROM,
} from "../config/env.js";

const isDev = NODE_ENV === "development";

// ── Resend (produção) ──────────────────────────────────────────────────────
let resend = null;

function getResendClient() {
  if (resend) return resend;

  if (!RESEND_API_KEY)  throw new Error("[EMAIL] ❌ RESEND_API_KEY não configurada.");
  if (!RESEND_FROM_EMAIL) throw new Error("[EMAIL] ❌ RESEND_FROM_EMAIL não configurada.");

  resend = new Resend(RESEND_API_KEY);
  console.log(`[EMAIL] ✓ Resend inicializado (from: ${RESEND_FROM_EMAIL})`);
  return resend;
}

// ── Nodemailer (desenvolvimento) ───────────────────────────────────────────
let devTransporter = null;

async function getNodemailerTransport() {
  if (devTransporter) return devTransporter;

  if (EMAIL_HOST && EMAIL_USER) {
    // SMTP configurado no .env
    devTransporter = nodemailer.createTransport({
      host: EMAIL_HOST,
      port: EMAIL_PORT,
      secure: EMAIL_SECURE,
      auth: { user: EMAIL_USER, pass: EMAIL_PASS },
    });
    console.log(`[EMAIL-DEV] ✓ Nodemailer via SMTP (${EMAIL_HOST}:${EMAIL_PORT})`);
  } else {
    // Sem SMTP configurado → Ethereal (catch-all de teste)
    const testAccount = await nodemailer.createTestAccount();
    devTransporter = nodemailer.createTransport({
      host: "smtp.ethereal.email",
      port: 587,
      secure: false,
      auth: { user: testAccount.user, pass: testAccount.pass },
    });
    console.log(`[EMAIL-DEV] ✓ Nodemailer via Ethereal (user: ${testAccount.user})`);
  }

  return devTransporter;
}

export function generateVerificationCode() {
  const code = Math.floor(100000 + Math.random() * 900000).toString();
  console.log(`[EMAIL] 🔢 Código gerado: ${code}`);
  return code;
}

async function sendEmail({ to, subject, html }) {
  console.log(`[EMAIL] 📤 Enviando para: ${to} | Assunto: ${subject} | Modo: ${isDev ? "DEV (Nodemailer)" : "PROD (Resend)"}`);

  if (isDev) {
    // ── Desenvolvimento: Nodemailer ────────────────────────────────────────
    try {
      const transport = await getNodemailerTransport();
      const fromAddr = EMAIL_FROM
        ? `${EMAIL_FROM_NAME} <${EMAIL_FROM}>`
        : `${EMAIL_FROM_NAME} <dev@amethys.local>`;

      const info = await transport.sendMail({ from: fromAddr, to, subject, html });
      const previewUrl = nodemailer.getTestMessageUrl(info);

      console.log(`[EMAIL-DEV] ✓ Enviado (messageId: ${info.messageId})`);
      if (previewUrl) console.log(`[EMAIL-DEV] 🔗 Preview: ${previewUrl}`);
      return true;
    } catch (err) {
      console.error("[EMAIL-DEV] ❌ Falha ao enviar via Nodemailer:", err.message);
      return false;
    }
  }

  // ── Produção: Resend ─────────────────────────────────────────────────────
  let client;
  try {
    client = getResendClient();
  } catch (err) {
    console.error("[EMAIL] ❌ Falha ao inicializar Resend:", err.message);
    return false;
  }

  try {
    const { data, error } = await client.emails.send({
      from: `${EMAIL_FROM_NAME} <${RESEND_FROM_EMAIL}>`,
      to: [to],
      subject,
      html,
    });

    if (error) {
      console.error("[EMAIL] ❌ Erro Resend:", JSON.stringify(error, null, 2));
      return false;
    }

    console.log(`[EMAIL] ✓ Enviado via Resend para ${to} (ID: ${data?.id})`);
    return true;
  } catch (err) {
    console.error("[EMAIL] ❌ Exceção Resend:", err.message);
    return false;
  }
}

function buildCodeEmail(title, description, code, extraWarning = "") {
  console.log(`[EMAIL] 🏗️ Montando template HTML: "${title}"`);
  return `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #333;">${title}</h2>
      <p>Olá,</p>
      <p>${description}</p>
      <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
        <h1 style="color: #ff6400; font-size: 32px; letter-spacing: 5px; margin: 0;">${code}</h1>
      </div>
      <p>Este código expira em 10 minutos.</p>
      ${extraWarning ? `<p>${extraWarning}</p>` : "<p>Se você não solicitou este código, ignore este e-mail.</p>"}
      <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
      <p style="color: #666; font-size: 12px;">Amethys Wallet - Sistema de Autenticação</p>
    </div>
  `;
}

export async function sendVerificationCode(email, code) {
  console.log(`[EMAIL] 🔐 sendVerificationCode chamado → email: ${email}, code: ${code}`);
  return sendEmail({
    to: email,
    subject: "Código de Verificação - Amethys Wallet",
    html: buildCodeEmail("Código de Verificação", "Seu código de verificação para fazer login é:", code),
  });
}

export async function sendSignupVerificationCode(email, code) {
  console.log(`[EMAIL] 📝 sendSignupVerificationCode chamado → email: ${email}, code: ${code}`);
  return sendEmail({
    to: email,
    subject: "Código de Verificação - Cadastro Amethys Wallet",
    html: buildCodeEmail("Bem-vindo ao Amethys Wallet!", "Seu código de verificação para completar o cadastro é:", code),
  });
}

export async function sendTransferVerificationCode(email, code, amount) {
  console.log(`[EMAIL] 💸 sendTransferVerificationCode chamado → email: ${email}, code: ${code}, amount: ${amount}`);

  const amountFormatted = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(amount);

  console.log(`[EMAIL] 💸 Valor formatado: ${amountFormatted}`);

  return sendEmail({
    to: email,
    subject: "Código de Verificação - Transferência Amethys Wallet",
    html: buildCodeEmail(
      "Código de Verificação para Transferência",
      `Uma transferência de <strong>${amountFormatted}</strong> foi solicitada. Para confirmar, use o código abaixo:`,
      code,
      "<strong>Se você não solicitou esta transferência, ignore este e-mail e entre em contato conosco imediatamente.</strong>"
    ),
  });
}

// Pré-aquecer o cliente adequado ao importar o módulo
if (isDev) {
  getNodemailerTransport().catch(() => {});
} else {
  try { getResendClient(); } catch { /* aviso já logado acima */ }
}
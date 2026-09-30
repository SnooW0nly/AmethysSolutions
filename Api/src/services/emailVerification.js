/**
 * Serviço de verificação por email
 */

import crypto from "crypto";
import VerificationCode from "../database/models/VerificationCode.js";
import User from "../database/models/User.js";
import { sendMail } from "./mail/mailService.js";

/**
 * Gera código de verificação de 6 dígitos
 */
function generateCode() {
  return crypto.randomInt(100000, 999999).toString();
}

/**
 * Verifica rate limiting para envio de códigos
 * Limites:
 * - Máximo 3 códigos por hora por email
 * - Máximo 5 códigos por hora por IP
 */
async function checkRateLimit(email, ip) {
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);

  // Verifica códigos enviados para este email na última hora
  const emailCount = await VerificationCode.countDocuments({
    email,
    createdAt: { $gte: oneHourAgo },
  });

  if (emailCount >= 3) {
    return {
      allowed: false,
      reason: "Muitos códigos solicitados para este email. Tente novamente em 1 hora.",
    };
  }

  // Verifica códigos enviados deste IP na última hora
  if (ip) {
    const ipCount = await VerificationCode.countDocuments({
      ip,
      createdAt: { $gte: oneHourAgo },
    });

    if (ipCount >= 5) {
      return {
        allowed: false,
        reason: "Muitos códigos solicitados deste IP. Tente novamente em 1 hora.",
      };
    }
  }

  return { allowed: true };
}

/**
 * Envia código de verificação por email
 */
export async function sendVerificationCode(email, ip, userAgent) {
  try {
    // Normaliza email
    email = email.toLowerCase().trim();

    // Verifica se o email existe no sistema
    const user = await User.findOne({ email });
    if (!user) {
      // Por segurança, não revela se o email existe ou não
      return {
        success: true,
        message: "Se o email existir no sistema, um código foi enviado.",
      };
    }

    // Verifica rate limiting
    const rateLimit = await checkRateLimit(email, ip);
    if (!rateLimit.allowed) {
      return {
        success: false,
        message: rateLimit.reason,
      };
    }

    // Invalida códigos anteriores não verificados
    await VerificationCode.updateMany(
      { email, verified: false },
      { $set: { verified: true } } // Marca como verificado para invalidar
    );

    // Gera novo código
    const code = generateCode();
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutos

    // Salva código no banco
    await VerificationCode.create({
      email,
      code,
      expiresAt,
      ip,
      userAgent,
    });

    // Envia email usando Resend via mailService
    const htmlContent = `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Código de Verificação</title>
  <style>img{max-width:100%;height:auto}</style>
  </head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f3f4f6;">
    <tr>
      <td align="center" style="padding:24px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="padding:24px 24px 12px 24px;background:#111827;">
              <table role="presentation" width="100%">
                <tr>
                  <td align="left">
                    <div style="color:#ffffff;font-weight:700;font-size:20px;line-height:1;">Vision Applications</div>
                    <div style="color:#9ca3af;font-size:12px;line-height:1.4;margin-top:4px;">Verificação de conta</div>
                  </td>
                  <td align="right">
                    <span style="display:inline-block;padding:6px 10px;border-radius:999px;background:#4f46e5;color:#ffffff;font-weight:600;font-size:12px;">VERIFICAÇÃO</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:16px 24px 16px 24px;background:#111827;border-top:1px solid #1f2937;">
              <div style="color:#ffffff;font-size:18px;font-weight:700;line-height:1.3;">Código de verificação</div>
              <div style="color:#9ca3af;font-size:12px;margin-top:4px;">Válido por 10 minutos</div>
            </td>
          </tr>

          <tr>
            <td style="padding:24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="padding:0;">
                    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:16px;text-align:center;">
                      <div style="color:#6b7280;font-size:12px;letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px;">Seu código</div>
                      <div style="font-size:28px;color:#111827;font-weight:800;letter-spacing:6px;">${code}</div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="padding-top:16px;font-size:14px;color:#374151;">
                    Use este código para acessar sua conta com segurança. Por favor:
                    <ul style="margin:8px 0 0 18px;padding:0;">
                      <li style="margin:6px 0;">Não compartilhe este código com ninguém</li>
                      <li style="margin:6px 0;">Nossa equipe nunca solicitará seu código</li>
                      <li style="margin:6px 0;">Utilize apenas no site oficial</li>
                    </ul>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td align="center" style="padding:18px;background:#111827;">
              <div style="color:#9ca3af;font-size:12px;line-height:1.5;">
                © ${new Date().getFullYear()} Vision Applications Ltda — Todos os direitos reservados<br>
                CNPJ ${process.env.CNPJ}
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

    await sendMail({
      to: email,
      subject: "Seu código de verificação",
      html: htmlContent,
      text: `Seu código de verificação é: ${code}\n\nEste código é válido por 10 minutos.\n\nSe você não solicitou este código, ignore este email.`,
    });

    console.log(`[EMAIL VERIFICATION] Código enviado para ${email}`);

    return {
      success: true,
      message: "Código de verificação enviado para seu email.",
    };
  } catch (error) {
    console.error("[EMAIL VERIFICATION] Erro ao enviar código:", error);
    return {
      success: false,
      message: "Erro ao enviar código de verificação. Tente novamente.",
    };
  }
}

/**
 * Verifica código de verificação
 */
export async function verifyCode(email, code) {
  try {
    email = email.toLowerCase().trim();

    // Busca o código mais recente não verificado do email (para rastrear tentativas)
    const latestCode = await VerificationCode.findOne({
      email,
      verified: false,
      expiresAt: { $gt: new Date() },
    }).sort({ createdAt: -1 });

    // Se não existe código válido, retorna erro
    if (!latestCode) {
      return {
        success: false,
        message: "Código inválido ou expirado.",
      };
    }

    // Verifica se já atingiu o limite de tentativas
    if (latestCode.attempts >= 5) {
      return {
        success: false,
        message: "Muitas tentativas. Solicite um novo código.",
      };
    }

    // Verifica se o código corresponde
    if (latestCode.code !== code) {
      // Incrementa tentativas para código incorreto
      latestCode.attempts += 1;
      await latestCode.save();

      // Verifica novamente se atingiu o limite após incrementar
      if (latestCode.attempts >= 5) {
        return {
          success: false,
          message: "Muitas tentativas. Solicite um novo código.",
        };
      }

      return {
        success: false,
        message: "Código inválido ou expirado.",
      };
    }

    // Código correto - marca como verificado
    latestCode.verified = true;
    await latestCode.save();

    // Busca usuário
    const user = await User.findOne({ email });
    if (!user) {
      return {
        success: false,
        message: "Usuário não encontrado.",
      };
    }

    console.log(`[EMAIL VERIFICATION] Código verificado para ${email}`);

    return {
      success: true,
      user,
    };
  } catch (error) {
    console.error("[EMAIL VERIFICATION] Erro ao verificar código:", error);
    return {
      success: false,
      message: "Erro ao verificar código. Tente novamente.",
    };
  }
}

/**
 * Limpa códigos expirados (executado periodicamente)
 */
export async function cleanExpiredCodes() {
  try {
    const result = await VerificationCode.deleteMany({
      expiresAt: { $lt: new Date() },
    });

    if (result.deletedCount > 0) {
      console.log(`[EMAIL VERIFICATION] ${result.deletedCount} códigos expirados removidos`);
    }
  } catch (error) {
    console.error("[EMAIL VERIFICATION] Erro ao limpar códigos:", error);
  }
}

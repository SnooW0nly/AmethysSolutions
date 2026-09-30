/**
 * Serviço de transferência de posse de bots
 */

import crypto from "crypto";
import { Client, GatewayIntentBits, Partials } from "discord.js";
import Application from "../database/models/Application.js";
import BotConfig from "../database/models/BotConfig.js";
import OwnerTransfer from "../database/models/OwnerTransfer.js";
import User from "../database/models/User.js";
import { sendMail } from "./mail/mailService.js";

/**
 * Gera código de verificação de 6 dígitos
 */
function generateCode() {
  return crypto.randomInt(100000, 999999).toString();
}

/**
 * Inicia processo de transferência de posse
 */
export async function initiateOwnerTransfer(applicationId, userId, newOwnerDiscordId, ip, userAgent) {
  try {
    // Busca a aplicação
    const application = await Application.findOne({ _id: applicationId, userId });
    if (!application) {
      return { success: false, message: "Aplicação não encontrada" };
    }

    // Busca o usuário atual
    const currentUser = await User.findById(userId);
    if (!currentUser || !currentUser.email) {
      return { success: false, message: "Email do usuário não configurado" };
    }

    // Valida Discord ID do novo dono
    if (!/^\d{17,19}$/.test(newOwnerDiscordId)) {
      return { success: false, message: "Discord ID inválido" };
    }

    // Verifica se o novo dono é diferente do atual
    const currentOwnerDiscordId = currentUser.discordId || application.bot?.owner;
    if (newOwnerDiscordId === currentOwnerDiscordId) {
      return { success: false, message: "O novo dono não pode ser o mesmo que o atual" };
    }

    // Cancela transferências anteriores pendentes
    await OwnerTransfer.updateMany(
      { applicationId, status: "pending" },
      { $set: { status: "cancelled" } }
    );

    // Cria nova transferência
    const code = generateCode();
    const transfer = await OwnerTransfer.create({
      applicationId,
      botID: application.botID,
      fromUserId: userId,
      fromDiscordId: currentOwnerDiscordId,
      toDiscordId: newOwnerDiscordId,
      verificationCode: code,
      ip,
      userAgent,
    });

    // Envia email com código usando Resend
    const htmlContent = `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transferência de Posse</title>
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
                    <div style="color:#ffffff;font-weight:700;font-size:20px;">Vision Applications</div>
                    <div style="color:#9ca3af;font-size:12px;margin-top:4px;">Transferência de Posse</div>
                  </td>
                  <td align="right">
                    <span style="display:inline-block;padding:6px 10px;border-radius:999px;background:#ef4444;color:#ffffff;font-weight:600;font-size:12px;">IMPORTANTE</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:16px 24px;background:#111827;border-top:1px solid #1f2937;">
              <div style="color:#ffffff;font-size:18px;font-weight:700;">Confirmação de Transferência</div>
              <div style="color:#9ca3af;font-size:12px;margin-top:4px;">Válido por 30 minutos</div>
            </td>
          </tr>

          <tr>
            <td style="padding:24px;">
              <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:16px;margin-bottom:20px;">
                <div style="color:#dc2626;font-weight:600;margin-bottom:8px;">⚠️ Ação Sensível</div>
                <div style="color:#7f1d1d;font-size:14px;">
                  Você está prestes a transferir a posse do bot <strong>${application.name}</strong> para outro usuário.
                </div>
              </div>

              <div style="margin-bottom:20px;">
                <p style="color:#374151;font-size:14px;margin:8px 0;">
                  <strong>Bot:</strong> ${application.name}<br>
                  <strong>Novo Dono (Discord ID):</strong> ${newOwnerDiscordId}
                </p>
              </div>

              <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:16px;text-align:center;margin-bottom:20px;">
                <div style="color:#6b7280;font-size:12px;text-transform:uppercase;margin-bottom:6px;">Código de Confirmação</div>
                <div style="font-size:28px;color:#111827;font-weight:800;letter-spacing:6px;">${code}</div>
              </div>

              <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;padding:16px;">
                <div style="color:#92400e;font-size:14px;">
                  <strong>Após a confirmação:</strong>
                  <ul style="margin:8px 0 0 0;padding-left:20px;">
                    <li>Você perderá acesso total ao bot</li>
                    <li>O novo dono terá controle completo</li>
                    <li>Esta ação não pode ser desfeita</li>
                  </ul>
                </div>
              </div>

              <div style="margin-top:20px;padding-top:20px;border-top:1px solid #e5e7eb;">
                <p style="color:#6b7280;font-size:12px;text-align:center;">
                  Se você não solicitou esta transferência, ignore este email e considere alterar sua senha.
                </p>
              </div>
            </td>
          </tr>

          <tr>
            <td align="center" style="padding:18px;background:#111827;">
              <div style="color:#9ca3af;font-size:12px;">
                © ${new Date().getFullYear()} Vision Applications - Todos os direitos reservados
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
      to: currentUser.email,
      subject: "Confirmação de Transferência de Posse",
      html: htmlContent,
    });

    console.log(`[OWNER TRANSFER] Código enviado para ${currentUser.email} - Transfer ID: ${transfer._id}`);

    return {
      success: true,
      transferId: transfer._id,
      message: "Código de confirmação enviado para seu email",
    };
  } catch (error) {
    console.error("[OWNER TRANSFER] Erro ao iniciar transferência:", error);
    return {
      success: false,
      message: "Erro ao iniciar transferência. Tente novamente.",
    };
  }
}

/**
 * Confirma transferência com código
 */
export async function confirmOwnerTransfer(transferId, code, userId) {
  try {
    // Busca a transferência
    const transfer = await OwnerTransfer.findOne({
      _id: transferId,
      fromUserId: userId,
      status: "pending",
      expiresAt: { $gt: new Date() },
    });

    if (!transfer) {
      return { success: false, message: "Transferência não encontrada ou expirada" };
    }

    // Verifica tentativas
    if (transfer.attempts >= 5) {
      await OwnerTransfer.updateOne(
        { _id: transferId },
        { $set: { status: "cancelled" } }
      );
      return { success: false, message: "Muitas tentativas. Transferência cancelada." };
    }

    // Verifica código
    if (transfer.verificationCode !== code) {
      await OwnerTransfer.updateOne(
        { _id: transferId },
        { $inc: { attempts: 1 } }
      );
      return { success: false, message: "Código inválido" };
    }

    // Marca como confirmado
    transfer.status = "confirmed";
    transfer.confirmedAt = new Date();
    await transfer.save();

    // Executa a transferência
    const result = await executeOwnerTransfer(transfer);

    if (result.success) {
      transfer.status = "completed";
      transfer.completedAt = new Date();
      await transfer.save();
    }

    return result;
  } catch (error) {
    console.error("[OWNER TRANSFER] Erro ao confirmar transferência:", error);
    return {
      success: false,
      message: "Erro ao confirmar transferência. Tente novamente.",
    };
  }
}

/**
 * Executa a transferência de posse
 */
async function executeOwnerTransfer(transfer) {
  try {
    const { applicationId, toDiscordId, botID } = transfer;

    // Busca ou cria o usuário do novo dono
    let newOwnerUser = await User.findOne({ discordId: toDiscordId });

    if (!newOwnerUser) {
      // Se o usuário não existe, cria um registro básico
      // Ele será completado quando fizer login
      newOwnerUser = await User.create({
        discordId: toDiscordId,
        username: `user_${toDiscordId}`,
        globalName: `User ${toDiscordId}`,
      });
      console.log(`[OWNER TRANSFER] Novo usuário criado: ${newOwnerUser._id}`);
    }

    // Atualiza Application - IMPORTANTE: muda o userId também
    const updateResult = await Application.updateOne(
      { _id: applicationId },
      {
        $set: {
          userId: newOwnerUser._id, // Transfere a propriedade real
          "bot.owner": toDiscordId,
          "bot.perms": [toDiscordId], // Reseta perms para apenas o novo dono
        },
      }
    );

    if (updateResult.modifiedCount === 0) {
      return { success: false, message: "Erro ao atualizar aplicação" };
    }

    // Atualiza BotConfig
    if (botID) {
      await BotConfig.updateOne(
        { botID },
        {
          $set: {
            "bot.owner": toDiscordId,
            "bot.perms": [toDiscordId],
          },
        }
      );
    }

    // Busca a aplicação atualizada para notificar o novo dono
    const application = await Application.findById(applicationId);

    // Envia notificação ao novo dono via Discord
    await notifyNewOwner(application, toDiscordId, botID);

    console.log(`[OWNER TRANSFER] Transferência concluída - App: ${applicationId}, Novo dono: ${toDiscordId}, Novo userId: ${newOwnerUser._id}`);

    return {
      success: true,
      message: "Transferência concluída com sucesso",
      newOwner: toDiscordId,
      newUserId: newOwnerUser._id,
    };
  } catch (error) {
    console.error("[OWNER TRANSFER] Erro ao executar transferência:", error);
    return {
      success: false,
      message: "Erro ao executar transferência",
    };
  }
}

/**
 * Notifica o novo dono via Discord
 */
async function notifyNewOwner(application, newOwnerDiscordId, botID) {
  return new Promise(async (resolve) => {
    let client;
    let timeout;

    try {
      // Busca o BotConfig para pegar o token
      const botConfig = await BotConfig.findOne({ botID });
      if (!botConfig || !botConfig.bot?.token) {
        console.log(`[OWNER TRANSFER] Token não encontrado para notificar novo dono`);
        return resolve();
      }

      client = new Client({
        intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages],
        partials: [Partials.Channel],
      });

      // Login com o bot
      await client.login(botConfig.bot.token);

      // Espera o bot estar pronto
      await new Promise((res, rej) => {
        timeout = setTimeout(() => rej(new Error("Timeout")), 10000);
        client.once("ready", () => {
          clearTimeout(timeout);
          res();
        });
      });

      // Link para o dashboard
      const dashboardLink = `${process.env.FRONTEND_URL}/dashboard/app/${application._id}/overview`;

      // Envia DM ao novo dono
      const user = await client.users.fetch(newOwnerDiscordId);
      if (user) {
        await user.send({
          components: [
            {
              type: 17,
              accent_color: null,
              spoiler: false,
              components: [
                {
                  type: 10,
                  content: `Parabéns <@${user.id}>!`,
                },
              ],
            },
            {
              type: 17,
              accent_color: 5763719, // Verde
              spoiler: false,
              components: [
                {
                  type: 10,
                  content: "# TRANSFERÊNCIA RECEBIDA",
                },
                {
                  type: 14,
                  divider: true,
                  spacing: 1,
                },
                {
                  type: 10,
                  content: `Você agora é o novo proprietário do bot **${application.name}**!\n\n**Informações:**\n• ID da Aplicação: \`${application._id}\`\n• Plano: **${application.plan?.name || "N/A"}**\n• Expira em: <t:${Math.floor(new Date(application.expiresAt).getTime() / 1000)}:D>`,
                },
                {
                  type: 14,
                  divider: true,
                  spacing: 1,
                },
                {
                  type: 10,
                  content: "**Como novo proprietário, você tem:**\n• Controle total sobre o bot\n• Acesso ao painel de controle\n• Responsabilidade pelos pagamentos futuros\n• Poder de configurar permissões",
                },
                {
                  type: 14,
                  divider: true,
                  spacing: 1,
                },
                {
                  type: 10,
                  content: "Acesse o painel de controle para gerenciar seu novo bot:",
                },
                {
                  type: 1,
                  components: [
                    {
                      type: 2,
                      style: 5,
                      label: "Acessar Dashboard",
                      disabled: false,
                      url: dashboardLink,
                    },
                  ],
                },
              ],
            },
          ],
          flags: 32768,
        });

        console.log(`[OWNER TRANSFER] Notificação enviada ao novo dono: ${newOwnerDiscordId}`);
      }
    } catch (e) {
      console.error(`[OWNER TRANSFER] Erro ao notificar novo dono:`, e.message);
    } finally {
      if (client && client.destroy) {
        await client.destroy();
      }
      resolve();
    }
  });
}

/**
 * Cancela transferência pendente
 */
export async function cancelOwnerTransfer(transferId, userId) {
  try {
    const result = await OwnerTransfer.updateOne(
      {
        _id: transferId,
        fromUserId: userId,
        status: "pending",
      },
      { $set: { status: "cancelled" } }
    );

    if (result.modifiedCount === 0) {
      return { success: false, message: "Transferência não encontrada" };
    }

    return { success: true, message: "Transferência cancelada" };
  } catch (error) {
    console.error("[OWNER TRANSFER] Erro ao cancelar:", error);
    return { success: false, message: "Erro ao cancelar transferência" };
  }
}

/**
 * Limpa transferências expiradas
 */
export async function cleanExpiredTransfers() {
  try {
    const result = await OwnerTransfer.updateMany(
      {
        status: "pending",
        expiresAt: { $lt: new Date() },
      },
      { $set: { status: "expired" } }
    );

    if (result.modifiedCount > 0) {
      console.log(`[OWNER TRANSFER] ${result.modifiedCount} transferências expiradas`);
    }
  } catch (error) {
    console.error("[OWNER TRANSFER] Erro ao limpar transferências:", error);
  }
}

export default {
  initiateOwnerTransfer,
  confirmOwnerTransfer,
  cancelOwnerTransfer,
  cleanExpiredTransfers,
};

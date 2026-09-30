/**
 * Serviço de verificação e deleção de aplicações free inativas
 * Um app free é considerado inativo se não for ligado por 30 dias
 * Fluxo: 30 dias inativo → aviso por DM → 3 dias → deleção
 */

import Application from "../../database/models/Application.js";
import User from "../../database/models/User.js";
import { connectToUserBot } from "../../database/bots.js";
import discloudService from "../discloudService.js";

const INACTIVITY_DAYS = 30;
const WARNING_GRACE_DAYS = 3;

/**
 * Deleta uma aplicação na Discloud
 */
async function deleteDiscloudApp(appId) {
  try {
    if (!appId) return false;

    const result = await discloudService.deleteApp(appId);

    if (!result.success) {
      console.error(`[INACTIVITY SERVICE] Erro ao deletar app ${appId}:`, result.error);
      return false;
    }

    console.log(`[INACTIVITY SERVICE] App ${appId} deletado com sucesso`);
    return true;
  } catch (error) {
    console.error(`[INACTIVITY SERVICE] Erro ao deletar app ${appId}:`, error.message);
    return false;
  }
}

/**
 * Verifica o status de uma aplicação na Discloud
 * Retorna true se o bot está online/running
 */
async function isDiscloudAppRunning(appId) {
  try {
    if (!appId) return false;

    const result = await discloudService.getAppStatus(appId);

    if (!result.success) return false;

    const isRunning = result.status?.running;

    if (isRunning) {
      console.log(`[INACTIVITY SERVICE] App ${appId} está online - considerando como ativo`);
    }

    return isRunning;
  } catch (error) {
    console.error(`[INACTIVITY SERVICE] Erro ao verificar status ${appId}:`, error.message);
    return false;
  }
}

/**
 * Envia DM avisando sobre inatividade
 */
async function sendInactivityWarningDM(application, user) {
  try {
    const botToken = application.bot?.token;
    if (!botToken) {
      console.log(`[INACTIVITY SERVICE] Bot sem token configurado para ${application._id}`);
      return false;
    }

    const discordUserId = user.discordId;
    if (!discordUserId) {
      console.log(`[INACTIVITY SERVICE] Usuário sem Discord ID: ${user._id}`);
      return false;
    }

    const bot = await connectToUserBot(botToken);
    if (!bot) {
      console.error(`[INACTIVITY SERVICE] Erro ao conectar bot para ${application._id}`);
      return false;
    }

    const dmChannel = await bot.users.createDM(discordUserId);
    const deleteAt = Math.floor((Date.now() + WARNING_GRACE_DAYS * 24 * 60 * 60 * 1000) / 1000);

    await dmChannel.send({
      components: [
        {
          type: 17,
          accent_color: null,
          spoiler: false,
          components: [{ type: 10, content: `Olá <@${discordUserId}>!` }],
        },
        {
          type: 17,
          accent_color: 16776960,
          spoiler: false,
          components: [
            { type: 10, content: "# AVISO DE INATIVIDADE" },
            { type: 14, divider: true, spacing: 1 },
            {
              type: 10,
              content: `Sua aplicação **${application.name}** (Plano Free) está **inativa há mais de ${INACTIVITY_DAYS} dias**.\n\nPlano: **${application.plan?.name || "Vision Free"}**\nID da Aplicação: \`${application._id}\``,
            },
            { type: 14, divider: false, spacing: 1 },
            {
              type: 10,
              content: `**Ação necessária:**\n• Ligue seu bot nos próximos **${WARNING_GRACE_DAYS} dias** para evitar a exclusão\n• Data limite: <t:${deleteAt}:D> (<t:${deleteAt}:R>)`,
            },
            { type: 14, divider: true, spacing: 1 },
            {
              type: 10,
              content: "Se não houver atividade, sua aplicação será **deletada permanentemente** após este prazo.\n-# Basta ligar o bot para cancelar a exclusão.",
            },
          ],
        },
      ],
      flags: 32768,
    });

    console.log(`[INACTIVITY SERVICE] DM de aviso enviada para usuário ${user._id}`);
    return true;
  } catch (error) {
    console.error(`[INACTIVITY SERVICE] Erro ao enviar DM de aviso:`, error.message);
    return false;
  }
}

/**
 * Envia DM notificando sobre deleção por inatividade
 */
async function sendDeletionDM(application, user) {
  try {
    const botToken = application.bot?.token;
    if (!botToken) return false;

    const discordUserId = user.discordId;
    if (!discordUserId) return false;

    const bot = await connectToUserBot(botToken);
    if (!bot) return false;

    const dmChannel = await bot.users.createDM(discordUserId);

    await dmChannel.send({
      components: [
        {
          type: 17,
          accent_color: 15158332,
          spoiler: false,
          components: [
            { type: 10, content: "# APLICAÇÃO EXCLUÍDA POR INATIVIDADE" },
            { type: 14, divider: true, spacing: 1 },
            {
              type: 10,
              content: `Sua aplicação **${application.name}** foi excluída por inatividade de mais de ${INACTIVITY_DAYS} dias.\n\nPlano: **${application.plan?.name || "Vision Free"}**\nID da Aplicação: \`${application._id}\``,
            },
            { type: 14, divider: true, spacing: 1 },
            {
              type: 10,
              content: "Você pode criar uma nova aplicação gratuita a qualquer momento em nosso site.\n-# Obrigado por usar a Vision!",
            },
          ],
        },
      ],
      flags: 32768,
    });

    console.log(`[INACTIVITY SERVICE] DM de deleção enviada para usuário ${user._id}`);
    return true;
  } catch (error) {
    console.error(`[INACTIVITY SERVICE] Erro ao enviar DM de deleção:`, error.message);
    return false;
  }
}

/**
 * Verifica e processa aplicações free inativas
 */
export async function checkInactiveFreePlans() {
  try {
    const now = new Date();
    const inactivityThreshold = new Date(now.getTime() - INACTIVITY_DAYS * 24 * 60 * 60 * 1000);
    const warningExpiredThreshold = new Date(now.getTime() - WARNING_GRACE_DAYS * 24 * 60 * 60 * 1000);

    const inactiveApps = await Application.find({
      isFree: true,
      isDeleted: false,
      lastStartedAt: { $lt: inactivityThreshold },
    }).populate("userId", "discordId");

    console.log(`[INACTIVITY SERVICE] Encontradas ${inactiveApps.length} aplicações free inativas`);

    for (const app of inactiveApps) {
      try {
        const appId = app.hosting?.appId;

        // Verifica se o bot está rodando na Discloud
        if (appId) {
          const isRunning = await isDiscloudAppRunning(appId);
          if (isRunning) {
            app.lastStartedAt = now;
            app.inactivityWarningSentAt = null;
            await app.save();
            console.log(`[INACTIVITY SERVICE] App ${app._id} está rodando - lastStartedAt atualizado`);
            continue;
          }
        }

        // Se ainda não recebeu aviso, envia agora
        if (!app.inactivityWarningSentAt) {
          const user = app.userId;
          if (user) await sendInactivityWarningDM(app, user);

          app.inactivityWarningSentAt = now;
          await app.save();
          console.log(`[INACTIVITY SERVICE] Aviso de inatividade enviado para app ${app._id}`);
          continue;
        }

        // Se já passou o período de graça, deleta
        if (app.inactivityWarningSentAt < warningExpiredThreshold) {
          const user = app.userId;

          if (appId) await deleteDiscloudApp(appId);
          if (user) await sendDeletionDM(app, user);

          app.isDeleted = true;
          app.deletedAt = now;
          await app.save();

          console.log(`[INACTIVITY SERVICE] App free ${app._id} deletado por inatividade`);
        }
      } catch (error) {
        console.error(`[INACTIVITY SERVICE] Erro ao processar app ${app._id}:`, error.message);
      }
    }

    console.log(`[INACTIVITY SERVICE] Verificação de inatividade concluída`);
  } catch (error) {
    console.error("[INACTIVITY SERVICE] Erro na verificação de inatividade:", error);
  }
}

/**
 * Inicia o serviço de inatividade (executado a cada 12 horas)
 */
export function startInactivityService() {
  console.log("[INACTIVITY SERVICE] Serviço de inatividade iniciado");
  checkInactiveFreePlans();
  setInterval(checkInactiveFreePlans, 12 * 60 * 60 * 1000);
}

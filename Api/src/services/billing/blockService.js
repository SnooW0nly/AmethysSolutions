import Application from "../../database/models/Application.js";
import User from "../../database/models/User.js";
import { connectToUserBot } from "../../database/bots.js";
import discloudService from "../discloudService.js";

async function stopDiscloudApp(appId) {
  try {
    if (!appId) return false;
    const result = await discloudService.stopApp(appId);
    if (!result.success) {
      console.error(`[BLOCK SERVICE] Erro ao parar app ${appId} na Discloud:`, result.error);
      return false;
    }
    console.log(`[BLOCK SERVICE] App ${appId} parado na Discloud com sucesso`);
    return true;
  } catch (error) {
    console.error(`[BLOCK SERVICE] Erro ao parar app ${appId}:`, error.message);
    return false;
  }
}

async function deleteDiscloudApp(appId) {
  try {
    if (!appId) return false;
    const result = await discloudService.deleteApp(appId);

    if (!result.success) {
      // Se o erro indicar que o app não existe, consideramos sucesso na deleção
      if (result.error && (result.error.includes("404") || result.error.toLowerCase().includes("not found"))) {
        console.log(`[BLOCK SERVICE] App ${appId} não encontrado na Discloud (já deletado ou nunca existiu)`);
        return true;
      }
      console.error(`[BLOCK SERVICE] Erro ao deletar app ${appId} na Discloud:`, result.error);
      return false;
    }

    console.log(`[BLOCK SERVICE] App ${appId} deletado na Discloud com sucesso`);
    return true;
  } catch (error) {
    console.error(`[BLOCK SERVICE] Erro ao deletar app ${appId}:`, error.message);
    return false;
  }
}

async function sendBlockDM(application, user) {
  try {
    const botToken = application.bot?.token;
    if (!botToken) return false;
    const discordUserId = user.discordId;
    if (!discordUserId) return false;
    const bot = await connectToUserBot(botToken);
    if (!bot) return false;
    const dmChannel = await bot.users.createDM(discordUserId);
    const blockedAt = Math.floor(new Date(application.blockedAt).getTime() / 1000);
    const deleteAt = Math.floor((new Date(application.blockedAt).getTime() + 7 * 24 * 60 * 60 * 1000) / 1000);
    const renewLink = `${process.env.FRONTEND_URL}/dashboard/invoices?renew=${application._id}`;
    await dmChannel.send({
      components: [
        { type: 17, accent_color: null, spoiler: false, components: [{ type: 10, content: `Olá senhor(a) <@${discordUserId}>!` }] },
        {
          type: 17, accent_color: 15158332, spoiler: false,
          components: [
            { type: 10, content: "# APLICAÇÃO BLOQUEADA" },
            { type: 14, divider: true, spacing: 1 },
            { type: 10, content: `Sua aplicação **${application.name}** foi bloqueada por falta de pagamento.\n\nPlano: **${application.plan.name}**\nID da Aplicação: \`${application._id}\`\nBloqueado em: <t:${blockedAt}:D>` },
            { type: 14, divider: false, spacing: 1 },
            { type: 10, content: `**Prazo para renovação:**\n• Você tem 7 dias para renovar sua assinatura\n• Após este prazo, a aplicação será deletada permanentemente\n• Data limite: <t:${deleteAt}:D> (<t:${deleteAt}:R>)` },
            { type: 14, divider: true, spacing: 1 },
            { type: 10, content: "Renove sua assinatura agora para reativar sua aplicação.\n-# Clique no botão abaixo para renovar. Se já renovou, ignore esta mensagem." },
            { type: 14, divider: true, spacing: 1 },
            { type: 1, components: [{ type: 2, style: 5, label: "Renovar Agora", emoji: null, disabled: false, url: renewLink }] },
          ],
        },
      ],
      flags: 32768,
    });
    console.log(`[BLOCK SERVICE] DM de bloqueio enviada para usuário ${user._id}`);
    return true;
  } catch (error) {
    console.error(`[BLOCK SERVICE] Erro ao enviar DM de bloqueio:`, error.message);
    return false;
  }
}

export async function blockExpiredApps() {
  try {
    const now = new Date();
    const expiredApps = await Application.find({
      expiresAt: { $lt: now },
      isBlocked: false,
      isDeleted: false,
      isFree: { $ne: true },
    });

    console.log(`[BLOCK SERVICE] Encontradas ${expiredApps.length} aplicações vencidas para bloquear`);

    for (const app of expiredApps) {
      try {
        const appId = app.hosting?.appId;
        // Para o app na Discloud ao bloquear
        if (appId) {
          const stopped = await stopDiscloudApp(appId);
          if (stopped) {
            console.log(`[BLOCK SERVICE] App ${appId} parado na Discloud (bloqueio por expiração)`);
          }
        }

        app.isBlocked = true;
        app.blockedAt = now;
        await app.save();
        console.log(`[BLOCK SERVICE] Aplicação ${app._id} bloqueada com sucesso`);

        // Notifica via DM
        try {
          const userDiscordIds = new Set();
          const user = await User.findById(app.userId);
          if (user?.discordId) userDiscordIds.add(user.discordId);
          if (app.bot?.owner && app.bot.owner !== user?.discordId) userDiscordIds.add(app.bot.owner);
          if (Array.isArray(app.bot?.perms)) app.bot.perms.forEach(permId => { if (permId) userDiscordIds.add(permId); });

          for (const discordId of userDiscordIds) {
            try {
              await sendBlockDM(app, { discordId, _id: app.userId });
              await new Promise(resolve => setTimeout(resolve, 1000));
            } catch (dmError) {
              console.error(`[BLOCK SERVICE] Erro ao enviar DM para ${discordId}:`, dmError.message);
            }
          }
        } catch (dmError) {
          console.error(`[BLOCK SERVICE] Erro ao processar DMs para ${app._id}:`, dmError.message);
        }
      } catch (error) {
        console.error(`[BLOCK SERVICE] Erro ao bloquear aplicação ${app._id}:`, error.message);
      }
    }

    console.log(`[BLOCK SERVICE] Bloqueio de aplicações concluído`);
  } catch (error) {
    console.error("[BLOCK SERVICE] Erro no bloqueio de aplicações:", error);
  }
}

export async function deleteOldBlockedApps() {
  try {
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const oldBlockedApps = await Application.find({
      isBlocked: true,
      blockedAt: { $lt: sevenDaysAgo },
      isDeleted: false,
    });

    console.log(`[BLOCK SERVICE] Encontradas ${oldBlockedApps.length} aplicações para deletar da Discloud e do banco`);

    for (const app of oldBlockedApps) {
      try {
        const appId = app.hosting?.appId;

        // SEMPRE tenta deletar da Discloud primeiro
        if (appId) {
          const deleted = await deleteDiscloudApp(appId);
          if (deleted) {
            console.log(`[BLOCK SERVICE] App ${appId} deletado da Discloud (expiração 7 dias)`);
          } else {
            console.warn(`[BLOCK SERVICE] Falha ao deletar app ${appId} da Discloud — marcando como deletado no banco mesmo assim`);
          }
        } else {
          console.log(`[BLOCK SERVICE] App ${app._id} sem appId na Discloud — apenas marcando como deletado no banco`);
        }

        // Marca como deletado no banco independente do resultado na Discloud
        app.isDeleted = true;
        app.deletedAt = now;
        await app.save();
        console.log(`[BLOCK SERVICE] Aplicação ${app._id} marcada como deletada no banco`);
      } catch (error) {
        console.error(`[BLOCK SERVICE] Erro ao deletar aplicação ${app._id}:`, error.message);
      }
    }

    console.log(`[BLOCK SERVICE] Deleção de aplicações concluída`);
  } catch (error) {
    console.error("[BLOCK SERVICE] Erro na deleção de aplicações:", error);
  }
}

export async function checkAndProcessBlocks() {
  console.log("[BLOCK SERVICE] Iniciando verificação de bloqueios e deleções");
  await blockExpiredApps();
  await deleteOldBlockedApps();
  console.log("[BLOCK SERVICE] Verificação concluída");
}

export function startBlockService() {
  console.log("[BLOCK SERVICE] Serviço de bloqueio iniciado");
  checkAndProcessBlocks();
  setInterval(checkAndProcessBlocks, 10 * 60 * 1000);
}

/**
 * Serviço de cobrança automática via DM do Discord
 * Envia mensagens de lembrete nos últimos 7 dias antes do vencimento
 */

import { Client, GatewayIntentBits, Partials } from "discord.js";
import Application from "../../database/models/Application.js";
import BotConfig from "../../database/models/BotConfig.js";
import User from "../../database/models/User.js";

/**
 * Busca o ID do bot usando o token
 */
async function fetchDiscordBotId(token) {
  try {
    const response = await fetch("https://discord.com/api/v10/users/@me", {
      headers: { Authorization: `Bot ${token}` },
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data.id;
  } catch (e) {
    return null;
  }
}

/**
 * Envia mensagem de cobrança via DM usando o bot do cliente
 */
async function sendChargeDM(application, botToken, ownerId, daysLeft) {
  return new Promise(async (resolve) => {
    const client = new Client({
      intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages],
      partials: [Partials.Channel],
    });

    let timeout;

    try {
      // Faz login com o token do bot do cliente
      await client.login(botToken);

      // Espera o bot estar pronto (timeout de 10s)
      await new Promise((res, rej) => {
        timeout = setTimeout(() => rej(new Error("Timeout ao logar")), 10000);
        client.once("ready", () => {
          clearTimeout(timeout);
          res();
        });
        client.once("error", (err) => {
          clearTimeout(timeout);
          rej(err);
        });
      });

      // Monta o link de renovação
      const renewLink = `${process.env.FRONTEND_URL}/dashboard/invoices?renew=${application._id}`;

      // Busca o usuário e envia a DM
      const user = await client.users.fetch(ownerId);
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
                  content: `Olá senhor(a) <@${user.id}>!`,
                },
              ],
            },
            {
              type: 17,
              accent_color: 6053616,
              spoiler: false,
              components: [
                {
                  type: 10,
                  content: "# ATENÇÃO - VENCIMENTO PRÓXIMO",
                },
                {
                  type: 14,
                  divider: true,
                  spacing: 1,
                },
                {
                  type: 10,
                  content: `Sua assinatura do bot **${application.name}** irá expirar em **${daysLeft} ${daysLeft === 1 ? "dia" : "dias"}**.\n\nPlano: **${application.plan.name}**\nID da Aplicação: \`${application._id}\`\nVence em: <t:${Math.floor(new Date(application.expiresAt).getTime() / 1000)}:D>`,
                },
                {
                  type: 14,
                  divider: false,
                  spacing: 1,
                },
                {
                  type: 10,
                  content: "**Após o vencimento:**\n• O bot será bloqueado imediatamente\n• Você terá 7 dias para renovar\n• Após 7 dias, o bot será deletado permanentemente",
                },
                {
                  type: 14,
                  divider: true,
                  spacing: 1,
                },
                {
                  type: 10,
                  content: "Evite a suspensão e bloqueio de sua aplicação e continue desfrutando de nossos serviços.\n-# Renove agora clicando no botão abaixo. Se já renovou, ignore esta mensagem.",
                },
                {
                  type: 14,
                  divider: true,
                  spacing: 1,
                },
                {
                  type: 1,
                  components: [
                    {
                      type: 2,
                      style: 5,
                      label: "Renovar Agora",
                      emoji: null,
                      disabled: false,
                      url: renewLink,
                    },
                  ],
                },
              ],
            },
          ],
          flags: 32768,
        });

        console.log(`[CHARGE SERVICE] DM enviada para ${ownerId} sobre aplicação ${application._id}`);
      }
    } catch (e) {
      console.error(`[CHARGE SERVICE] Erro ao enviar DM:`, e.message);
    } finally {
      if (client && client.destroy) {
        await client.destroy();
      }
      resolve();
    }
  });
}

/**
 * Verifica aplicações próximas do vencimento e envia cobranças
 * Envia nos últimos 7 dias, a cada 12 horas
 */
export async function checkAndSendCharges() {
  try {
    const now = new Date();
    const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

    // Busca aplicações que vão vencer nos próximos 7 dias
    const expiringApps = await Application.find({
      expiresAt: {
        $gte: now,
        $lte: sevenDaysFromNow,
      },
    })
      .populate("userId", "discordId")
      .lean();

    console.log(`[CHARGE SERVICE] Encontradas ${expiringApps.length} aplicações próximas do vencimento`);

    for (const app of expiringApps) {
      try {
        // Calcula dias restantes
        const daysLeft = Math.ceil((new Date(app.expiresAt) - now) / (1000 * 60 * 60 * 24));

        if (daysLeft <= 0 || daysLeft > 7) continue;

        // Busca o BotConfig para pegar o token
        const botConfig = await BotConfig.findOne({ botID: app.botID });
        if (!botConfig || !botConfig.bot?.token) {
          console.log(`[CHARGE SERVICE] Token não encontrado para aplicação ${app._id}`);
          continue;
        }

        // Verifica se já enviou recentemente (últimas 12 horas)
        const lastChargeSent = app.lastChargeSent ? new Date(app.lastChargeSent).getTime() : 0;
        const twelveHoursAgo = now.getTime() - 12 * 60 * 60 * 1000;

        if (lastChargeSent > twelveHoursAgo) {
          console.log(`[CHARGE SERVICE] Cobrança já enviada recentemente para ${app._id}`);
          continue;
        }

        // Coleta todos os IDs de usuários que devem receber DM
        const userIds = new Set();
        
        // Adiciona o owner
        const ownerId = app.userId?.discordId || app.bot?.owner;
        if (ownerId) {
          userIds.add(ownerId);
        }
        
        // Adiciona todos os usuários com permissões
        if (app.bot?.perms && Array.isArray(app.bot.perms)) {
          app.bot.perms.forEach(permId => {
            if (permId && permId !== ownerId) {
              userIds.add(permId);
            }
          });
        }

        if (userIds.size === 0) {
          console.log(`[CHARGE SERVICE] Nenhum usuário encontrado para ${app._id}`);
          continue;
        }

        // Envia DM para todos os usuários
        console.log(`[CHARGE SERVICE] Enviando DM para ${userIds.size} usuário(s) da aplicação ${app._id}`);
        
        for (const userId of userIds) {
          try {
            await sendChargeDM(app, botConfig.bot.token, userId, daysLeft);
            console.log(`[CHARGE SERVICE] DM enviada para usuário ${userId}`);
            
            // Aguarda 1 segundo entre cada envio para evitar rate limit
            await new Promise((resolve) => setTimeout(resolve, 1000));
          } catch (dmError) {
            console.error(`[CHARGE SERVICE] Erro ao enviar DM para ${userId}:`, dmError.message);
          }
        }

        // Atualiza a data do último envio
        await Application.updateOne(
          { _id: app._id },
          { $set: { lastChargeSent: now } }
        );
      } catch (error) {
        console.error(`[CHARGE SERVICE] Erro ao processar aplicação ${app._id}:`, error.message);
      }
    }

    console.log(`[CHARGE SERVICE] Verificação de cobranças concluída`);
  } catch (error) {
    console.error("[CHARGE SERVICE] Erro na verificação de cobranças:", error);
  }
}

/**
 * Inicia o serviço de cobrança (executado a cada 5 minutos)
 */
export function startChargeService() {
  console.log("[CHARGE SERVICE] Serviço de cobrança iniciado");
  
  // Executa imediatamente
  checkAndSendCharges();
  
  // Executa a cada 5 minutos
  setInterval(checkAndSendCharges, 5 * 60 * 1000);
}

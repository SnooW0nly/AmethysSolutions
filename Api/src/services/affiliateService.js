/**
 * Serviço de Afiliados
 * Gerencia geração de links, rastreamento de cliques e conversões
 */

import Affiliate from "../database/models/Affiliate.js";
import Application from "../database/models/Application.js";
import User from "../database/models/User.js";
import { deployBotWithConfig } from "../services/botDeployment.js";
import path from "path";
import fs from "fs";

/**
 * Gera um código único de afiliado (6 caracteres alfanuméricos)
 */
function generateAffiliateCode() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // sem I, O, 0, 1 pra evitar confusão
  let code = "";
  for (let i = 0; i < 6; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
}

/**
 * Cria ou retorna o afiliado de um usuário
 */
export async function getOrCreateAffiliate(userId) {
  let affiliate = await Affiliate.findOne({ userId });

  if (!affiliate) {
    // Garante código único
    let code;
    let attempts = 0;
    do {
      code = generateAffiliateCode();
      attempts++;
      if (attempts > 20) throw new Error("Não foi possível gerar um código único");
    } while (await Affiliate.findOne({ code }));

    affiliate = await Affiliate.create({ userId, code });
  }

  return affiliate;
}

/**
 * Registra um clique no link de afiliado
 * Retorna o afiliado se encontrado
 */
export async function registerAffiliateClick(code) {
  if (!code) return null;

  const affiliate = await Affiliate.findOneAndUpdate(
    { code: code.toUpperCase(), isActive: true },
    { $inc: { clicks: 1 } },
    { new: true }
  );

  return affiliate;
}

/**
 * Processa conversão de afiliado após pagamento aprovado
 * Chamado quando um pagamento com affiliateCode é aprovado
 */
export async function processAffiliateConversion(paymentId, buyerUserId, affiliateCode) {
  if (!affiliateCode) return null;

  const affiliate = await Affiliate.findOne({
    code: affiliateCode.toUpperCase(),
    isActive: true,
  });

  if (!affiliate) return null;

  // Não processa se o comprador for o próprio afiliado
  if (String(affiliate.userId) === String(buyerUserId)) return null;

  // Verifica se já processou esse payment
  const alreadyProcessed = affiliate.conversionHistory.some(
    (c) => String(c.paymentId) === String(paymentId)
  );
  if (alreadyProcessed) return affiliate;

  // Registra conversão
  affiliate.conversions += 1;
  affiliate.rewardDays += 1;
  affiliate.conversionHistory.push({
    paymentId,
    buyerUserId,
    rewarded: false,
    rewardDays: 1,
  });

  await affiliate.save();

  console.log(
    `[AFFILIATE] Conversão registrada - Code: ${affiliateCode}, Afiliado: ${affiliate.userId}, Comprador: ${buyerUserId}`
  );

  // Tenta criar/estender bot de recompensa automaticamente
  await grantAffiliateReward(affiliate);

  return affiliate;
}

/**
 * Concede ou estende o bot de recompensa ao afiliado
 */
async function grantAffiliateReward(affiliate) {
  try {
    const pendingDays = affiliate.rewardDays - affiliate.claimedDays;
    if (pendingDays <= 0) return;

    // Busca usuário afiliado
    const user = await User.findById(affiliate.userId).lean();
    if (!user) return;

    // Verifica se já tem um bot de recompensa ativo
    const existingRewardApp = await Application.findOne({
      userId: affiliate.userId,
      isAffiliateReward: true,
      isDeleted: false,
    });

    if (existingRewardApp) {
      // Estende o bot existente por mais 1 dia
      const newExpiry = new Date(
        Math.max(existingRewardApp.expiresAt.getTime(), Date.now()) +
          pendingDays * 24 * 60 * 60 * 1000
      );
      await Application.updateOne(
        { _id: existingRewardApp._id },
        {
          $set: {
            expiresAt: newExpiry,
            isBlocked: false,
            blockedAt: null,
          },
        }
      );

      console.log(
        `[AFFILIATE] Bot de recompensa estendido para ${newExpiry.toISOString()} - App: ${existingRewardApp._id}`
      );
    } else {
      // Cria novo bot de recompensa (sem deploy na Discloud, sem token)
      const expiresAt = new Date(Date.now() + pendingDays * 24 * 60 * 60 * 1000);

      const rewardApp = await Application.create({
        userId: affiliate.userId,
        name: "🎁 Bot Afiliado",
        isAffiliateReward: true,
        isFree: false,
        isBlocked: false,
        isDeleted: false,
        plan: {
          id: "affiliate-reward",
          name: "Recompensa de Afiliado",
          price: 0,
          months: 0,
        },
        bot: {
          token: "",
          owner: user.discordId || "",
          id: "",
          perms: user.discordId ? [user.discordId] : [],
          server: "",
        },
        expiresAt,
        hosting: {},
      });

      affiliate.rewardApps.push({
        applicationId: rewardApp._id,
        days: pendingDays,
      });

      console.log(`[AFFILIATE] Bot de recompensa criado - App: ${rewardApp._id}, Dias: ${pendingDays}`);
    }

    // Marca dias como concedidos
    affiliate.claimedDays = affiliate.rewardDays;
    await affiliate.save();
  } catch (error) {
    console.error("[AFFILIATE] Erro ao conceder recompensa:", error.message);
  }
}

/**
 * Retorna estatísticas do afiliado de um usuário
 */
export async function getAffiliateStats(userId) {
  const affiliate = await getOrCreateAffiliate(userId);

  return {
    code: affiliate.code,
    link: `${process.env.FRONTEND_URL}/purchase?ref=${affiliate.code}`,
    clicks: affiliate.clicks,
    conversions: affiliate.conversions,
    rewardDays: affiliate.rewardDays,
    claimedDays: affiliate.claimedDays,
    pendingDays: Math.max(0, affiliate.rewardDays - affiliate.claimedDays),
    rewardApps: affiliate.rewardApps,
    conversionHistory: affiliate.conversionHistory
      .slice()
      .reverse()
      .slice(0, 20), // últimas 20
    createdAt: affiliate.createdAt,
  };
}
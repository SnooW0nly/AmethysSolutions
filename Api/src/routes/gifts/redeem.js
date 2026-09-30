import Gift from "../../database/models/Gift.js";
import Application from "../../database/models/Application.js";
import Payment from "../../database/models/Payment.js";
import Plan from "../../database/models/Plan.js";
import User from "../../database/models/User.js";
import mongoose from "mongoose";
const { Types } = mongoose;
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { deployBotWithConfig } from "../../services/botDeployment.js";
import { addRoleToMember } from "../../services/discord/cargoCliente.js";
import { addUserToGuild } from "../../services/discord/puxarDiscord.js";
import { getLatestPlanVersion } from "../../services/massUpdate.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * POST /gifts/redeem
 * Resgata um gift code, cria aplicação, hospeda bot e atribui cargo Discord
 */
export default async function redeemGift(req, res) {
  // Referências para rollback manual caso necessário
  let createdPaymentId = null;
  let createdApplicationId = null;

  try {
    const { code, applicationId } = req.body;
    const userId = req.user?._id;

    console.log(`[GIFT REDEEM] Resgatando gift - Code: ${code}, ApplicationId: ${applicationId || 'NOVO BOT'}, UserId: ${userId}`);

    if (!userId) {
      return res.status(401).json({ success: false, message: "Usuário não autenticado" });
    }

    if (!code || typeof code !== "string") {
      return res.status(400).json({ success: false, message: "Código do gift é obrigatório" });
    }

    const normalizedCode = code.trim().toUpperCase();

    // Busca e valida o gift
    const gift = await Gift.findOne({ code: normalizedCode });

    if (!gift) {
      return res.status(404).json({ success: false, message: "Gift não encontrado" });
    }

    if (gift.isUsed) {
      return res.status(400).json({ success: false, message: "Este gift já foi resgatado" });
    }

    if (gift.expiresAt && new Date() > gift.expiresAt) {
      return res.status(400).json({ success: false, message: "Este gift expirou" });
    }

    // Busca o plano
    const plan = await Plan.findOne({ id: gift.planId });
    if (!plan) {
      return res.status(404).json({ success: false, message: "Plano associado ao gift não encontrado" });
    }

    // Busca o usuário
    const user = await User.findById(userId).select("discordId oauth");
    if (!user) {
      return res.status(404).json({ success: false, message: "Usuário não encontrado" });
    }

    // ─── RENOVAÇÃO: adiciona dias ao bot existente ───────────────────────────
    if (applicationId) {
      console.log(`[GIFT REDEEM] Buscando aplicação - ID: ${applicationId}, UserId: ${userId}`);

      const userObjectId = Types.ObjectId.isValid(userId) ? new Types.ObjectId(userId) : userId;

      const existingApp = await Application.findOne({
        _id: applicationId,
        userId: userObjectId,
        isDeleted: { $ne: true },
      });

      if (!existingApp) {
        const appExists = await Application.findById(applicationId);
        console.log(`[GIFT REDEEM] App existe no banco:`, appExists ? 'SIM' : 'NÃO');
        if (appExists) {
          console.log(`[GIFT REDEEM] App userId:`, appExists.userId, 'JWT userId:', userId);
        }
        return res.status(404).json({ success: false, message: "Aplicação não encontrada ou não pertence a você" });
      }

      // Marca o gift como usado ANTES de modificar a aplicação
      // (evita duplo resgate em caso de erro posterior)
      gift.isUsed = true;
      gift.usedBy = userId;
      gift.usedAt = new Date();
      gift.applicationId = existingApp._id;
      await gift.save();

      // Estende a expiração
      const currentExpiry = new Date(existingApp.expiresAt);
      const now = new Date();
      const baseDate = currentExpiry > now ? currentExpiry : now;
      baseDate.setMonth(baseDate.getMonth() + gift.months);
      existingApp.expiresAt = baseDate;

      if (existingApp.isBlocked) {
        existingApp.isBlocked = false;
        existingApp.blockedAt = null;
      }

      await existingApp.save();

      // Registro de pagamento (sem transação, não é crítico)
      try {
        const paymentExpiresAt = new Date();
        paymentExpiresAt.setDate(paymentExpiresAt.getDate() + 30);
        await Payment.create({
          userId,
          priceFinal: 0,
          efiId: `GIFT-${gift.code}`,
          status: "approved",
          expiresAt: paymentExpiresAt,
          plan: { id: gift.planId, name: gift.planName, price: 0, months: gift.months },
          qrCodeText: `Gift Code: ${gift.code} (Renovação)`,
        });
      } catch (e) {
        console.warn("[GIFT REDEEM] Falha ao criar registro de pagamento (não crítico):", e.message);
      }

      return res.status(200).json({
        success: true,
        message: "Gift aplicado com sucesso!",
        data: { planName: gift.planName, months: gift.months, expiresAt: existingApp.expiresAt },
      });
    }

    // ─── NOVO BOT ────────────────────────────────────────────────────────────

    // Marca o gift como usado logo no início para evitar duplo resgate
    gift.isUsed = true;
    gift.usedBy = userId;
    gift.usedAt = new Date();
    await gift.save();

    const paymentExpiresAt = new Date();
    paymentExpiresAt.setDate(paymentExpiresAt.getDate() + 30);

    const payment = await Payment.create({
      userId,
      priceFinal: 0,
      efiId: `GIFT-${gift.code}`,
      status: "approved",
      expiresAt: paymentExpiresAt,
      plan: { id: gift.planId, name: gift.planName, price: 0, months: gift.months },
      qrCodeBase64: null,
      qrCodeText: `Gift Code: ${gift.code}`,
    });
    createdPaymentId = payment._id;

    const expiresAt = new Date();
    expiresAt.setMonth(expiresAt.getMonth() + gift.months);

    // Localiza o ZIP do plano
    let zipPath = null;
    if (plan.zipFilename) {
      const possiblePaths = [
        path.resolve(process.cwd(), "src/database/zip", plan.zipFilename),
        path.resolve(process.cwd(), "backend/src/database/zip", plan.zipFilename),
        path.join(__dirname, "../../database/zip", plan.zipFilename),
      ];
      for (const testPath of possiblePaths) {
        if (fs.existsSync(testPath)) {
          zipPath = testPath;
          console.log(`[GIFT REDEEM] ZIP encontrado em: ${zipPath}`);
          break;
        }
      }
      if (!zipPath) {
        console.error(`[GIFT REDEEM] ZIP não encontrado para: ${plan.zipFilename}`);
      }
    }

    const botID = String(payment._id);
    const ownerDiscordId = user.discordId;
    const planVersion = await getLatestPlanVersion(plan.id);
    console.log(`[GIFT REDEEM] Versão do plano ${plan.id}: ${planVersion || 'Nenhuma'}`);

    // Deploy do bot
    let hostingResponse = null;
    let hostingApp = null;
    let hostingAppId = null;

    if (zipPath) {
      try {
        const deployResult = await deployBotWithConfig(zipPath, botID, ownerDiscordId, planVersion);
        console.log(`[GIFT REDEEM] deployResult:`, JSON.stringify({
          success: deployResult.success,
          appId: deployResult.appId,
          botID: deployResult.botID,
          botToken: deployResult.botToken,
        }, null, 2));

        hostingResponse = deployResult.discloudResponse;
        hostingAppId = deployResult.appId;
        hostingApp = hostingResponse?.app || hostingResponse?.apps || null;

        if (!hostingAppId) {
          hostingAppId = hostingResponse?.app?.id || hostingApp?.id || hostingResponse?.appId || hostingResponse?.id || null;
        }

        console.log(`[GIFT REDEEM] Bot hospedado! AppID final: ${hostingAppId}`);
      } catch (err) {
        console.error("[GIFT REDEEM] Erro ao fazer deploy do bot:", err);
        // Continua mesmo sem deploy
      }
    }

    const finalAppId = hostingAppId ? String(hostingAppId) : "";

    // Cria a aplicação
    const application = new Application({
      userId,
      paymentId: payment._id,
      name: `${plan.name} (Gift)`,
      botID,
      plan: {
        id: plan.id,
        name: plan.name,
        months: gift.months,
        price: 0,
        paymentId: payment._id,
      },
      hosting: {
        provider: "discloud",
        appId: finalAppId,
        name: hostingApp?.name || hostingResponse?.app?.name || null,
        ram: hostingApp?.ram || hostingResponse?.app?.ram || null,
        version: hostingApp?.version || hostingResponse?.app?.version || null,
        main: hostingApp?.mainFile || hostingResponse?.app?.mainFile || hostingApp?.main || null,
        status: hostingResponse?.message || hostingResponse?.status || null,
        url: hostingApp?.avatarURL || hostingResponse?.app?.avatarURL || null,
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      bot: {
        token: null,
        owner: String(ownerDiscordId || null),
        id: null,
        perms: [],
        server: null,
      },
      info: { name: plan.name, imageUrl: null, id: null },
      expiresAt,
      updateVersion: planVersion,
    });

    if (!application.hosting.appId && finalAppId) {
      application.hosting.appId = String(finalAppId);
    }

    await application.save();
    createdApplicationId = application._id;

    // Vincula gift à aplicação criada
    gift.applicationId = application._id;
    await gift.save();

    // Atribui cargo Discord (não crítico)
    try {
      const roleId = plan.discordRoleId || process.env.DISCORD_DEFAULT_ROLE_ID;
      if (roleId && user.discordId) {
        if (user.oauth?.accessToken) {
          try {
            await addUserToGuild({
              userId: user.discordId,
              accessToken: user.oauth.accessToken,
              guildId: process.env.DISCORD_GUILD_ID,
            });
          } catch (e) {
            console.warn("[GIFT REDEEM] Falha ao adicionar usuário ao servidor:", e?.message);
          }
        }
        await addRoleToMember({ userId: user.discordId, roleId, guildId: process.env.DISCORD_GUILD_ID });
        console.log(`[GIFT REDEEM] Cargo ${roleId} atribuído ao usuário ${user.discordId}`);
      }
    } catch (e) {
      console.warn("[GIFT REDEEM] Falha ao atribuir cargo Discord:", e?.message || e);
    }

    return res.status(200).json({
      success: true,
      message: "Gift resgatado com sucesso!",
      data: {
        application: {
          id: application._id,
          name: application.name,
          planName: plan.name,
          months: gift.months,
          expiresAt: application.expiresAt,
        },
      },
    });
  } catch (error) {
    console.error("[GIFT REDEEM ERROR]", error);

    // Rollback manual: remove payment e application criados (best-effort)
    if (createdApplicationId) {
      try { await Application.findByIdAndDelete(createdApplicationId); } catch {}
    }
    if (createdPaymentId) {
      try { await Payment.findByIdAndDelete(createdPaymentId); } catch {}
    }

    return res.status(500).json({
      success: false,
      message: "Erro ao resgatar gift",
      error: error.message,
    });
  }
}
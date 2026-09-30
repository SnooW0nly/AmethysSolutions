import { isPaymentExpired, markPaymentExpired, updatePaymentStatus } from "./payment/payments.js";
import { fetchPixStatus as fetchEfiStatus } from "./payment/efi.js";
import { fetchPixStatus as fetchWooviStatus } from "./payment/mistic.js";
import { redeemCouponUsage } from "./payment/coupons.js";
import { sendReceiptForPayment } from "./payment/receipts.js";
import { hospedarApp } from "./payment/hospedar.js";
import { addRoleToMember } from "../../services/discord/cargoCliente.js";
import { addUserToGuild } from "../../services/discord/puxarDiscord.js";
import { deployBotWithConfig } from "../../services/botDeployment.js";
import { notifySaleApproved } from "../../services/discord/salesNotification.js";
import { withdrawPayment } from "../../services/mistic/withdraw.js";
import Plan from "../../database/models/Plan.js";
import User from "../../database/models/User.js";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import Application from "../../database/models/Application.js";
import { processAffiliateConversion } from "../../services/affiliateService.js";
import discloudService from "../../services/discloudService.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ========== FUNÇÃO PRINCIPAL QUE O POLLER USA ==========
export async function processPayment(payment) {
  if (isPaymentExpired(payment)) {
    await markPaymentExpired(payment);
    return;
  }

  const provider = payment.provider || "mistic";

  let paymentId;
  if (provider === "mistic") {
    paymentId = payment.misticId;
  } else if (provider === "woovi") {
    paymentId = payment.wooviId;
  } else {
    paymentId = payment.efiId;
  }

  if (!paymentId) {
    console.error(`[poller] Pagamento ${payment._id} sem ID do provedor (provider: ${provider})`);
    return;
  }

  let status;
  try {
    if (provider === "mistic" || provider === "woovi") {
      status = await fetchWooviStatus(paymentId, provider);
    } else {
      status = await fetchEfiStatus(paymentId);
    }
  } catch (error) {
    console.error(`[poller] Erro ao verificar pagamento ${paymentId}:`, error?.message || error);
    return;
  }

  const changed = await updatePaymentStatus(payment, status);

  if (status === "approved") {
    const existingApp = await Application.findOne({ paymentId: payment._id }).lean();

    if (!existingApp) {
      console.log(`[poller] Pagamento ${payment._id} aprovado mas sem Application. Processando...`);
      await handleApprovedPayment(payment);
    } else if (changed) {
      console.log(`[poller] Pagamento ${payment._id} mudou para approved. Processando...`);
      await handleApprovedPayment(payment);
    }
  }
}

// ========== SAQUE AUTOMÁTICO ==========
async function triggerWithdraw(payment) {
  try {
    if (payment.provider !== "mistic") {
      console.log(`[withdraw] Provedor "${payment.provider}" não é Mistic — saque automático ignorado.`);
      return;
    }

    const transactionId = payment.misticId;
    if (!transactionId) {
      console.warn(`[withdraw] Pagamento ${payment._id} sem misticId — saque não realizado.`);
      return;
    }

    const amount = Number(payment.priceFinal ?? 0);
    if (!amount || amount <= 0) {
      console.warn(`[withdraw] Valor inválido (${amount}) para pagamento ${payment._id} — saque ignorado.`);
      return;
    }

    const planName = payment.plan?.name || "Plano";
    const isRenewal = payment.metadata?.isRenewal ? "Renovação" : "Nova compra";

    const result = await withdrawPayment({
      transactionId,
      amount,
      description: `${isRenewal} — ${planName} — ID ${payment._id}`,
    });

    if (result.success) {
      console.log(`[withdraw] ✅ Saque de R$ ${amount} iniciado — withdrawId: ${result.withdrawTxId || result.jobId} | pagamento: ${payment._id}`);
    } else {
      console.error(`[withdraw] ❌ Saque falhou para pagamento ${payment._id}: ${result.error}`);
    }
  } catch (err) {
    console.error(`[withdraw] Erro inesperado ao sacar pagamento ${payment._id}:`, err?.message || err);
  }
}

// ========== HANDLE APPROVED ==========
export async function handleApprovedPayment(payment) {
  const isRenewal = payment.metadata?.isRenewal;

  if (isRenewal) {
    await handleRenewalPayment(payment);
    return;
  }

  const planId = payment?.plan?.id;
  if (!planId) return;

  const planObject = await Plan.findOne({ id: planId }).lean();
  if (!planObject) return;

  await redeemCouponUsage(payment);
  await sendReceiptForPayment(payment);
  await triggerWithdraw(payment);

  let zipPath = null;
  if (planObject.zipFilename) {
    const possiblePaths = [
      path.resolve(process.cwd(), "src/database/zip", planObject.zipFilename),
      path.resolve(process.cwd(), "backend/src/database/zip", planObject.zipFilename),
      path.join(__dirname, "../../database/zip", planObject.zipFilename),
    ];

    for (const testPath of possiblePaths) {
      if (fs.existsSync(testPath)) {
        zipPath = testPath;
        console.log(`[handleApprovedPayment] ZIP encontrado em: ${zipPath}`);
        break;
      }
    }

    if (!zipPath) {
      console.error(`[handleApprovedPayment] ZIP não encontrado para: ${planObject.zipFilename}`);
      return;
    }
  } else {
    console.error("[handleApprovedPayment] Plano sem zipFilename definido");
    return;
  }

  const owner = await User.findById(payment.userId).select("discordId").lean();
  const ownerDiscordId = owner?.discordId;
  const botID = String(payment._id);

  let hostingResponse;
  let hostingAppId;

  try {
    const deployResult = await deployBotWithConfig(zipPath, botID, ownerDiscordId, planObject?.version);
    hostingAppId = deployResult.appId;
    hostingResponse = deployResult.discloudResponse;
    console.log(`[handleApprovedPayment] Bot hospedado na Discloud! AppID: ${hostingAppId}`);
  } catch (err) {
    console.error("[handleApprovedPayment] Erro ao fazer deploy do bot:", err);
    hostingResponse = await hospedarApp(zipPath);
    hostingAppId = hostingResponse?.appId || hostingResponse?.id || null;
  }

  const months = Number(payment?.plan?.months) || planObject?.plans?.find(p => String(p.id) === String(payment?.plan?.monthId))?.months || 1;
  const daysToAdd = Number(months) * 30;
  const expiresAt = new Date(Date.now() + daysToAdd * 24 * 60 * 60 * 1000);

  const applicationPayload = {
    name: planObject.name,
    userId: payment.userId,
    paymentId: payment._id,
    botID,
    plan: {
      id: planObject.id,
      name: planObject.name,
      months,
      price: payment?.priceFinal,
      paymentId: payment._id,
    },
    hosting: {
      provider: "discloud",
      appId: hostingAppId ? String(hostingAppId) : "",
      name: hostingResponse?.name || null,
      ram: hostingResponse?.ram || null,
      version: hostingResponse?.version || null,
      main: hostingResponse?.main || null,
      status: hostingResponse?.status || hostingResponse?.message || null,
      url: hostingResponse?.url || null,
      createdAt: new Date(),
      updatedAt: new Date(),
    },
    bot: {
      token: null,
      owner: String(ownerDiscordId || ""),
      id: null,
      perms: ownerDiscordId ? [String(ownerDiscordId)] : [],
      server: null,
    },
    info: {
      name: planObject.name,
      imageUrl: null,
      id: null,
    },
    expiresAt,
  };

  let savedApp = null;
  try {
    savedApp = await Application.findOneAndUpdate(
      { paymentId: payment._id },
      { $set: applicationPayload, $setOnInsert: { createdAt: new Date() } },
      { upsert: true, new: true }
    );
  } catch (err) {
    console.error("[handleApprovedPayment] Erro ao salvar/atualizar Application:", err?.message || err);
  }

  try {
    const roleId = planObject.discordRoleId || process.env.DISCORD_DEFAULT_ROLE_ID;
    if (roleId) {
      const buyer = await User.findById(payment.userId).select("discordId oauth").lean();
      if (buyer?.discordId) {
        if (buyer?.oauth?.accessToken) {
          try {
            await addUserToGuild({ userId: buyer.discordId, accessToken: buyer.oauth.accessToken, guildId: process.env.DISCORD_GUILD_ID });
          } catch { }
        }
        await addRoleToMember({ userId: buyer.discordId, roleId, guildId: process.env.DISCORD_GUILD_ID });
      }
    }
  } catch (e) {
    console.warn("[payments] falha ao atribuir cargo:", e?.message || e);
  }

  const affiliateCode = payment?.metadata?.affiliateCode;
  if (affiliateCode) {
    try {
      await processAffiliateConversion(payment._id, payment.userId, affiliateCode);
    } catch (affiliateError) {
      console.error("[handleApprovedPayment] Erro ao processar conversão de afiliado:", affiliateError.message);
    }
  }

  try {
    const userForNotif = await User.findById(payment.userId).lean();
    await notifySaleApproved({
      payment,
      user: userForNotif,
      application: savedApp,
      isRenewal: false,
    });
  } catch (err) {
    console.warn("[handleApprovedPayment] Notificação Discord falhou (não crítico):", err?.message);
  }
}

// ========== HANDLE RENEWAL ==========
export async function handleRenewalPayment(payment) {
  try {
    const applicationId = payment.metadata?.applicationId;
    if (!applicationId) {
      console.error("[RENEWAL] applicationId não encontrado no metadata");
      return;
    }

    const application = await Application.findById(applicationId);
    if (!application) {
      console.error("[RENEWAL] Aplicação não encontrada:", applicationId);
      return;
    }

    const currentExpiration = new Date(application.expiresAt);
    const now = new Date();
    const months = payment.metadata?.months || payment.plan?.months || 1;
    const daysToAdd = Number(months) * 30;
    const baseDate = currentExpiration > now ? currentExpiration : now;
    const newExpiration = new Date(baseDate.getTime() + daysToAdd * 24 * 60 * 60 * 1000);

    application.expiresAt = newExpiration;
    application.lastChargeSent = null;

    if (application.isBlocked && !application.isDeleted) {
      const appId = application.hosting?.appId;
      if (appId) {
        try {
          const result = await discloudService.startApp(appId);
          if (result.success) {
            application.isBlocked = false;
            application.blockedAt = null;
            console.log(`[RENEWAL] Aplicação ${applicationId} desbloqueada e reiniciada na Discloud`);
          }
        } catch (error) {
          console.error(`[RENEWAL] Erro ao reiniciar app:`, error.message);
        }
      }
    }

    await application.save();
    await redeemCouponUsage(payment);
    await sendReceiptForPayment(payment);
    await triggerWithdraw(payment);

    console.log(`[RENEWAL] Aplicação ${applicationId} renovada até ${newExpiration.toISOString()}`);

    try {
      const userForNotif = await User.findById(payment.userId).lean();
      await notifySaleApproved({
        payment,
        user: userForNotif,
        application,
        isRenewal: true,
      });
    } catch (err) {
      console.warn("[RENEWAL] Notificação Discord falhou (não crítico):", err?.message);
    }
  } catch (error) {
    console.error("[RENEWAL] Erro ao processar renovação:", error);
  }
}

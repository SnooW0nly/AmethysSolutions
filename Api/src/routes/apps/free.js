import express from "express";
import Application from "../../database/models/Application.js";
import Plan from "../../database/models/Plan.js";
import User from "../../database/models/User.js";
import FreePlanConfig from "../../database/models/FreePlanConfig.js";
import { deployBotWithConfig } from "../../services/botDeployment.js";
import { addRoleToMember } from "../../services/discord/cargoCliente.js";
import { addUserToGuild } from "../../services/discord/puxarDiscord.js";
import { assessRisk, checkDiscordAccountAge } from "../../services/riskAssessment.js";
import mongoose from "mongoose";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import getClientIp from "../../functions/getClientIp.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const router = express.Router();

// ─── POST /apps/free ─────────────────────────────────────────────────────────
router.post("/free", async (req, res) => {
  try {
    const userId = req.user._id;
    const ip = getClientIp(req);

    // 1. Carrega configuração do plano gratuito
    const freeConfig = await FreePlanConfig.findOne({ active: true }).lean();
    if (!freeConfig) {
      return res.status(503).json({
        success: false,
        error: "Indisponível",
        message: "O plano gratuito não está disponível no momento.",
      });
    }

    const user = await User.findById(userId).select("discordId oauth email createdAt freePlanRedeemed ipHistory globalName username");
    if (!user?.discordId) {
      return res.status(400).json({
        success: false,
        error: "Conta Discord não vinculada",
        message: "Você precisa ter uma conta Discord vinculada para criar um plano gratuito.",
      });
    }

    // 2. Verificação de idade mínima da conta Discord
    const ageCheck = checkDiscordAccountAge(user.discordId, freeConfig.minAccountAgeDays);
    if (!ageCheck.ok) {
      return res.status(403).json({
        success: false,
        error: "Conta muito nova",
        message: `Sua conta Discord precisa ter pelo menos ${ageCheck.required} dias. Sua conta tem ${ageCheck.ageDays} dia(s).`,
        details: {
          ageDays: ageCheck.ageDays,
          required: ageCheck.required,
          createdAt: ageCheck.createdAt,
        },
      });
    }

    // 3. Avaliação de risco (VPN, proxy, alt-account, etc.)
    const risk = await assessRisk({
      user,
      ip,
      minAccountAgeDays: freeConfig.minAccountAgeDays,
    });

    if (risk.score >= freeConfig.maxRiskScore) {
      console.warn(
        `[FREE BOT] Bloqueado userId=${userId} ip=${ip} score=${risk.score} reasons=${risk.reasons.join("; ")}`
      );
      return res.status(403).json({
        success: false,
        error: "Verificação de segurança falhou",
        message:
          "Não foi possível verificar sua conta. Certifique-se de não estar usando VPN ou proxy e tente novamente.",
        riskScore: risk.score,
      });
    }

    // 4. Verifica se já resgatou
    const alreadyRedeemed = await Application.exists({
      userId,
      isFree: true,
      isDeleted: false,
    });
    if (alreadyRedeemed || user.freePlanRedeemed) {
      return res.status(400).json({
        success: false,
        error: "Limite atingido",
        message: "Você já resgatou seu bot gratuito. Apenas 1 resgate é permitido por conta.",
      });
    }

    // 5. Marca como resgatado atomicamente
    const userUpdate = await User.findOneAndUpdate(
      { _id: userId, freePlanRedeemed: { $ne: true } },
      { $set: { freePlanRedeemed: true } }
    );
    if (!userUpdate) {
      return res.status(400).json({
        success: false,
        error: "Limite atingido",
        message: "Você já resgatou seu bot gratuito. Apenas 1 resgate é permitido por conta.",
      });
    }

    // 6. Busca o plano de origem configurado
    const sourcePlan = await Plan.findOne({ id: freeConfig.sourcePlanId }).lean();
    if (!sourcePlan) {
      await User.updateOne({ _id: userId }, { $set: { freePlanRedeemed: false } });
      return res.status(500).json({
        success: false,
        error: "Configuração inválida",
        message: "O plano de origem do bot gratuito não foi encontrado. Contate o suporte.",
      });
    }

    // 7. Localiza ZIP
    let zipPath = null;
    if (sourcePlan.zipFilename) {
      const possiblePaths = [
        path.resolve(process.cwd(), "src/database/zip", sourcePlan.zipFilename),
        path.resolve(process.cwd(), "backend/src/database/zip", sourcePlan.zipFilename),
        path.join(__dirname, "../../database/zip", sourcePlan.zipFilename),
      ];
      for (const testPath of possiblePaths) {
        if (fs.existsSync(testPath)) {
          zipPath = testPath;
          break;
        }
      }
    }

    const botID = new mongoose.Types.ObjectId().toString();
    const now = new Date();
    const expiresAt = freeConfig.durationDays
      ? new Date(now.getTime() + freeConfig.durationDays * 24 * 60 * 60 * 1000)
      : null; // null = sem expiração (vitalício)

    const applicationPayload = {
      userId,
      paymentId: null,
      name: `${sourcePlan.name} (Free)`,
      botID,
      plan: {
        id: sourcePlan.id,
        name: `${sourcePlan.name} (Free)`,
        months: null,
        price: 0,
        paymentId: null,
      },
      hosting: {
        provider: "discloud",
        status: "deploying",
        createdAt: now,
        updatedAt: now,
      },
      bot: {
        token: null,
        owner: user.discordId,
        id: null,
        perms: [String(user.discordId)],
        server: null,
      },
      info: { name: `${sourcePlan.name} Free`, imageUrl: null, id: null },
      expiresAt,
      isFree: true,
      lastStartedAt: now,
      inactivityWarningSentAt: null,
      // Metadados de risco para auditoria
      _riskScore: risk.score,
    };

    const newApp = await Application.create(applicationPayload);

    // 8. Deploy
    if (zipPath) {
      try {
        const deployResult = await deployBotWithConfig(
          zipPath,
          botID,
          user.discordId,
          sourcePlan.version
        );
        const response = deployResult.discloudResponse;
        const appId = deployResult.appId;

        newApp.hosting = {
          provider: "discloud",
          appId: appId ? String(appId) : "",
          name: response?.name || null,
          ram: response?.ram || null,
          version: response?.version || null,
          main: response?.main || null,
          status: response?.message || response?.status || "online",
          url: null,
          createdAt: now,
          updatedAt: new Date(),
          lastDeployAt: new Date(),
        };
        await newApp.save();
      } catch (deployError) {
        console.error("[FREE BOT] Erro no deploy:", deployError);
        newApp.hosting.status = "error";
        await newApp.save();
      }
    } else {
      newApp.hosting.status = "created";
      await newApp.save();
    }

    res.status(201).json({
      success: true,
      message: "Bot gratuito criado com sucesso!",
      data: {
        applicationId: newApp._id,
        name: newApp.name,
        plan: newApp.plan,
        hosting: newApp.hosting,
        expiresAt: newApp.expiresAt,
        riskScore: risk.score, // informativo
      },
    });

    // 9. Cargo Discord (best-effort)
    try {
      const roleId = sourcePlan.discordRoleId || process.env.DISCORD_DEFAULT_ROLE_ID;
      if (roleId && user.discordId) {
        if (user.oauth?.accessToken) {
          try {
            await addUserToGuild({
              userId: user.discordId,
              accessToken: user.oauth.accessToken,
              guildId: process.env.DISCORD_GUILD_ID,
            });
          } catch (e) {
            console.warn("[FREE BOT] Erro ao adicionar user na guilda:", e.message);
          }
        }
        await addRoleToMember({
          userId: user.discordId,
          roleId,
          guildId: process.env.DISCORD_GUILD_ID,
        });
      }
    } catch (roleError) {
      console.warn("[FREE BOT] Falha ao atribuir cargo:", roleError.message);
    }
  } catch (error) {
    if (error.code === 11000) {
      // Desfaz flag se foi erro de duplicata
      await User.updateOne({ _id: req.user._id }, { $set: { freePlanRedeemed: false } }).catch(() => {});
      return res.status(400).json({
        success: false,
        error: "Limite atingido",
        message: "Você já possui um bot gratuito. Apenas 1 permitido.",
      });
    }
    console.error("[FREE BOT CREATE] Erro:", error);
    res.status(500).json({ success: false, error: "Erro ao criar bot", message: error.message });
  }
});

// ─── GET /apps/free/check ─────────────────────────────────────────────────────
router.get("/free/check", async (req, res) => {
  try {
    const userId = req.user._id;
    const ip = getClientIp(req);
    const user = await User.findById(userId).select("discordId email createdAt freePlanRedeemed ipHistory").lean();

    const freeConfig = await FreePlanConfig.findOne({ active: true }).lean();
    const minDays = freeConfig?.minAccountAgeDays ?? 15;
    const maxRisk = freeConfig?.maxRiskScore ?? 60;

    const existingFreeApp = await Application.exists({ userId, isFree: true, isDeleted: false });

    // Verificação de idade
    const ageCheck = checkDiscordAccountAge(user?.discordId, minDays);

    // Score de risco (rápido, sem bloquear)
    let riskScore = 0;
    let riskReasons = [];
    if (user) {
      const risk = await assessRisk({ user, ip, minAccountAgeDays: minDays });
      riskScore = risk.score;
      riskReasons = risk.reasons;
    }

    return res.json({
      success: true,
      canCreate: !existingFreeApp && !user?.freePlanRedeemed,
      existingCount: existingFreeApp ? 1 : 0,
      accountAge: {
        ok: ageCheck.ok,
        ageDays: ageCheck.ageDays,
        required: minDays,
        createdAt: ageCheck.createdAt,
      },
      risk: {
        score: riskScore,
        blocked: riskScore >= maxRisk,
        reasons: riskReasons,
      },
      config: freeConfig
        ? {
            durationDays: freeConfig.durationDays,
            sourcePlanId: freeConfig.sourcePlanId,
          }
        : null,
    });
  } catch (error) {
    res.status(500).json({ success: false, error: "Erro ao verificar" });
  }
});

export default router;

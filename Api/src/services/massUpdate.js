/**
 * Serviço de atualização em massa de bots
 *
 * Suporta:
 *  - Um único planId (retrocompatível)
 *  - Array de planIds (ex: ["amethys-pro", "amethys-pro-gift"])
 *  - planId = "all" → atualiza TODOS os planos ativos
 *
 * Garante que todos os bots com hosting.appId válido na Discloud recebam
 * o commit, independente do plano.
 */

import Application from "../database/models/Application.js";
import Plan from "../database/models/Plan.js";
import UpdateLog from "../database/models/UpdateLog.js";
import { commitApp } from "./discloud/commit.js";
import { setRestartFlag } from "../utils/setRestartFlag.js";
import discloudService from "./discloudService.js";
import fs from "fs";

// Progresso em memória (para atualizações em andamento)
const updateProgress = new Map();

function generateUpdateVersion(label) {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8).toUpperCase();
  return `${label}-${timestamp}-${random}`;
}

/**
 * Inicia uma atualização em massa.
 *
 * @param {string|string[]} planIdOrIds
 *   Um planId, array de planIds, ou a string especial "all" para todos os planos.
 * @param {string|Buffer} zipPath   Caminho do ZIP de atualização OU Buffer direto do ZIP
 * @param {string}   adminUserId    ID do admin que disparou a atualização
 * @param {string}   [customVersion] Versão personalizada (gerada automaticamente se omitida)
 * @param {string[]} [foldersToDelete] Pastas a remover antes do commit
 */
export async function startMassUpdate(
  planIdOrIds,
  zipPath,
  adminUserId,
  customVersion = null,
  foldersToDelete = []
) {
  // Normaliza planIds para array
  let planIds;
  if (planIdOrIds === "all") {
    // Busca todos os planos ativos para usar como label; a query de apps não filtra por plano
    planIds = ["all"];
  } else if (Array.isArray(planIdOrIds)) {
    planIds = planIdOrIds.filter(Boolean);
  } else {
    planIds = [planIdOrIds];
  }

  const label = planIds.join("+");
  const updateId = `update-${Date.now()}`;
  const updateVersion = customVersion || generateUpdateVersion(label);

  console.log(
    `[MASS UPDATE] startMassUpdate — planIds: [${planIds.join(", ")}], updateId: ${updateId}`
  );

  const progress = {
    id: updateId,
    planIds,
    // Mantém planId singular para retrocompatibilidade com o UpdateLog existente
    planId: label,
    updateVersion,
    foldersToDelete,
    status: "running",
    startedAt: new Date(),
    finishedAt: null,
    total: 0,
    processed: 0,
    successful: 0,
    failed: 0,
    skipped: 0,
    logs: [],
    errors: [],
  };

  updateProgress.set(updateId, progress);

  try {
    const updateLog = new UpdateLog({
      updateId,
      planId: label,
      updateVersion,
      adminUserId,
      status: "running",
      startedAt: progress.startedAt,
      stats: { total: 0, processed: 0, successful: 0, failed: 0, skipped: 0 },
      logs: [],
      errors: [],
    });
    await updateLog.save();
  } catch (error) {
    console.error(`[MASS UPDATE] Erro ao salvar UpdateLog:`, error);
    throw error;
  }

  // Executa em background
  processUpdate(updateId, planIds, zipPath, adminUserId, foldersToDelete).catch((error) => {
    console.error("[MASS UPDATE] Erro fatal no processamento:", error);
    progress.status = "error";
    progress.logs.push({
      timestamp: new Date(),
      type: "error",
      message: `Erro fatal: ${error.message}`,
    });
    UpdateLog.updateOne(
      { updateId },
      {
        $set: { status: "error" },
        $push: { logs: { timestamp: new Date(), type: "error", message: `Erro fatal: ${error.message}` } },
      }
    ).catch((err) => console.error("[MASS UPDATE] Erro ao salvar log:", err));
  });

  return updateId;
}

// ─── Helpers de log/stats ────────────────────────────────────────────────────

async function addLog(updateId, type, message) {
  const progress = updateProgress.get(updateId);
  const logEntry = { timestamp: new Date(), type, message };
  if (progress) {
    progress.logs.push(logEntry);
    // Mantém no máximo 200 logs em memória — histórico completo fica no MongoDB
    if (progress.logs.length > 200) progress.logs.shift();
  }
  try {
    await UpdateLog.updateOne({ updateId }, { $push: { logs: logEntry } });
  } catch (error) {
    console.error("[MASS UPDATE] Erro ao salvar log no MongoDB:", error);
  }
}

async function updateStats(updateId, stats) {
  const progress = updateProgress.get(updateId);
  if (progress) Object.assign(progress, stats);
  try {
    const updateFields = {};
    if (stats.total !== undefined) updateFields["stats.total"] = stats.total;
    if (stats.processed !== undefined) updateFields["stats.processed"] = stats.processed;
    if (stats.successful !== undefined) updateFields["stats.successful"] = stats.successful;
    if (stats.failed !== undefined) updateFields["stats.failed"] = stats.failed;
    if (stats.skipped !== undefined) updateFields["stats.skipped"] = stats.skipped;
    if (Object.keys(updateFields).length > 0) {
      await UpdateLog.updateOne({ updateId }, { $set: updateFields });
    }
  } catch (error) {
    console.error("[MASS UPDATE] Erro ao atualizar stats no MongoDB:", error);
  }
}

// ─── Processamento ───────────────────────────────────────────────────────────

async function processUpdate(updateId, planIds, zipPath, adminUserId, foldersToDelete = []) {
  const progress = updateProgress.get(updateId);
  // Declarado fora do try para que o finally consiga acessar sem ReferenceError
  const zipIsBuffer = Buffer.isBuffer(zipPath);

  try {
    if (!zipIsBuffer && !fs.existsSync(zipPath)) {
      throw new Error(`Arquivo ZIP não encontrado: ${zipPath}`);
    }

    await addLog(updateId, "info", `Iniciando atualização em massa — planos: [${planIds.join(", ")}]`);
    await addLog(updateId, "info", `Código de referência: ${progress.updateVersion}`);

    // ── Monta a query de aplicações ────────────────────────────────────────
    const baseQuery = {
      isDeleted: { $ne: true },
      // isBlocked intencionalmente não filtrado: apps bloqueadas pelo sistema de cobrança
      // ainda existem e rodam na Discloud — o commit deve chegar em todas elas.
      "hosting.appId": { $exists: true, $ne: null, $nin: ["", " "] },
    };

    if (!planIds.includes("all")) {
      baseQuery["plan.id"] = { $in: planIds };
    }

    const applications = await Application.find(baseQuery).select(
      "_id name botID hosting.appId plan.id updateVersion"
    ).lean();

    progress.total = applications.length;
    await updateStats(updateId, { total: applications.length });
    await addLog(updateId, "info", `${applications.length} aplicação(ões) encontrada(s) para atualizar`);

    if (applications.length === 0) {
      progress.status = "completed";
      progress.finishedAt = new Date();
      await addLog(updateId, "warning", "Nenhuma aplicação ativa encontrada para atualizar");
      await UpdateLog.updateOne(
        { updateId },
        { $set: { status: "completed", finishedAt: progress.finishedAt } }
      );
      return;
    }

    // Lê o ZIP uma única vez como Buffer (imutável, seguro para reuso entre bots)
    // Aceita Buffer direto (vindo do githubUpdateService) ou path de arquivo
    const fileBuffer = zipIsBuffer ? zipPath : fs.readFileSync(zipPath);

    // ── Processamento em lotes concorrentes ────────────────────────────────
    // Limite conservador para não sobrecarregar a Discloud com uploads simultâneos
    const CONCURRENT_LIMIT = 3;

    async function processApplication(app, index, total) {
      const appId = app.hosting.appId;

      try {
        if (!appId || String(appId).trim() === "") {
          await addLog(updateId, "warning", `⚠️ ${app.name} — Ignorado: appId ausente`);
          progress.skipped++;
          progress.processed++;
          return;
        }

        // Pula apps já na versão atual (idempotência)
        if (app.updateVersion === progress.updateVersion) {
          progress.skipped++;
          progress.processed++;
          return;
        }

        await addLog(
          updateId, "info",
          `[${index + 1}/${total}] Processando ${app.name} (${appId}) — plano: ${app.plan?.id || "?"}...`
        );

        // Remove pastas via console da Discloud antes do commit
        if (foldersToDelete.length > 0) {
          for (const folder of foldersToDelete) {
            const safe = folder.replace(/[^a-zA-Z0-9_\-./]/g, "");
            if (!safe) continue;
            const result = await discloudService.exec(appId, `rm -rf /home/container/${safe}`);
            if (result.success) {
              await addLog(updateId, "info", `🗑️ ${app.name}: pasta '${safe}' removida`);
            } else {
              await addLog(updateId, "warning", `⚠️ ${app.name}: falha ao remover '${safe}': ${result.error}`);
            }
          }
        }

        if (app.botID) {
          await setRestartFlag(app.botID);
        }

        const commitResult = await commitApp(appId, fileBuffer);

        if (commitResult.success) {
          // lean() retorna objeto simples, usar updateOne em vez de .save()
          await Application.updateOne(
            { _id: app._id },
            { $set: { updateVersion: progress.updateVersion, lastUpdateAt: new Date() } }
          );

          progress.successful++;
          await addLog(updateId, "success", `✅ ${app.name} atualizado com sucesso`);
        } else {
          throw new Error(commitResult.error || "Erro desconhecido no commit");
        }

      } catch (error) {
        progress.failed++;
        const msg =
          error.message ||
          error.cause?.message ||
          error.cause?.code ||
          "Erro desconhecido";

        // Se a app não existe na Discloud, limpa o appId para não tentar novamente
        if (
          msg.includes("não encontrada") ||
          msg.includes("not found") ||
          msg.includes("404")
        ) {
          try {
            await Application.updateOne(
              { _id: app._id },
              { $set: { "hosting.appId": null, invalidHosting: true } }
            );
            await addLog(
              updateId, "warning",
              `⚠️ ${app.name}: appId inválido removido (app não existe na Discloud)`
            );
          } catch (dbErr) {
            console.error("[MASS UPDATE] Erro ao limpar appId inválido:", dbErr.message);
          }
        }

        await addLog(updateId, "error", `❌ Falha em ${app.name}: ${msg}`);
      } finally {
        progress.processed++;
        // Não escreve no MongoDB aqui — updateStats é chamado uma vez por lote abaixo
      }
    }

    // Processa em lotes de CONCURRENT_LIMIT
    // updateStats é escrito uma vez por lote em vez de uma vez por bot (menos writes no Mongo)
    for (let i = 0; i < applications.length; i += CONCURRENT_LIMIT) {
      const batch = applications.slice(i, i + CONCURRENT_LIMIT);
      await Promise.all(
        batch.map((app, batchIndex) => processApplication(app, i + batchIndex, applications.length))
      );
      await updateStats(updateId, {
        processed: progress.processed,
        successful: progress.successful,
        failed: progress.failed,
        skipped: progress.skipped,
      });
    }

    progress.status = "completed";
    progress.finishedAt = new Date();

    await addLog(
      updateId, "info",
      `Atualização concluída — ✅ ${progress.successful} sucesso(s), ❌ ${progress.failed} falha(s), ⏭ ${progress.skipped} ignorado(s)`
    );

    await UpdateLog.updateOne(
      { updateId },
      { $set: { status: "completed", finishedAt: progress.finishedAt } }
    );

  } catch (error) {
    console.error("[MASS UPDATE] Erro no processamento:", error);
    progress.status = "error";
    await addLog(updateId, "error", `Erro no processamento: ${error.message}`);
    await UpdateLog.updateOne(
      { updateId },
      { $set: { status: "error" } }
    ).catch(() => {});
  } finally {
    // Remove o ZIP temporário após o processamento (somente se veio de arquivo, não Buffer)
    try {
      if (!zipIsBuffer && zipPath && fs.existsSync(zipPath)) fs.unlinkSync(zipPath);
    } catch (_) { /* silencioso */ }

    // Remove entrada do Map após 10 minutos para não acumular RAM indefinidamente
    // (mantém tempo suficiente para o front consultar o progresso final)
    setTimeout(() => updateProgress.delete(updateId), 10 * 60 * 1000);
  }
}

// ─── Exports públicos ────────────────────────────────────────────────────────

export function getUpdateProgress(updateId) {
  return updateProgress.get(updateId);
}

/**
 * Retorna a versão mais recente de um conjunto de planos com base nos logs concluídos.
 * @param {string|string[]} planIdOrIds
 */
export async function getLatestPlanVersion(planIdOrIds) {
  const label = Array.isArray(planIdOrIds) ? planIdOrIds.join("+") : planIdOrIds;
  const log = await UpdateLog.findOne(
    { planId: label, status: "completed" },
    { updateVersion: 1 },
    { sort: { startedAt: -1 } }
  ).lean();
  return log?.updateVersion ?? null;
}
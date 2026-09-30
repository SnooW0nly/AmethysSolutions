/**
 * src/tasks/discloud/discloudSync.js
 *
 * Task de sincronização profunda entre a Discloud e o MongoDB.
 *
 * Problema resolvido:
 *   A Discloud pode ter N apps que não estão corretamente refletidas no banco
 *   (hosting.appId ausente, status desatualizado, nome divergente, apps
 *   "fantasma" sem registro, apps no DB sem hosting real, contagem errada, etc).
 *
 * O que este serviço faz a cada ciclo:
 *
 *  1. INVENTÁRIO
 *     - Busca TODOS os apps da Discloud via `GET /app/all`.
 *     - Busca TODAS as Applications não deletadas do MongoDB.
 *
 *  2. CRUZAMENTO
 *     - Para cada app da Discloud, tenta encontrar o registro correspondente
 *       no MongoDB pelo campo `hosting.appId`.
 *     - Se não achar por `hosting.appId`, tenta por `hosting.name` ou `name`
 *       (fallback de reconciliação).
 *
 *  3. CORREÇÕES AUTOMÁTICAS no MongoDB
 *     a) App existe na Discloud mas o registro não tem `hosting.appId`
 *        → preenche `hosting.appId`, `hosting.name`, `hosting.status`, etc.
 *     b) `hosting.status`, `hosting.ram`, `hosting.version`, `hosting.main`
 *        divergem do estado real da Discloud → atualiza.
 *     c) App existe na Discloud mas não tem nenhum registro no banco
 *        → loga como "app ÓRFÃ na Discloud" (não cria nada automaticamente —
 *          isso exigiria decisão humana).
 *     d) Registro no banco tem `hosting.appId` mas a Discloud não conhece
 *        esse ID → loga como "app FANTASMA no banco" e marca
 *        `hosting.status = "not_found"` para que a UI possa alertar.
 *
 *  4. RELATÓRIO
 *     - Ao final de cada ciclo, imprime um resumo completo com contagens e
 *       lista de divergências encontradas/corrigidas.
 *
 * Uso:
 *   import { startDiscloudSync } from "./tasks/discloud/discloudSync.js";
 *   startDiscloudSync(); // chame uma vez ao subir o servidor
 */

import Application from "../../database/models/Application.js";
import discloudService from "../../services/discloudService.js";

// ─── Configurações ────────────────────────────────────────────────────────────

/** Intervalo entre ciclos completos (padrão: 15 minutos) */
const CYCLE_INTERVAL_MS = 15 * 60 * 1000;

/** Delay entre updates no MongoDB para não sobrecarregar */
const DB_OP_DELAY_MS = 100;

// ─── Estado interno ───────────────────────────────────────────────────────────

let _intervalId = null;
let _isCycleRunning = false;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

/**
 * Normaliza o status retornado pela Discloud para um valor consistente.
 * A Discloud retorna strings como "Online", "Offline", "Starting"…
 */
function normalizeDiscloudStatus(container) {
  if (!container) return "unknown";
  const lower = String(container).toLowerCase();
  if (lower === "online") return "online";
  if (lower === "offline") return "offline";
  if (lower.includes("restart")) return "restarting";
  if (lower.includes("start")) return "starting";
  return lower;
}

/**
 * Compara dois valores normalizando nulos/undefined como strings vazias.
 */
function isDiff(a, b) {
  return String(a ?? "") !== String(b ?? "");
}

// ─── Ciclo principal ──────────────────────────────────────────────────────────

async function runDiscloudSyncCycle() {
  const cycleStart = Date.now();
  console.log("[DISCLOUD SYNC] ▶ Iniciando ciclo de sincronização...");

  // ── 1. INVENTÁRIO ─────────────────────────────────────────────────────────

  // 1a. Busca todos os apps da Discloud
  const discloudResult = await discloudService.listAllApps();

  if (!discloudResult.success) {
    console.error(
      "[DISCLOUD SYNC] ✗ Falha ao listar apps da Discloud:",
      discloudResult.error
    );
    return;
  }

  /** @type {Array<{appId: string, name: string, ram: number, version: string, main: string, online: boolean, container: string}>} */
  const discloudApps = discloudResult.apps ?? [];

  console.log(`[DISCLOUD SYNC] 📡 Apps na Discloud: ${discloudApps.length}`);

  // 1b. Busca todos os registros não deletados do MongoDB
  const dbApps = await Application.find({ isDeleted: false }).lean();

  console.log(`[DISCLOUD SYNC] 🗄  Registros no MongoDB (não deletados): ${dbApps.length}`);

  // ── 2. ÍNDICES PARA CRUZAMENTO ────────────────────────────────────────────

  // Indexa apps da Discloud por appId (campo que a Discloud chama de "appId" ou "id")
  /** @type {Map<string, object>} */
  const discloudById = new Map();
  for (const app of discloudApps) {
    const id = app.appId || app.id;
    if (id) discloudById.set(String(id), app);
  }

  // Indexa registros do MongoDB por hosting.appId
  /** @type {Map<string, object>} */
  const dbByHostingAppId = new Map();
  // Também indexa por name (fallback de reconciliação)
  /** @type {Map<string, object>} */
  const dbByName = new Map();

  for (const app of dbApps) {
    const hid = app.hosting?.appId;
    if (hid) dbByHostingAppId.set(String(hid), app);
    if (app.name) dbByName.set(String(app.name).toLowerCase(), app);
    // Também tenta pelo hosting.name
    if (app.hosting?.name) dbByName.set(String(app.hosting.name).toLowerCase(), app);
  }

  // ── 3. ANÁLISE E CORREÇÕES ────────────────────────────────────────────────

  const report = {
    discloudTotal: discloudApps.length,
    dbTotal: dbApps.length,
    matched: 0,
    updated: 0,
    orphansInDiscloud: [],   // na Discloud, sem registro no DB
    ghostsInDb: [],          // no DB com appId, mas Discloud não reconhece
    missingAppId: [],        // no DB sem hosting.appId mas encontrado por nome
    fieldCorrections: [],    // campos atualizados
    errors: [],
  };

  // ── 3a. Percorre apps da Discloud e cruza com MongoDB ─────────────────────

  for (const dcApp of discloudApps) {
    const dcId = String(dcApp.appId || dcApp.id || "");
    const dcName = String(dcApp.name || "");
    const dcStatus = normalizeDiscloudStatus(dcApp.container);
    const dcRam = dcApp.ram ?? null;
    const dcVersion = dcApp.version ?? null;
    const dcMain = dcApp.main ?? null;

    // Tenta encontrar por appId primeiro
    let dbApp = dcId ? dbByHostingAppId.get(dcId) : null;

    // Fallback: tenta por nome
    if (!dbApp && dcName) {
      dbApp = dbByName.get(dcName.toLowerCase());
    }

    if (!dbApp) {
      // Não encontrou registro no MongoDB para este app da Discloud
      report.orphansInDiscloud.push({ appId: dcId, name: dcName, status: dcStatus });
      console.warn(
        `[DISCLOUD SYNC] ⚠ App ÓRFÃ na Discloud — id: ${dcId || "(sem id)"}, nome: "${dcName}" — sem registro correspondente no MongoDB`
      );
      continue;
    }

    report.matched++;

    // Monta os campos que precisam ser atualizados
    const $set = {};

    // 3a-i. hosting.appId ausente ou diferente
    if (!dbApp.hosting?.appId && dcId) {
      $set["hosting.appId"] = dcId;
      report.missingAppId.push({ dbId: String(dbApp._id), name: dbApp.name, dcId });
      console.log(
        `[DISCLOUD SYNC] 🔗 hosting.appId preenchido → "${dbApp.name}" (db: ${dbApp._id}) ← "${dcId}"`
      );
    }

    // 3a-ii. hosting.name
    if (isDiff(dbApp.hosting?.name, dcName) && dcName) {
      $set["hosting.name"] = dcName;
    }

    // 3a-iii. hosting.status
    if (isDiff(dbApp.hosting?.status, dcStatus)) {
      $set["hosting.status"] = dcStatus;
    }

    // 3a-iv. hosting.ram
    if (isDiff(dbApp.hosting?.ram, dcRam) && dcRam !== null) {
      $set["hosting.ram"] = dcRam;
    }

    // 3a-v. hosting.version
    if (isDiff(dbApp.hosting?.version, dcVersion) && dcVersion !== null) {
      $set["hosting.version"] = dcVersion;
    }

    // 3a-vi. hosting.main
    if (isDiff(dbApp.hosting?.main, dcMain) && dcMain !== null) {
      $set["hosting.main"] = dcMain;
    }

    // 3a-vii. Marca provider como discloud (garante consistência)
    if (!dbApp.hosting?.provider || dbApp.hosting.provider !== "discloud") {
      $set["hosting.provider"] = "discloud";
    }

    if (Object.keys($set).length > 0) {
      try {
        await Application.updateOne({ _id: dbApp._id }, { $set });
        report.updated++;
        report.fieldCorrections.push({
          dbId: String(dbApp._id),
          name: dbApp.name,
          fields: Object.keys($set),
        });
        console.log(
          `[DISCLOUD SYNC] 🔧 Atualizado "${dbApp.name}" — campos: ${Object.keys($set).join(", ")}`
        );
        await sleep(DB_OP_DELAY_MS);
      } catch (err) {
        report.errors.push({ dbId: String(dbApp._id), error: err.message });
        console.error(
          `[DISCLOUD SYNC] ✗ Erro ao atualizar "${dbApp.name}":`,
          err.message
        );
      }
    }
  }

  // ── 3b. Percorre registros do MongoDB com hosting.appId e verifica se a Discloud os reconhece ──

  for (const dbApp of dbApps) {
    const hid = dbApp.hosting?.appId;
    if (!hid) continue; // sem appId no banco, já tratado acima

    const existsInDiscloud = discloudById.has(String(hid));

    if (!existsInDiscloud) {
      // App no banco com appId, mas Discloud não tem esse app
      report.ghostsInDb.push({
        dbId: String(dbApp._id),
        name: dbApp.name,
        appId: hid,
        isBlocked: dbApp.isBlocked,
        expiresAt: dbApp.expiresAt,
      });

      console.warn(
        `[DISCLOUD SYNC] 👻 App FANTASMA no banco — "${dbApp.name}" (db: ${dbApp._id}) ` +
        `tem hosting.appId="${hid}" mas esse ID não existe na Discloud`
      );

      // Marca status como not_found no banco para a UI poder alertar
      try {
        const currentStatus = dbApp.hosting?.status;
        if (currentStatus !== "not_found") {
          await Application.updateOne(
            { _id: dbApp._id },
            { $set: { "hosting.status": "not_found" } }
          );
          console.log(
            `[DISCLOUD SYNC] 🏷  hosting.status → "not_found" para "${dbApp.name}"`
          );
          await sleep(DB_OP_DELAY_MS);
        }
      } catch (err) {
        report.errors.push({ dbId: String(dbApp._id), error: err.message });
      }
    }
  }

  // ── 4. RELATÓRIO FINAL ────────────────────────────────────────────────────

  const elapsed = ((Date.now() - cycleStart) / 1000).toFixed(1);

  console.log("\n[DISCLOUD SYNC] ══════════════ RELATÓRIO DO CICLO ══════════════");
  console.log(`[DISCLOUD SYNC]   Duração               : ${elapsed}s`);
  console.log(`[DISCLOUD SYNC]   Apps na Discloud       : ${report.discloudTotal}`);
  console.log(`[DISCLOUD SYNC]   Registros no MongoDB   : ${report.dbTotal}`);
  console.log(`[DISCLOUD SYNC]   Correspondências       : ${report.matched}`);
  console.log(`[DISCLOUD SYNC]   Registros atualizados  : ${report.updated}`);
  console.log(`[DISCLOUD SYNC]   Apps ÓRFÃS (Discloud)  : ${report.orphansInDiscloud.length}`);
  console.log(`[DISCLOUD SYNC]   Apps FANTASMAS (DB)    : ${report.ghostsInDb.length}`);
  console.log(`[DISCLOUD SYNC]   appId preenchidos      : ${report.missingAppId.length}`);
  console.log(`[DISCLOUD SYNC]   Erros                  : ${report.errors.length}`);

  if (report.orphansInDiscloud.length > 0) {
    console.log("[DISCLOUD SYNC]   ── Apps órfãs na Discloud (sem registro no DB):");
    for (const o of report.orphansInDiscloud) {
      console.log(`[DISCLOUD SYNC]      • ${o.name} (${o.appId}) — status: ${o.status}`);
    }
  }

  if (report.ghostsInDb.length > 0) {
    console.log("[DISCLOUD SYNC]   ── Apps fantasmas no DB (appId inexistente na Discloud):");
    for (const g of report.ghostsInDb) {
      console.log(
        `[DISCLOUD SYNC]      • "${g.name}" (db: ${g.dbId}) — appId: ${g.appId}` +
        (g.isBlocked ? " [bloqueado]" : "") +
        (g.expiresAt ? ` | expira: ${new Date(g.expiresAt).toISOString()}` : "")
      );
    }
  }

  if (report.fieldCorrections.length > 0) {
    console.log("[DISCLOUD SYNC]   ── Campos corrigidos:");
    for (const c of report.fieldCorrections) {
      console.log(`[DISCLOUD SYNC]      • "${c.name}" → ${c.fields.join(", ")}`);
    }
  }

  if (report.errors.length > 0) {
    console.log("[DISCLOUD SYNC]   ── Erros:");
    for (const e of report.errors) {
      console.log(`[DISCLOUD SYNC]      ✗ db:${e.dbId} — ${e.error}`);
    }
  }

  console.log("[DISCLOUD SYNC] ════════════════════════════════════════════════\n");

  return report;
}

// ─── API pública ──────────────────────────────────────────────────────────────

/**
 * Inicia a task de sincronização Discloud ↔ MongoDB.
 * Roda imediatamente e depois a cada CYCLE_INTERVAL_MS.
 */
export async function startDiscloudSync() {
  if (_intervalId) {
    console.warn("[DISCLOUD SYNC] Serviço já está rodando");
    return;
  }

  console.log(
    `[DISCLOUD SYNC] 🚀 Serviço iniciado — ciclo a cada ${CYCLE_INTERVAL_MS / 60_000} minutos`
  );

  // Primeiro ciclo imediato
  runDiscloudSyncCycle().catch((err) =>
    console.error("[DISCLOUD SYNC] Erro no ciclo inicial:", err.message)
  );

  _intervalId = setInterval(async () => {
    if (_isCycleRunning) {
      console.warn("[DISCLOUD SYNC] Ciclo anterior ainda em execução — pulando");
      return;
    }
    _isCycleRunning = true;
    try {
      await runDiscloudSyncCycle();
    } catch (err) {
      console.error("[DISCLOUD SYNC] Erro no ciclo:", err.message);
    } finally {
      _isCycleRunning = false;
    }
  }, CYCLE_INTERVAL_MS);
}

/**
 * Para o serviço de sincronização.
 */
export function stopDiscloudSync() {
  if (_intervalId) {
    clearInterval(_intervalId);
    _intervalId = null;
  }
  _isCycleRunning = false;
  console.log("[DISCLOUD SYNC] Serviço parado");
}

/**
 * Força execução imediata de um ciclo.
 * Útil para acionar manualmente via rota admin.
 *
 * @returns {Promise<object>} Relatório do ciclo
 */
export async function forceDiscloudSync() {
  console.log("[DISCLOUD SYNC] 🔁 Execução forçada solicitada");
  return runDiscloudSyncCycle();
}
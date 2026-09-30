/**
 * githubUpdateService.js
 *
 * Responsável por:
 *  1. Validar a assinatura HMAC do webhook do GitHub
 *  2. Extrair do payload os arquivos added/modified/removed de todos os commits do push
 *  3. Baixar apenas os arquivos alterados via GitHub Contents API
 *  4. Montar um ZIP mínimo (só os arquivos que mudaram) mantendo o caminho completo
 *  5. Disparar o massUpdate com esse ZIP + foldersToDelete dos arquivos removidos
 *
 * Resultado: em vez de mandar 10MB por bot, manda só os KB que mudaram.
 */

import crypto from "crypto";
import JSZip from "jszip";
import fetch from "node-fetch";
import { startMassUpdate } from "./massUpdate.js";

// ─── Arquivos/pastas que NUNCA devem ser atualizados pelo GitHub ──────────────
// Esses existem localmente em cada bot e são exclusivos de cada instância.
const PROTECTED_PATHS = [
  "config.json",
  "database/",
  "database_template.json",
  "requirements.txt",
];

/**
 * Verifica se um caminho é protegido (não deve ser sobrescrito).
 * @param {string} filePath
 * @returns {boolean}
 */
function isProtected(filePath) {
  return PROTECTED_PATHS.some(
    (p) => filePath === p || filePath.startsWith(p)
  );
}

/**
 * Valida a assinatura HMAC-SHA256 enviada pelo GitHub no header X-Hub-Signature-256.
 *
 * @param {string} secret     - GITHUB_WEBHOOK_SECRET do .env
 * @param {string} signature  - Valor do header X-Hub-Signature-256
 * @param {Buffer} rawBody    - Body cru da requisição (Buffer)
 * @returns {boolean}
 */
export function validateGithubSignature(secret, signature, rawBody) {
  if (!signature || !signature.startsWith("sha256=")) return false;
  const expected = "sha256=" + crypto
    .createHmac("sha256", secret)
    .update(rawBody)
    .digest("hex");
  // Comparação em tempo constante para evitar timing attacks
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}

/**
 * Extrai os arquivos alterados de todos os commits de um push payload.
 * Deduplica: se o mesmo arquivo aparece em múltiplos commits, conta uma vez.
 * Se um arquivo foi added/modified em um commit mas removed em outro posterior,
 * prevalece o removed.
 *
 * @param {object} payload - Payload JSON do webhook de push do GitHub
 * @returns {{ toUpdate: string[], toDelete: string[] }}
 */
export function extractChangedFiles(payload) {
  const toUpdateSet = new Set();
  const toDeleteSet = new Set();

  const commits = payload.commits || [];

  for (const commit of commits) {
    for (const f of (commit.added || [])) {
      if (!isProtected(f)) {
        toUpdateSet.add(f);
        toDeleteSet.delete(f); // garantia: se antes estava em removed, agora voltou
      }
    }
    for (const f of (commit.modified || [])) {
      if (!isProtected(f)) {
        toUpdateSet.add(f);
        toDeleteSet.delete(f);
      }
    }
    for (const f of (commit.removed || [])) {
      if (!isProtected(f)) {
        toDeleteSet.add(f);
        toUpdateSet.delete(f); // removido prevalece
      }
    }
  }

  return {
    toUpdate: Array.from(toUpdateSet),
    toDelete: Array.from(toDeleteSet),
  };
}

/**
 * Baixa um único arquivo do GitHub via Contents API.
 *
 * @param {string} repo    - "owner/repo"
 * @param {string} ref     - SHA do commit ou branch
 * @param {string} path    - Caminho do arquivo no repo
 * @param {string} token   - GitHub Personal Access Token
 * @returns {Promise<Buffer>} - Conteúdo do arquivo como Buffer
 */
async function downloadFile(repo, ref, path, token) {
  const url = `https://api.github.com/repos/${repo}/contents/${encodeURIComponent(path)}?ref=${ref}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github.raw+json",
      "User-Agent": "AmethysAPI-AutoUpdate/1.0",
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(
      `GitHub API erro ao baixar '${path}': HTTP ${res.status} — ${body.slice(0, 200)}`
    );
  }

  return Buffer.from(await res.arrayBuffer());
}

/**
 * Monta um ZIP com apenas os arquivos alterados, mantendo o caminho completo.
 * Baixa os arquivos em paralelo (sem limite agressivo, são poucos arquivos por push).
 *
 * @param {string[]} filePaths - Lista de caminhos a incluir no ZIP
 * @param {string}   repo      - "owner/repo"
 * @param {string}   ref       - SHA do commit
 * @param {string}   token     - GitHub Personal Access Token
 * @returns {Promise<Buffer>} - ZIP como Buffer
 */
async function buildDiffZip(filePaths, repo, ref, token) {
  const zip = new JSZip();

  // Baixa todos em paralelo — commits normais têm poucos arquivos
  const downloads = filePaths.map(async (filePath) => {
    try {
      const content = await downloadFile(repo, ref, filePath, token);
      zip.file(filePath, content);
      console.log(`[GITHUB UPDATE] ✅ Baixado: ${filePath} (${content.length} bytes)`);
    } catch (err) {
      // Log mas não para o processo — arquivo pode ter sido renomeado/movido
      console.warn(`[GITHUB UPDATE] ⚠️ Não foi possível baixar '${filePath}': ${err.message}`);
    }
  });

  await Promise.all(downloads);

  const fileCount = Object.keys(zip.files).length;
  if (fileCount === 0) {
    throw new Error("Nenhum arquivo foi baixado com sucesso — ZIP ficaria vazio");
  }

  console.log(`[GITHUB UPDATE] ZIP montado com ${fileCount} arquivo(s)`);
  return zip.generateAsync({
    type: "nodebuffer",
    compression: "DEFLATE",
    compressionOptions: { level: 6 },
  });
}

/**
 * Ponto de entrada principal.
 * Processa um webhook de push do GitHub e dispara a atualização em massa.
 *
 * @param {object} payload     - Payload JSON do webhook
 * @param {string} adminUserId - ID do admin (pode ser um ID fixo de sistema)
 * @returns {Promise<{ updateId: string, toUpdate: string[], toDelete: string[], zipSizeKB: number }>}
 */
export async function processGithubPush(payload, adminUserId) {
  const repo   = process.env.GITHUB_REPO;
  const token  = process.env.GITHUB_TOKEN;
  const branch = process.env.GITHUB_BRANCH || "main";

  if (!repo)  throw new Error("GITHUB_REPO não configurado no .env");
  if (!token) throw new Error("GITHUB_TOKEN não configurado no .env");

  // Ignora pushes em branches diferentes do configurado
  const pushedBranch = (payload.ref || "").replace("refs/heads/", "");
  if (pushedBranch !== branch) {
    console.log(`[GITHUB UPDATE] Push ignorado — branch '${pushedBranch}' ≠ '${branch}'`);
    return null;
  }

  // SHA do commit mais recente do push
  const commitSha = payload.after;
  if (!commitSha || commitSha === "0000000000000000000000000000000000000000") {
    console.log("[GITHUB UPDATE] Push ignorado — branch deletada (after = zeros)");
    return null;
  }

  const { toUpdate, toDelete } = extractChangedFiles(payload);

  console.log(`[GITHUB UPDATE] Push detectado — commit: ${commitSha.slice(0, 8)}`);
  console.log(`[GITHUB UPDATE] Arquivos para atualizar: ${toUpdate.length}`);
  console.log(`[GITHUB UPDATE] Arquivos para deletar:   ${toDelete.length}`);

  if (toUpdate.length === 0 && toDelete.length === 0) {
    console.log("[GITHUB UPDATE] Nenhuma mudança relevante detectada (tudo protegido ou vazio)");
    return null;
  }

  // Se só tem arquivos para deletar (sem nada para atualizar),
  // monta um ZIP mínimo com um arquivo marker para o commit não ficar vazio
  let zipBuffer;
  if (toUpdate.length === 0) {
    // ZIP com arquivo de versão apenas para forçar o commit/restart na Discloud
    const zip = new JSZip();
    zip.file(".github_update_version", commitSha);
    zipBuffer = await zip.generateAsync({ type: "nodebuffer" });
    console.log("[GITHUB UPDATE] ZIP mínimo (só deleções) criado com marker de versão");
  } else {
    zipBuffer = await buildDiffZip(toUpdate, repo, commitSha, token);
  }

  const zipSizeKB = Math.round(zipBuffer.length / 1024);
  console.log(`[GITHUB UPDATE] ZIP final: ${zipSizeKB} KB`);

  // Salva o buffer em arquivo temporário para reutilizar a interface do massUpdate
  // (que aceita path de arquivo ou Buffer — usamos Buffer diretamente via nossa versão)
  const updateId = await startMassUpdate(
    "all",
    zipBuffer,          // ← passamos Buffer diretamente (massUpdate já aceita)
    adminUserId,
    `github-${commitSha.slice(0, 8)}`,
    toDelete            // arquivos removidos viram foldersToDelete
  );

  return { updateId, toUpdate, toDelete, zipSizeKB };
}
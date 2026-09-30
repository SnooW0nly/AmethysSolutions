/**
 * Serviço para preparar e fazer deploy de bots com config.json personalizado
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import JSZip from "jszip";
import FormData from "form-data";
import fetch from "node-fetch";
import discloudService from "./discloudService.js";
import BotConfig from "../database/models/BotConfig.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);





/**
 * Gera um botToken de 5 dígitos
 */
function generateBotToken() {
  return String(Math.floor(10000 + Math.random() * 90000));
}

/**
 * Sanitiza string para uso como NAME no discloud.config
 * Remove espaços, acentos e caracteres especiais, deixa apenas letras/números/underscore
 */
function sanitizeName(name) {
  if (!name) return "bot";
  return String(name)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // remove acentos
    .replace(/[^a-zA-Z0-9_]/g, "")  // remove tudo que não for alfanumérico ou _
    .toLowerCase()
    .slice(0, 32)                    // limite de 32 chars por segurança
    || "bot";
}

/**
 * Cria/atualiza BotConfig no MongoDB
 */
async function ensureBotConfig(botID, ownerDiscordId, planVersion = null) {
  let config = await BotConfig.findOne({ botID });

  if (!config) {
    config = new BotConfig({
      botID,
      botToken: generateBotToken(),
      apiURL: process.env.BACKEND_URL || "http://localhost",
      version: planVersion || "BETA",
      syncEmojis: true,
      saveConfig: true,
      startOnBackup: true,
      bot: {
        token: "",
        owner: ownerDiscordId || "",
        id: "",
        perms: ownerDiscordId ? [ownerDiscordId] : [],
        server: "",
      },
    });
    await config.save();
    console.log(`[BOT DEPLOYMENT] BotConfig criado com versão: ${config.version}`);
    return config;
  }

  let changed = false;
  if (ownerDiscordId && config.bot?.owner !== ownerDiscordId) {
    config.bot.owner = ownerDiscordId;
    changed = true;
  }
  const currentPerms = Array.isArray(config.bot?.perms) ? config.bot.perms.slice() : [];
  const targetOwner = ownerDiscordId || config.bot?.owner || "";
  if (targetOwner && !currentPerms.includes(targetOwner)) {
    config.bot.perms = Array.from(new Set([...currentPerms, targetOwner]));
    changed = true;
  } else if (Array.isArray(config.bot?.perms)) {
    const normalized = Array.from(new Set(currentPerms.filter(Boolean)));
    if (normalized.length !== currentPerms.length) {
      config.bot.perms = normalized;
      changed = true;
    }
  }
  if (planVersion && config.version !== planVersion) {
    config.version = planVersion;
    changed = true;
  }
  if (changed) await config.save();
  return config;
}

/**
 * Converte BotConfig para o formato do config.json
 */
function toConfigJson(doc) {
  return {
    botID: doc.botID,
    botToken: doc.botToken,
    apiURL: doc.apiURL,
    version: doc.version ?? "BETA",
    syncEmojis: !!doc.syncEmojis,
    saveConfig: !!doc.saveConfig,
    startOnBackup: !!doc.startOnBackup,
    bot: {
      token: doc.bot?.token || "",
      owner: doc.bot?.owner || "",
      id: doc.bot?.id || "",
      perms: Array.isArray(doc.bot?.perms) ? doc.bot.perms : [],
      server: doc.bot?.server || "",
    },
  };
}

/**
 * Gera conteúdo do discloud.config
 * NAME deve ser sólido (sem espaços ou caracteres especiais)
 * @param {string} ownerDiscordId
 * @param {string} mainFile - arquivo principal detectado (ex: "main.py")
 */
function toDiscloudConfig(ownerDiscordId, mainFile = "bot.py", ram = 175) {
  const name = ownerDiscordId || "bot";
  return `NAME=${name}\nTYPE=bot\nMAIN=${mainFile}\nRAM=${ram}\nAUTORESTART=true\nAPT=tools, \nVERSION=latest\nSTART=python ${mainFile}\nBUILD=pip install --upgrade pip\n`;
}

/**
 * Busca o requirements.txt do banco de dados global, com fallback para o valor padrão
 */
async function getGlobalRequirements() {
  try {
    const GlobalConfig = (await import("../database/models/GlobalConfig.js")).default;
    const config = await GlobalConfig.findOne({ key: "bot_requirements" }).lean();
    if (config?.value) return config.value;
  } catch (err) {
    console.warn("[botDeployment] Falha ao buscar requirements global:", err.message);
  }
  // Fallback
  return `disnake\npy-discord-html-transcripts\npymongo\ndnspython\nrequests\npytz\naiohttp\nwebsockets>=12.0\nPyJWT>=2.8.0\nmatplotlib\npsutil\nPyNaCl\nPillow\n`;
}

/**
 * Lê o ZIP original com JSZip, injeta config.json na raiz
 * Preserva o discloud.config original do ZIP se NAME estiver preenchido;
 * caso NAME= esteja vazio, preenche com ownerDiscordId sanitizado.
 * Devolve um novo buffer sem alterar a estrutura original.
 */
async function injectConfigIntoZip(sourceZipPath, configData, ownerDiscordId) {
  const timestamp = Date.now();
  const tempBase = process.env.TEMP_DIR || "/tmp";
  const tempZipDir = path.join(tempBase, `discloud-output-${timestamp}`);
  const outputZipPath = path.join(tempZipDir, "bot-with-config.zip");

  fs.mkdirSync(tempZipDir, { recursive: true });

  console.log(`[injectConfigIntoZip] Lendo ZIP original: ${sourceZipPath}`);

  // Lê o ZIP original em memória
  const sourceBuffer = fs.readFileSync(sourceZipPath);
  const zip = await JSZip.loadAsync(sourceBuffer);

  const fileList = Object.keys(zip.files);
  console.log(`[injectConfigIntoZip] Arquivos no ZIP: ${fileList.length}`);

  // Detecta prefixo raiz (caso o ZIP tenha subpasta raiz única)
  const rootPrefix = detectRootPrefix(fileList);
  console.log(`[injectConfigIntoZip] Prefixo raiz detectado: "${rootPrefix || '(raiz)'}"`);

  // Trata o stackr.config existente
  const existingDiscloudConfig = zip.files[`${rootPrefix}discloud.config`];
  if (existingDiscloudConfig) {
    let content = await existingDiscloudConfig.async("string");
    console.log(`[injectConfigIntoZip] discloud.config original encontrado:\n${content}`);

    // Se NAME= estiver vazio, preenche com o ownerDiscordId sanitizado
    if (!/^NAME=/m.test(content)) {
      const name = sanitizeName(ownerDiscordId || "bot");
      content = `NAME=${name}\n` + content;
      zip.file(`${rootPrefix}discloud.config`, content);
      console.log(`[injectConfigIntoZip] discloud.config: NAME preenchido com "${name}"`);
    } else {
      console.log(`[injectConfigIntoZip] discloud.config: NAME já preenchido, mantendo original`);
    }
  } else {
    // Só cria se não existir
    console.log(`[injectConfigIntoZip] discloud.config não encontrado no ZIP — criando...`);
    const mainPy = detectMainPy(fileList, rootPrefix);
    const discloudContent = toDiscloudConfig(ownerDiscordId, mainPy);
    zip.file(`${rootPrefix}discloud.config`, discloudContent);
    console.log(`[injectConfigIntoZip] discloud.config criado (MAIN=${mainPy})`);
  }

  // Injeta/sobrescreve apenas o config.json
  zip.file(`${rootPrefix}config.json`, JSON.stringify(configData, null, 2));
  console.log(`[injectConfigIntoZip] config.json injetado em "${rootPrefix}config.json"`);

  // Atualiza requirements.txt (buscado do banco, com fallback)
  const requirementsContent = await getGlobalRequirements();
  zip.file(`${rootPrefix}requirements.txt`, requirementsContent);
  console.log(`[injectConfigIntoZip] requirements.txt atualizado (global)`);

  // Gera ZIP final
  console.log(`[injectConfigIntoZip] Gerando ZIP final...`);
  const zipBuffer = await zip.generateAsync({
    type: "nodebuffer",
    compression: "DEFLATE",
    compressionOptions: { level: 6 },
    streamFiles: true,
  });

  fs.writeFileSync(outputZipPath, zipBuffer);
  console.log(`[injectConfigIntoZip] ZIP criado: ${outputZipPath} (${zipBuffer.length} bytes)`);

  if (zipBuffer.length < 1000) {
    throw new Error(`ZIP criado está muito pequeno: ${zipBuffer.length} bytes`);
  }

  return outputZipPath;
}

/**
 * Detecta se o ZIP tem uma subpasta raiz única (ex: "bot/")
 * Retorna o prefixo (com / no final) ou string vazia se os arquivos estão na raiz
 */
function detectRootPrefix(fileList) {
  const nonDirFiles = fileList.filter(f => !f.endsWith("/"));
  if (nonDirFiles.length === 0) return "";

  // Pega o primeiro segmento de todos os arquivos
  const firstSegments = nonDirFiles.map(f => f.split("/")[0]);
  const unique = [...new Set(firstSegments)];

  // Se todos os arquivos têm o mesmo primeiro segmento E não é um arquivo (tem subpastas)
  if (unique.length === 1 && nonDirFiles.some(f => f.includes("/"))) {
    return `${unique[0]}/`;
  }

  return "";
}

/**
 * Detecta o arquivo Python principal na raiz do ZIP
 * Prioridade: main.py > bot.py > app.py > primeiro .py encontrado
 */
function detectMainPy(fileList, rootPrefix) {
  const priority = ["bot.py", "main.py", "app.py", "index.py", "run.py", "start.py"];

  for (const name of priority) {
    const candidate = `${rootPrefix}${name}`;
    if (fileList.includes(candidate)) {
      return name;
    }
  }

  // Fallback: primeiro .py na raiz (sem subpastas adicionais)
  const depth = rootPrefix ? 2 : 1;
  const rootPy = fileList.find(f => {
    if (!f.endsWith(".py")) return false;
    const parts = f.split("/");
    return parts.length === depth;
  });

  if (rootPy) {
    return rootPy.split("/").pop();
  }

  // Último recurso
  return "main.py";
}

/**
 * Limpa diretório temporário
 */
function cleanupTempDir(tempZipPath) {
  try {
    const tempDir = path.dirname(tempZipPath);
    if (
      tempDir.includes("discloud-output-") ||
      tempDir.includes("/temp/output-") ||
      tempDir.includes("\\temp\\output-")
    ) {
      console.log(`[cleanupTempDir] Limpando diretório temporário: ${tempDir}`);
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  } catch (err) {
    console.warn("[cleanupTempDir] Erro ao limpar:", err.message);
  }
}

/**
 * Faz deploy do bot na Discloud com config.json + discloud.config personalizados
 * @param {string} sourceZipPath - ZIP original do plano
 * @param {string} botID - ID único do bot (ex: applicationId)
 * @param {string} ownerDiscordId - Discord ID do dono
 * @param {string} planVersion - Versão do plano (opcional)
 * @returns {Promise<object>} - Resposta da Discloud
 */
export async function deployBotWithConfig(sourceZipPath, botID, ownerDiscordId, planVersion = null) {
  let tempZipPath = null;

  try {
    if (!sourceZipPath || !fs.existsSync(sourceZipPath)) {
      throw new Error(`Arquivo ZIP não encontrado: ${sourceZipPath}`);
    }

    const sourceStats = fs.statSync(sourceZipPath);
    if (!sourceStats.isFile() || sourceStats.size < 1000) {
      throw new Error(`Arquivo ZIP inválido ou muito pequeno: ${sourceZipPath}`);
    }

    console.log(`[deployBotWithConfig] ZIP de origem validado: ${sourceZipPath} (${sourceStats.size} bytes)`);

    // 1. Garante que BotConfig existe no MongoDB
    const botConfig = await ensureBotConfig(botID, ownerDiscordId, planVersion);
    const configData = toConfigJson(botConfig);

    console.log(`[deployBotWithConfig] Preparando deploy para botID: ${botID}`);

    // 2. Injeta config.json + discloud.config no ZIP
    tempZipPath = await injectConfigIntoZip(sourceZipPath, configData, ownerDiscordId);

    console.log(`[deployBotWithConfig] Config.json + discloud.config injetados. ZIP preparado: ${tempZipPath}`);

    // 3. Valida arquivo
    const stats = fs.statSync(tempZipPath);
    if (!stats.isFile() || stats.size <= 0) {
      throw new Error("ZIP gerado está vazio ou inválido");
    }

    // 4. Envia para Discloud
    console.log(`[deployBotWithConfig] Enviando para Discloud...`);
    const formData = new FormData();
    formData.append("file", fs.createReadStream(tempZipPath));

    // A documentação oficial diz que apenas o campo 'file' é necessário.
    // Configurações ficam no discloud.config dentro do zip.
    const apiResponse = await discloudService.uploadApp(tempZipPath);



    const response = apiResponse.data;

    if (!apiResponse.success) {
      throw new Error(`Deploy failed: ${apiResponse.error || response?.message || JSON.stringify(response)}`);
    }

    // Extrai o appId da resposta da Discloud
    const appId = response?.app?.id || response?.apps?.[0]?.id || response?.id || null;

    console.log(`[deployBotWithConfig] Deploy concluído com sucesso!`);
    console.log(`[deployBotWithConfig] AppId da Discloud: ${appId}`);
    console.log(`[deployBotWithConfig] Resposta completa:`, JSON.stringify(response, null, 2));

    return {
      success: true,
      botID,
      botToken: botConfig.botToken,
      appId,
      discloudResponse: response,
    };
  } catch (err) {
    console.error(`[deployBotWithConfig] Erro no deploy:`, err);
    throw err;
  } finally {
    if (tempZipPath) cleanupTempDir(tempZipPath);
  }
}

/**
 * Atualiza bot existente na Discloud (commit)
 * @param {string} appId - ID da aplicação na Discloud
 * @param {string} sourceZipPath - ZIP original do plano
 * @param {string} botID - ID único do bot
 * @returns {Promise<object>}
 */
export async function updateBotWithConfig(appId, sourceZipPath, botID) {
  let tempZipPath = null;

  try {
    const botConfig = await BotConfig.findOne({ botID });
    if (!botConfig) {
      throw new Error(`BotConfig não encontrado para botID: ${botID}`);
    }

    const configData = toConfigJson(botConfig);
    const ownerDiscordId = botConfig.bot?.owner || "";

    console.log(`[updateBotWithConfig] Preparando atualização para appId: ${appId}`);

    // Injeta config.json + discloud.config no ZIP
    tempZipPath = await injectConfigIntoZip(sourceZipPath, configData, ownerDiscordId);

    // Valida arquivo
    const stats = fs.statSync(tempZipPath);
    if (!stats.isFile() || stats.size <= 0) {
      throw new Error("ZIP gerado está vazio ou inválido");
    }

    // Envia commit para Discloud
    console.log(`[updateBotWithConfig] Enviando atualização para Discloud...`);
    const formData = new FormData();
    formData.append("file", fs.createReadStream(tempZipPath));

    const apiResponse = await discloudService.commitApp(appId, tempZipPath);



    const response = apiResponse.data;

    if (!apiResponse.ok && apiResponse.status !== 404) {
      throw new Error(response.message || `Erro HTTP ${apiResponse.status}`);
    }

    console.log(`[updateBotWithConfig] Atualização concluída com sucesso!`);
    console.log(`[updateBotWithConfig] Resposta da Discloud:`, JSON.stringify(response, null, 2));

    return {
      success: true,
      botID,
      appId,
      discloudResponse: response,
    };
  } catch (err) {
    console.error(`[updateBotWithConfig] Erro na atualização:`, err);
    throw err;
  } finally {
    if (tempZipPath) cleanupTempDir(tempZipPath);
  }
}

export default { deployBotWithConfig, updateBotWithConfig };
// src/services/requirementsRebuildService.js
// Atualiza o requirements.txt de um bot via commit de ZIP na Discloud
// A Discloud não tem API de filesystem direto, então precisamos enviar um ZIP com o arquivo.

import discloudService from "./discloudService.js";
import archiver from "archiver";
import { PassThrough } from "stream";

/**
 * Cria um buffer de ZIP contendo apenas o requirements.txt
 * @param {string} content 
 * @returns {Promise<Buffer>}
 */
async function createRequirementsZip(content) {
  return new Promise((resolve, reject) => {
    const bufs = [];
    const archive = archiver("zip", { zlib: { level: 9 } });
    const stream = new PassThrough();

    stream.on("data", (d) => bufs.push(d));
    stream.on("end", () => resolve(Buffer.concat(bufs)));
    archive.on("error", (err) => reject(err));

    archive.pipe(stream);
    archive.append(content, { name: "requirements.txt" });
    archive.finalize();
  });
}

/**
 * Atualiza o requirements.txt do bot na Discloud via commit.
 *
 * @param {string} appId        - ID da aplicação na Discloud
 * @param {string} requirements - Conteúdo do novo requirements.txt
 */
export async function commitRequirementsToBot(appId, requirements) {
  if (!appId) throw new Error("appId é obrigatório");
  if (typeof requirements !== "string") throw new Error("requirements deve ser string");

  try {
    const zipBuffer = await createRequirementsZip(requirements);
    const result = await discloudService.commitApp(appId, zipBuffer);

    if (!result.success) {
      throw new Error(result.error || "Erro ao realizar commit de requirements na Discloud");
    }

    return { success: true, message: "Requirements atualizado via commit" };
  } catch (error) {
    console.error(`[REQUIREMENTS REBUILD] Erro ao atualizar app ${appId}:`, error.message);
    throw error;
  }
}

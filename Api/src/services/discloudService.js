import fetch from "node-fetch";
import FormData from "form-data";
import fs from "fs";
import { discloud } from "discloud.app";

const DISCLOUD_BASE = "https://api.discloud.app/v2";

// ─── SDK auth ────────────────────────────────────────────────────────────────
// discloud.app usa singleton global `discloud` + discloud.login(token).
// Fazemos login lazy na primeira chamada que usa a SDK, e só uma vez.
let _sdkReady = false;

async function ensureSdkLogin() {
  if (_sdkReady) return;
  const token = process.env.DISCLOUD_TOKEN;
  if (!token) throw new Error("DISCLOUD_TOKEN não configurado");
  await discloud.login(token);
  _sdkReady = true;
}

// ─── Classe principal ─────────────────────────────────────────────────────────
class DiscloudService {
  constructor() {
    this.statusCache = new Map();
    this.CACHE_TTL = 30000;
  }

  _authHeaders(extra = {}) {
    const token = process.env.DISCLOUD_TOKEN;
    if (!token) throw new Error("DISCLOUD_TOKEN não configurado");
    return { "api-token": token, ...extra };
  }

  async getAppInfo(appId) {
    try {
      console.log(`[DiscloudService] → GET /app/${appId}`);
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}`, {
        headers: this._authHeaders(),
      });
      console.log(`[DiscloudService] ← HTTP ${response.status} getAppInfo appId=${appId}`);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }
      const app = await response.json();
      return { success: true, app: app.apps };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao buscar app ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async getAppStatus(appId) {
    try {
      const cached = this.statusCache.get(appId);
      if (cached && Date.now() - cached.timestamp < this.CACHE_TTL) {
        return cached.data;
      }

      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/status`, {
        headers: this._authHeaders(),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }

      const appStatus = await response.json();
      const status = {
        running: appStatus.apps.container === "Online",
        container: appStatus.apps.container.toLowerCase(),
        ram: appStatus.apps.memory,
        cpu: appStatus.apps.cpu,
      };

      const result = { success: true, status };
      this.statusCache.set(appId, { data: result, timestamp: Date.now() });
      return result;
    } catch (error) {
      console.error(`[DiscloudService] Erro ao buscar status ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  clearCache(appId = null) {
    if (appId) {
      this.statusCache.delete(appId);
    } else {
      this.statusCache.clear();
    }
  }

  async getAppLogs(appId) {
    try {
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/logs`, {
        headers: this._authHeaders(),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }
      const logs = await response.json();
      return { success: true, logs: logs.apps.terminal.big };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao buscar logs ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async restartApp(appId) {
    try {
      console.log(`[DiscloudService] → PUT /app/${appId}/restart`);
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/restart`, {
        method: "PUT",
        headers: this._authHeaders(),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }
      this.clearCache(appId);
      return { success: true, message: data.message || "App restarting..." };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao reiniciar ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async stopApp(appId) {
    try {
      console.log(`[DiscloudService] → PUT /app/${appId}/stop`);
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/stop`, {
        method: "PUT",
        headers: this._authHeaders(),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }
      this.clearCache(appId);
      return { success: true, message: data.message || "App stopped successfully" };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao parar ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async startApp(appId) {
    try {
      console.log(`[DiscloudService] → PUT /app/${appId}/start`);
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/start`, {
        method: "PUT",
        headers: this._authHeaders(),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }
      this.clearCache(appId);
      return { success: true, message: data.message || "App started successfully" };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao iniciar ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async deleteApp(appId) {
    try {
      console.log(`[DiscloudService] → DELETE /app/${appId}/delete`);
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/delete`, {
        method: "DELETE",
        headers: this._authHeaders(),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }
      this.clearCache(appId);
      return { success: true, message: data.message || "App deleted successfully" };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao deletar ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async uploadApp(zipPath) {
    try {
      const formData = new FormData();
      formData.append("file", fs.createReadStream(zipPath));
      const response = await fetch(`${DISCLOUD_BASE}/upload`, {
        method: "POST",
        headers: this._authHeaders(formData.getHeaders()),
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }
      return { success: true, data };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao fazer upload:`, error.message);
      return { success: false, error: error.message };
    }
  }

  /**
   * Realiza commit de uma aplicação na Discloud usando a SDK oficial (discloud.app).
   *
   * A SDK usa `discloud.apps.update(appId, { file: { data: Buffer, name: "bot.zip" } })`
   * e gerencia internamente o multipart/form-data, eliminando os erros de
   * "request failed, reason:" causados por streams zerados no node-fetch.
   *
   * Backoff progressivo entre tentativas: 5s → 15s → 30s.
   *
   * @param {string}        appId       ID da app na Discloud
   * @param {Buffer|string} fileBuffer  Buffer do ZIP ou caminho absoluto do arquivo
   */
  async commitApp(appId, fileBuffer) {
    const MAX_RETRIES = 3;
    const RETRY_DELAYS_MS = [5_000, 15_000, 30_000];

    // Garante que o buffer seja um Buffer (imutável, seguro para reuso entre tentativas)
    let buffer;
    if (Buffer.isBuffer(fileBuffer)) {
      buffer = fileBuffer;
    } else if (typeof fileBuffer === "string") {
      buffer = fs.readFileSync(fileBuffer);
    } else {
      return { success: false, error: "fileBuffer deve ser Buffer ou caminho de arquivo" };
    }

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        await ensureSdkLogin();

        console.log(
          `[DiscloudService] → commit SDK apps.update(${appId}) (tentativa ${attempt}/${MAX_RETRIES})`
        );

        // API oficial: discloud.apps.update(appId, { file: { data: Buffer, name: string } })
        const result = await discloud.apps.update(appId, {
          file: {
            data: buffer,
            name: "bot.zip",
          },
        });

        // A SDK lança em caso de erro HTTP; validamos status por segurança
        const status = result?.status;
        if (status && status !== "ok" && status !== "200") {
          throw new Error(result?.message || `SDK retornou status inesperado: ${status}`);
        }

        this.clearCache(appId);
        console.log(`[DiscloudService] ✅ commit OK para ${appId}`);
        return { success: true, data: result };

      } catch (error) {
        const msg =
          error?.cause?.message ||
          error?.cause?.code ||
          (typeof error?.cause === "string" ? error.cause : null) ||
          error.message ||
          "Erro desconhecido";

        // Erros de rede e 5xx são retriables; 4xx (404, 403) não
        const isRetryable =
          msg.includes("ECONNRESET") ||
          msg.includes("ETIMEDOUT") ||
          msg.includes("ENOTFOUND") ||
          msg.includes("socket hang up") ||
          msg.includes("UND_ERR") ||
          msg.includes("timeout") ||
          msg.includes("fetch failed") ||
          msg.includes("503") ||
          msg.includes("502") ||
          msg.includes("504") ||
          (error.type === "system" && !error?.cause?.message);

        if (isRetryable && attempt < MAX_RETRIES) {
          const delay = RETRY_DELAYS_MS[attempt - 1];
          console.warn(
            `[DiscloudService] Tentativa ${attempt}/${MAX_RETRIES} falhou para ${appId} (${msg}). ` +
            `Aguardando ${delay / 1000}s antes de tentar novamente...`
          );
          await new Promise((r) => setTimeout(r, delay));
          continue;
        }

        console.error(
          `[DiscloudService] ✗ commit falhou definitivamente para ${appId} (${attempt} tentativa(s)):`, msg
        );
        return { success: false, error: msg };
      }
    }

    return { success: false, error: "Número máximo de tentativas esgotado" };
  }

  async updateSettings(appId, settings) {
    try {
      if (settings.ram) {
        return this.changeAppRam(appId, settings.ram);
      }
      console.warn(`[DiscloudService] updateSettings sem suporte direto para ${appId}:`, settings);
      return {
        success: false,
        error: "updateSettings não suportado sem commit para essa configuração.",
      };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao atualizar configurações ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async changeAppRam(appId, ram) {
    try {
      console.log(`[DiscloudService] → PUT /app/${appId}/ram`);
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/ram`, {
        method: "PUT",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ ramMB: ram }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || `Erro HTTP ${response.status}`);
      }
      return { success: true, data };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao mudar RAM ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async getAppBackup(appId) {
    try {
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/backup`, {
        headers: this._authHeaders(),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Erro HTTP ${response.status}`);
      return { success: true, backup: data.backups };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao buscar backup ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async listAllApps() {
    try {
      const response = await fetch(`${DISCLOUD_BASE}/app/all`, {
        headers: this._authHeaders(),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Erro HTTP ${response.status}`);
      return { success: true, apps: data.apps || [] };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao listar apps:`, error.message);
      return { success: false, error: error.message, apps: [] };
    }
  }

  async exec(appId, cmd) {
    try {
      console.log(`[DiscloudService] → PUT /app/${appId}/console cmd="${cmd}"`);
      const response = await fetch(`${DISCLOUD_BASE}/app/${appId}/console`, {
        method: "PUT",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ cmd }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || `Erro HTTP ${response.status}`);
      return { success: true, output: data.apps?.terminal?.small || data.terminal?.small || "" };
    } catch (error) {
      console.error(`[DiscloudService] Erro ao executar cmd no ${appId}:`, error.message);
      return { success: false, error: error.message };
    }
  }

  async listFiles(appId, filePath = ".") {
    const result = await this.exec(appId, `ls -la ${filePath}`);
    return result.success ? { success: true, output: result.output } : result;
  }

  async readFile(appId, filePath) {
    const result = await this.exec(appId, `cat ${filePath}`);
    return result.success ? { success: true, content: result.output } : result;
  }

  async deleteFile(appId, filePath) {
    return this.exec(appId, `rm -f ${filePath}`);
  }

  async deleteDirectory(appId, dirPath) {
    return this.exec(appId, `rm -rf ${dirPath}`);
  }

  async createDirectory(appId, dirPath) {
    return this.exec(appId, `mkdir -p ${dirPath}`);
  }

  async renameFile(appId, oldPath, newPath) {
    return this.exec(appId, `mv ${oldPath} ${newPath}`);
  }
}

export default new DiscloudService();
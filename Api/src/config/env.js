import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { existsSync } from "fs";

// Obter o diretório do arquivo atual
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Caminhos possíveis para .env (backend/.env e raiz/.env)
const backendEnvPath = join(__dirname, "../../.env");
const rootEnvPath = join(__dirname, "../../../.env");

// Sempre carregar .env primeiro (base) - tentar backend primeiro, depois raiz
let envLoaded = false;
if (existsSync(backendEnvPath)) {
  const result = dotenv.config({ path: backendEnvPath });
  if (!result.error) {
    console.log(`[ENV] ✓ Carregado: ${backendEnvPath}`);
    envLoaded = true;
  }
} else if (existsSync(rootEnvPath)) {
  const result = dotenv.config({ path: rootEnvPath });
  if (!result.error) {
    console.log(`[ENV] ✓ Carregado: ${rootEnvPath}`);
    envLoaded = true;
  }
}

if (!envLoaded) {
  console.warn(`[ENV] ⚠ Nenhum arquivo .env encontrado em ${backendEnvPath} ou ${rootEnvPath}`);
}

// Em desenvolvimento, tentar carregar .env.development (override)
if (process.env.NODE_ENV !== "production") {
  const backendDevEnvPath = join(__dirname, "../../.env.development");
  const rootDevEnvPath = join(__dirname, "../../../.env.development");
  
  if (existsSync(backendDevEnvPath)) {
    const result = dotenv.config({ path: backendDevEnvPath, override: true });
    if (!result.error) {
      console.log(`[ENV] ✓ Carregado (override): ${backendDevEnvPath}`);
    }
  } else if (existsSync(rootDevEnvPath)) {
    const result = dotenv.config({ path: rootDevEnvPath, override: true });
    if (!result.error) {
      console.log(`[ENV] ✓ Carregado (override): ${rootDevEnvPath}`);
    }
  }
}

export const NODE_ENV = process.env.NODE_ENV || "development";
export const PORT = process.env.PORT || 8080;

export const FRONTEND_URL = process.env.FRONTEND_URL;
export const BACKEND_URL = process.env.BACKEND_URL;
export const COOKIE_DOMAIN = process.env.COOKIE_DOMAIN;

export const MONGODB_URI = process.env.MONGODB_URI;
export const MONGO_BOTS_URI = process.env.MONGO_BOTS_URI;

export const JWT_SECRET = process.env.JWT_SECRET;

import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { existsSync } from "fs";

// Obter o diretório do arquivo atual
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Caminhos possíveis para .env
const backendEnvPath = join(__dirname, "../../.env");
const rootEnvPath = join(__dirname, "../../../.env");

// Carregar .env
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
  console.warn(`[ENV] ⚠ Nenhum arquivo .env encontrado`);
}

export const NODE_ENV = process.env.NODE_ENV || "development";
export const PORT = process.env.PORT || 3001;

export const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:3000";
export const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:3001";

export const MONGODB_URI = process.env.MONGODB_URI;
if (!MONGODB_URI) {
  console.warn("[ENV] ⚠ MONGODB_URI não definido");
}

export const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET) {
  console.warn("[ENV] ⚠ JWT_SECRET não definido");
}

// Configurações de e-mail - Resend
export const RESEND_API_KEY = process.env.RESEND_API_KEY;
export const RESEND_FROM_EMAIL = process.env.RESEND_FROM_EMAIL || process.env.EMAIL_FROM;
export const EMAIL_FROM_NAME = process.env.EMAIL_FROM_NAME || process.env.SMTP_FROM_NAME || "Amethys Wallet";

// Configurações legadas (mantidas para compatibilidade, mas não usadas)
export const EMAIL_HOST = process.env.EMAIL_HOST || process.env.SMTP_HOST;
export const EMAIL_PORT = parseInt(process.env.EMAIL_PORT || process.env.SMTP_PORT || "587");
export const EMAIL_USER = process.env.EMAIL_USER || process.env.SMTP_USER;
export const EMAIL_PASS = process.env.EMAIL_PASS || process.env.SMTP_PASS;
export const EMAIL_SECURE = process.env.SMTP_SECURE === "true" || EMAIL_PORT === 465;
export const EMAIL_FROM = process.env.EMAIL_FROM || process.env.SMTP_FROM_EMAIL || EMAIL_USER;

// Configurações de segurança
export const COOKIE_DOMAIN = process.env.COOKIE_DOMAIN;
export const TRUSTED_IPS = process.env.TRUSTED_IPS;
export const DEFENSE_AUTH_TOKEN = process.env.DEFENSE_AUTH_TOKEN || 'LOOP_FIREWALL';
export const JWT_ISSUER = process.env.JWT_ISSUER;
export const JWT_AUDIENCE = process.env.JWT_AUDIENCE;
export const FRONTEND_URL_SECONDARY = process.env.FRONTEND_URL_SECONDARY;

export const GOATPAY_API_URL = process.env.GOATPAY_API_URL || 'https://api.goatpay.com.br/v1';
export const GOATPAY_API_KEY = process.env.GOATPAY_API_KEY;
export const GOATPAY_API_KEY_BLACK = process.env.GOATPAY_API_KEY_BLACK;
export const GOATPAY_WEBHOOK_SECRET = process.env.GOATPAY_WEBHOOK_SECRET;


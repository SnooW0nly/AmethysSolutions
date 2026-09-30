import axios from "axios";
import https from "node:https";
import fs from "node:fs";
import path from "node:path";

/**
 * Cria um httpsAgent a partir de um arquivo .p12
 */
export function mkHttpsAgentFromFile(cert_path, passphrase = "") {
  const resolvedPath = path.isAbsolute(cert_path)
    ? cert_path
    : path.resolve(process.cwd(), cert_path);
  const certBuffer = fs.readFileSync(resolvedPath);
  // Node/TLS usa a opção 'pfx' para PKCS#12 (.p12/.pfx)
  return new https.Agent({ pfx: certBuffer, passphrase });
}

/**
 * Gera o access_token para autenticação Pix
 */
export async function getAccessToken(overrides = {}) {
  const {
    client_id = process.env.EFI_CLIENT_ID,
    client_secret = process.env.EFI_CLIENT_SECRET,
    cert_path = process.env.EFI_CERT_PATH,
    passphrase = process.env.EFI_CERT_PASSWORD || "",
    baseUrl = "https://pix.api.efipay.com.br",
  } = overrides;

  const httpsAgent = mkHttpsAgentFromFile(cert_path, passphrase);
  const auth = Buffer.from(`${client_id}:${client_secret}`).toString("base64");

  const resp = await axios.post(
    `${baseUrl}/oauth/token`,
    { grant_type: "client_credentials" },
    { headers: { Authorization: `Basic ${auth}` }, httpsAgent }
  );

  return { accessToken: resp.data.access_token, httpsAgent };
}

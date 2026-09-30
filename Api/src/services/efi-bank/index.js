import { getAccessToken } from "./auth.js";
import { createCharge, getQRCodeByLoc, getChargeStatus, mapStatus } from "./pix.js";
import qrcode from "qrcode";
import Payment from "../../database/models/Payment.js";

export async function createPixPayment({ price, description }) {
  // Modo mock para desenvolvimento/local quando credenciais não existem
  const shouldMock =
    process.env.EFI_MOCK === "true" ||
    !process.env.EFI_CLIENT_ID ||
    !process.env.EFI_CLIENT_SECRET ||
    !process.env.EFI_CERT_PATH ||
    !process.env.EFI_PIX_KEY;

  if (shouldMock) {
    if (process.env.EFI_MOCK !== "true") {
      console.warn("[efi] Mock ativado por falta de env:", {
        hasClientId: Boolean(process.env.EFI_CLIENT_ID),
        hasClientSecret: Boolean(process.env.EFI_CLIENT_SECRET),
        hasCertPath: Boolean(process.env.EFI_CERT_PATH),
        hasPixKey: Boolean(process.env.EFI_PIX_KEY),
      });
    }
    const efiId = `MOCK-${Date.now()}`;
    const emv = `000201MOCKTXID${efiId}`;
    const qrBase64 = await qrcode.toDataURL(emv, { width: 300 });
    const raw = { mock: true, description, price };
    return { efiId, emv, qrBase64, raw };
  }

  // Autenticação real
  const { accessToken, httpsAgent } = await getAccessToken();

  // Criar cobrança
  const { txid, locId, pixCopiaECola, raw } = await createCharge({
    accessToken,
    httpsAgent,
    amount: price,
    pixKey: process.env.EFI_PIX_KEY,
    description,
  });

  let emv = pixCopiaECola;
  if (!emv && locId) {
    const qr = await getQRCodeByLoc({ accessToken, httpsAgent, locId });
    emv = qr?.qrcode;
  }

  // Gera QR em base64
  const qrBase64 = await qrcode.toDataURL(emv, { width: 300 });

  // Não persiste no banco aqui; apenas retorna dados para quem chama decidir
  return { efiId: txid, emv, qrBase64, raw };
}

export async function checkPixPayment({ payment_id }) {
  const { accessToken, httpsAgent } = await getAccessToken();

  const raw = await getChargeStatus({ accessToken, httpsAgent, txid: payment_id });
  const status = mapStatus(raw.status);

  await Payment.findOneAndUpdate({ efiId: payment_id }, { status, efiRaw: raw });

  return { status, raw };
}

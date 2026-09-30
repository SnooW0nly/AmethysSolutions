import { checkPixPayment } from "../../../services/efi-bank/index.js";

export function getEfiCredentials() {
  return {
    client_id: process.env.EFI_CLIENT_ID,
    client_secret: process.env.EFI_CLIENT_SECRET,
    certificate: process.env.EFI_CERT_BASE64,
    passphrase: process.env.EFI_CERT_PASSWORD || "",
  };
}

export async function fetchPixStatus(paymentId) {
  const credentials = getEfiCredentials();
  const { status } = await checkPixPayment({
    ...credentials,
    payment_id: paymentId,
  });
  return status;
}



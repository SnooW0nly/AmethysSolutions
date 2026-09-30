import axios from "axios";

export async function createCharge({
  accessToken,
  httpsAgent,
  amount,
  pixKey,
  expirationSeconds = 600,
  description = "Pagamento via Efi",
  baseUrl = "https://pix.api.efipay.com.br",
}) {
  const body = {
    calendario: { expiracao: expirationSeconds },
    valor: { original: Number(amount).toFixed(2) },
    chave: pixKey,
    solicitacaoPagador: description,
  };

  const resp = await axios.post(`${baseUrl}/v2/cob`, body, {
    headers: { Authorization: `Bearer ${accessToken}` },
    httpsAgent,
  });

  const cob = resp.data;
  return {
    txid: cob.txid,
    locId: cob?.loc?.id || null,
    pixCopiaECola: cob.pixCopiaECola || null,
    raw: cob,
  };
}

export async function getQRCodeByLoc({ accessToken, httpsAgent, locId, baseUrl = "https://pix.api.efipay.com.br" }) {
  const resp = await axios.get(`${baseUrl}/v2/pix/loc/${locId}/qrcode`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    httpsAgent,
  });
  return resp.data;
}

export async function getChargeStatus({ accessToken, httpsAgent, txid, baseUrl = "https://pix.api.efipay.com.br" }) {
  const resp = await axios.get(`${baseUrl}/v2/cob/${txid}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    httpsAgent,
  });
  return resp.data;
}

export function mapStatus(efiStatus) {
  if (efiStatus === "CONCLUIDA") return "approved";
  if (efiStatus && efiStatus.startsWith("REMOVIDA")) return "cancelled";
  return "pending";
}


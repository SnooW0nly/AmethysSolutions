import { sendMail } from "./mailService.js";

export async function sendReceiptEmail({
  to,
  subject,
  invoiceNumber,
  invoiceDate,
  invoiceSubTotal,
  invoiceDiscount,
  invoiceTotal,
  userName,
  userEmail,
  planName,
  months,
}) {
  const formatCurrency = (value) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
      Number(value || 0)
    );

  const safe = (v) => (v === undefined || v === null ? "" : String(v));

  const html = `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fatura #${invoiceNumber}</title>
  <style>img{max-width:100%;height:auto}</style>
  </head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f3f4f6;">
    <tr>
      <td align="center" style="padding:24px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="padding:24px 24px 12px 24px;background:#111827;">
              <table role="presentation" width="100%">
                <tr>
                  <td align="left">
                    <div style="color:#ffffff;font-weight:700;font-size:20px;line-height:1;">Amethys Applications</div>
                    <div style="color:#9ca3af;font-size:12px;line-height:1.4;margin-top:4px;">Seu pagamento foi aprovado</div>
                  </td>
                  <td align="right">
                    <span style="display:inline-block;padding:6px 10px;border-radius:999px;background:#4f46e5;color:#ffffff;font-weight:600;font-size:12px;">FATURA</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:16px 24px 16px 24px;background:#111827;border-top:1px solid #1f2937;">
              <div style="color:#ffffff;font-size:18px;font-weight:700;line-height:1.3;">Fatura #${safe(invoiceNumber)}</div>
              <div style="color:#9ca3af;font-size:12px;margin-top:4px;">Emitida em ${safe(invoiceDate)}</div>
            </td>
          </tr>

          <tr>
            <td style="padding:24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="vertical-align:top;width:50%;padding-right:12px;">
                    <div style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px;">Cobrado de</div>
                    <div style="font-size:14px;color:#111827;font-weight:700;">${safe(userName)}</div>
                    <div style="font-size:13px;color:#374151;margin-top:2px;">${safe(userEmail)}</div>
                  </td>
                  <td style="vertical-align:top;width:50%;padding-left:12px;">
                    <div style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px;">Empresa</div>
                    <div style="font-size:14px;color:#111827;font-weight:700;">Vision Applications Ltda</div>
                    <div style="font-size:13px;color:#374151;margin-top:2px;">CNPJ ${process.env.CNPJ}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:0 24px 8px 24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;">
                <thead>
                  <tr>
                    <th align="left" style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;padding:10px 0;border-bottom:1px solid #e5e7eb;">Descrição</th>
                    <th align="right" style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;padding:10px 0;border-bottom:1px solid #e5e7eb;">Preço</th>
                    <th align="right" style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;padding:10px 0;border-bottom:1px solid #e5e7eb;">Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style="padding:12px 0;font-size:14px;color:#111827;">Plano ${safe(planName)} — ${Number(months) === 1 ? "1 mês" : `${Number(months || 0)} meses`}</td>
                    <td align="right" style="padding:12px 0;font-size:14px;color:#111827;">${formatCurrency(invoiceTotal)}</td>
                    <td align="right" style="padding:12px 0;font-size:14px;color:#111827;">${formatCurrency(invoiceTotal)}</td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:8px 24px 0 24px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td align="left" style="padding:6px 0;font-size:13px;color:#6b7280;">Subtotal</td>
                        <td align="right" style="padding:6px 0;font-size:13px;color:#111827;">${formatCurrency(invoiceSubTotal)}</td>
                      </tr>
                      <tr>
                        <td align="left" style="padding:6px 0;font-size:13px;color:#6b7280;">Desconto</td>
                        <td align="right" style="padding:6px 0;font-size:13px;color:#dc2626;">- ${formatCurrency(invoiceDiscount)}</td>
                      </tr>
                      <tr>
                        <td align="left" style="padding:10px 0;font-size:14px;color:#111827;font-weight:700;border-top:1px solid #e5e7eb;">Total</td>
                        <td align="right" style="padding:10px 0;font-size:16px;color:#111827;font-weight:800;border-top:1px solid #e5e7eb;">${formatCurrency(invoiceTotal)}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:0 24px 24px 24px; margin-top: 6px;">
              <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px;">
                <div style="font-size:12px;color:#6b7280;letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px;">Observações</div>
                <div style="font-size:13px;color:#374151;line-height:1.5;">Obrigado por escolher a Amethys! O seu produto deve estar disponível em até 24 horas na sua conta.</div>
              </div>
            </td>
          </tr>

          <tr>
            <td align="center" style="padding:18px;background:#111827;">
              <div style="color:#9ca3af;font-size:12px;line-height:1.5;">
                © 2026 Amethys Applications Ltda — Todos os direitos reservados<br>
                CNPJ ${process.env.CNPJ}
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  await sendMail({
    to,
    subject: subject || `Fatura #${safe(invoiceNumber)} aprovada`,
    html,
  });
}
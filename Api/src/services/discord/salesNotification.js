/**
 * src/services/discord/salesNotification.js
 * Envia notificação no canal de vendas quando um pagamento é aprovado.
 * O canal é configurado via admin (/api/admin/discord-config) e salvo no MongoDB.
 */

/**
 * Resolve token e canal de vendas do MongoDB com fallback para .env
 */
async function resolveConfig() {
  try {
    const { getDiscordConfig } = await import(
      "../../routes/admin/discord/discord-config.js"
    );
    const [token, channelId] = await Promise.all([
      getDiscordConfig("discord_bot_token"),
      getDiscordConfig("discord_sales_channel_id"),
    ]);
    return { token, channelId };
  } catch {
    return {
      token: process.env.DISCORD_BOT_TOKEN || null,
      channelId: process.env.DISCORD_SALES_CHANNEL_ID || null,
    };
  }
}

/**
 * Envia embed de venda aprovada no canal de logs.
 *
 * @param {object} opts
 * @param {object} opts.payment    Documento Payment do MongoDB
 * @param {object} opts.user       Documento User do MongoDB
 * @param {object} opts.application Documento Application criado (pode ser null em renovações)
 * @param {boolean} opts.isRenewal
 */
export async function notifySaleApproved({ payment, user, application, isRenewal = false }) {
  try {
    const { token, channelId } = await resolveConfig();

    if (!token || !channelId) {
      console.warn(
        "[SALES NOTIF] Token ou canal de vendas não configurado — notificação ignorada"
      );
      return;
    }

    const planName = payment?.plan?.name || "—";
    const months   = payment?.plan?.months || 1;
    const price    = Number(payment?.priceFinal ?? 0).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
    const couponCode = payment?.coupon?.code || null;
    const username   = user?.globalName || user?.username || "Usuário desconhecido";
    const discordId  = user?.discordId || null;

    const now = new Date();
    const timestamp = now.toISOString();

    // Monta campos do embed
    const fields = [
      {
        name: "👤 Cliente",
        value: discordId ? `<@${discordId}> (${username})` : username,
        inline: true,
      },
      {
        name: "📦 Plano",
        value: `**${planName}** — ${months} ${months === 1 ? "mês" : "meses"}`,
        inline: true,
      },
      {
        name: "💰 Valor",
        value: price,
        inline: true,
      },
    ];

    if (couponCode) {
      fields.push({
        name: "🎟️ Cupom",
        value: `\`${couponCode}\` (${payment.coupon.discountPercent}% off)`,
        inline: true,
      });
    }

    if (application?._id) {
      fields.push({
        name: "🤖 Aplicação",
        value: `\`${application._id}\``,
        inline: true,
      });
    }

    if (payment?.metadata?.affiliateCode) {
      fields.push({
        name: "🔗 Afiliado",
        value: `\`${payment.metadata.affiliateCode}\``,
        inline: true,
      });
    }

    const embed = {
      title: isRenewal ? "🔄 Renovação Aprovada" : "🎉 Nova Venda Aprovada",
      description: isRenewal
        ? `A renovação de **${planName}** foi confirmada via PIX.`
        : `Uma nova assinatura de **${planName}** foi confirmada via PIX.`,
      color: isRenewal ? 0x5865f2 : 0x57f287, // azul para renovação, verde para nova
      fields,
      footer: {
        text: `Payment ID: ${payment?._id ?? "—"} • Provider: ${payment?.provider ?? "—"}`,
      },
      timestamp,
    };

    const body = JSON.stringify({ embeds: [embed] });

    const resp = await fetch(
      `https://discord.com/api/v10/channels/${channelId}/messages`,
      {
        method: "POST",
        headers: {
          Authorization: `Bot ${token}`,
          "Content-Type": "application/json",
        },
        body,
      }
    );

    if (!resp.ok) {
      const err = await resp.text();
      console.error(
        `[SALES NOTIF] Falha ao enviar mensagem (${resp.status}):`,
        err
      );
      return;
    }

    console.log(
      `[SALES NOTIF] Notificação enviada — pagamento ${payment?._id}`
    );
  } catch (err) {
    // Nunca deixa travar o fluxo principal
    console.error("[SALES NOTIF] Erro inesperado:", err?.message ?? err);
  }
}
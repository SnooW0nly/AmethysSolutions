/**
 * src/services/discord/shop/shopMessage.js
 *
 * Publica (ou re-publica) o embed de compra no canal DISCORD_SHOP_CHANNEL_ID.
 *
 * Layout da embed:
 *   🤖 Amethys Solutions — Loja de Bots
 *   Hospede seu bot Discord de forma simples e confiável.
 *
 * Botão de compra:
 *   - Múltiplos planos → StringSelectMenu com opções de plano
 *   - 1 plano          → StringSelectMenu com opções de tempo (mensal/trimestral/anual)
 *
 * Persistência: salva/restaura o ID da mensagem via GlobalConfig { key: "shop_message_id" }
 */

import {
  EmbedBuilder,
  ActionRowBuilder,
  StringSelectMenuBuilder,
  StringSelectMenuOptionBuilder,
  ButtonBuilder,
  ButtonStyle,
} from "discord.js";

import client from "./client.js";
import Plan from "../../../database/models/Plan.js";
import GlobalConfig from "../../../database/models/GlobalConfig.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Formata um valor em Real brasileiro.
 * @param {number} value
 */
function formatBRL(value) {
  return Number(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

/**
 * Retorna o label de duração baseado no número de meses.
 * @param {number} months
 */
function monthLabel(months) {
  if (months === 1) return "Mensal";
  if (months === 3) return "Trimestral";
  if (months === 6) return "Semestral";
  if (months === 12) return "Anual";
  return `${months} meses`;
}

/**
 * Retorna o emoji de desconto se houver.
 * @param {number} discount
 */
function discountBadge(discount) {
  if (!discount || discount <= 0) return "";
  return ` 🏷️ -${discount}%`;
}

// ─── Builders ─────────────────────────────────────────────────────────────────

/**
 * Monta o embed principal da loja.
 * @param {Array} plans - planos ativos do MongoDB
 */
function buildShopEmbed(plans) {
  const planList = plans
    .map((p) => {
      const minPrice = Math.min(...(p.plans || []).map((o) => o.value));
      return `**${p.icon ? `${p.icon} ` : ""}${p.name}** — a partir de ${formatBRL(minPrice)}/mês`;
    })
    .join("\n");

  return new EmbedBuilder()
    .setColor(0x9b59b6)
    .setTitle("🤖  Amethys Solutions — Loja de Bots")
    .setDescription(
      "Hospede seu bot Discord de forma simples e confiável.\nEscolha seu plano e comece agora mesmo!"
    )
    .addFields(
      {
        name: "📦 Planos disponíveis",
        value: planList || "Nenhum plano disponível no momento.",
      },
      {
        name: "💳 Pagamento",
        value: "Via **PIX instantâneo** — aprovação automática em segundos.",
      }
    )
    .setFooter({ text: "Amethys Solutions • amethys.com.br" })
    .setTimestamp();
}

/**
 * Monta o ActionRow de compra.
 *
 * Regra:
 *  - +1 plano  → SelectMenu listando cada plano (valor = "shop_buy:<planId>:<optionId>")
 *  - 1 plano   → SelectMenu listando as opções de tempo do plano
 *
 * @param {Array} plans
 */
function buildBuyRow(plans) {
  const activePlans = plans.filter((p) => !p.isFree && p.plans?.length > 0);

  if (activePlans.length === 0) {
    // Fallback: botão desativado se não há planos
    return new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId("shop_noop")
        .setLabel("Sem planos disponíveis")
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(true)
    );
  }

  if (activePlans.length === 1) {
    // ── Caso: somente 1 plano → select com opções de tempo ──────────────────
    const plan = activePlans[0];
    const options = (plan.plans || []).map((opt) =>
      new StringSelectMenuOptionBuilder()
        .setValue(`shop_buy:${plan.id}:${opt.id}`)
        .setLabel(`${monthLabel(opt.months)}${discountBadge(opt.discount)}`)
        .setDescription(
          `${formatBRL(opt.value)}${opt.discount ? ` (economize ${opt.discount}%)` : ""}`
        )
        .setEmoji(opt.months >= 12 ? "🏆" : opt.months >= 3 ? "⭐" : "🛒")
    );

    const select = new StringSelectMenuBuilder()
      .setCustomId("shop_plan_select")
      .setPlaceholder(`🛒 Assinar ${plan.name} — escolha o período`)
      .addOptions(options);

    return new ActionRowBuilder().addComponents(select);
  }

  // ── Caso: múltiplos planos → select listando os planos ────────────────────
  const options = activePlans.map((plan) => {
    const prices = (plan.plans || []).map((o) => o.value);
    const min = Math.min(...prices);
    const max = Math.max(...prices);

    return new StringSelectMenuOptionBuilder()
      .setValue(`shop_plan:${plan.id}`)
      .setLabel(`${plan.name}`)
      .setDescription(
        prices.length > 1
          ? `de ${formatBRL(min)} a ${formatBRL(max)}`
          : formatBRL(min)
      )
      .setDefault(!!plan.primary);
  });

  const select = new StringSelectMenuBuilder()
    .setCustomId("shop_plan_select")
    .setPlaceholder("🛒 Selecione um plano para comprar")
    .addOptions(options);

  return new ActionRowBuilder().addComponents(select);
}

// ─── Publicação ───────────────────────────────────────────────────────────────

export async function publishShopMessage() {
  const channelId = process.env.DISCORD_SHOP_CHANNEL_ID;
  if (!channelId) {
    console.warn("[SHOP MSG] DISCORD_SHOP_CHANNEL_ID não configurado — embed de compra ignorada");
    return;
  }

  const channel = await client.channels.fetch(channelId).catch(() => null);
  if (!channel) {
    console.error("[SHOP MSG] Canal de compras não encontrado:", channelId);
    return;
  }

  // Deleta mensagem anterior se existir
  const cfg = await GlobalConfig.findOne({ key: "shop_message_id" }).lean();
  if (cfg?.value) {
    await channel.messages.delete(cfg.value).catch(() => null);
  }

  // Busca planos ativos
  const plans = await Plan.find({ active: true }).lean();

  const embed = buildShopEmbed(plans);
  const row = buildBuyRow(plans);

  const msg = await channel.send({ embeds: [embed], components: [row] });

  await GlobalConfig.findOneAndUpdate(
    { key: "shop_message_id" },
    { value: msg.id },
    { upsert: true }
  );

  console.log("[SHOP MSG] Embed de compra publicada:", msg.id);
}

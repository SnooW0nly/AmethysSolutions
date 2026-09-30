/**
 * src/services/discord/shop/flows/buyFlow.js
 */

import {
  EmbedBuilder,
  AttachmentBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  StringSelectMenuBuilder,
  StringSelectMenuOptionBuilder,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  ChannelType,
} from "discord.js";

import User from "../../../../database/models/User.js";
import Plan from "../../../../database/models/Plan.js";
import Payment from "../../../../database/models/Payment.js";
import Coupon from "../../../../database/models/Coupon.js";
import { createPixPayment } from "../../../../services/payment/index.js";

function formatBRL(value) {
  return Number(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function monthLabel(months) {
  if (months === 1) return "Mensal";
  if (months === 3) return "Trimestral";
  if (months === 6) return "Semestral";
  if (months === 12) return "Anual";
  return `${months} meses`;
}

function discountBadge(discount) {
  if (!discount || discount <= 0) return "";
  return ` -${discount}%`;
}

export async function onPlanSelect(interaction, planId) {
  await interaction.deferReply({ ephemeral: true });

  const plan = await Plan.findOne({ id: planId, active: true }).lean();
  if (!plan || !plan.plans?.length) {
    return interaction.editReply({ content: "Plano não encontrado ou indisponível." });
  }

  const options = plan.plans.map((opt) =>
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
    .setPlaceholder(`${plan.name} — escolha o período`)
    .addOptions(options);

  await interaction.editReply({
    content: `Você escolheu **${plan.name}**. Selecione o período:`,
    components: [new ActionRowBuilder().addComponents(select)],
  });
}

export async function onBuyOption(interaction, planId, optionId) {
  await interaction.deferReply({ ephemeral: true });

  const discordId = interaction.user.id;

  const user = await User.findOne({ discordId }).lean();
  if (!user) {
    const frontendUrl = process.env.FRONTEND_URL || "https://amethys.com.br";
    return interaction.editReply({
      content:
        `Você ainda não tem conta na Amethys.\n` +
        `[**Criar conta aqui**](${frontendUrl}/login) e depois volte para comprar.`,
    });
  }

  const plan = await Plan.findOne({ id: planId, active: true }).lean();
  if (!plan) {
    return interaction.editReply({ content: "Plano não encontrado ou indisponível." });
  }

  const planOption = (plan.plans || []).find((o) => o.id === optionId);
  if (!planOption) {
    return interaction.editReply({ content: "Opção de período inválida." });
  }

  await interaction.editReply({
    embeds: [
      new EmbedBuilder()
        .setColor(0x9b59b6)
        .setTitle("🛒  Abrindo seu carrinho...")
        .setDescription(`Aguarde um instante!`)
        .setFooter({ text: "Isso leva apenas alguns segundos..." }),
    ],
  });

  try {
    const channel = interaction.channel;
    const threadName = `carrinho - ${interaction.user.username} - ${plan.name} ${monthLabel(planOption.months)}`;

    const thread = await channel.threads.create({
      name: threadName.slice(0, 100),
      autoArchiveDuration: 60,
      type: ChannelType.PrivateThread,
      reason: `Compra: ${plan.name} - ${interaction.user.tag}`,
    });

    await thread.members.add(discordId).catch(() => null);

    const cartPayment = await Payment.create({
      userId: user._id,
      plan: {
        id: plan.id,
        name: plan.name,
        price: planOption.value,
        monthId: planOption.id,
        months: planOption.months,
      },
      priceFinal: planOption.value,
      provider: null,
      status: "cart",
      threadId: thread.id,
      metadata: { isRenewal: false },
    });

    const cartEmbed = new EmbedBuilder()
      .setColor(0x9b59b6)
      .setTitle("🛒  Carrinho de Compras")
      .setDescription(`Olá <@${discordId}>! Revise seu pedido antes de continuar.`)
      .addFields(
        { name: "📦 Plano", value: `${plan.name} — ${monthLabel(planOption.months)}`, inline: true },
        { name: "💰 Valor", value: formatBRL(planOption.value), inline: true }
      )
      .setFooter({ text: "Aplique um cupom ou clique em Continuar para gerar o PIX." })
      .setTimestamp();

    const cartMsg = await thread.send({
      content: `<@${discordId}>`,
      embeds: [cartEmbed],
      components: [
        new ActionRowBuilder().addComponents(
          new ButtonBuilder()
            .setCustomId(`shop_pay:${cartPayment._id}`)
            .setLabel("Continuar pagamento")
            .setStyle(ButtonStyle.Success)
            .setEmoji("💳"),
          new ButtonBuilder()
            .setCustomId(`shop_coupon:${cartPayment._id}`)
            .setLabel("Cupom")
            .setStyle(ButtonStyle.Secondary)
            .setEmoji("🎟️")
        ),
      ],
    });

    await Payment.findByIdAndUpdate(cartPayment._id, { messageId: cartMsg.id });

    await interaction.editReply({
      embeds: [
        new EmbedBuilder()
          .setColor(0x57f287)
          .setTitle("✅  Carrinho aberto com sucesso!")
          .setDescription(`Acesse o tópico e clique em **Continuar pagamento** para gerar o PIX.`)
          .addFields(
            { name: "📦 Plano", value: `${plan.name} — ${monthLabel(planOption.months)}`, inline: true },
            { name: "💰 Valor", value: formatBRL(planOption.value), inline: true }
          )
          .setFooter({ text: "O QR Code será gerado após confirmar." }),
      ],
      components: [
        new ActionRowBuilder().addComponents(
          new ButtonBuilder()
            .setLabel("Abrir meu carrinho")
            .setStyle(ButtonStyle.Link)
            .setURL(thread.url)
            .setEmoji("🛒")
        ),
      ],
    });
  } catch (err) {
    console.error("[BUY FLOW] Erro ao criar pagamento:", err.message);
    await interaction.editReply({
      embeds: [],
      components: [],
      content: "Erro ao gerar o pagamento. Tente novamente em instantes ou contate o suporte.",
    });
  }
}

export async function onContinuePayment(interaction, cartPaymentId) {
  console.log("[BUY FLOW] onContinuePayment iniciado, cartPaymentId:", cartPaymentId);
  await interaction.deferUpdate();
  console.log("[BUY FLOW] deferUpdate ok");

  const cartPayment = await Payment.findById(cartPaymentId).lean();
  console.log("[BUY FLOW] cartPayment:", cartPayment ? `status=${cartPayment.status} threadId=${cartPayment.threadId}` : "NÃO ENCONTRADO");
  if (!cartPayment || cartPayment.status !== "cart") {
    return interaction.followUp({ content: "Carrinho não encontrado ou já processado.", ephemeral: true });
  }

  const owner = await User.findById(cartPayment.userId).lean();
  console.log("[BUY FLOW] owner:", owner ? `discordId=${owner.discordId}` : "NÃO ENCONTRADO");
  if (!owner || String(owner.discordId) !== String(interaction.user.id)) {
    return interaction.followUp({ content: "Apenas o dono do carrinho pode continuar.", ephemeral: true });
  }

  try {
    const { plan } = cartPayment;
    console.log("[BUY FLOW] Criando pagamento PIX para plano:", plan);
    const { provider, paymentId, emv, qrBase64, raw } = await createPixPayment({
      price: plan.price,
      description: `Plano ${plan.name} - ${monthLabel(plan.months)}`,
    });
    console.log("[BUY FLOW] PIX criado: provider=%s, paymentId=%s, temEmv=%s, temQr=%s", provider, paymentId, !!emv, !!qrBase64);

    const expiresAt = new Date(Date.now() + 10 * 60 * 1000);

    const updateData = {
      provider,
      status: "pending",
      qrCodeBase64: qrBase64,
      qrCodeText: emv,
      expiresAt,
    };
    if (provider === "mistic") { updateData.misticId = paymentId; updateData.misticRaw = raw; }
    else if (provider === "woovi") { updateData.wooviId = paymentId; updateData.wooviRaw = raw; }
    else { updateData.efiId = paymentId; updateData.efiRaw = raw; }

    const payment = await Payment.findByIdAndUpdate(cartPaymentId, updateData, { new: true });
    console.log("[BUY FLOW] Payment atualizado no banco:", payment?._id);

    console.log("[BUY FLOW] Buscando thread:", cartPayment.threadId);
    const thread = await interaction.client.channels.fetch(cartPayment.threadId).catch((e) => {
      console.error("[BUY FLOW] Erro ao buscar thread:", e.message);
      return null;
    });
    console.log("[BUY FLOW] Thread:", thread ? `id=${thread.id} type=${thread.type}` : "NÃO ENCONTRADA");
    if (!thread) {
      return interaction.followUp({ content: "❌ Thread não encontrada. Contate o suporte.", ephemeral: true });
    }

    const files = [];
    const qrEmbed = new EmbedBuilder()
      .setColor(0x9b59b6)
      .setTitle("💳  Pagamento PIX")
      .setDescription(
        `<@${interaction.user.id}> seu pagamento foi gerado!\n\n` +
        `> **Plano:** ${plan.name} — ${monthLabel(plan.months)}\n` +
        `> **Valor:** ${formatBRL(payment.priceFinal)}\n` +
        `> **Expira:** <t:${Math.floor(expiresAt.getTime() / 1000)}:R>`
      )
      .setFooter({ text: `Aprovação automática via PIX  •  ID: ${payment._id}` })
      .setTimestamp();

    if (qrBase64) {
      console.log("[BUY FLOW] Processando QR base64, tamanho:", qrBase64.length);
      const rawBase64 = qrBase64.includes(",") ? qrBase64.split(",")[1] : qrBase64;
      const buffer = Buffer.from(rawBase64, "base64");
      console.log("[BUY FLOW] Buffer QR gerado, tamanho:", buffer.length);
      const attachment = new AttachmentBuilder(buffer, { name: "qr.png" });
      qrEmbed.setImage("attachment://qr.png");
      files.push(attachment);
    } else {
      console.warn("[BUY FLOW] qrBase64 vazio — embed será enviada SEM imagem");
    }

    console.log("[BUY FLOW] Deletando mensagem do carrinho...");
    await interaction.message.delete().catch((e) => console.error("[BUY FLOW] Erro ao deletar mensagem:", e.message));
    console.log("[BUY FLOW] Mensagem deletada. Enviando embed na thread...");

    await thread.send({
      content: `<@${interaction.user.id}>`,
      embeds: [qrEmbed],
      files,
    });
    console.log("[BUY FLOW] Embed enviada na thread com sucesso!");

    await interaction.followUp({
      ephemeral: true,
      embeds: [
        new EmbedBuilder()
          .setColor(0x9b59b6)
          .setTitle("📋  Pix Copia e Cola")
          .setDescription(`\`\`\`${emv || "—"}\`\`\``)
          .setFooter({ text: "Cole este código no seu banco para pagar." }),
      ],
    });
    console.log("[BUY FLOW] followUp copia e cola enviado. Fluxo concluído.");

  } catch (err) {
    console.error("[BUY FLOW] Erro ao gerar pagamento:", err.message, err.stack);
    await interaction.followUp({
      ephemeral: true,
      content: "Erro ao gerar o pagamento. Tente novamente ou contate o suporte.",
    });
  }
}

export async function onCouponButton(interaction, cartPaymentId) {
  const modal = new ModalBuilder()
    .setCustomId(`shop_coupon_modal:${cartPaymentId}`)
    .setTitle("🎟️  Aplicar Cupom");

  const input = new TextInputBuilder()
    .setCustomId("coupon_code")
    .setLabel("Código do cupom")
    .setStyle(TextInputStyle.Short)
    .setPlaceholder("Ex: PROMO20")
    .setRequired(true)
    .setMaxLength(20);

  modal.addComponents(new ActionRowBuilder().addComponents(input));
  await interaction.showModal(modal);
}

export async function onCouponModal(interaction, cartPaymentId) {
  await interaction.deferUpdate();

  const code = interaction.fields.getTextInputValue("coupon_code").trim().toUpperCase();

  const cartPayment = await Payment.findById(cartPaymentId);
  if (!cartPayment || cartPayment.status !== "cart") {
    return interaction.followUp({ content: "Carrinho não encontrado ou já processado.", ephemeral: true });
  }

  const owner = await User.findById(cartPayment.userId).lean();
  if (!owner || String(owner.discordId) !== String(interaction.user.id)) {
    return interaction.followUp({ content: "Apenas o dono do carrinho pode aplicar cupons.", ephemeral: true });
  }

  const coupon = await Coupon.findOne({ name: code, archived: false }).lean();

  if (!coupon) {
    return interaction.followUp({ content: `❌ Cupom **${code}** não encontrado ou inválido.`, ephemeral: true });
  }

  if (coupon.maxUses && coupon.usedCount >= coupon.maxUses) {
    return interaction.followUp({ content: `❌ O cupom **${code}** já atingiu o limite de usos.`, ephemeral: true });
  }

  if (coupon.availableDays) {
    const expiresAt = new Date(coupon.createdAt);
    expiresAt.setDate(expiresAt.getDate() + coupon.availableDays);
    if (new Date() > expiresAt) {
      return interaction.followUp({ content: `❌ O cupom **${code}** está expirado.`, ephemeral: true });
    }
  }

  if (coupon.minCart && cartPayment.plan.price < coupon.minCart) {
    return interaction.followUp({
      content: `❌ O cupom **${code}** exige valor mínimo de ${formatBRL(coupon.minCart)}.`,
      ephemeral: true,
    });
  }

  const discount = coupon.percent / 100;
  const priceFinal = parseFloat((cartPayment.plan.price * (1 - discount)).toFixed(2));

  await Payment.findByIdAndUpdate(cartPaymentId, {
    coupon: {
      id: coupon._id,
      code: coupon.name,
      discountPercent: coupon.percent,
    },
    priceFinal,
  });

  const updatedEmbed = new EmbedBuilder()
    .setColor(0x57f287)
    .setTitle("🛒  Carrinho de Compras")
    .setDescription(`Olá <@${interaction.user.id}>! Cupom aplicado com sucesso.`)
    .addFields(
      { name: "📦 Plano", value: `${cartPayment.plan.name} — ${monthLabel(cartPayment.plan.months)}`, inline: true },
      { name: "💰 Valor original", value: formatBRL(cartPayment.plan.price), inline: true },
      { name: "🎟️ Cupom", value: `${code} (-${coupon.percent}%)`, inline: true },
      { name: "✅ Valor final", value: formatBRL(priceFinal), inline: true }
    )
    .setFooter({ text: "Clique em Continuar pagamento para gerar o PIX." })
    .setTimestamp();

  await interaction.message.edit({ embeds: [updatedEmbed] });

  await interaction.followUp({
    ephemeral: true,
    content: `✅ Cupom **${code}** aplicado! Desconto de **${coupon.percent}%** — valor final: **${formatBRL(priceFinal)}**`,
  });
}

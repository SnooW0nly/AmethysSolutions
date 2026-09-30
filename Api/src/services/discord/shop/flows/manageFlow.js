/**
 * src/services/discord/shop/flows/manageFlow.js
 */

import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  StringSelectMenuBuilder,
  StringSelectMenuOptionBuilder,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  AttachmentBuilder,
} from "discord.js";

import User from "../../../../database/models/User.js";
import Application from "../../../../database/models/Application.js";
import Plan from "../../../../database/models/Plan.js";
import Payment from "../../../../database/models/Payment.js";
import { createPixPayment } from "../../../../services/payment/index.js";
import discloudService from "../../../../services/discloudService.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatBRL(value) {
  return Number(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatDate(date) {
  if (!date) return "—";
  return new Date(date).toLocaleDateString("pt-BR");
}

function monthLabel(months) {
  if (months === 1) return "mensal";
  if (months === 3) return "trimestral";
  if (months === 6) return "semestral";
  if (months === 12) return "anual";
  return `${months} meses`;
}

// ─── Embed do painel de uma app ───────────────────────────────────────────────

function buildAppPanel(app, isOwner) {
  const status = app.hosting?.status || "desconhecido";
  const statusEmoji =
    status === "online" ? "🟢" : status === "offline" ? "🔴" : "⚪";

  return new EmbedBuilder()
    .setColor(status === "online" ? 0x57f287 : status === "offline" ? 0xed4245 : 0x95a5a6)
    .setTitle(`⚙️  ${app.name}`)
    .addFields(
      { name: "📊 Status", value: `${statusEmoji} ${status}`, inline: true },
      { name: "📦 Plano", value: app.plan?.name || "—", inline: true },
      { name: "📅 Expira", value: formatDate(app.expiresAt), inline: true }
    )
    .setFooter({
      text: isOwner
        ? "Você é o dono desta aplicação"
        : "Você tem permissão de gerenciamento",
    })
    .setTimestamp();
}

function buildAppRows(appId, isOwner) {
  const row1 = new ActionRowBuilder().addComponents(
    new ButtonBuilder()
      .setCustomId(`mgr:start:${appId}`)
      .setLabel("Ligar")
      .setStyle(ButtonStyle.Success)
      .setEmoji("▶"),
    new ButtonBuilder()
      .setCustomId(`mgr:stop:${appId}`)
      .setLabel("Parar")
      .setStyle(ButtonStyle.Danger)
      .setEmoji("⏹"),
    new ButtonBuilder()
      .setCustomId(`mgr:restart:${appId}`)
      .setLabel("Reiniciar")
      .setStyle(ButtonStyle.Primary)
      .setEmoji("🔄")
  );

  const row2 = new ActionRowBuilder().addComponents(
    new ButtonBuilder()
      .setCustomId(`mgr:token:${appId}`)
      .setLabel("Token")
      .setStyle(ButtonStyle.Secondary)
      .setEmoji("🔑")
      .setDisabled(!isOwner),
    new ButtonBuilder()
      .setCustomId(`mgr:server:${appId}`)
      .setLabel("Servidor")
      .setStyle(ButtonStyle.Secondary)
      .setEmoji("🌐")
      .setDisabled(!isOwner),
    new ButtonBuilder()
      .setCustomId(`mgr:perms:${appId}`)
      .setLabel("Permissão")
      .setStyle(ButtonStyle.Secondary)
      .setEmoji("👥")
      .setDisabled(!isOwner),
    new ButtonBuilder()
      .setCustomId(`mgr:renew:${appId}`)
      .setLabel("Renovar")
      .setStyle(ButtonStyle.Secondary)
      .setEmoji("🔁")
  );

  return [row1, row2];
}

// ─── Handlers públicos ────────────────────────────────────────────────────────

export async function onManageButton(interaction) {
  await interaction.deferReply({ ephemeral: true });

  const discordId = interaction.user.id;

  const user = await User.findOne({ discordId }).lean();
  if (!user) {
    const frontendUrl = process.env.FRONTEND_URL || "https://amethys.com.br";
    return interaction.editReply({
      content:
        `❌ Você não tem conta vinculada ao Discord na Amethys.\n` +
        `[**Criar conta**](${frontendUrl}/login) e tente novamente.`,
    });
  }

  const apps = await Application.find({
    $or: [{ userId: user._id }, { "bot.perms": discordId }],
    isDeleted: false,
    isBlocked: false,
  })
    .select("name hosting.status expiresAt bot plan userId")
    .lean();

  if (apps.length === 0) {
    return interaction.editReply({
      content: "❌ Você não tem nenhuma aplicação hospedada na Amethys.",
    });
  }

  if (apps.length === 1) {
    const app = apps[0];
    const isOwner = String(app.userId) === String(user._id);
    const embed = buildAppPanel(app, isOwner);
    const rows = buildAppRows(String(app._id), isOwner);
    return interaction.editReply({ embeds: [embed], components: rows });
  }

  const options = apps.slice(0, 25).map((app) => {
    const statusEmoji =
      app.hosting?.status === "online" ? "🟢" :
      app.hosting?.status === "offline" ? "🔴" : "⚪";

    return new StringSelectMenuOptionBuilder()
      .setValue(String(app._id))
      .setLabel(app.name)
      .setDescription(
        `${statusEmoji} ${app.hosting?.status || "—"} • Expira: ${formatDate(app.expiresAt)}`
      );
  });

  const select = new StringSelectMenuBuilder()
    .setCustomId("mgr_select")
    .setPlaceholder("Selecione qual bot deseja gerenciar")
    .addOptions(options);

  await interaction.editReply({
    content: "Selecione qual bot deseja gerenciar:",
    components: [new ActionRowBuilder().addComponents(select)],
  });
}

export async function onAppSelect(interaction) {
  await interaction.deferUpdate();

  const discordId = interaction.user.id;
  const appId = interaction.values[0];

  const user = await User.findOne({ discordId }).lean();
  if (!user) return;

  const app = await Application.findOne({
    _id: appId,
    $or: [{ userId: user._id }, { "bot.perms": discordId }],
    isDeleted: false,
    isBlocked: false,
  })
    .select("name hosting.status expiresAt bot plan userId")
    .lean();

  if (!app) {
    return interaction.editReply({
      content: "❌ Aplicação não encontrada ou sem permissão.",
      components: [],
    });
  }

  const isOwner = String(app.userId) === String(user._id);
  await interaction.editReply({
    content: null,
    embeds: [buildAppPanel(app, isOwner)],
    components: buildAppRows(appId, isOwner),
  });
}

export async function onAction(interaction, args) {
  const [action, appId] = args;
  const discordId = interaction.user.id;

  const user = await User.findOne({ discordId }).lean();
  if (!user) {
    return interaction.reply({ content: "❌ Conta não encontrada.", ephemeral: true });
  }

  const app = await Application.findOne({
    _id: appId,
    $or: [{ userId: user._id }, { "bot.perms": discordId }],
    isDeleted: false,
    isBlocked: false,
  }).lean();

  if (!app) {
    return interaction.reply({ content: "❌ Aplicação não encontrada ou sem permissão.", ephemeral: true });
  }

  const isOwner = String(app.userId) === String(user._id);
  const ownerOnlyActions = ["token", "server", "perms"];

  if (ownerOnlyActions.includes(action) && !isOwner) {
    return interaction.reply({
      content: "❌ Apenas o dono da aplicação pode realizar esta ação.",
      ephemeral: true,
    });
  }

  // Ações que abrem Modal
  if (action === "token") {
    return interaction.showModal(
      new ModalBuilder()
        .setCustomId(`mgr_modal:token:${appId}`)
        .setTitle("Novo Token do Bot")
        .addComponents(
          new ActionRowBuilder().addComponents(
            new TextInputBuilder()
              .setCustomId("value")
              .setLabel("Token do bot")
              .setStyle(TextInputStyle.Short)
              .setRequired(true)
              .setPlaceholder("Cole o token do seu bot aqui")
          )
        )
    );
  }

  if (action === "server") {
    return interaction.showModal(
      new ModalBuilder()
        .setCustomId(`mgr_modal:server:${appId}`)
        .setTitle("ID do Servidor Principal")
        .addComponents(
          new ActionRowBuilder().addComponents(
            new TextInputBuilder()
              .setCustomId("value")
              .setLabel("ID do servidor Discord")
              .setStyle(TextInputStyle.Short)
              .setRequired(true)
              .setPlaceholder("Ex: 1234567890123456789")
          )
        )
    );
  }

  if (action === "perms") {
    const current = (app.bot?.perms || [])
      .filter((id) => id !== String(user.discordId))
      .join(", ");

    return interaction.showModal(
      new ModalBuilder()
        .setCustomId(`mgr_modal:perms:${appId}`)
        .setTitle("Permissões de Gerenciamento")
        .addComponents(
          new ActionRowBuilder().addComponents(
            new TextInputBuilder()
              .setCustomId("value")
              .setLabel("Discord IDs (separados por vírgula)")
              .setStyle(TextInputStyle.Paragraph)
              .setRequired(false)
              .setValue(current)
              .setPlaceholder("Ex: 1234567890, 9876543210")
          )
        )
    );
  }

  // Ações que chamam Discloud
  await interaction.deferReply({ ephemeral: true });

  if (action === "renew") {
    return handleRenew(interaction, user, app);
  }

  const hostingAppId = app.hosting?.appId;
  if (!hostingAppId) {
    return interaction.editReply({ content: "❌ Esta aplicação não possui ID de hospedagem." });
  }

  try {
    let result;
    if (action === "start")   result = await discloudService.startApp(hostingAppId);
    if (action === "stop")    result = await discloudService.stopApp(hostingAppId);
    if (action === "restart") result = await discloudService.restartApp(hostingAppId);

    const labels = { start: "ligada", stop: "parada", restart: "reiniciada" };
    if (result?.success) {
      await interaction.editReply({ content: `✅ Aplicação **${app.name}** ${labels[action]} com sucesso.` });
    } else {
      await interaction.editReply({ content: `❌ Falha: ${result?.error || "Erro desconhecido"}` });
    }
  } catch (err) {
    console.error(`[MGR FLOW] Erro na ação ${action}:`, err.message);
    await interaction.editReply({ content: "❌ Erro ao processar a ação. Tente novamente." });
  }
}

async function handleRenew(interaction, user, app) {
  const plan = await Plan.findOne({ id: app.plan?.id, active: true }).lean();
  if (!plan || !plan.plans?.length) {
    return interaction.editReply({ content: "❌ Plano atual não encontrado para renovação." });
  }

  const planOption =
    plan.plans.find((o) => o.id === app.plan?.monthId) || plan.plans[0];

  try {
    const { provider, paymentId, emv, qrBase64, raw } = await createPixPayment({
      price: planOption.value,
      description: `Renovacao ${plan.name} - ${planOption.months} mes(es)`,
    });

    const paymentData = {
      userId: user._id,
      plan: {
        id: plan.id,
        name: plan.name,
        price: planOption.value,
        monthId: planOption.id,
        months: planOption.months,
      },
      priceFinal: planOption.value,
      provider,
      status: "pending",
      qrCodeBase64: qrBase64,
      qrCodeText: emv,
      expiresAt: new Date(Date.now() + 10 * 60 * 1000),
      metadata: {
        isRenewal: true,
        applicationId: app._id,
        months: planOption.months,
      },
    };

    if (provider === "mistic") paymentData.misticId = paymentId, paymentData.misticRaw = raw;
    else if (provider === "woovi") paymentData.wooviId = paymentId, paymentData.wooviRaw = raw;
    else paymentData.efiId = paymentId, paymentData.efiRaw = raw;

    await Payment.create(paymentData);

    const embed = new EmbedBuilder()
      .setColor(0x9b59b6)
      .setTitle("🔁  Renovação PIX")
      .setDescription(
        `**App:** ${app.name}\n` +
        `**Plano:** ${plan.name} — ${planOption.months} mês(es)\n` +
        `**Valor:** ${formatBRL(planOption.value)}\n` +
        `**Expira em:** 10 minutos`
      )
      .addFields({ name: "📋 Código Pix", value: `\`\`\`${emv || "—"}\`\`\`` })
      .setTimestamp();

    const files = [];
    if (qrBase64) {
      const buffer = Buffer.from(qrBase64, "base64");
      const attachment = new AttachmentBuilder(buffer, { name: "qr.png" });
      embed.setImage("attachment://qr.png");
      files.push(attachment);
    }

    await interaction.editReply({ embeds: [embed], files });
  } catch (err) {
    console.error("[MGR FLOW] Erro ao criar renovação:", err.message);
    await interaction.editReply({
      content: "❌ Erro ao gerar o pagamento de renovação. Tente novamente.",
    });
  }
}

export async function onModal(interaction) {
  await interaction.deferUpdate();

  const [, action, appId] = interaction.customId.split(":");
  const value = interaction.fields.getTextInputValue("value");
  const discordId = interaction.user.id;

  const user = await User.findOne({ discordId }).lean();
  if (!user) return;

  const app = await Application.findOne({
    _id: appId,
    userId: user._id,
    isDeleted: false,
  }).lean();

  if (!app) {
    return interaction.followUp({ content: "❌ Aplicação não encontrada.", ephemeral: true });
  }

  try {
    if (action === "token") {
      await Application.updateOne({ _id: appId }, { $set: { "bot.token": value } });
      await interaction.followUp({ content: "✅ Token atualizado com sucesso.", ephemeral: true });
    }

    if (action === "server") {
      await Application.updateOne({ _id: appId }, { $set: { "bot.server": value } });
      await interaction.followUp({ content: "✅ Servidor atualizado com sucesso.", ephemeral: true });
    }

    if (action === "perms") {
      const ids = value
        .split(",")
        .map((s) => s.trim())
        .filter((s) => /^\d{15,20}$/.test(s));

      await Application.updateOne({ _id: appId }, { $set: { "bot.perms": ids } });
      await interaction.followUp({
        content: `✅ Permissões atualizadas. ${ids.length} usuário(s) com acesso.`,
        ephemeral: true,
      });
    }
  } catch (err) {
    console.error(`[MGR FLOW] Erro no modal ${action}:`, err.message);
    await interaction.followUp({ content: "❌ Erro ao salvar alteração.", ephemeral: true });
  }
}

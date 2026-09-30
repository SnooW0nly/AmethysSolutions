/**
 * src/services/discord/shop/managerMessage.js
 *
 * Publica (ou re-publica) o embed de gerenciamento no canal DISCORD_MANAGER_CHANNEL_ID.
 *
 * Layout:
 *   ⚙️ Gerenciar Bots — Amethys Solutions
 *   Clique abaixo para gerenciar suas aplicações hospedadas.
 *   [ ⚙️ Gerenciar meus bots ]
 *
 * Persistência: salva/restaura o ID da mensagem via GlobalConfig { key: "manager_message_id" }
 */

import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
} from "discord.js";

import client from "./client.js";
import GlobalConfig from "../../../database/models/GlobalConfig.js";

function buildManagerEmbed() {
  return new EmbedBuilder()
    .setColor(0x5865f2)
    .setTitle("⚙️  Gerenciar Bots — Amethys Solutions")
    .setDescription(
      "Clique abaixo para gerenciar suas aplicações hospedadas.\n\n" +
        "Você precisa ter uma **conta vinculada** ao seu Discord para continuar."
    )
    .addFields({
      name: "🔧 O que você pode fazer",
      value:
        "▶ Ligar / ⏹ Parar / 🔄 Reiniciar\n" +
        "🔑 Trocar token • 🌐 Alterar servidor • 👥 Permissões • 🔁 Renovar plano",
    })
    .setFooter({ text: "Amethys Solutions • amethys.com.br" })
    .setTimestamp();
}

export async function publishManagerMessage() {
  const channelId = process.env.DISCORD_MANAGER_CHANNEL_ID;
  if (!channelId) {
    console.warn("[MGR MSG] DISCORD_MANAGER_CHANNEL_ID não configurado — embed de gerenciamento ignorada");
    return;
  }

  const channel = await client.channels.fetch(channelId).catch(() => null);
  if (!channel) {
    console.error("[MGR MSG] Canal de gerenciamento não encontrado:", channelId);
    return;
  }

  // Deleta mensagem anterior se existir
  const cfg = await GlobalConfig.findOne({ key: "manager_message_id" }).lean();
  if (cfg?.value) {
    await channel.messages.delete(cfg.value).catch(() => null);
  }

  const embed = buildManagerEmbed();

  const row = new ActionRowBuilder().addComponents(
    new ButtonBuilder()
      .setCustomId("shop_manage")
      .setLabel("Gerenciar meus bots")
      .setStyle(ButtonStyle.Primary)
      .setEmoji("⚙️")
  );

  const msg = await channel.send({ embeds: [embed], components: [row] });

  await GlobalConfig.findOneAndUpdate(
    { key: "manager_message_id" },
    { value: msg.id },
    { upsert: true }
  );

  console.log("[MGR MSG] Embed de gerenciamento publicada:", msg.id);
}

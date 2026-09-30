/**
 * src/services/discord/shop/interactions.js
 *
 * Router central de todas as interações do shop/manager.
 *
 * Mapa de custom_ids:
 *
 * StringSelectMenu:
 *   "shop_plan_select" (value = "shop_buy:<planId>:<optId>")  → buyFlow.onBuyOption
 *   "shop_plan_select" (value = "shop_plan:<planId>")          → buyFlow.onPlanSelect
 *   "mgr_select"                                               → manageFlow.onAppSelect
 *
 * Button:
 *   "shop_manage"      → manageFlow.onManageButton
 *   "mgr:<action>:<appId>" → manageFlow.onAction
 *
 * Modal:
 *   "mgr_modal:<action>:<appId>" → manageFlow.onModal
 */

import * as buyFlow from "./flows/buyFlow.js";
import * as manageFlow from "./flows/manageFlow.js";

export async function handleInteraction(interaction) {
  try {
    // ── StringSelectMenu ─────────────────────────────────────────────────────
    if (interaction.isStringSelectMenu()) {
      if (interaction.customId === "shop_plan_select") {
        const value = interaction.values[0];

        if (value.startsWith("shop_buy:")) {
          // Direto para compra: "shop_buy:<planId>:<optionId>"
          const [, planId, optionId] = value.split(":");
          return buyFlow.onBuyOption(interaction, planId, optionId);
        }

        if (value.startsWith("shop_plan:")) {
          // Escolheu plano → exibe select de período: "shop_plan:<planId>"
          const planId = value.replace("shop_plan:", "");
          return buyFlow.onPlanSelect(interaction, planId);
        }
      }

      if (interaction.customId === "mgr_select") {
        return manageFlow.onAppSelect(interaction);
      }

      return; // ignora outros selects
    }

    // ── Buttons ──────────────────────────────────────────────────────────────
    if (interaction.isButton()) {
      const parts = interaction.customId.split(":");
      const ns = parts[0];

      if (ns === "shop_pay") {
        const cartPaymentId = parts[1];
        return buyFlow.onContinuePayment(interaction, cartPaymentId);
      }

      if (ns === "shop_coupon") {
        const cartPaymentId = parts[1];
        return buyFlow.onCouponButton(interaction, cartPaymentId);
      }

      if (ns === "shop_manage") {
        return manageFlow.onManageButton(interaction);
      }

      if (ns === "mgr") {
        // "mgr:<action>:<appId>"
        const args = parts.slice(1);
        return manageFlow.onAction(interaction, args);
      }

      if (ns === "shop_noop") {
        return interaction.reply({ content: "Sem planos disponíveis no momento.", ephemeral: true });
      }

      return; // ignora outros botões
    }

    // ── Modals ───────────────────────────────────────────────────────────────
    if (interaction.isModalSubmit()) {
      if (interaction.customId.startsWith("shop_coupon_modal:")) {
        const cartPaymentId = interaction.customId.split(":")[1];
        return buyFlow.onCouponModal(interaction, cartPaymentId);
      }
      if (interaction.customId.startsWith("mgr_modal:")) {
        return manageFlow.onModal(interaction);
      }
      return;
    }
  } catch (err) {
    console.error("[SHOP INTERACTIONS] Erro não tratado:", err.message, err.stack);

    // Tenta responder ao usuário se a interação ainda não foi respondida
    try {
      const content = "❌ Ocorreu um erro inesperado. Tente novamente.";
      if (interaction.replied || interaction.deferred) {
        await interaction.followUp({ content, ephemeral: true });
      } else {
        await interaction.reply({ content, ephemeral: true });
      }
    } catch {
      // ignora se não conseguir responder
    }
  }
}

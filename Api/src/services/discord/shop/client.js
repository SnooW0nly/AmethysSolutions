/**
 * src/services/discord/shop/client.js
 *
 * Instância única do Client discord.js compartilhada entre o shop e o botCounter.
 * O botCounter.js deve importar este client em vez de instanciar o próprio,
 * evitando dois logins com o mesmo token (Discord derruba o mais antigo com op 9).
 *
 * Intents mínimos:
 *  - Guilds           → obrigatório para buscar guild/channel
 *  - GuildVoiceStates → necessário para o botCounter
 * Interações chegam via Gateway sem intent adicional.
 */

import { Client, GatewayIntentBits } from "discord.js";

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildVoiceStates,
    GatewayIntentBits.GuildMessages,  // necessário para enviar mensagens em threads
  ],
  // Desliga caches que não usamos para economizar RAM
  sweepers: {
    messages: { interval: 300, lifetime: 60 },
  },
});

export default client;

/**
 * Serviço de IA para assistente virtual
 */

const AI_API_URL = 'https://project.squareweb.app/api/unlimited-generate';
const AI_API_KEY = 'c5db5f0b6b1dad0021b90537e4cbd42fbc50960ecff22c8a';

export interface AIMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AIResponse {
  content: string;
  action?: {
    type: 'create_payment' | 'create_transfer' | 'update_settings' | 'show_balance' | 'show_last_transactions' | 'explain';
    data?: any;
  };
}

/**
 * Enviar mensagem para a IA
 */
export async function sendAIMessage(
  messages: AIMessage[],
  imageBase64?: string,
  imageMimeType?: string
): Promise<AIResponse> {
  try {
    const response = await fetch(AI_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${AI_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'Project-Model-Free',
        messages: messages.map(msg => ({ content: msg.content })),
        imageBase64: imageBase64 || undefined,
        imageMimeType: imageMimeType || undefined,
      }),
    });

    if (!response.ok) {
      throw new Error('Erro ao comunicar com a IA');
    }

    const data = await response.json();

    // Processar resposta da IA
    const content = data.content || data.message || data.text || '';

    // Tentar extrair ação do JSON estruturado retornado pela IA
    let action = extractActionFromResponse(content);

    // Se não encontrou ação estruturada, usar fallback de regex (compatibilidade)
    if (!action) {
      action = parseAIAction(content);
    }

    // Se encontrou ação no JSON, usar a ação extraída diretamente
    // Isso garante que a ação seja processada mesmo se o conteúdo contiver JSON

    return {
      content,
      action: action || undefined,
    };
  } catch (error) {
    console.error('Erro ao enviar mensagem para IA:', error);
    throw error;
  }
}

/**
 * Extrair ação de resposta estruturada da IA (JSON)
 */
function extractActionFromResponse(content: string): AIResponse['action'] | null {
  try {
    // Tentar encontrar JSON na resposta (pode estar em bloco de código ou texto)
    const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/) ||
      content.match(/```\s*([\s\S]*?)\s*```/) ||
      content.match(/\{[\s\S]*"action"[\s\S]*\}/);

    if (jsonMatch) {
      const jsonStr = jsonMatch[1] || jsonMatch[0];
      const parsed = JSON.parse(jsonStr);

      if (parsed.action) {
        return parsed.action;
      }
    }

    // Tentar parse direto se a resposta for apenas JSON
    if (content.trim().startsWith('{')) {
      const parsed = JSON.parse(content);
      if (parsed.action) {
        return parsed.action;
      }
    }
  } catch (error) {
    // Se não conseguir parsear JSON, retornar null para usar fallback
    return null;
  }

  return null;
}

/**
 * Remover JSON do conteúdo para exibição visual
 */
export function cleanContentForDisplay(content: string): string {
  if (!content || !content.trim()) {
    return '';
  }

  let cleaned = content;

  // Remover blocos de código JSON (```json ... ```)
  cleaned = cleaned.replace(/```json\s*[\s\S]*?```/gi, '');

  // Remover blocos de código genéricos que contenham JSON com "action"
  cleaned = cleaned.replace(/```\s*\{[\s\S]*?"action"[\s\S]*?\}\s*```/gi, '');

  // Remover JSON solto no texto que contenha "action"
  cleaned = cleaned.replace(/\{[\s\S]*?"action"[\s\S]*?\}/g, '');

  // Se o conteúdo inteiro for JSON válido, retornar string vazia
  const trimmed = content.trim();
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmed);
      // Se for um objeto JSON válido, especialmente se tiver "action", não mostrar
      if (parsed && typeof parsed === 'object') {
        return '';
      }
    } catch {
      // Não é JSON válido, manter conteúdo
    }
  }

  // Limpar linhas vazias extras e espaços múltiplos
  cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n'); // Máximo 2 quebras de linha
  cleaned = cleaned.trim();

  // Se após limpeza ficou vazio ou só tem espaços, retornar string vazia
  if (!cleaned || cleaned.trim().length === 0) {
    return '';
  }

  return cleaned;
}

/**
 * Processar resposta da IA para detectar ações
 */
export function parseAIAction(content: string): AIResponse['action'] {
  const lowerContent = content.toLowerCase();

  // Detectar perguntas sobre funcionalidades (deve vir ANTES de detectar ações)
  // Padrões mais específicos para perguntas que devem retornar explicação
  const explainPatterns = [
    /(?:o\s+)?que\s+(?:você|vc|tu)\s+(?:pode|consegue|faz|faz por mim)/i,
    /(?:quais|quais são)\s+(?:suas|as)\s+(?:funcionalidades|funções|capacidades)/i,
    /(?:me\s+)?(?:explique|explica|mostre|mostra)\s+(?:o\s+)?que\s+(?:você|vc|tu)\s+(?:pode|faz)/i,
    /(?:como|de que forma)\s+(?:você|vc|tu)\s+(?:pode|consegue|ajuda)/i,
    /(?:ajuda|help|help me)/i,
    /(?:o\s+)?que\s+(?:posso|consigo)\s+(?:fazer|pedir)/i,
    // Detectar perguntas sobre "como fazer" algo (explicação, não ação) - MAIS ESPECÍFICO
    /^como\s+(?:faço|fazer|posso fazer|consigo fazer|eu faço|se faz|realizar|realizo)\s+(?:uma\s+)?(?:transferência|transferir|pagamento|pix|saque|depósito|depositar)/i,
    /^como\s+(?:enviar|transferir|gerar|criar|fazer|realizar)\s+(?:uma\s+)?(?:transferência|pagamento|pix|saque|depósito)/i,
    /(?:me\s+)?(?:ensine|ensina|mostre|mostra|explique|explica)\s+(?:como\s+)?(?:fazer|enviar|transferir|gerar|criar|realizar)\s+(?:uma\s+)?(?:transferência|pagamento|pix|saque|depósito)/i,
    /(?:quero|preciso|gostaria)\s+(?:saber|aprender|entender)\s+(?:como\s+)?(?:fazer|enviar|transferir|gerar|criar|realizar)\s+(?:uma\s+)?(?:transferência|pagamento|pix|saque|depósito)/i,
    // Detectar perguntas que começam com "como" e não têm valor/chave
    /^como\s+(?:faço|fazer|posso|consigo)\s+(?:uma\s+)?transferência\s*[?]?$/i,
    /^como\s+(?:faço|fazer|posso|consigo)\s+(?:um\s+)?pagamento\s*[?]?$/i,
    /^como\s+(?:faço|fazer|posso|consigo)\s+(?:um\s+)?depósito\s*[?]?$/i,
    /^como\s+(?:faço|fazer|posso|consigo)\s+(?:um\s+)?saque\s*[?]?$/i,
  ];

  // Verificar se é uma pergunta (termina com ? ou corresponde a padrões de pergunta)
  const trimmedContent = content.trim();
  const isQuestionMark = trimmedContent.endsWith('?');
  const matchesQuestionPattern = explainPatterns.some(pattern => pattern.test(trimmedContent));

  if (isQuestionMark || matchesQuestionPattern) {
    // Se for pergunta, verificar se tem padrão COMPLETO de transferência (valor E chave juntos no mesmo padrão)
    // Padrão rigoroso: deve ter "enviar/transferir VALOR para CHAVE" no mesmo padrão
    const hasCompleteTransferPattern = /(?:enviar|transferir|mandar|quero|preciso|gostaria de|fazer|realizar)\s+(?:r\$\s*)?([\d.,]+)\s*(?:reais?|r\$)?\s+(?:para|pro|ao|à)\s+([a-zA-Z0-9@._+-]{5,})/i.test(content);

    // Se for pergunta mas NÃO tiver padrão completo de transferência, é explicação
    if (!hasCompleteTransferPattern) {
      return {
        type: 'explain',
      };
    }
  }

  // Detectar criação de pagamento - padrões mais flexíveis
  const paymentPatterns = [
    /(?:gerar|criar|fazer|gerar um|gerar o)\s+(?:pagamento|pix|qr code|qrcode)/i,
    /(?:quero|preciso|gostaria de)\s+(?:gerar|criar|fazer)\s+(?:um\s+)?(?:pagamento|pix)/i,
  ];

  const hasPaymentIntent = paymentPatterns.some(pattern => pattern.test(content));

  if (hasPaymentIntent) {
    // Tentar extrair valor de diferentes formatos
    const amountPatterns = [
      /r\$\s*([\d.,]+)/i,
      /([\d.,]+)\s*reais?/i,
      /valor\s*(?:de|:)?\s*r\$\s*([\d.,]+)/i,
      /valor\s*(?:de|:)?\s*([\d.,]+)/i,
      /([\d.,]+)\s*(?:reais|r\$)/i,
      /(?:de|por|no\s+valor\s+de)\s+r\$\s*([\d.,]+)/i,
      /(?:de|por|no\s+valor\s+de)\s+([\d.,]+)\s*reais?/i,
    ];

    let amountMatch = null;
    for (const pattern of amountPatterns) {
      const match = content.match(pattern);
      if (match) {
        amountMatch = match[1] || match[2];
        break;
      }
    }

    // SÓ retornar create_payment se houver um valor válido
    if (!amountMatch) {
      // Se não houver valor, não é uma ação de criar pagamento, apenas explicação
      return {
        type: 'explain',
      };
    }

    // Tentar extrair descrição
    const descriptionPatterns = [
      /descri[çc][ãa]o[:\s]+(.+?)(?:\.|$|para|com)/i,
      /(?:para|com|sobre)\s+(.+?)(?:\.|$)/i,
    ];

    let descriptionMatch = null;
    for (const pattern of descriptionPatterns) {
      const match = content.match(pattern);
      if (match) {
        descriptionMatch = match[1]?.trim();
        break;
      }
    }

    return {
      type: 'create_payment',
      data: {
        value: amountMatch,
        description: descriptionMatch || undefined,
      },
    };
  }

  // Detectar envio de transferência (deve ter valor E chave PIX explícitos no mesmo padrão)
  // Padrões mais rigorosos que exigem valor E chave juntos
  const transferPatterns = [
    // Padrão: "enviar R$ 100 para 12345678900"
    /(?:enviar|transferir|mandar|pix|pagar)\s+(?:r\$\s*)?([\d.,]+)\s*(?:reais?|r\$)?\s+(?:para|pro|ao|à|chave|pix)\s+([a-zA-Z0-9@._+-]{5,})/i,
    // Padrão: "quero enviar 50 reais para email@exemplo.com"
    /(?:quero|preciso|gostaria de|vou)\s+(?:enviar|transferir|mandar|fazer|realizar)\s+(?:r\$\s*)?([\d.,]+)\s*(?:reais?|r\$)?\s+(?:para|pro|ao|à|chave|pix)\s+([a-zA-Z0-9@._+-]{5,})/i,
    // Padrão: "fazer transferência de R$ 200 para CPF 12345678900"
    /(?:fazer|realizar|criar)\s+(?:uma\s+)?(?:transferência|pix|envio)\s+(?:de\s+)?(?:r\$\s*)?([\d.,]+)\s*(?:reais?|r\$)?\s+(?:para|pro|ao|à|chave|pix)\s+([a-zA-Z0-9@._+-]{5,})/i,
    // Padrão Invertido: "para 12345678900 enviar 100"
    /(?:para|pro|ao|à|chave|pix)\s+([a-zA-Z0-9@._+-]{5,})\s+(?:enviar|transferir|mandar|depositar)\s+(?:r\$\s*)?([\d.,]+)/i,
  ];

  // Verificar se há padrão completo de transferência com valor E chave
  let hasTransferIntent = false;
  let transferMatch = null;

  for (const pattern of transferPatterns) {
    const match = content.match(pattern);
    if (match) {
      // Verificar qual grupo é o valor e qual é a chave
      // Geralmente grupo 1 é valor e 2 é chave, exceto no padrão invertido
      let val = match[1];
      let key = match[2];

      // Se o padrão for invertido (chave primeiro), trocar
      if (pattern.source.includes('para') && pattern.source.indexOf('([a-zA-Z0-9') < pattern.source.indexOf('([\\d.,]+)')) {
        val = match[2];
        key = match[1];
      }

      // Validar que o valor é numérico válido
      const valueStr = val.replace(/\./g, '').replace(',', '.');
      if (!isNaN(parseFloat(valueStr)) && parseFloat(valueStr) > 0) {
        hasTransferIntent = true;
        transferMatch = [match[0], val, key]; // Normalizar para [full, value, key]
        break;
      }
    }
  }

  if (hasTransferIntent && transferMatch) {
    // Valor e chave já foram extraídos do match e validados
    const amountMatch = transferMatch[1];
    const pixKeyMatch = transferMatch[2]?.trim();

    // Tentar identificar tipo da chave PIX
    let pixKeyType: 'CPF' | 'CNPJ' | 'EMAIL' | 'PHONE' | 'RANDOM' | null = null;
    const lowerContent = content.toLowerCase();

    if (/cpf|^\d{11}$/.test(pixKeyMatch || '')) {
      pixKeyType = 'CPF';
    } else if (/cnpj|^\d{14}$/.test(pixKeyMatch || '')) {
      pixKeyType = 'CNPJ';
    } else if (/@|email/.test(pixKeyMatch || '') || lowerContent.includes('email')) {
      pixKeyType = 'EMAIL';
    } else if (/^\d{10,11}$|telefone|celular|phone/.test(pixKeyMatch || '') || lowerContent.includes('telefone') || lowerContent.includes('celular')) {
      pixKeyType = 'PHONE';
    } else if (pixKeyMatch && pixKeyMatch.length === 32) {
      pixKeyType = 'RANDOM';
    }

    // Tentar extrair descrição
    const descriptionPatterns = [
      /descri[çc][ãa]o[:\s]+(.+?)(?:\.|$|para|com)/i,
      /(?:para|com|sobre)\s+(.+?)(?:\.|$)/i,
    ];

    let descriptionMatch = null;
    for (const pattern of descriptionPatterns) {
      const match = content.match(pattern);
      if (match) {
        descriptionMatch = match[1]?.trim();
        break;
      }
    }

    // SÓ retornar create_transfer se houver valor E chave PIX
    if (!amountMatch || !pixKeyMatch) {
      // Se faltar informação essencial, não é uma ação, apenas explicação
      return {
        type: 'explain',
      };
    }

    return {
      type: 'create_transfer',
      data: {
        amount: amountMatch,
        pixKey: pixKeyMatch,
        pixKeyType: pixKeyType || null,
        description: descriptionMatch || undefined,
      },
    };
  }

  // Detectar consulta de saldo
  const balancePatterns = [
    /(?:meu|ver|qual|mostrar)\s+(?:saldo)/i,
    /\bsaldo\b/i,
  ];
  if (balancePatterns.some(p => p.test(content))) {
    return { type: 'show_balance', data: {} };
  }

  // Detectar últimas transações
  const lastTxPatterns = [
    /(últimas|ultimas|recentes)\s+(?:transa[cç][õo]es|pagamentos|saques|movimenta[cç][õo]es)/i,
    /ver\s+(?:transa[cç][õo]es|extrato)/i,
  ];
  if (lastTxPatterns.some(p => p.test(content))) {
    return { type: 'show_last_transactions', data: {} };
  }

  // Detectar alteração de configurações
  const settingsPatterns = [
    /(?:alterar|mudar|atualizar|modificar|configurar)\s+(?:configura[çc][ãa]o|configura[çc][õo]es|config)/i,
    /(?:como|quero|preciso)\s+(?:alterar|mudar|atualizar|modificar)/i,
    /(?:ir para|acessar|abrir)\s+(?:configura[çc][õo]es|config)/i,
  ];

  const hasSettingsIntent = settingsPatterns.some(pattern => pattern.test(content));

  if (hasSettingsIntent) {
    return {
      type: 'update_settings',
      data: {},
    };
  }

  // Se não detectar ação específica, é apenas explicação
  return {
    type: 'explain',
  };
}

/**
 * Construir contexto para a IA sobre o sistema
 */
export function buildSystemContext(userInfo?: {
  name?: string;
  balance?: number;
  plan?: string;
}): string {
  let context = `Você é um assistente virtual inteligente da Amethys Wallet, uma plataforma completa de pagamentos PIX.

🎯 SUA FUNÇÃO PRINCIPAL:
Analise a mensagem do usuário e identifique a intenção. Você deve:
1. Entender o contexto e a intenção do usuário (não apenas palavras-chave)
2. Responder de forma natural e útil
3. Quando detectar uma ação solicitada, retorne um JSON estruturado com a ação

📋 FORMATO DE RESPOSTA:
- Para explicações/perguntas: Responda normalmente em texto
- Para ações executáveis: Retorne JSON no formato:
\`\`\`json
{
  "action": {
    "type": "create_payment" | "create_transfer" | "show_balance" | "show_last_transactions" | "update_settings" | "explain",
    "data": {
      // Dados específicos da ação (valor, chave PIX, descrição, etc.)
    }
  }
}
\`\`\`

IMPORTANTE: Quando o usuário pedir para fazer algo, você DEVE executar automaticamente! Não pergunte confirmação, apenas execute a ação solicitada.

═══════════════════════════════════════════════════════════════
📚 TUTORIAIS COMPLETOS DA PLATAFORMA
═══════════════════════════════════════════════════════════════

**1. GERAR PAGAMENTOS PIX (Depósitos)**
   Quando o usuário pedir para gerar um pagamento, retorne JSON com ação "create_payment":
   - Exemplos de intenção: "Gerar pagamento de R$ 100", "Criar PIX de 50 reais", "Quero um QR code de R$ 200", "Preciso receber 75 reais"
   - Extraia o valor numérico e descrição (se houver)
   - Formato JSON: {"action": {"type": "create_payment", "data": {"value": "100", "description": "opcional"}}}
   - Valores: mínimo R$ 1,00 | máximo R$ 1.000,00 por pagamento
   - Opção "Cobrir taxa": Se ativada, o valor digitado é o líquido recebido, e a taxa é adicionada ao QR Code
   - O sistema retorna um QR Code e código copia-e-cola PIX
   - Acesse em: /dashboard/deposit ou use o botão "Depositar" no dashboard

**2. ENVIAR TRANSFERÊNCIAS PIX**
   Quando o usuário pedir para transferir dinheiro, retorne JSON com ação "create_transfer":
   - Exemplos de intenção: "Enviar R$ 100 para 12345678900", "Transferir 50 reais para email@exemplo.com", "Mandou 200 pro CPF 12345678900", "Pix de 50 para chave aleatoria"
   - Extraia: valor, chave PIX, tipo da chave e descrição (se houver)
   - Formato JSON: {"action": {"type": "create_transfer", "data": {"amount": "100", "pixKey": "12345678900", "pixKeyType": "CPF", "description": "opcional"}}}
   - Tipos de chave PIX (identifique automaticamente):
     * CPF: 11 dígitos numéricos (ex: 12345678900)
     * CNPJ: 14 dígitos numéricos (ex: 12345678000190)
     * EMAIL: contém @ (ex: usuario@email.com)
     * PHONE: 10-11 dígitos numéricos (ex: 11987654321)
     * RANDOM: 32 caracteres alfanuméricos ou qualquer outra string que não se encaixe nos anteriores
   - IMPORTANTE: Só retorne create_transfer se tiver valor E chave PIX explícitos. Se faltar informação, retorne "explain" perguntando o dado faltante.
   - A taxa do plano é deduzida do valor enviado
   - Acesse em: /dashboard/transfer ou use o botão "Transferir" no dashboard

**3. REALIZAR SAQUES**
   Quando o usuário pedir para sacar dinheiro:
   - Exemplos: "Sacar R$ 50", "Fazer saque de 100 reais"
   - Valor mínimo: R$ 5,00
   - Se não informar chave PIX, usa a chave cadastrada no perfil
   - A taxa do plano é deduzida do valor sacado
   - Acesse via API ou interface

**4. VER SALDO**
   Quando o usuário perguntar sobre saldo, retorne JSON com ação "show_balance":
   - Exemplos de intenção: "Meu saldo", "Qual meu saldo", "Ver saldo", "Quanto tenho", "Saldo atual"
   - Formato JSON: {"action": {"type": "show_balance", "data": {}}}
   - O sistema buscará e mostrará o saldo total disponível
   - Inclua informações sobre o plano atual e taxas na resposta

**5. VER TRANSAÇÕES**
   Quando o usuário pedir para ver transações, retorne JSON com ação "show_last_transactions":
   - Exemplos de intenção: "Últimas transações", "Ver extrato", "Meu histórico", "Transações recentes"
   - Formato JSON: {"action": {"type": "show_last_transactions", "data": {}}}
   - O sistema buscará e mostrará as últimas transações (pagamentos recebidos e transferências/saques enviados)
   - Inclua data, valor e descrição na resposta
   - Acesse em: /dashboard/transactions (Extrato completo)

**6. VISUALIZAR RESUMO FINANCEIRO**
   Página com análise detalhada das finanças:
   - Gráficos de receitas e despesas
   - Filtros por período (hoje, 7 dias, 30 dias, ano, todos)
   - Estatísticas de movimentação
   - Acesse em: /dashboard/summary ou menu "Resumo"

**7. CONFIGURAÇÕES DA CONTA**
   Acesse em: /dashboard/settings
   
   **7.1. Informações Pessoais:**
   - Alterar nome completo
   - Alterar telefone (com código de verificação)
   - Alterar e-mail (com código de verificação)
   - Alterar data de nascimento
   - Alterar foto de perfil (avatar)
   
   **7.2. Taxas e Planos:**
   - Ver plano atual (FREE, CARBON, DIAMOND, RICH, ENTERPRISE)
   - Ver taxa por transação e mensalidade
   - Ver limites mínimo e máximo de transações mensais
   - Fazer upgrade de plano manualmente
   - Ativar/desativar renovação automática (padrão: ativado)
   - Ativar/desativar upgrade automático (padrão: ativado)
   
   **7.3. Notificações:**
   - Ativar/desativar notificações de pagamentos recebidos
   - Ativar/desativar notificações de saques concluídos
   - Solicitar permissão de notificações do navegador
   
   **7.4. Segurança:**
   - Alterar senha (com código de verificação)
   - Ativar/desativar segurança de transferências (requer código para transferir)

**8. GERENCIAR API KEYS E CREDENCIAIS**
   Acesse em: /dashboard/credentials
   - Ver API Key principal
   - Criar API Keys secundárias com permissões específicas
   - Gerenciar IPs autorizados
   - Resetar API Keys
   - Ver permissões disponíveis
   - Editar e deletar API Keys secundárias

**9. METAS E RECOMPENSAS**
   Acesse em: /dashboard/goals
   - Sistema de metas de faturamento
   - Recompensas por atingir valores específicos:
     * R$ 10.000: Pulseira Amethys
     * R$ 30.000: Placa 30 Mil
     * R$ 50.000: Placa 50 Mil
     * R$ 100.000: Placa 100 Mil
     * R$ 500.000: Placa 500 Mil
     * R$ 1.000.000: Placa 1 Milhão
     * R$ 5.000.000: Placa 5 Milhões
     * R$ 10.000.000: Placa 10 Milhões
   - (Página em desenvolvimento)

**10. SISTEMA DE PLANOS**
   A plataforma possui 5 planos baseados em volume de transações:
   
   **FREE:**
   - Taxa por transação: R$ 0,70
   - Mensalidade: R$ 0,00
   - Faixa: Até 300 transações/mês
   - Mínimo mensal: 0 (sem mínimo)
   
   **CARBON:**
   - Taxa por transação: R$ 0,65
   - Mensalidade: R$ 19,90
   - Faixa: 300-800 transações/mês
   - Mínimo mensal: 300 transações
   
   **DIAMOND:**
   - Taxa por transação: R$ 0,60
   - Mensalidade: R$ 49,90
   - Faixa: 800-2.000 transações/mês
   - Mínimo mensal: 800 transações
   
   **RICH:**
   - Taxa por transação: R$ 0,55
   - Mensalidade: R$ 149,90
   - Faixa: 3.000-6.000 transações/mês
   - Mínimo mensal: 3.000 transações
   
   **ENTERPRISE:**
   - Taxa por transação: R$ 0,50
   - Mensalidade: R$ 999,97
   - Faixa: Acima de 6.000 transações/mês
   - Mínimo mensal: 6.000 transações
   - Limite máximo sugerido: Sem Limite
   
   **Como funciona:**
   - Renovação automática: Ocorre 1 dia útil antes do vencimento (se tiver saldo)
   - Upgrade automático: Se ativado, upgrade quando ultrapassar limite superior (se tiver saldo)
   - Rebaixamento automático: Se ficar abaixo do mínimo, rebaixa no mês seguinte
   - Conversão proporcional: Ao fazer upgrade, valor restante do plano antigo é convertido
   - Análise mensal: Executada no dia 1 de cada mês às 00:00

**11. NAVEGAÇÃO DO DASHBOARD**
   Menu principal:
   - Início (/dashboard): Visão geral, saldo, botões rápidos, últimas transações, IA
   - Resumo (/dashboard/summary): Análise detalhada com gráficos
   - Extrato (/dashboard/transactions): Todas as transações com filtros
   - Metas (/dashboard/goals): Sistema de metas e recompensas
   - Transferir (/dashboard/transfer): Enviar dinheiro via PIX
   - Depositar (/dashboard/deposit): Gerar QR Code PIX para receber
   - Configurações (/dashboard/settings): Gerenciar conta e preferências
   - Credenciais (/dashboard/credentials): Gerenciar API Keys

═══════════════════════════════════════════════════════════════
🎯 REGRAS DE EXECUÇÃO E DETECÇÃO DE INTENÇÕES
═══════════════════════════════════════════════════════════════

**DETECÇÃO INTELIGENTE DE INTENÇÕES:**
- Use seu conhecimento contextual para entender a intenção do usuário, não apenas palavras-chave
- Perguntas como "Como faço X?" ou "O que é Y?" devem retornar explicação (type: "explain")
- Solicitações diretas como "Gerar pagamento de R$ 100" devem retornar ação (type: "create_payment")
- Se o usuário pedir algo mas faltar informação essencial (ex: "transferir" sem valor/chave), retorne "explain" explicando o que falta

**REGRAS DE EXECUÇÃO:**
- Seja PROATIVO: execute ações automaticamente quando detectar intenção clara
- Não peça confirmação: se o usuário pediu com dados completos, execute (exceto para pagamentos/transferências que requerem confirmação no frontend)
- Se faltar informação essencial (valor, chave PIX), retorne "explain" explicando o que está faltando
- Use markdown **negrito** para destacar títulos e informações importantes
- Seja educativo: quando explicar funcionalidades, forneça tutoriais detalhados
- Direcione o usuário para as páginas corretas quando apropriado

**EXEMPLOS DE DETECÇÃO:**
- "Como faço uma transferência?" → {"action": {"type": "explain"}} + explicação textual
- "Transferir R$ 100 para 12345678900" → {"action": {"type": "create_transfer", "data": {"amount": "100", "pixKey": "12345678900", "pixKeyType": "CPF"}}}
- "Gerar pagamento de 50 reais" → {"action": {"type": "create_payment", "data": {"value": "50"}}}
- "Meu saldo" → {"action": {"type": "show_balance", "data": {}}}
- "O que você pode fazer?" → {"action": {"type": "explain"}} + explicação textual

═══════════════════════════════════════════════════════════════`;

  if (userInfo) {
    context += `\n\n👤 INFORMAÇÕES DO USUÁRIO ATUAL:`;
    if (userInfo.name) context += `\n- Nome: ${userInfo.name}`;
    if (userInfo.balance !== undefined) {
      context += `\n- Saldo: R$ ${(userInfo.balance / 100).toFixed(2)}`;
    }
    if (userInfo.plan) {
      context += `\n- Plano: ${userInfo.plan}`;
      // Adicionar informações do plano
      const planInfo: Record<string, { fee: string; monthly: string; min: string; max: string }> = {
        'FREE': { fee: 'R$ 0,70', monthly: 'R$ 0,00', min: '0', max: '300' },
        'CARBON': { fee: 'R$ 0,65', monthly: 'R$ 19,90', min: '300', max: '800' },
        'DIAMOND': { fee: 'R$ 0,60', monthly: 'R$ 49,90', min: '800', max: '2.000' },
        'RICH': { fee: 'R$ 0,55', monthly: 'R$ 149,90', min: '3.000', max: '6.000' },
        'ENTERPRISE': { fee: 'R$ 0,50', monthly: 'R$ 999,97', min: '6.000', max: 'Sem Limite' },
      };
      const info = planInfo[userInfo.plan];
      if (info) {
        context += `\n  - Taxa por transação: ${info.fee}`;
        context += `\n  - Mensalidade: ${info.monthly}`;
        context += `\n  - Limite mínimo: ${info.min} transações/mês`;
        context += `\n  - Limite máximo sugerido: ${info.max} transações/mês`;
      }
    }
  }

  return context;
}


/**
 * Serviço de IA para análise de descrições de negócio
 * Usa Groq (LLaMA) para classificar se é atividade de risco
 */

const GROQ_API_KEY = process.env.GROQ_API_KEY;
const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';

/**
 * Analisa a descrição do negócio para determinar se é atividade de risco
 * @param {string} description - Descrição do negócio/uso
 * @returns {Promise<{isHighRisk: boolean, reason: string, suggestedCategory: 'WHITE' | 'BLACK'}>}
 */
export async function analyzeBusinessDescription(description) {
    if (!GROQ_API_KEY) {
        console.warn('GROQ_API_KEY não configurada, usando análise por keywords');
        return analyzeByKeywords(description);
    }

    try {
        const response = await fetch(GROQ_API_URL, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${GROQ_API_KEY}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: 'llama-3.1-8b-instant',
                messages: [
                    {
                        role: 'system',
                        content: `Você é um analista de risco de uma plataforma de pagamentos PIX.
Sua tarefa é analisar descrições de negócios e classificar se são de ALTO RISCO (BLACK) ou BAIXO RISCO (WHITE).

⚠️ REGRA CRÍTICA: Seja CONSERVADOR ao classificar como BLACK. Em caso de dúvida, classifique como WHITE.

ALTO RISCO (BLACK) - APENAS se houver CERTEZA de atividade problemática:
- Cassinos, apostas, jogos de azar, bets (blaze, tigrinho, mines, crash, roleta)
- Esquemas de pirâmide, MMN suspeitos, "investimento garantido"
- Golpes, fraudes, estelionato, furto, roubo, crimes em geral
- Se o usuário LITERALMENTE menciona crimes ou atividades criminosas
- Forex, trading de alto risco, opções binárias
- Venda de contas falsas, seguidores/likes falsos, spam
- Drogas, armas, contrabando, produtos ilegais
- Lavagem de dinheiro, laranja, conta laranja
- Usuário EXPLICITAMENTE menciona que recebe muitos estornos/MEDs/chargebacks

BAIXO RISCO (WHITE) - Padrão para negócios legítimos:
- E-commerce, lojas online, dropshipping
- Serviços profissionais, freelancer, consultoria
- Infoprodutos, cursos, mentorias
- Venda de conteúdo adulto/OnlyFans (NÃO é alto risco!)
- Uso pessoal, receber de amigos/família
- Pequenos negócios, restaurantes, serviços locais
- Qualquer pessoa que quer anonimato/privacidade financeira

🔴 NÃO CLASSIFICAR COMO BLACK apenas porque:
- O usuário menciona "anônimo", "privacidade", "sem aparecer"
- O usuário trabalha com conteúdo adulto
- O usuário não quer se identificar
- A descrição é vaga mas não menciona atividades ilegais

Responda APENAS em JSON válido no formato:
{"isHighRisk": true/false, "reason": "motivo breve", "confidence": 0.0-1.0}`
                    },
                    {
                        role: 'user',
                        content: `Analise esta descrição de negócio:\n\n"${description}"`
                    }
                ],
                temperature: 0.1,
                max_tokens: 200,
            }),
        });

        if (!response.ok) {
            console.error('Erro na API Groq:', response.status);
            return analyzeByKeywords(description);
        }

        const data = await response.json();
        const content = data.choices?.[0]?.message?.content;

        if (!content) {
            return analyzeByKeywords(description);
        }

        try {
            // Tentar extrair JSON da resposta
            const jsonMatch = content.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                const result = JSON.parse(jsonMatch[0]);
                return {
                    isHighRisk: result.isHighRisk === true,
                    reason: result.reason || 'Análise automática',
                    suggestedCategory: result.isHighRisk ? 'BLACK' : 'WHITE',
                    confidence: result.confidence || 0.5,
                    aiAnalyzed: true,
                };
            }
        } catch (parseError) {
            console.error('Erro ao parsear resposta da IA:', parseError);
        }

        return analyzeByKeywords(description);

    } catch (error) {
        console.error('Erro ao chamar API Groq:', error);
        return analyzeByKeywords(description);
    }
}

/**
 * Análise por keywords como fallback
 */
function analyzeByKeywords(description) {
    const descLower = (description || '').toLowerCase();

    // Keywords que SEMPRE são alto risco
    const alwaysHighRiskKeywords = [
        'casino', 'cassino', 'aposta', 'apostas', 'bet', 'betting', 'jogo', 'jogos de azar',
        'blaze', 'tigrinho', 'fortune', 'mines', 'crash', 'roleta',
        'pirâmide', 'piramide', 'mmn', 'multinível', 'esquema',
        'golpe', 'golpes', 'fraude', 'fraudes', 'scam',
        'forex', 'trading', 'day trade', 'opções binárias', 'binary',
        'investimento garantido', 'renda passiva fácil', 'ganho fácil',
        'conta fake', 'seguidores', 'likes', 'engajamento', 'spam',
        'droga', 'arma', 'ilegal', 'contrabando',
        'lavagem', 'laranja', 'empréstimo pessoal'
    ];

    // Keywords que indicam problemas com pagamentos (tornam qualquer coisa BLACK)
    const fraudIndicatorKeywords = [
        'estorno', 'estornos', 'chargeback', 'chargebacks',
        'reembolso', 'reembolsos', 'med', 'meds',
        'devolução', 'devoluções', 'contestação', 'contestações'
    ];

    // Keywords de conteúdo adulto/anonimato (só são BLACK se combinadas com fraude)
    const adultAnonKeywords = [
        'xxx', 'pornô', 'porno', 'adult', 'onlyfans', 'privacy',
        'anônimo', 'anonimo', 'anonimato', 'privacidade'
    ];

    // Primeiro: checar keywords sempre de alto risco
    const foundAlwaysHighRisk = alwaysHighRiskKeywords.find(keyword => descLower.includes(keyword));
    if (foundAlwaysHighRisk) {
        return {
            isHighRisk: true,
            reason: `Atividade de risco detectada: ${foundAlwaysHighRisk}`,
            suggestedCategory: 'BLACK',
            confidence: 0.9,
            aiAnalyzed: false,
        };
    }

    // Segundo: checar se menciona problemas com pagamentos
    const hasFraudIndicator = fraudIndicatorKeywords.some(keyword => descLower.includes(keyword));

    // Terceiro: checar conteúdo adulto/anonimato
    const hasAdultAnon = adultAnonKeywords.find(keyword => descLower.includes(keyword));

    // Se tem adulto/anon MAS também menciona fraude -> BLACK
    if (hasAdultAnon && hasFraudIndicator) {
        return {
            isHighRisk: true,
            reason: `Conteúdo adulto/anônimo com indicadores de problemas de pagamento`,
            suggestedCategory: 'BLACK',
            confidence: 0.85,
            aiAnalyzed: false,
        };
    }

    // Se só menciona fraude sem adulto -> BLACK
    if (hasFraudIndicator) {
        return {
            isHighRisk: true,
            reason: `Menção a estornos/problemas de pagamento`,
            suggestedCategory: 'BLACK',
            confidence: 0.8,
            aiAnalyzed: false,
        };
    }

    // Conteúdo adulto/anonimato SEM fraude -> WHITE (mudança importante!)
    if (hasAdultAnon) {
        return {
            isHighRisk: false,
            reason: `Conteúdo adulto/anônimo sem indicadores de fraude`,
            suggestedCategory: 'WHITE',
            confidence: 0.7,
            aiAnalyzed: false,
        };
    }

    return {
        isHighRisk: false,
        reason: 'Nenhum indicador de risco encontrado',
        suggestedCategory: 'WHITE',
        confidence: 0.7,
        aiAnalyzed: false,
    };
}

export default {
    analyzeBusinessDescription,
};

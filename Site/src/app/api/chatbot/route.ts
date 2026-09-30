import { NextRequest, NextResponse } from "next/server";

/** Remove blocos <think>...</think> que alguns modelos (DeepSeek, QwQ, etc.) vazam no output */
function stripThinkTags(text: string): string {
  return text
    .replace(/<think[^>]*>[\s\S]*?<\/think>/gi, "") // tag com fechamento
    .replace(/<think[^>]*>[\s\S]*/gi, "")           // tag sem fechamento
    .trim();
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages } = body;

    if (!Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json({ error: "messages inválidas" }, { status: 400 });
    }

    const apiUrl = process.env.CYM_API_URL;
    const apiKey = process.env.CYM_API_KEY;

    if (!apiUrl || !apiKey) {
      console.warn("[chatbot] CYM_API_URL ou CYM_API_KEY não configuradas");
      return NextResponse.json({
        reply: "Desculpe, o assistente ainda não está configurado. Adicione CYM_API_URL e CYM_API_KEY no .env 🔧",
      });
    }

    const response = await fetch(`${apiUrl}/api/ai/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        model: "CyM Pro",
        messages,
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!response.ok) {
      const errText = await response.text().catch(() => "");
      console.error(`[chatbot] CyM API error ${response.status}:`, errText.slice(0, 200));

      if (response.status === 401 || response.status === 403)
        return NextResponse.json({ reply: "Chave da API inválida. Verifique o CYM_API_KEY no .env" });
      if (response.status === 402)
        return NextResponse.json({ reply: "Créditos insuficientes na conta da API" });
      if (response.status === 429)
        return NextResponse.json({ reply: "Muitas requisições! Aguarde um momento e tente novamente" });

      return NextResponse.json({ reply: "Ops, tive um problema interno. Tente novamente em breve!" });
    }

    const data = await response.json();

    // Limpa <think> do reply antes de enviar pro frontend
    if (typeof data.reply === "string") {
      data.reply = stripThinkTags(data.reply);
    }

    return NextResponse.json(data);

  } catch (err: any) {
    if (err?.name === "TimeoutError") {
      return NextResponse.json({ reply: "A resposta demorou muito. Tente novamente!" });
    }
    console.error("[chatbot] Erro inesperado:", err?.message);
    return NextResponse.json({ reply: "Erro de conexão. Verifique sua internet e tente de novo" });
  }
}
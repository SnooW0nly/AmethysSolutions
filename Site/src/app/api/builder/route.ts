import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { json, ttlDays = 7 } = body;

    if (!json || typeof json !== "string") {
      return NextResponse.json({ error: "json inválido" }, { status: 400 });
    }

    // Valida que é um JSON válido
    try {
      JSON.parse(json);
    } catch {
      return NextResponse.json({ error: "json mal-formado" }, { status: 400 });
    }

    const res = await fetch(`${BACKEND_URL}/builder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ json, ttlDays }),
      cache: "no-store",
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(
        { error: data?.error || "Erro no backend" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 201 });
  } catch (err: any) {
    return NextResponse.json(
      { error: "Erro interno", details: err?.message },
      { status: 500 }
    );
  }
}
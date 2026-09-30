import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params;

  if (!id) {
    return NextResponse.json({ error: "ID inválido" }, { status: 400 });
  }

  const res = await fetch(`${BACKEND_URL}/builder/${id}`, {
    cache: "no-store",
  });

  if (res.status === 404) {
    return NextResponse.json({ error: "Não encontrado" }, { status: 404 });
  }

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
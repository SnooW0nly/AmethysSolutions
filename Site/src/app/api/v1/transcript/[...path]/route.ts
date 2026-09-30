import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

/**
 * Proxy para /api/v1/transcript/[...path]
 * Repassa para o backend: GET e POST
 */

type Params = { path: string[] };

async function handleProxy(req: NextRequest, params: Params) {
  const pathStr = params.path.join("/");
  const search = req.nextUrl?.search || "";
  const url = `${BACKEND_URL}/api/v1/transcript/${pathStr}${search}`;

  const method = req.method;
  const headers = new Headers();

  const incomingHeaders = req.headers;
  const contentType = incomingHeaders.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  const auth = incomingHeaders.get("authorization");
  if (auth) headers.set("authorization", auth);

  const apiKey = incomingHeaders.get("x-api-key");
  if (apiKey) headers.set("x-api-key", apiKey);

  const cookie = incomingHeaders.get("cookie");
  if (cookie) headers.set("cookie", cookie);

  headers.set("accept", incomingHeaders.get("accept") || "application/json");

  let body: BodyInit | undefined = undefined;
  if (["POST", "PUT", "PATCH"].includes(method)) {
    const ct = contentType || "";
    if (ct.includes("multipart/form-data")) {
      const formData = await req.formData();
      body = formData;
      headers.delete("content-type"); // deixa o fetch gerar o boundary correto
    } else {
      body = await req.text();
    }
  }

  try {
    const backendRes = await fetch(url, {
      method,
      headers,
      body,
      cache: "no-store",
    });

    const respContentType =
      backendRes.headers.get("content-type") || "application/json";

    // Se for HTML (transcript), retorna diretamente
    if (respContentType.includes("text/html")) {
      const html = await backendRes.text();
      return new NextResponse(html, {
        status: backendRes.status,
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "public, max-age=300",
        },
      });
    }

    const data = await backendRes.text();

    return new NextResponse(data, {
      status: backendRes.status,
      headers: {
        "Content-Type": respContentType,
        "Cache-Control": "no-store",
      },
    });
  } catch (err: any) {
    console.error("[TRANSCRIPT PROXY]", err);
    return NextResponse.json(
      { error: "Erro ao conectar com o servidor" },
      { status: 503 }
    );
  }
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<Params> }
) {
  return handleProxy(req, await context.params);
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<Params> }
) {
  return handleProxy(req, await context.params);
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<Params> }
) {
  return handleProxy(req, await context.params);
}
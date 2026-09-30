import { NextRequest, NextResponse } from "next/server";

type EndpointParams = {
  endpoint: string[];
};

export async function GET(
  req: NextRequest,
  context: { params: Promise<EndpointParams> }
) {
  return handleProxy(req, context.params);
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<EndpointParams> }
) {
  return handleProxy(req, context.params);
}

export async function PUT(
  req: NextRequest,
  context: { params: Promise<EndpointParams> }
) {
  return handleProxy(req, context.params);
}

export async function PATCH(
  req: NextRequest,
  context: { params: Promise<EndpointParams> }
) {
  return handleProxy(req, context.params);
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<EndpointParams> }
) {
  return handleProxy(req, context.params);
}

async function handleProxy(
  req: NextRequest,
  paramsPromise: Promise<EndpointParams>
) {
  // 👇 AGORA a gente espera o params antes de usar
  const { endpoint } = await paramsPromise;

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (!backendUrl) {
    console.error("NEXT_PUBLIC_BACKEND_URL não definida");
    return NextResponse.json({ error: "Erro interno" }, { status: 500 });
  }

  // Support singular alias: /api/app/... -> backend /apps/...
  let endpointPath = endpoint.join("/");
  if (endpointPath === "app") {
    endpointPath = "apps";
  } else if (endpointPath.startsWith("app/")) {
    endpointPath = `apps/${endpointPath.slice(4)}`;
  }

  const search = req.nextUrl?.search || "";
  const url = `${backendUrl}/${endpointPath}${search}`;

  const method = req.method;
  const headers = new Headers();
  const incomingHeaders = req.headers;
  const contentType = incomingHeaders.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const auth = incomingHeaders.get("authorization");
  if (auth) headers.set("authorization", auth);
  const cookie = incomingHeaders.get("cookie");
  if (cookie) headers.set("cookie", cookie);
  headers.set("accept", incomingHeaders.get("accept") || "application/json");

  let body: BodyInit | undefined = undefined;
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const ct = contentType || "";
    if (ct.includes("multipart/form-data")) {
      const formData = await req.formData();
      body = formData;
      headers.delete("content-type");
    } else {
      body = await req.text();
    }
  }

  try {
    const backendResponse = await fetch(url, {
      method,
      headers,
      body: body ?? undefined,
      cache: "no-store",
      redirect: "manual",
    });

    const setCookie = backendResponse.headers.get("set-cookie");
    const location = backendResponse.headers.get("location");
    const isRedirect =
      backendResponse.status >= 300 &&
      backendResponse.status < 400 &&
      location;

    if (isRedirect && location) {
      const redirectResponse = NextResponse.redirect(
        location,
        backendResponse.status
      );
      if (setCookie) redirectResponse.headers.set("set-cookie", setCookie);
      return redirectResponse;
    }

    const respContentType =
      backendResponse.headers.get("content-type") || "application/octet-stream";

    let proxyBody: BodyInit;
    if (
      respContentType.includes("application/zip") ||
      respContentType.includes("octet-stream")
    ) {
      const arrayBuffer = await backendResponse.arrayBuffer();
      proxyBody = new Uint8Array(arrayBuffer);
    } else {
      proxyBody = await backendResponse.text();
    }

    const response = new NextResponse(proxyBody, {
      status: backendResponse.status,
      headers: {
        "Content-Type": respContentType,
        "Cache-Control": "no-store",
      },
    });

    if (setCookie) response.headers.set("set-cookie", setCookie);
    const contentLength = backendResponse.headers.get("content-length");
    if (contentLength) response.headers.set("content-length", contentLength);

    return response;
  } catch (err: any) {
    console.error("Erro no proxy:", err);

    if (err.cause?.code === "ECONNREFUSED" || err.code === "ECONNREFUSED") {
      console.error("Backend não está respondendo:", url);
      return NextResponse.json(
        { error: "Servidor backend não está disponível" },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: "Erro ao conectar com o servidor", details: err.message },
      { status: 500 }
    );
  }
}

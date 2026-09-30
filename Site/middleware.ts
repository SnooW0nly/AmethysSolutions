import { NextRequest, NextResponse } from "next/server";

export function middleware(req: NextRequest) {
  const raw = req.headers.get("x-forwarded-host") || req.headers.get("host") || "";
  const hostname = raw.toLowerCase().replace(/:.*$/, "");

  // LOG TEMPORÁRIO — remove depois
  console.log("=== MIDDLEWARE DEBUG ===");
  console.log("raw:", raw);
  console.log("hostname:", hostname);
  console.log("pathname:", req.nextUrl.pathname);
  console.log("=======================");
  
  // ── Domínios raiz — nunca são tratados como subdomínio ──────────────────
  const ROOT_DOMAINS = [
    "amethys.solutions",
    "amethysapplications.com.br",
    "amethysapp.vercel.app",
    "localhost",
    "127.0.0.1",
  ];

  const isRootDomain = ROOT_DOMAINS.some(
    (root) => hostname === root || hostname === `www.${root}`
  );

  if (isRootDomain) {
    return NextResponse.next();
  }

  // ── Detecta subdomínio em domínios conhecidos ────────────────────────────
  const knownRootSuffixes = [
    ".amethys.solutions",
    ".amethysapplications.com.br",
    ".amethysapp.vercel.app",
    ".localhost",
  ];

  let subdomain: string | null = null;
  for (const suffix of knownRootSuffixes) {
    if (hostname.endsWith(suffix)) {
      const candidate = hostname.slice(0, hostname.length - suffix.length);
      // Aceita só um nível: "builder" sim, "x.builder" não
      if (!candidate.includes(".")) {
        subdomain = candidate;
        break;
      }
    }
  }

  console.log("🔍 MIDDLEWARE subdomain detectado:", subdomain);

  if (subdomain === "builder") {
    const url = req.nextUrl.clone();
    url.pathname = `/builder${url.pathname === "/" ? "" : url.pathname}`;
    console.log("🔍 MIDDLEWARE rewrite para:", url.pathname);
    return NextResponse.rewrite(url);
  }

  // Subdomínio desconhecido ou ambiente Vercel interno → rota normal
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon|icons|amethys\\.png).*)"],
};

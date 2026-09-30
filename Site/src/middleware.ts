import { NextRequest, NextResponse } from "next/server";

export function middleware(req: NextRequest) {
  const raw = req.headers.get("x-forwarded-host") || req.headers.get("host") || "";
  const hostname = raw.toLowerCase().replace(/:.*$/, "");

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
      if (!candidate.includes(".")) {
        subdomain = candidate;
        break;
      }
    }
  }

  if (subdomain === "builder") {
    const url = req.nextUrl.clone();
    url.pathname = `/builder${url.pathname === "/" ? "" : url.pathname}`;
    return NextResponse.rewrite(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon|icons|amethys\\.png).*)"],
};

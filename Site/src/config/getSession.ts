import "server-only";
import { headers, cookies } from "next/headers";

export async function getSession() {
    const hdrs = await headers();
    const host = hdrs.get("x-forwarded-host") || hdrs.get("host");
    const proto = hdrs.get("x-forwarded-proto") || "http";
    const base = process.env.NEXT_PUBLIC_BASE_URL || (host ? `${proto}://${host}` : "");

    if (!base) return null;

    const cookieStore = await cookies();
    const cookieHeader = cookieStore.getAll().map((c: { name: string; value: string }) => `${c.name}=${c.value}`).join("; ");

    try {
        const res = await fetch(`${base}/api/auth/session`, {
            cache: "no-store",
            headers: {
                accept: "application/json",
                ...(cookieHeader ? { cookie: cookieHeader } : {}),
            },
        });

        if (!res.ok) return null;
        const data = await res.json();
        return data?.user ?? null;
    } catch {
        return null;
    }
}
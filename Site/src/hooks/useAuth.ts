"use client";

import { useEffect, useState } from "react";
import type { User } from "@/config/dashboard";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUser() {
      try {
        const res = await fetch(`/api/auth/session`, { credentials: "include" });

        if (!res.ok) {
          setUser(null);
          setLoading(false);
          return;
        }

        const data = await res.json();
        setUser(data.user as User);
      } catch (err) {
        console.error("Erro ao buscar sessão:", err);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    fetchUser();
  }, []);

  async function logout() {
    try {
      await fetch(`/api/auth/logout`, { method: "POST", credentials: "include" });
      setUser(null);
    } catch (err) {
      console.error("Erro ao fazer logout:", err);
    }
  }

  return { user, loading, logout };
}

export function useRequireAuth() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  return { user, loading } as const;
}

export function useRequireAdmin() {
  const { user, loading } = useRequireAuth();

  useEffect(() => {
    if (!loading && user && !user.admin) {
      // For stricter UX and security posture, do not render admin UI to non-admins
      notFound();
    }
  }, [loading, user]);

  return { user, loading } as const;
}
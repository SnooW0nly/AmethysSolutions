"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export type PaymentStatus = "pending" | "approved" | "cancelled";

export type PaymentData = {
  id: string;
  plan: { id: string; name: string; price: number; months?: number | null };
  coupon: { code: string; discountPercent: number } | null;
  priceFinal: number;
  applicationId?: string;
  status: PaymentStatus;
  qr_code_base64: string;
  qr_code_text: string;
  expiresAt: string;
  createdAt?: string;
};

export function usePayment(paymentId: string) {
  const [data, setData] = useState<PaymentData | null>(null);
  const [status, setStatus] = useState<PaymentStatus>("pending");
  const [expiresAt, setExpiresAt] = useState<number>(Date.now() + 10 * 60 * 1000);
  const [now, setNow] = useState<number>(Date.now());
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  // Time calculations
  const secondsLeft = useMemo(() => {
    const diff = Math.max(0, Math.floor((expiresAt - now) / 1000));
    return diff;
  }, [expiresAt, now]);

  const progress = useMemo(() => {
    const total = 10 * 60; // 10 minutes in seconds
    const clamped = Math.max(0, Math.min(total, secondsLeft));
    return 100 - Math.round((clamped / total) * 100);
  }, [secondsLeft]);

  const imgSrc = useMemo(() => {
    const s = data?.qr_code_base64 || "";
    return s.startsWith("data:") ? s : `data:image/png;base64,${s}`;
  }, [data?.qr_code_base64]);

  const isExpired = status !== "approved" && secondsLeft <= 0;

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setLoadError(null);
      try {
        const res = await fetch(`/api/payment/${paymentId}/status`, {
          credentials: "include",
          cache: "no-store",
          headers: { accept: "application/json" },
        });
        if (res.status === 404 || res.status === 403) {
          setNotFound(true);
          return;
        }
        const json = await res.json().catch(() => null);
        if (!res.ok || !json?.id) throw new Error(json?.error || "Falha ao carregar pagamento");
        if (cancelled) return;
        setData(json as PaymentData);
        setStatus((json as PaymentData).status);
        setExpiresAt(new Date((json as PaymentData).expiresAt).getTime());
      } catch (err: any) {
        if (!cancelled) setLoadError(String(err?.message || "Erro inesperado"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [paymentId]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  // Poll payment status every 5s while pending and not expired
  useEffect(() => {
    if (!data?.id) return;
    if (status !== "pending" || isExpired) {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }
    async function pollOnce() {
      if (!data?.id) return;
      try {
        const res = await fetch(`/api/payment/${data.id}/status`, {
          credentials: "include",
          cache: "no-store",
          headers: { accept: "application/json" },
        });
        const json = await res.json().catch(() => null);
        if (json?.status) setStatus(json.status as PaymentStatus);
        if (json?.expiresAt) setExpiresAt(new Date(json.expiresAt).getTime());
      } catch {}
    }
    pollOnce();
    pollRef.current = setInterval(pollOnce, 5_000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [data?.id, status, isExpired]);

  return {
    data,
    status,
    loading,
    loadError,
    notFound,
    secondsLeft,
    progress,
    minutes: Math.floor(secondsLeft / 60),
    seconds: secondsLeft % 60,
    imgSrc,
    isExpired,
  };
}



"use client";

import { useEffect } from "react";
import { Loading } from "@/components/Loading";

export default function LogoutPage() {
  useEffect(() => {
    const doLogout = async () => {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
      window.location.href = "/";
    };
    doLogout();
  }, []);

  return <Loading />;
}
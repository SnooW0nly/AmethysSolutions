"use client";

import { useEffect } from "react";
import { useRouter, useParams } from "next/navigation";

export default function AppIndexRedirect() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = params?.id as string | undefined;

  useEffect(() => {
    if (id) router.replace(`/dashboard/app/${id}/overview`);
  }, [id, router]);

  return null;
}
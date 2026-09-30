"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loading } from "@/components/Loading";

export default function ConfigPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params?.id as string | undefined;

  useEffect(() => {
    if (id) {
      router.replace(`/dashboard/app/${id}/config/customization`);
    }
  }, [id, router]);

  return <Loading />;
}



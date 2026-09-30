"use client";

import { Button } from "@heroui/react";
import { useRouter } from "next/navigation";

type ExpiredViewProps = {
  planId?: string;
};

export default function ExpiredView({ planId }: ExpiredViewProps) {
  const router = useRouter();
  return (
    <section className="flex flex-col items-center justify-center h-full gap-4 py-20">
      <div className="flex flex-col items-center justify-center gap-2 px-4 text-center">
        <h2 className="text-2xl font-bold">Pagamento expirado</h2>
        <p className="text-foreground/50 font-normal text-sm max-w-xl">O QR Code não é mais válido. Você pode gerar um novo pagamento e tentar novamente.</p>
      </div>
      <div className="flex gap-2">
        <Button color="primary" onPress={() => router.push(`/purchase?plan=${planId ?? ""}`)}>Criar novo pagamento</Button>
        <Button variant="flat" onPress={() => router.push("/pricing")}>Ver planos</Button>
      </div>
    </section>
  );
}



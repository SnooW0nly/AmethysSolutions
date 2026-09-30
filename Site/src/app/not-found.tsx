"use client";

import {
  Button,
} from "@heroui/react";
import { useRouter } from "next/navigation"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft } from "@fortawesome/free-solid-svg-icons";

export default function NotFound() {
  const router = useRouter();

  return (
    <section className="flex flex-col items-center justify-center h-full gap-4 py-20">
      <div className="flex items-center w-full">
        <div className="flex-grow border-t border-foreground/20"></div>
        <span className="mx-4 text-6xl font-bold">404</span>
        <div className="flex-grow border-t border-foreground/20"></div>
      </div>
      <div className="flex flex-col items-center justify-center gap-1">
        <h2 className="text-2xl font-bold">Página não encontrada</h2>
        <p className="text-foreground/50 font-normal text-sm text-center">A página que você está procurando foi movida ou não existe.</p>
      </div>
      <Button onPress={() => router.push("/")} color="primary" className="w-fit">
        <FontAwesomeIcon icon={faArrowLeft} className="w-4 h-4 text-foreground/80" />
        Voltar para a página inicial
      </Button>
    </section>
  );
}

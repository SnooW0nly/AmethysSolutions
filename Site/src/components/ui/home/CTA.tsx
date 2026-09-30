"use client";

import { Button } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";

export function CTASection() {
  return (
    <section>
      <div className="flex flex-col md:flex-row md:justify-between gap-2 md:items-center">
        <h1 className="text-4xl font-bold max-w-2xl">Transforme seu servidor em uma fonte de renda</h1>
        <div className="flex flex-row gap-2 md:max-w-xl">
          <Button
            className="w-fit bg-transparent border border-foreground/10 text-foreground hover:bg-foreground/5"
            onClick={() => {
              window.location.href = "/dashboard";
            }}
          >
            <span className="flex items-center gap-1">
              Acessar a Dashboard
              <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[11px]" />
            </span>
          </Button>
          <Button
            className="w-fit bg-foreground text-background hover:bg-foreground/90"
            onClick={() => {
              window.location.href = "/pricing";
            }}
          >
            <span>Começar agora</span>
          </Button>
        </div>
      </div>
    </section>
  );
}



"use client";

import React from "react";

type Action = "start" | "stop" | "restart";

type ActionOverlayProps = {
  visible: boolean;
  action: Action | null;
};

export function ActionOverlay({ visible, action }: ActionOverlayProps) {
  if (!visible || !action) return null;

  const title =
    action === "restart" ? "Reiniciando o bot..." :
    action === "start" ? "Ligando o bot..." :
    "Desligando o bot...";

  const description =
    action === "stop"
      ? "Estamos desligando seu bot com segurança. Isso leva poucos instantes."
      : "Verificando emojis, configurando criptografia e preparando o ambiente. Isso pode levar alguns instantes.";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      aria-live="polite"
      aria-busy="true"
    >
      {/* Backdrop with blur */}
      <div className="absolute inset-0 backdrop-blur-sm md:backdrop-blur bg-background/60" />

      {/* Content */}
      <div className="relative flex flex-col items-center text-center px-6">
        <div className="p-4 rounded-full bg-primary/10">
          <img
            src="/amethys.png"
            width={56}
            height={56}
            alt="Amethys"
            className="animate-spin [animation-duration:2.2s]"
          />
        </div>
        <h3 className="mt-4 text-xl font-semibold text-foreground">{title}</h3>
        <p className="mt-2 text-sm text-foreground/70 max-w-md">{description}</p>
      </div>
    </div>
  );
}



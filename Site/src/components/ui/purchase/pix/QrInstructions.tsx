"use client";

import { Button, Tooltip } from "@heroui/react";
import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { faCheck } from "@fortawesome/free-solid-svg-icons";

type QrInstructionsProps = {
  imgSrc: string;
  qrText: string;
};

export default function QrInstructions({ imgSrc, qrText }: QrInstructionsProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      if (!qrText) return;
      await navigator.clipboard.writeText(qrText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  return (
    <div className="w-full flex flex-col lg:flex-row items-start gap-6">
      <div className="rounded-md self-center md:self-start">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={imgSrc} alt="QR Code PIX" className="h-56 w-56 rounded-md" />
      </div>
      <div className="flex-1 w-full max-w-xl">
        <div className="flex flex-col gap-3">
          <div className="flex items-start gap-3">
            <div className="h-7 w-7 rounded-full bg-foreground/10 border border-foreground/10 flex items-center justify-center text-sm font-semibold">1</div>
            <div>
              <p className="text-sm font-medium">Abra seu banco</p>
              <p className="text-xs text-foreground/60">Acesse o aplicativo do seu banco.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="h-7 w-7 rounded-full bg-foreground/10 border border-foreground/10 flex items-center justify-center text-sm font-semibold">2</div>
            <div>
              <p className="text-sm font-medium">Escaneie ou use copia e cola</p>
              <p className="text-xs text-foreground/60">Escaneie o QR Code ao lado ou copie o código abaixo.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="h-7 w-7 rounded-full bg-foreground/10 border border-foreground/10 flex items-center justify-center text-sm font-semibold">3</div>
            <div>
              <p className="text-sm font-medium">Efetue o pagamento</p>
              <p className="text-xs text-foreground/60">Confirme o valor e finalize no seu banco.</p>
            </div>
          </div>
          <div className="relative mt-2">
            <p className="text-xs text-foreground/70 border border-foreground/10 break-all text-left max-w-full p-3 pr-12 bg-foreground/5 rounded-md font-[monospace]">{qrText}</p>
            <div className="absolute top-2 right-2">
              <Tooltip content={copied ? "Copiado!" : "Copiar código PIX"} isOpen={copied} placement="top">
                <Button isIconOnly variant="flat" size="sm" onPress={handleCopy} aria-label="Copiar código PIX">
                  {copied ? (
                    <FontAwesomeIcon icon={faCheck} className="w-4 h-4" />
                  ) : (
                    <FontAwesomeIcon icon={faCopy} className="w-4 h-4" />
                  )}
                </Button>
              </Tooltip>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}



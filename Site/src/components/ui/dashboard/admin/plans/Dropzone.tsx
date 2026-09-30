"use client";

import { PropsWithChildren, useRef } from "react";

type DropzoneProps = {
  onFile: (file: File | null) => void;
  accept?: string;
  placeholder: React.ReactNode;
  selected?: File | null;
  linkHref?: string;
};

export function Dropzone({ onFile, accept = ".zip", placeholder, selected, linkHref }: PropsWithChildren<DropzoneProps>) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  return (
    <div
      className="border-2 border-dashed border-foreground/20 rounded-lg p-4 text-center cursor-pointer hover:border-foreground/30 transition-colors"
      onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
      onDrop={(e) => {
        e.preventDefault();
        const file = e.dataTransfer.files?.[0] || null;
        if (file && accept.split(',').some(ext => file.name.endsWith(ext.trim()))) onFile(file);
      }}
      onClick={() => {
        inputRef.current?.click();
      }}
    >
      {placeholder}
      {selected ? (
        <p className="text-xs text-foreground mt-1">Selecionado: {selected.name}</p>
      ) : linkHref ? (
        <a className="text-xs text-primary underline" href={linkHref} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>Baixar arquivo atual</a>
      ) : null}
      <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={(e) => {
        const f = e.target.files?.[0] || null;
        onFile(f);
      }} />
    </div>
  );
}



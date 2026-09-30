"use client";

import { Sidebar } from "@/components/Sidebar";
import { Button } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faXmark } from "@fortawesome/free-solid-svg-icons";

export type AdminSection = "usuarios" | "cupons" | "aplicacoes" | "planos" | "pagamentos" | "gifts" | "updates";

type SectionDef = { id: AdminSection; label: string; icon: any };

export function AdminSidebar({
  sections,
  selected,
  onSelect,
}: {
  sections: SectionDef[];
  selected: AdminSection;
  onSelect: (s: AdminSection) => void;
}) {
  return (
    <aside className="hidden md:block w-64 shrink-0">
      <Sidebar sections={sections} selected={selected} onSelect={(s) => onSelect(s as AdminSection)} />
    </aside>
  );
}

export function AdminSidebarOverlay({
  isOpen,
  onClose,
  sections,
  selected,
  onSelect,
}: {
  isOpen: boolean;
  onClose: () => void;
  sections: SectionDef[];
  selected: AdminSection;
  onSelect: (s: AdminSection) => void;
}) {
  if (!isOpen) return null;
  return (
    <div className="md:hidden fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/80" onClick={onClose} />
      <div className="relative h-full w-72 bg-background border-r border-foreground/10 p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold">Admin</h2>
          <Button size="sm" isIconOnly variant="light" onPress={onClose}>
            <FontAwesomeIcon icon={faXmark} />
          </Button>
        </div>
        <Sidebar
          sections={sections}
          selected={selected}
          onSelect={(s) => {
            onSelect(s as AdminSection);
            onClose();
          }}
        />
      </div>
    </div>
  );
}



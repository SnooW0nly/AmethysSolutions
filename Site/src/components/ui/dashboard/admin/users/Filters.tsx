"use client";

import { Button, Input, Select, SelectItem } from "@heroui/react";

export function UsersFilters({
  search,
  adminFilter,
  sort,
  onChange,
  onApply,
}: {
  search: string;
  adminFilter: string;
  sort: string;
  onChange: (next: { search?: string; adminFilter?: string; sort?: string }) => void;
  onApply: () => void;
}) {
  return (
    <div className="grid grid-cols-4 gap-1 items-end">
      <Input label="Buscar" placeholder="nome, email ou id" size="sm" value={search} onChange={(e) => onChange({ search: e.target.value })} />
      <Select label="Admin" size="sm" selectedKeys={adminFilter ? new Set([adminFilter]) : new Set([])} onSelectionChange={(keys) => { const val = Array.from(keys as any)[0] as string | undefined; onChange({ adminFilter: val || "" }); }}>
        <SelectItem key="">Todos</SelectItem>
        <SelectItem key="true">Sim</SelectItem>
        <SelectItem key="false">Não</SelectItem>
      </Select>
      <Select label="Ordenar" size="sm" selectedKeys={new Set([sort])} onSelectionChange={(keys) => { const val = Array.from(keys as any)[0] as string; onChange({ sort: val }); }}>
        <SelectItem key="createdAt_desc">Criado (recente)</SelectItem>
        <SelectItem key="createdAt_asc">Criado (antigo)</SelectItem>
        <SelectItem key="name_asc">Nome (A-Z)</SelectItem>
        <SelectItem key="name_desc">Nome (Z-A)</SelectItem>
      </Select>
      <Button size="lg" radius="sm" onPress={onApply}>Filtrar</Button>
    </div>
  );
}



"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, Switch, Select, SelectItem } from "@heroui/react";
import { Coupon, CouponForm } from "@/types/coupons";
import { CouponCard } from "@/components/ui/dashboard/admin/coupons/CouponCard";
import { AuditTable } from "@/components/ui/dashboard/admin/coupons/AuditTable";
import { SectionHeader } from "@/components/layout/SectionHeader";

export function CuponsSection() {
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [totalLogs, setTotalLogs] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [logLoading, setLogLoading] = useState(false);
  const [filters, setFilters] = useState<{ action?: string; name?: string; from?: string; to?: string }>({});

  const [isOpen, setIsOpen] = useState(false);
  const [editName, setEditName] = useState<string | null>(null);
  const [form, setForm] = useState<CouponForm>({ name: "", percent: "", maxUses: "", availableDays: "", minCart: "", archived: false });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/admin/coupons", { cache: "no-store" });
      if (!res.ok) throw new Error("Erro ao carregar cupons");
      const data = await res.json();
      setCoupons(Array.isArray(data?.coupons) ? data.coupons : []);
    } catch (e: any) {
      setError(e?.message || "Erro ao carregar cupons");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const loadLogs = async () => {
    try {
      setLogLoading(true);
      const qs = new URLSearchParams();
      if (filters.action) qs.set("action", filters.action);
      if (filters.name) qs.set("name", filters.name);
      if (filters.from) qs.set("from", filters.from);
      if (filters.to) qs.set("to", filters.to);
      qs.set("page", String(page));
      qs.set("limit", String(limit));
      const res = await fetch(`/api/admin/coupons/audit?${qs.toString()}`);
      const data = await res.json();
      setLogs(Array.isArray(data?.logs) ? data.logs : []);
      setTotalLogs(Number(data?.total || 0));
    } catch {
      setLogs([]);
    } finally {
      setLogLoading(false);
    }
  };

  // Auto-carrega auditoria ao abrir a página e quando filtros/paginação mudarem
  useEffect(() => {
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.action, filters.name, filters.from, filters.to, page, limit]);

  const openCreate = () => {
    setEditName(null);
    setForm({ name: "", percent: "", maxUses: "", availableDays: "", minCart: "", archived: false });
    setShowAdvanced(false);
    setModalError(null);
    setIsOpen(true);
  };

  const openEdit = (c: Coupon) => {
    setEditName(c.name);
    setForm({
      name: c.name,
      percent: String(c.percent ?? ""),
      maxUses: String(c.maxUses ?? ""),
      availableDays: String(c.availableDays ?? ""),
      minCart: String(c.minCart ?? ""),
      archived: !!c.archived,
    });
    setShowAdvanced(false);
    setModalError(null);
    setIsOpen(true);
  };

  const submit = async () => {
    try {
      setModalError(null);
      if (!form.name.trim()) throw new Error("Nome é obrigatório");
      if (!form.percent) throw new Error("Percentual é obrigatório");
      const payload = {
        name: form.name.trim(),
        percent: Number(form.percent || 0),
        maxUses: form.maxUses ? Number(form.maxUses) : undefined,
        availableDays: form.availableDays ? Number(form.availableDays) : undefined,
        minCart: form.minCart ? Number(form.minCart) : undefined,
        archived: !!form.archived,
      };
      const url = editName ? `/api/admin/coupons/${encodeURIComponent(editName)}` : "/api/admin/coupons";
      const method = editName ? "PUT" : "POST";
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.error || "Erro ao salvar cupom");
      }
      setIsOpen(false);
      await load();
    } catch (e: any) {
      setModalError(e?.message || "Erro ao salvar");
    }
  };

  const toggleArchive = async (c: Coupon) => {
    const url = `/api/admin/coupons/${encodeURIComponent(c.name)}/${c.archived ? "restore" : "archive"}`;
    const res = await fetch(url, { method: "POST" });
    if (res.ok) await load();
  };

  const handleDelete = async (c: Coupon) => {
    if (!confirm(`Apagar cupom ${c.name}?`)) return;
    const res = await fetch(`/api/admin/coupons/${encodeURIComponent(c.name)}`, { method: "DELETE" });
    if (res.ok) {
      setIsOpen(false);
      await load();
    }
  };

  const grid = useMemo(() => {
    if (loading) {
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-36 rounded-lg bg-foreground/5 border border-foreground/10 animate-pulse" />
          ))}
        </div>
      );
    }
    if (!coupons.length) {
      return <div className="rounded-lg bg-foreground/5 border border-foreground/10 p-4 text-sm text-foreground/70">Nenhum cupom cadastrado.</div>;
    }
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {coupons.map((c) => (
          <CouponCard key={c.name} coupon={c} onEdit={openEdit} onToggleArchive={toggleArchive} />
        ))}
      </div>
    );
  }, [coupons, loading]);

  return (
    <div className="flex flex-col gap-3">
      {error ? <div className="rounded-lg bg-danger/10 border border-danger/20 text-danger-500 text-sm p-2">{error}</div> : null}
      <SectionHeader description="Gerencie cupons de desconto" actions={<Button size="sm" color="primary" onPress={openCreate}>Novo cupom</Button>} />
      {grid}

      <div className="mt-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">Auditoria</h3>
          <Button size="sm" variant="light" onPress={loadLogs}>Atualizar</Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-2">
          <Select
            label="Ação"
            size="sm"
            selectedKeys={filters.action ? new Set([filters.action]) : new Set([])}
            onSelectionChange={(keys) => {
              const val = Array.from(keys as any)[0] as string | undefined;
              setFilters({ ...filters, action: val || undefined });
            }}
          >
            <SelectItem key="">Todas</SelectItem>
            <SelectItem key="create">create</SelectItem>
            <SelectItem key="update">update</SelectItem>
            <SelectItem key="validate">validate</SelectItem>
            <SelectItem key="redeem">redeem</SelectItem>
            <SelectItem key="archive">archive</SelectItem>
            <SelectItem key="restore">restore</SelectItem>
          </Select>
          <Input label="Cupom (nome)" value={filters.name || ""} onChange={(e) => setFilters({ ...filters, name: e.target.value })} size="sm" />
          <Input label="De" type="date" value={filters.from || ""} onChange={(e) => setFilters({ ...filters, from: e.target.value })} size="sm" />
          <Input label="Até" type="date" value={filters.to || ""} onChange={(e) => setFilters({ ...filters, to: e.target.value })} size="sm" />
        </div>
        <div className="rounded-lg border border-foreground/10 bg-foreground/2 p-3">
          <AuditTable logs={logs} loading={logLoading} />
          <div className="flex items-center justify-between mt-2 text-xs text-foreground/70">
            <span>Total: {totalLogs}</span>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="light" isDisabled={page <= 1} onPress={() => setPage((p) => Math.max(p - 1, 1))}>Anterior</Button>
              <span>Página {page}</span>
              <Button size="sm" variant="light" isDisabled={(page * limit) >= totalLogs} onPress={() => setPage((p) => p + 1)}>Próxima</Button>
            </div>
          </div>
        </div>
      </div>

      <Modal isOpen={isOpen} onOpenChange={(o) => setIsOpen(o)}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>{editName ? `Editar cupom` : `Novo cupom`}</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-2">
                  {modalError ? <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">{modalError}</div> : null}
                  <Input label={<>Nome <span className="text-danger">*</span></>} value={form.name} onChange={(e) => {
                    const v = (e.target.value || "").toUpperCase().replace(/\s+/g, "-").slice(0, 20);
                    setForm({ ...form, name: v });
                  }} size="sm" isDisabled={!!editName} description="Máx. 20 caracteres, maiúsculo" />
                  <Input label={<>Percentual (%) <span className="text-danger">*</span></>} type="number" value={form.percent} onChange={(e) => setForm({ ...form, percent: e.target.value })} size="sm" />

                  <Button variant="light" size="sm" onPress={() => setShowAdvanced((v) => !v)}>{showAdvanced ? "Ocultar avançados" : "Mostrar avançados"}</Button>
                  {showAdvanced ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                      <Input label="Máximo de usos" type="number" value={form.maxUses} onChange={(e) => setForm({ ...form, maxUses: e.target.value })} size="sm" />
                      <Input label="Disponível por (dias)" type="number" value={form.availableDays} onChange={(e) => setForm({ ...form, availableDays: e.target.value })} size="sm" />
                      <Input label="Mínimo no carrinho (R$)" type="number" value={form.minCart} onChange={(e) => setForm({ ...form, minCart: e.target.value })} size="sm" />
                      <div className="col-span-1 md:col-span-3 flex items-center justify-between">
                        <Switch isSelected={form.archived} onValueChange={(v) => setForm({ ...form, archived: v })}>Arquivado</Switch>
                        {editName ? (
                          <Button size="sm" color="danger" variant="light" onPress={() => handleDelete({ name: editName, percent: Number(form.percent || 0), archived: form.archived } as any)}>Apagar</Button>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>Cancelar</Button>
                <Button color="primary" onPress={submit}>Salvar</Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}



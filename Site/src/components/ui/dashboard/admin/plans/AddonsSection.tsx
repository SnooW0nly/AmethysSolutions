"use client";

import { useEffect, useState } from "react";
import {
  Button,
  Input,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  Switch,
  Textarea,
  Chip,
} from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPlus,
  faPen,
  faTrash,
  faToggleOn,
  faToggleOff,
  faPuzzlePiece,
} from "@fortawesome/free-solid-svg-icons";

type Addon = {
  id: string;
  name: string;
  shortDescription: string;
  extraValue: number;
  active: boolean;
  enabledForPlans: string[];
};

type Plan = { id: string; name: string };

export function AddonsSection() {
  const [addons, setAddons] = useState<Addon[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    id: "",
    name: "",
    shortDescription: "",
    extraValue: "",
    active: true,
    enabledForPlans: [] as string[],
  });

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editAddon, setEditAddon] = useState<Addon | null>(null);
  const [editForm, setEditForm] = useState({
    name: "",
    shortDescription: "",
    extraValue: "",
    active: true,
    enabledForPlans: [] as string[],
  });
  const [editError, setEditError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const [addonsRes, plansRes] = await Promise.all([
        fetch("/api/admin/plans-config/addons", { cache: "no-store" }),
        fetch("/api/admin/plans/list", { cache: "no-store" }),
      ]);
      const addonsData = await addonsRes.json();
      const plansData = await plansRes.json();
      setAddons(Array.isArray(addonsData?.addons) ? addonsData.addons : []);
      setPlans(Array.isArray(plansData?.data) ? plansData.data : []);
    } catch {
      setError("Erro ao carregar addons");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const togglePlan = (planId: string, current: string[]) => {
    const has = current.includes(planId);
    return has ? current.filter((p) => p !== planId) : [...current, planId];
  };

  const handleCreate = async () => {
    try {
      setCreateError(null);
      if (!createForm.name.trim()) throw new Error("Nome é obrigatório");
      const extraValue = parseFloat(createForm.extraValue);
      if (isNaN(extraValue) || extraValue < 0) throw new Error("Valor adicional inválido");

      const res = await fetch("/api/admin/plans-config/addons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: createForm.id || createForm.name,
          name: createForm.name,
          shortDescription: createForm.shortDescription,
          extraValue,
          active: createForm.active,
          enabledForPlans: createForm.enabledForPlans,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.error || "Erro ao criar addon");
      }
      setIsCreateOpen(false);
      setCreateForm({ id: "", name: "", shortDescription: "", extraValue: "", active: true, enabledForPlans: [] });
      await load();
    } catch (err: any) {
      setCreateError(err?.message || "Erro");
    }
  };

  const openEdit = (addon: Addon) => {
    setEditAddon(addon);
    setEditForm({
      name: addon.name,
      shortDescription: addon.shortDescription,
      extraValue: String(addon.extraValue),
      active: addon.active,
      enabledForPlans: addon.enabledForPlans,
    });
    setIsEditOpen(true);
  };

  const handleEdit = async () => {
    try {
      setEditError(null);
      if (!editAddon) return;
      const extraValue = parseFloat(editForm.extraValue);
      if (isNaN(extraValue) || extraValue < 0) throw new Error("Valor adicional inválido");

      const res = await fetch(`/api/admin/plans-config/addons/${encodeURIComponent(editAddon.id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editForm.name,
          shortDescription: editForm.shortDescription,
          extraValue,
          active: editForm.active,
          enabledForPlans: editForm.enabledForPlans,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.error || "Erro ao salvar");
      }
      setIsEditOpen(false);
      await load();
    } catch (err: any) {
      setEditError(err?.message || "Erro");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Tem certeza que deseja remover este addon?")) return;
    try {
      await fetch(`/api/admin/plans-config/addons/${encodeURIComponent(id)}`, { method: "DELETE" });
      await load();
    } catch {
      setError("Erro ao remover addon");
    }
  };

  const PlanToggle = ({
    planId,
    planName,
    enabled,
    onChange,
  }: {
    planId: string;
    planName: string;
    enabled: boolean;
    onChange: () => void;
  }) => (
    <button
      onClick={onChange}
      className={`flex items-center gap-2 text-xs px-2 py-1.5 rounded-lg border transition-colors ${
        enabled
          ? "border-primary/40 bg-primary/10 text-primary"
          : "border-foreground/10 bg-foreground/2 text-foreground/50 hover:bg-foreground/5"
      }`}
    >
      <FontAwesomeIcon icon={enabled ? faToggleOn : faToggleOff} className="text-base" />
      {planName}
    </button>
  );

  return (
    <div className="flex flex-col gap-3">
      {error && (
        <div className="rounded-lg bg-danger/10 border border-danger/20 text-danger-500 text-sm p-2">{error}</div>
      )}

      <div className="flex items-center justify-between">
        <p className="text-sm text-foreground/70">
          Gerencie os adicionais disponíveis para os planos (ex: Bot Black)
        </p>
        <Button
          onPress={() => setIsCreateOpen(true)}
          color="primary"
          size="sm"
          startContent={<FontAwesomeIcon icon={faPlus} />}
        >
          Novo Addon
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-28 rounded-lg bg-foreground/5 border border-foreground/10 animate-pulse" />
          ))}
        </div>
      ) : addons.length === 0 ? (
        <div className="rounded-lg bg-foreground/5 border border-foreground/10 p-4 text-sm text-foreground/60 flex items-center gap-2">
          <FontAwesomeIcon icon={faPuzzlePiece} className="opacity-30" />
          Nenhum addon cadastrado.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {addons.map((addon) => (
            <div
              key={addon.id}
              className={`rounded-lg border p-4 flex flex-col gap-2 ${
                addon.active ? "border-foreground/10 bg-foreground/2" : "border-foreground/5 bg-foreground/1 opacity-60"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-sm truncate">{addon.name}</h3>
                    <Chip size="sm" color={addon.active ? "success" : "default"} variant="flat" className="text-[10px]">
                      {addon.active ? "Ativo" : "Inativo"}
                    </Chip>
                  </div>
                  <p className="text-xs text-foreground/50 truncate">{addon.shortDescription}</p>
                  <p className="text-sm font-bold text-primary mt-1">
                    +R$ {addon.extraValue.toFixed(2)}
                    <span className="text-xs font-normal text-foreground/50"> por opção</span>
                  </p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button isIconOnly size="sm" variant="light" onPress={() => openEdit(addon)}>
                    <FontAwesomeIcon icon={faPen} className="text-xs" />
                  </Button>
                  <Button isIconOnly size="sm" color="danger" variant="light" onPress={() => handleDelete(addon.id)}>
                    <FontAwesomeIcon icon={faTrash} className="text-xs" />
                  </Button>
                </div>
              </div>

              <div>
                <p className="text-[10px] text-foreground/40 mb-1 uppercase tracking-wide">Planos habilitados</p>
                <div className="flex flex-wrap gap-1">
                  {plans.length === 0 ? (
                    <span className="text-xs text-foreground/30">Nenhum plano</span>
                  ) : (
                    plans.map((plan) => (
                      <Chip
                        key={plan.id}
                        size="sm"
                        color={addon.enabledForPlans.includes(plan.id) ? "primary" : "default"}
                        variant="flat"
                        className="text-[10px]"
                      >
                        {plan.name}
                      </Chip>
                    ))
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Criar */}
      <Modal isOpen={isCreateOpen} onOpenChange={setIsCreateOpen} scrollBehavior="inside">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Novo Addon</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-2">
                  {createError && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">{createError}</div>
                  )}
                  <Input label="Nome" size="sm" value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} />
                  <Input label="ID (slug)" size="sm" value={createForm.id} onChange={(e) => setCreateForm({ ...createForm, id: e.target.value })} description="Gerado automaticamente se vazio" />
                  <Textarea label="Breve descrição" size="sm" minRows={2} value={createForm.shortDescription} onChange={(e) => setCreateForm({ ...createForm, shortDescription: e.target.value })} />
                  <Input
                    label="Valor adicional (R$)"
                    size="sm"
                    type="number"
                    value={createForm.extraValue}
                    onChange={(e) => setCreateForm({ ...createForm, extraValue: e.target.value })}
                    startContent={<span className="text-foreground/60 text-sm">R$</span>}
                    description="Somado ao valor base do plano"
                  />
                  <Switch isSelected={createForm.active} onValueChange={(v) => setCreateForm({ ...createForm, active: v })}>
                    Ativo
                  </Switch>
                  <div>
                    <p className="text-xs text-foreground/70 mb-1">Habilitar para planos</p>
                    <div className="flex flex-wrap gap-1">
                      {plans.map((plan) => (
                        <PlanToggle
                          key={plan.id}
                          planId={plan.id}
                          planName={plan.name}
                          enabled={createForm.enabledForPlans.includes(plan.id)}
                          onChange={() =>
                            setCreateForm({
                              ...createForm,
                              enabledForPlans: togglePlan(plan.id, createForm.enabledForPlans),
                            })
                          }
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>Cancelar</Button>
                <Button color="primary" onPress={handleCreate}>Criar</Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Modal Editar */}
      <Modal isOpen={isEditOpen} onOpenChange={setIsEditOpen} scrollBehavior="inside">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Editar Addon: {editAddon?.name}</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-2">
                  {editError && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">{editError}</div>
                  )}
                  <Input label="Nome" size="sm" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                  <Textarea label="Breve descrição" size="sm" minRows={2} value={editForm.shortDescription} onChange={(e) => setEditForm({ ...editForm, shortDescription: e.target.value })} />
                  <Input
                    label="Valor adicional (R$)"
                    size="sm"
                    type="number"
                    value={editForm.extraValue}
                    onChange={(e) => setEditForm({ ...editForm, extraValue: e.target.value })}
                    startContent={<span className="text-foreground/60 text-sm">R$</span>}
                  />
                  <Switch isSelected={editForm.active} onValueChange={(v) => setEditForm({ ...editForm, active: v })}>
                    Ativo
                  </Switch>
                  <div>
                    <p className="text-xs text-foreground/70 mb-1">Habilitar para planos</p>
                    <div className="flex flex-wrap gap-1">
                      {plans.map((plan) => (
                        <PlanToggle
                          key={plan.id}
                          planId={plan.id}
                          planName={plan.name}
                          enabled={editForm.enabledForPlans.includes(plan.id)}
                          onChange={() =>
                            setEditForm({
                              ...editForm,
                              enabledForPlans: togglePlan(plan.id, editForm.enabledForPlans),
                            })
                          }
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>Cancelar</Button>
                <Button color="primary" onPress={handleEdit}>Salvar</Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}
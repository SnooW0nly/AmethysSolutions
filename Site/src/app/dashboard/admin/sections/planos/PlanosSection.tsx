"use client";

import { useEffect, useMemo, useState } from "react";
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
  Tab,
  Tabs,
} from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlus, faRobot, faPuzzlePiece, faBoxes } from "@fortawesome/free-solid-svg-icons";
import { Plan, PlanOption, Feature, PlanFormState } from "@/types/plans";
import { PlanCard } from "@/components/ui/dashboard/admin/plans/PlanCard";
import { Dropzone } from "@/components/ui/dashboard/admin/plans/Dropzone";
import { FreePlanConfigSection } from "@/components/ui/dashboard/admin/plans/FreePlanConfigSection";
import { AddonsSection } from "@/components/ui/dashboard/admin/plans/AddonsSection";

export function PlanosSection() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<PlanFormState>({
    id: "",
    name: "",
    description: "",
    primary: false,
    featuresText: "",
    monthlyPrice: "",
    monthlyDiscount: "0",
    quarterlyPrice: "",
    quarterlyDiscount: "0",
    annualPrice: "",
    annualDiscount: "0",
    zipFile: null,
  });

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editOriginalId, setEditOriginalId] = useState<string>("");
  const [editForm, setEditForm] = useState<PlanFormState>({
    id: "",
    name: "",
    description: "",
    primary: false,
    featuresText: "",
    monthlyPrice: "",
    monthlyDiscount: "0",
    quarterlyPrice: "",
    quarterlyDiscount: "0",
    annualPrice: "",
    annualDiscount: "0",
    zipFile: null,
  });

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/admin/plans/list", { cache: "no-store" });
      if (!res.ok) throw new Error("Erro ao carregar planos");
      const data = await res.json();
      setPlans(Array.isArray(data?.data) ? data.data : []);
    } catch (err: any) {
      setError(err?.message || "Erro ao carregar planos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    try {
      setCreateError(null);
      if (!createForm.name.trim()) throw new Error("Nome é obrigatório");
      const planSlug = (createForm.id || createForm.name)
        .toLowerCase()
        .replace(/\s+/g, "-")
        .replace(/[^a-z0-9-]/g, "");
      if (!planSlug) throw new Error("ID é obrigatório");
      if (!createForm.monthlyPrice || !createForm.quarterlyPrice || !createForm.annualPrice) {
        throw new Error("Preencha os valores mensal, trimestral e anual");
      }
      if (!createForm.zipFile) throw new Error("Arquivo .zip é obrigatório");
      const features: Feature[] = createForm.featuresText
        .split("\n")
        .map((t) => t.trim())
        .filter(Boolean)
        .map((title) => ({ title }));

      const options: PlanOption[] = [
        { id: `mensal`, name: "Mensal", value: Number(createForm.monthlyPrice || 0), discount: Number(createForm.monthlyDiscount || 0), months: 1, description: "mês" },
        { id: `trimestral`, name: "Trimestral", value: Number(createForm.quarterlyPrice || 0), discount: Number(createForm.quarterlyDiscount || 0), months: 3, description: "trimestre" },
        { id: `anual`, name: "Anual", value: Number(createForm.annualPrice || 0), discount: Number(createForm.annualDiscount || 0), months: 12, description: "ano" },
      ];

      const payload: Partial<Plan> = {
        id: planSlug,
        name: createForm.name,
        description: createForm.description,
        primary: createForm.primary,
        features,
        plans: options,
      } as any;
      const res = await fetch("/api/admin/plans/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.error || "Erro ao criar plano");
      }
      if (createForm.zipFile) {
        const fd = new FormData();
        fd.append("file", createForm.zipFile);
        await fetch(`/api/admin/plans/upload/${encodeURIComponent(planSlug)}/zip`, {
          method: "POST",
          body: fd,
        });
      }
      setIsCreateOpen(false);
      setCreateError(null);
      setCreateForm({
        id: "",
        name: "",
        description: "",
        primary: false,
        featuresText: "",
        monthlyPrice: "",
        monthlyDiscount: "0",
        quarterlyPrice: "",
        quarterlyDiscount: "0",
        annualPrice: "",
        annualDiscount: "0",
        zipFile: null,
      });
      await load();
    } catch (err: any) {
      setCreateError(err?.message || "Erro ao criar plano");
    }
  };

  const handleRemove = async (id: string) => {
    if (!confirm("Tem certeza que deseja remover este plano?")) return;
    try {
      const res = await fetch(`/api/admin/plans/remove/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Erro ao remover plano");
      await load();
    } catch (err: any) {
      setError(err?.message || "Erro ao remover plano");
    }
  };

  const openEdit = (plan: Plan) => {
    setEditOriginalId(plan.id);
    const monthly = plan.plans?.find((p) => p.months === 1);
    const quarterly = plan.plans?.find((p) => p.months === 3);
    const annual = plan.plans?.find((p) => p.months === 12);
    setEditForm({
      id: plan.id,
      name: plan.name,
      description: plan.description || "",
      primary: !!plan.primary,
      featuresText: (plan.features || []).map((f) => f.title).join("\n"),
      monthlyPrice: monthly ? String(monthly.value ?? "") : "",
      monthlyDiscount: monthly ? String(monthly.discount ?? 0) : "0",
      quarterlyPrice: quarterly ? String(quarterly.value ?? "") : "",
      quarterlyDiscount: quarterly ? String(quarterly.discount ?? 0) : "0",
      annualPrice: annual ? String(annual.value ?? "") : "",
      annualDiscount: annual ? String(annual.discount ?? 0) : "0",
      zipFile: null,
    });
    setIsEditOpen(true);
  };

  const handleUpdate = async () => {
    try {
      setEditError(null);
      if (!editForm.name.trim()) throw new Error("Nome é obrigatório");
      const features: Feature[] = editForm.featuresText
        .split("\n")
        .map((t) => t.trim())
        .filter(Boolean)
        .map((title) => ({ title }));
      const planSlug = (editForm.id || editOriginalId)
        .toLowerCase()
        .replace(/\s+/g, "-")
        .replace(/[^a-z0-9-]/g, "");
      const options: PlanOption[] = [
        { id: `mensal`, name: "Mensal", value: Number(editForm.monthlyPrice || 0), discount: Number(editForm.monthlyDiscount || 0), months: 1, description: "mês" },
        { id: `trimestral`, name: "Trimestral", value: Number(editForm.quarterlyPrice || 0), discount: Number(editForm.quarterlyDiscount || 0), months: 3, description: "trimestre" },
        { id: `anual`, name: "Anual", value: Number(editForm.annualPrice || 0), discount: Number(editForm.annualDiscount || 0), months: 12, description: "ano" },
      ];
      const payload: Partial<Plan> = {
        id: planSlug,
        name: editForm.name,
        description: editForm.description,
        primary: editForm.primary,
        features,
        plans: options,
      } as any;
      const res = await fetch(
        `/api/admin/plans/update/${encodeURIComponent(editOriginalId)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.error || "Erro ao atualizar plano");
      }
      if (editForm.zipFile) {
        const fd = new FormData();
        fd.append("file", editForm.zipFile);
        await fetch(
          `/api/admin/plans/upload/${encodeURIComponent(planSlug)}/zip`,
          { method: "POST", body: fd }
        );
      }
      setIsEditOpen(false);
      setEditError(null);
      await load();
    } catch (err: any) {
      setEditError(err?.message || "Erro ao atualizar plano");
    }
  };

  const grid = useMemo(() => {
    if (loading) {
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-36 rounded-lg bg-foreground/5 border border-foreground/10 animate-pulse"
            />
          ))}
        </div>
      );
    }
    if (plans.length === 0) {
      return (
        <div className="rounded-lg bg-foreground/5 border border-foreground/10 p-4 text-sm text-foreground/70">
          Nenhum plano cadastrado ainda.
        </div>
      );
    }
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {plans.map((plan) => (
          <PlanCard key={plan.id} plan={plan} onEdit={openEdit} onRemove={handleRemove} />
        ))}
      </div>
    );
  }, [loading, plans]);

  return (
    <div className="flex flex-col gap-4">
      {error ? (
        <div className="rounded-lg bg-danger/10 border border-danger/20 text-danger-500 text-sm p-2">
          {error}
        </div>
      ) : null}

      <Tabs aria-label="Configuração de Planos" variant="underlined" size="sm">
        {/* ── Aba: Planos ──────────────────────────────────────────────── */}
        <Tab
          key="plans"
          title={
            <span className="flex items-center gap-1.5 text-xs">
              <FontAwesomeIcon icon={faBoxes} />
              Planos
            </span>
          }
        >
          <div className="flex flex-col gap-3 pt-2">
            <div className="flex flex-row gap-2 items-center justify-between">
              <p className="text-sm text-foreground/70 self-center max-w-[200px] md:max-w-full">
                Selecione um plano para editar ou crie um novo plano
              </p>
              <Button
                onPress={() => setIsCreateOpen(true)}
                color="primary"
                size="sm"
                startContent={<FontAwesomeIcon icon={faPlus} />}
              >
                Criar plano
              </Button>
            </div>
            {grid}
          </div>
        </Tab>

        {/* ── Aba: Bot Free ────────────────────────────────────────────── */}
        <Tab
          key="free"
          title={
            <span className="flex items-center gap-1.5 text-xs">
              <FontAwesomeIcon icon={faRobot} />
              Bot Free
            </span>
          }
        >
          <div className="pt-3 rounded-lg border border-foreground/10 bg-foreground/2 p-4">
            <FreePlanConfigSection />
          </div>
        </Tab>

        {/* ── Aba: Addons ───────────────────────────────────────────────── */}
        <Tab
          key="addons"
          title={
            <span className="flex items-center gap-1.5 text-xs">
              <FontAwesomeIcon icon={faPuzzlePiece} />
              Addons
            </span>
          }
        >
          <div className="pt-2">
            <AddonsSection />
          </div>
        </Tab>
      </Tabs>

      {/* ── Modal Criar Plano ─────────────────────────────────────────── */}
      <Modal isOpen={isCreateOpen} onOpenChange={(o) => setIsCreateOpen(o)} scrollBehavior="inside">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Novo plano</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-2">
                  {createError ? (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">
                      {createError}
                    </div>
                  ) : null}
                  <Input
                    label="Nome"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    size="sm"
                  />
                  <Input
                    label={<>ID (slug) <span className="text-danger">*</span></>}
                    value={createForm.id}
                    onChange={(e) => setCreateForm({ ...createForm, id: e.target.value })}
                    size="sm"
                    description="Se vazio, será gerado a partir do nome"
                  />
                  <Textarea
                    label="Descrição"
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    size="sm"
                    minRows={2}
                  />
                  <Switch
                    isSelected={createForm.primary}
                    onValueChange={(v) => setCreateForm({ ...createForm, primary: v })}
                  >
                    Marcar como principal
                  </Switch>
                  <Textarea
                    label="Recursos (um por linha)"
                    value={createForm.featuresText}
                    onChange={(e) => setCreateForm({ ...createForm, featuresText: e.target.value })}
                    size="sm"
                    minRows={3}
                  />
                  <div className="flex flex-col gap-3">
                    <Dropzone
                      onFile={(f) => setCreateForm({ ...createForm, zipFile: f })}
                      selected={createForm.zipFile}
                      placeholder={
                        <>
                          <p className="text-xs text-foreground/70">
                            Arquivo .zip <span className="text-danger">*</span>
                          </p>
                          <p className="text-xs text-foreground/60">
                            Arraste e solte aqui, ou clique para selecionar
                          </p>
                        </>
                      }
                    />
                    <div>
                      <p className="text-xs text-foreground/70 mb-1">
                        Mensal (1 mês) <span className="text-danger">*</span>
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <Input
                          label="Preço"
                          type="number"
                          value={createForm.monthlyPrice}
                          onChange={(e) => setCreateForm({ ...createForm, monthlyPrice: e.target.value })}
                          size="sm"
                          startContent={<span className="text-foreground/60 text-sm">R$</span>}
                        />
                        <Input
                          label="Desconto (%)"
                          type="number"
                          value={createForm.monthlyDiscount}
                          onChange={(e) => setCreateForm({ ...createForm, monthlyDiscount: e.target.value })}
                          size="sm"
                        />
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-foreground/70 mb-1">
                        Trimestral (3 meses) <span className="text-danger">*</span>
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <Input
                          label="Preço"
                          type="number"
                          value={createForm.quarterlyPrice}
                          onChange={(e) => setCreateForm({ ...createForm, quarterlyPrice: e.target.value })}
                          size="sm"
                          startContent={<span className="text-foreground/60 text-sm">R$</span>}
                        />
                        <Input
                          label="Desconto (%)"
                          type="number"
                          value={createForm.quarterlyDiscount}
                          onChange={(e) => setCreateForm({ ...createForm, quarterlyDiscount: e.target.value })}
                          size="sm"
                        />
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-foreground/70 mb-1">
                        Anual (12 meses) <span className="text-danger">*</span>
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <Input
                          label="Preço"
                          type="number"
                          value={createForm.annualPrice}
                          onChange={(e) => setCreateForm({ ...createForm, annualPrice: e.target.value })}
                          size="sm"
                          startContent={<span className="text-foreground/60 text-sm">R$</span>}
                        />
                        <Input
                          label="Desconto (%)"
                          type="number"
                          value={createForm.annualDiscount}
                          onChange={(e) => setCreateForm({ ...createForm, annualDiscount: e.target.value })}
                          size="sm"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>
                  Cancelar
                </Button>
                <Button color="primary" onPress={handleCreate}>
                  Criar
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* ── Modal Editar Plano ────────────────────────────────────────── */}
      <Modal isOpen={isEditOpen} onOpenChange={(o) => setIsEditOpen(o)} scrollBehavior="inside">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Editar plano</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-2">
                  {editError ? (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">
                      {editError}
                    </div>
                  ) : null}
                  <Input
                    label="Nome"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    size="sm"
                  />
                  <Input
                    label={<>ID (slug) <span className="text-danger">*</span></>}
                    value={editForm.id}
                    onChange={(e) => setEditForm({ ...editForm, id: e.target.value })}
                    size="sm"
                    description="Se vazio, será gerado a partir do nome"
                  />
                  <Textarea
                    label="Descrição"
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    size="sm"
                    minRows={2}
                  />
                  <Switch
                    isSelected={editForm.primary}
                    onValueChange={(v) => setEditForm({ ...editForm, primary: v })}
                  >
                    Marcar como principal
                  </Switch>
                  <Textarea
                    label="Recursos (um por linha)"
                    value={editForm.featuresText}
                    onChange={(e) => setEditForm({ ...editForm, featuresText: e.target.value })}
                    size="sm"
                    minRows={3}
                  />
                  <Dropzone
                    onFile={(f) => setEditForm({ ...editForm, zipFile: f })}
                    selected={editForm.zipFile}
                    linkHref={
                      editOriginalId
                        ? `/api/admin/plans/download/${encodeURIComponent(editOriginalId)}/zip`
                        : undefined
                    }
                    placeholder={
                      <>
                        <p className="text-xs text-foreground/70">
                          Arquivo .zip <span className="text-danger">*</span>
                        </p>
                        <p className="text-xs text-foreground/60">
                          Arraste e solte aqui, ou clique para selecionar
                        </p>
                      </>
                    }
                  />
                  <div className="flex flex-col gap-3">
                    <div>
                      <p className="text-xs text-foreground/70 mb-1">Mensal (1 mês)</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <Input
                          label="Preço"
                          type="number"
                          value={editForm.monthlyPrice}
                          onChange={(e) => setEditForm({ ...editForm, monthlyPrice: e.target.value })}
                          size="sm"
                          startContent={<span className="text-foreground/60 text-sm">R$</span>}
                        />
                        <Input
                          label="Desconto (%)"
                          type="number"
                          value={editForm.monthlyDiscount}
                          onChange={(e) => setEditForm({ ...editForm, monthlyDiscount: e.target.value })}
                          size="sm"
                        />
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-foreground/70 mb-1">Trimestral (3 meses)</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <Input
                          label="Preço"
                          type="number"
                          value={editForm.quarterlyPrice}
                          onChange={(e) => setEditForm({ ...editForm, quarterlyPrice: e.target.value })}
                          size="sm"
                          startContent={<span className="text-foreground/60 text-sm">R$</span>}
                        />
                        <Input
                          label="Desconto (%)"
                          type="number"
                          value={editForm.quarterlyDiscount}
                          onChange={(e) => setEditForm({ ...editForm, quarterlyDiscount: e.target.value })}
                          size="sm"
                        />
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-foreground/70 mb-1">Anual (12 meses)</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <Input
                          label="Preço"
                          type="number"
                          value={editForm.annualPrice}
                          onChange={(e) => setEditForm({ ...editForm, annualPrice: e.target.value })}
                          size="sm"
                          startContent={<span className="text-foreground/60 text-sm">R$</span>}
                        />
                        <Input
                          label="Desconto (%)"
                          type="number"
                          value={editForm.annualDiscount}
                          onChange={(e) => setEditForm({ ...editForm, annualDiscount: e.target.value })}
                          size="sm"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>
                  Cancelar
                </Button>
                <Button color="primary" onPress={handleUpdate}>
                  Salvar
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Button,
  Input,
  Textarea,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Switch,
  Select,
  SelectItem,
  Chip,
  Card,
  CardBody,
  Divider,
  Spinner,
} from "@heroui/react";
import { SectionHeader } from "@/components/layout/SectionHeader";
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  ExternalLink,
  Star,
  ToggleLeft,
  ToggleRight,
  Tag,
  Globe,
  MessageCircle,
  Gift,
  RefreshCw,
  Image,
  ChevronUp,
  ChevronDown,
  Filter,
} from "lucide-react";

const CATEGORIES = [
  { key: "hosting", label: "Hospedagem" },
  { key: "bot", label: "Bot" },
  { key: "community", label: "Comunidade" },
  { key: "tool", label: "Ferramenta" },
  { key: "service", label: "Serviço" },
  { key: "other", label: "Outros" },
];

const CATEGORY_COLORS: Record<string, any> = {
  hosting: "warning",
  bot: "primary",
  community: "success",
  tool: "secondary",
  service: "danger",
  other: "default",
};

const EMPTY_FORM = {
  name: "",
  description: "",
  shortDescription: "",
  logoUrl: "",
  bannerUrl: "",
  websiteUrl: "",
  discordUrl: "",
  discordServerId: "",
  category: "other",
  tags: [] as string[],
  benefits: [] as string[],
  couponCode: "",
  couponDiscount: "",
  featured: false,
  active: true,
  order: 0,
};

type Partnership = typeof EMPTY_FORM & {
  _id: string;
  createdAt: string;
  updatedAt: string;
  createdBy?: { username: string };
};

export function ParceriasSection() {
  const [partnerships, setPartnerships] = useState<Partnership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [featuredFilter, setFeaturedFilter] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const limit = 12;

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Tag/benefit input
  const [tagInput, setTagInput] = useState("");
  const [benefitInput, setBenefitInput] = useState("");

  // Delete confirmation
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit),
        search,
        category: categoryFilter,
        active: activeFilter,
        featured: featuredFilter,
        sortBy: "order",
        sortOrder: "asc",
      });
      const res = await fetch(`/api/admin/partnerships?${params}`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error("Erro ao carregar parcerias");
      const data = await res.json();
      setPartnerships(data.partnerships || []);
      setTotal(data.pagination?.total || 0);
      setTotalPages(data.pagination?.totalPages || 1);
    } catch (e: any) {
      setError(e?.message || "Erro ao carregar parcerias");
    } finally {
      setLoading(false);
    }
  }, [page, search, categoryFilter, activeFilter, featuredFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ ...EMPTY_FORM });
    setFormError(null);
    setTagInput("");
    setBenefitInput("");
    setModalOpen(true);
  };

  const openEdit = (p: Partnership) => {
    setEditingId(p._id);
    setForm({
      name: p.name,
      description: p.description,
      shortDescription: p.shortDescription || "",
      logoUrl: p.logoUrl || "",
      bannerUrl: p.bannerUrl || "",
      websiteUrl: p.websiteUrl || "",
      discordUrl: p.discordUrl || "",
      discordServerId: p.discordServerId || "",
      category: p.category || "other",
      tags: Array.isArray(p.tags) ? [...p.tags] : [],
      benefits: Array.isArray(p.benefits) ? [...p.benefits] : [],
      couponCode: p.couponCode || "",
      couponDiscount: p.couponDiscount || "",
      featured: Boolean(p.featured),
      active: p.active !== false,
      order: p.order || 0,
    });
    setFormError(null);
    setTagInput("");
    setBenefitInput("");
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      setFormError(null);
      if (!form.name.trim()) throw new Error("Nome é obrigatório");
      if (!form.description.trim()) throw new Error("Descrição é obrigatória");

      setSaving(true);
      const url = editingId
        ? `/api/admin/partnerships/${editingId}`
        : "/api/admin/partnerships";
      const method = editingId ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Erro ao salvar parceria");
      }

      setModalOpen(false);
      await load();
    } catch (e: any) {
      setFormError(e?.message || "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      setDeleteLoading(true);
      const res = await fetch(`/api/admin/partnerships/${deleteId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Erro ao deletar");
      setDeleteId(null);
      await load();
    } catch (e: any) {
      alert(e?.message || "Erro ao deletar");
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleToggle = async (id: string) => {
    try {
      const res = await fetch(`/api/admin/partnerships/${id}/toggle`, {
        method: "PATCH",
      });
      if (!res.ok) throw new Error("Erro ao alternar");
      await load();
    } catch (e: any) {
      alert(e?.message || "Erro ao alternar status");
    }
  };

  const addTag = () => {
    const v = tagInput.trim();
    if (v && !form.tags.includes(v)) {
      setForm((f) => ({ ...f, tags: [...f.tags, v] }));
    }
    setTagInput("");
  };

  const removeTag = (idx: number) => {
    setForm((f) => ({ ...f, tags: f.tags.filter((_, i) => i !== idx) }));
  };

  const addBenefit = () => {
    const v = benefitInput.trim();
    if (v) {
      setForm((f) => ({ ...f, benefits: [...f.benefits, v] }));
    }
    setBenefitInput("");
  };

  const removeBenefit = (idx: number) => {
    setForm((f) => ({ ...f, benefits: f.benefits.filter((_, i) => i !== idx) }));
  };

  const adjustOrder = async (p: Partnership, direction: "up" | "down") => {
    const newOrder = direction === "up"
      ? Math.max(0, (p.order || 0) - 1)
      : (p.order || 0) + 1;

    const res = await fetch(`/api/admin/partnerships/${p._id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order: newOrder }),
    });
    if (res.ok) await load();
  };

  return (
    <div className="flex flex-col gap-4">
      <SectionHeader
        description="Gerencie as parcerias exibidas no site"
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="light"
              onPress={load}
              startContent={<RefreshCw className="w-4 h-4" />}
            >
              Atualizar
            </Button>
            <Button
              size="sm"
              color="primary"
              onPress={openCreate}
              startContent={<Plus className="w-4 h-4" />}
            >
              Nova Parceria
            </Button>
          </div>
        }
      />

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total", value: total, color: "text-foreground" },
          {
            label: "Ativas",
            value: partnerships.filter((p) => p.active).length,
            color: "text-success",
          },
          {
            label: "Destaque",
            value: partnerships.filter((p) => p.featured).length,
            color: "text-warning",
          },
          {
            label: "Inativas",
            value: partnerships.filter((p) => !p.active).length,
            color: "text-danger",
          },
        ].map((s) => (
          <Card key={s.label} className="border border-foreground/10">
            <CardBody className="p-3">
              <p className="text-xs text-foreground/60">{s.label}</p>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
        <Input
          size="sm"
          placeholder="Buscar por nome, tags..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          startContent={<Search className="w-4 h-4 text-foreground/50" />}
        />
        <Select
          size="sm"
          placeholder="Categoria"
          selectedKeys={categoryFilter ? new Set([categoryFilter]) : new Set()}
          onSelectionChange={(k) => {
            setCategoryFilter(Array.from(k)[0] as string || "");
            setPage(1);
          }}
        >
          <>
            <SelectItem key="">Todas</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c.key}>{c.label}</SelectItem>
            ))}
          </>
        </Select>
        <Select
          size="sm"
          placeholder="Status"
          selectedKeys={activeFilter ? new Set([activeFilter]) : new Set()}
          onSelectionChange={(k) => {
            setActiveFilter(Array.from(k)[0] as string || "");
            setPage(1);
          }}
        >
          <SelectItem key="">Todos</SelectItem>
          <SelectItem key="true">Ativas</SelectItem>
          <SelectItem key="false">Inativas</SelectItem>
        </Select>
        <Select
          size="sm"
          placeholder="Destaque"
          selectedKeys={featuredFilter ? new Set([featuredFilter]) : new Set()}
          onSelectionChange={(k) => {
            setFeaturedFilter(Array.from(k)[0] as string || "");
            setPage(1);
          }}
        >
          <SelectItem key="">Todos</SelectItem>
          <SelectItem key="true">Em destaque</SelectItem>
        </Select>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-danger/10 border border-danger/20 text-danger-500 text-sm p-3">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && partnerships.length === 0 && (
        <div className="flex items-center justify-center h-48">
          <Spinner size="lg" />
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {partnerships.map((p) => (
          <PartnershipCard
            key={p._id}
            partnership={p}
            onEdit={() => openEdit(p)}
            onDelete={() => setDeleteId(p._id)}
            onToggle={() => handleToggle(p._id)}
            onOrderUp={() => adjustOrder(p, "up")}
            onOrderDown={() => adjustOrder(p, "down")}
          />
        ))}
      </div>

      {/* Empty */}
      {!loading && partnerships.length === 0 && (
        <div className="rounded-lg bg-foreground/5 border border-foreground/10 p-10 text-center">
          <p className="text-foreground/60 mb-3">Nenhuma parceria encontrada</p>
          <Button size="sm" color="primary" onPress={openCreate} startContent={<Plus className="w-4 h-4" />}>
            Criar primeira parceria
          </Button>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-foreground/70">
          <span>Total: {total}</span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="light" isDisabled={page <= 1} onPress={() => setPage((p) => Math.max(1, p - 1))}>
              Anterior
            </Button>
            <span>Página {page} de {totalPages}</span>
            <Button size="sm" variant="light" isDisabled={page >= totalPages} onPress={() => setPage((p) => p + 1)}>
              Próxima
            </Button>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={modalOpen}
        onOpenChange={(o) => {
          if (!saving) setModalOpen(o);
        }}
        size="3xl"
        scrollBehavior="inside"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>
                {editingId ? "Editar Parceria" : "Nova Parceria"}
              </ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-4">
                  {formError && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-3">
                      {formError}
                    </div>
                  )}

                  {/* Basic info */}
                  <div>
                    <p className="text-sm font-semibold mb-2">Informações Básicas</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Input
                        label={<>Nome <span className="text-danger">*</span></>}
                        value={form.name}
                        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                        size="sm"
                        placeholder="Nome da empresa parceira"
                      />
                      <Select
                        label="Categoria"
                        size="sm"
                        selectedKeys={new Set([form.category])}
                        onSelectionChange={(k) =>
                          setForm((f) => ({
                            ...f,
                            category: Array.from(k)[0] as string || "other",
                          }))
                        }
                      >
                        {CATEGORIES.map((c) => (
                          <SelectItem key={c.key}>{c.label}</SelectItem>
                        ))}
                      </Select>
                      <div className="md:col-span-2">
                        <Textarea
                          label={<>Descrição <span className="text-danger">*</span></>}
                          value={form.description}
                          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                          size="sm"
                          minRows={3}
                          placeholder="Descrição detalhada da parceria"
                        />
                      </div>
                      <div className="md:col-span-2">
                        <Input
                          label="Descrição Curta"
                          value={form.shortDescription}
                          onChange={(e) => setForm((f) => ({ ...f, shortDescription: e.target.value }))}
                          size="sm"
                          placeholder="Resumo em até 150 caracteres"
                        />
                      </div>
                    </div>
                  </div>

                  <Divider />

                  {/* Media */}
                  <div>
                    <p className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <Image className="w-4 h-4" /> Mídia
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Input
                        label="URL do Logo"
                        value={form.logoUrl}
                        onChange={(e) => setForm((f) => ({ ...f, logoUrl: e.target.value }))}
                        size="sm"
                        placeholder="https://..."
                      />
                      <Input
                        label="URL do Banner"
                        value={form.bannerUrl}
                        onChange={(e) => setForm((f) => ({ ...f, bannerUrl: e.target.value }))}
                        size="sm"
                        placeholder="https://..."
                      />
                    </div>
                    {/* Preview */}
                    {(form.logoUrl || form.bannerUrl) && (
                      <div className="mt-2 flex items-center gap-4">
                        {form.logoUrl && (
                          <div className="flex flex-col items-center gap-1">
                            <p className="text-xs text-foreground/50">Logo Preview</p>
                            <img
                              src={form.logoUrl}
                              alt="Logo"
                              className="w-16 h-16 rounded-xl object-contain bg-foreground/5 border border-foreground/10"
                              onError={(e) => (e.currentTarget.src = "")}
                            />
                          </div>
                        )}
                        {form.bannerUrl && (
                          <div className="flex flex-col items-center gap-1 flex-1">
                            <p className="text-xs text-foreground/50">Banner Preview</p>
                            <img
                              src={form.bannerUrl}
                              alt="Banner"
                              className="w-full h-20 rounded-xl object-cover bg-foreground/5 border border-foreground/10"
                              onError={(e) => (e.currentTarget.src = "")}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <Divider />

                  {/* Links */}
                  <div>
                    <p className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <Globe className="w-4 h-4" /> Links
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Input
                        label="Website"
                        value={form.websiteUrl}
                        onChange={(e) => setForm((f) => ({ ...f, websiteUrl: e.target.value }))}
                        size="sm"
                        placeholder="https://..."
                        startContent={<Globe className="w-4 h-4 text-foreground/50" />}
                      />
                      <Input
                        label="Discord (URL convite)"
                        value={form.discordUrl}
                        onChange={(e) => setForm((f) => ({ ...f, discordUrl: e.target.value }))}
                        size="sm"
                        placeholder="https://discord.gg/..."
                        startContent={<MessageCircle className="w-4 h-4 text-foreground/50" />}
                      />
                      <Input
                        label="Discord Server ID"
                        value={form.discordServerId}
                        onChange={(e) => setForm((f) => ({ ...f, discordServerId: e.target.value }))}
                        size="sm"
                        placeholder="ID do servidor"
                      />
                    </div>
                  </div>

                  <Divider />

                  {/* Coupon */}
                  <div>
                    <p className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <Gift className="w-4 h-4" /> Cupom / Benefício
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Input
                        label="Código do Cupom"
                        value={form.couponCode}
                        onChange={(e) => setForm((f) => ({ ...f, couponCode: e.target.value.toUpperCase() }))}
                        size="sm"
                        placeholder="EX: AMETHYS20"
                      />
                      <Input
                        label="Desconto / Benefício"
                        value={form.couponDiscount}
                        onChange={(e) => setForm((f) => ({ ...f, couponDiscount: e.target.value }))}
                        size="sm"
                        placeholder="Ex: 20% de desconto"
                      />
                    </div>
                  </div>

                  <Divider />

                  {/* Tags */}
                  <div>
                    <p className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <Tag className="w-4 h-4" /> Tags
                    </p>
                    <div className="flex items-center gap-2 mb-2">
                      <Input
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
                        size="sm"
                        placeholder="Adicionar tag"
                      />
                      <Button size="sm" color="primary" onPress={addTag}>
                        Adicionar
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {form.tags.map((tag, i) => (
                        <Chip
                          key={i}
                          size="sm"
                          variant="flat"
                          onClose={() => removeTag(i)}
                        >
                          {tag}
                        </Chip>
                      ))}
                    </div>
                  </div>

                  <Divider />

                  {/* Benefits */}
                  <div>
                    <p className="text-sm font-semibold mb-2">Benefícios da Parceria</p>
                    <div className="flex items-center gap-2 mb-2">
                      <Input
                        value={benefitInput}
                        onChange={(e) => setBenefitInput(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addBenefit(); } }}
                        size="sm"
                        placeholder="Ex: 20% de desconto para membros"
                      />
                      <Button size="sm" color="primary" onPress={addBenefit}>
                        Adicionar
                      </Button>
                    </div>
                    <div className="flex flex-col gap-1">
                      {form.benefits.map((b, i) => (
                        <div key={i} className="flex items-center justify-between text-sm bg-foreground/5 rounded-lg px-3 py-2">
                          <span>• {b}</span>
                          <button
                            type="button"
                            onClick={() => removeBenefit(i)}
                            className="text-danger hover:text-danger/80 text-xs ml-2"
                          >
                            Remover
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <Divider />

                  {/* Settings */}
                  <div>
                    <p className="text-sm font-semibold mb-3">Configurações</p>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Ativa</span>
                        <Switch
                          isSelected={form.active}
                          onValueChange={(v) => setForm((f) => ({ ...f, active: v }))}
                          size="sm"
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Destaque</span>
                        <Switch
                          isSelected={form.featured}
                          onValueChange={(v) => setForm((f) => ({ ...f, featured: v }))}
                          size="sm"
                        />
                      </div>
                      <Input
                        label="Ordem de exibição"
                        type="number"
                        value={String(form.order)}
                        onChange={(e) => setForm((f) => ({ ...f, order: Number(e.target.value) || 0 }))}
                        size="sm"
                        min={0}
                      />
                    </div>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose} isDisabled={saving}>
                  Cancelar
                </Button>
                <Button color="primary" onPress={handleSave} isLoading={saving}>
                  {editingId ? "Salvar Alterações" : "Criar Parceria"}
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Delete confirmation modal */}
      <Modal isOpen={!!deleteId} onOpenChange={(o) => { if (!o) setDeleteId(null); }} size="sm">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Confirmar Exclusão</ModalHeader>
              <ModalBody>
                <p className="text-sm text-foreground/70">
                  Tem certeza que deseja remover esta parceria permanentemente? Esta ação não pode ser desfeita.
                </p>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose} isDisabled={deleteLoading}>
                  Cancelar
                </Button>
                <Button
                  color="danger"
                  onPress={handleDelete}
                  isLoading={deleteLoading}
                  startContent={!deleteLoading && <Trash2 className="w-4 h-4" />}
                >
                  Remover
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Partnership Card Component
───────────────────────────────────────────── */
function PartnershipCard({
  partnership,
  onEdit,
  onDelete,
  onToggle,
  onOrderUp,
  onOrderDown,
}: {
  partnership: Partnership;
  onEdit: () => void;
  onDelete: () => void;
  onToggle: () => void;
  onOrderUp: () => void;
  onOrderDown: () => void;
}) {
  const catLabel = CATEGORIES.find((c) => c.key === partnership.category)?.label || partnership.category;
  const catColor = CATEGORY_COLORS[partnership.category] || "default";

  return (
    <Card
      className={`border transition-all ${
        partnership.active
          ? "border-foreground/10 bg-foreground/2 hover:bg-foreground/5"
          : "border-foreground/5 bg-foreground/1 opacity-60"
      }`}
    >
      {/* Banner */}
      {partnership.bannerUrl && (
        <div className="relative h-20 overflow-hidden rounded-t-xl">
          <img
            src={partnership.bannerUrl}
            alt=""
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-background/60" />
        </div>
      )}

      <CardBody className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {partnership.logoUrl ? (
              <img
                src={partnership.logoUrl}
                alt={partnership.name}
                className="w-12 h-12 rounded-xl object-contain bg-foreground/5 border border-foreground/10 flex-shrink-0"
              />
            ) : (
              <div className="w-12 h-12 rounded-xl bg-foreground/10 flex items-center justify-center text-foreground/30 text-xl font-bold flex-shrink-0">
                {partnership.name[0]?.toUpperCase()}
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-sm truncate">{partnership.name}</h4>
                {partnership.featured && (
                  <Star className="w-3 h-3 text-warning fill-warning flex-shrink-0" />
                )}
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <Chip size="sm" color={catColor} variant="flat">
                  {catLabel}
                </Chip>
                <span className={`text-xs ${partnership.active ? "text-success" : "text-danger"}`}>
                  {partnership.active ? "Ativa" : "Inativa"}
                </span>
              </div>
            </div>
          </div>

          {/* Order controls */}
          <div className="flex flex-col gap-0.5">
            <button
              onClick={onOrderUp}
              className="p-0.5 text-foreground/40 hover:text-foreground/80 transition-colors"
              title="Subir"
            >
              <ChevronUp className="w-4 h-4" />
            </button>
            <span className="text-[10px] text-foreground/40 text-center">{partnership.order || 0}</span>
            <button
              onClick={onOrderDown}
              className="p-0.5 text-foreground/40 hover:text-foreground/80 transition-colors"
              title="Descer"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Description */}
        <p className="text-xs text-foreground/60 mt-3 line-clamp-2">
          {partnership.shortDescription || partnership.description}
        </p>

        {/* Tags */}
        {partnership.tags && partnership.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {partnership.tags.slice(0, 3).map((tag, i) => (
              <span
                key={i}
                className="text-[10px] bg-foreground/5 border border-foreground/10 rounded-full px-2 py-0.5 text-foreground/60"
              >
                {tag}
              </span>
            ))}
            {partnership.tags.length > 3 && (
              <span className="text-[10px] text-foreground/40">+{partnership.tags.length - 3}</span>
            )}
          </div>
        )}

        {/* Coupon */}
        {partnership.couponCode && (
          <div className="mt-3 flex items-center gap-2 p-2 rounded-lg bg-primary/10 border border-primary/20">
            <Gift className="w-3 h-3 text-primary" />
            <code className="text-xs font-mono text-primary font-bold">{partnership.couponCode}</code>
            {partnership.couponDiscount && (
              <span className="text-xs text-primary/80">– {partnership.couponDiscount}</span>
            )}
          </div>
        )}

        {/* Links */}
        <div className="flex items-center gap-1 mt-3">
          {partnership.websiteUrl && (
            <a
              href={partnership.websiteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-lg text-foreground/40 hover:text-foreground/80 hover:bg-foreground/5 transition-all"
              title="Website"
            >
              <Globe className="w-3.5 h-3.5" />
            </a>
          )}
          {partnership.discordUrl && (
            <a
              href={partnership.discordUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-lg text-foreground/40 hover:text-foreground/80 hover:bg-foreground/5 transition-all"
              title="Discord"
            >
              <MessageCircle className="w-3.5 h-3.5" />
            </a>
          )}
        </div>

        <Divider className="my-3" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="flat"
            className="flex-1"
            onPress={onEdit}
            startContent={<Edit2 className="w-3.5 h-3.5" />}
          >
            Editar
          </Button>
          <Button
            size="sm"
            variant="flat"
            color={partnership.active ? "warning" : "success"}
            isIconOnly
            onPress={onToggle}
            title={partnership.active ? "Desativar" : "Ativar"}
          >
            {partnership.active ? (
              <ToggleRight className="w-4 h-4" />
            ) : (
              <ToggleLeft className="w-4 h-4" />
            )}
          </Button>
          <Button
            size="sm"
            variant="flat"
            color="danger"
            isIconOnly
            onPress={onDelete}
            title="Remover"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
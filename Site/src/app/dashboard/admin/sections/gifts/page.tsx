"use client";

import { useState, useEffect } from "react";
import { Gift, GiftListResponse, GiftStatsResponse } from "@/types/gifts";
import { Plan } from "@/types/plans";
import { Gift as GiftIcon, Plus, Trash2, Search, Filter, Download } from "lucide-react";
import CreateGiftModal from "@/components/ui/dashboard/admin/gifts/CreateGiftModal";
import GiftStatsCards from "@/components/ui/dashboard/admin/gifts/GiftStatsCards";
import GiftTable from "@/components/ui/dashboard/admin/gifts/GiftTable";

export default function GiftsAdminPage() {
  const [gifts, setGifts] = useState<Gift[]>([]);
  const [stats, setStats] = useState<GiftStatsResponse | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  
  // Filtros
  const [filters, setFilters] = useState({
    page: 1,
    limit: 20,
    planId: "",
    isUsed: undefined as boolean | undefined,
    search: "",
  });

  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
  });

  useEffect(() => {
    loadPlans();
    loadStats();
  }, []);

  useEffect(() => {
    loadGifts();
  }, [filters]);

  const loadPlans = async () => {
    try {
      const response = await fetch("/api/admin/plans/list", {
        credentials: "include",
      });
      
      if (!response.ok) {
        console.error("Erro na resposta:", response.status, response.statusText);
        return;
      }
      
      const data = await response.json();
      console.log("Planos carregados:", data);
      
      if (data.success && data.data) {
        setPlans(data.data);
        console.log(`${data.data.length} planos encontrados`);
      } else {
        console.warn("Resposta sem sucesso ou sem dados:", data);
      }
    } catch (error) {
      console.error("Erro ao carregar planos:", error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch("/api/admin/gifts/stats", {
        credentials: "include",
      });
      const data = await response.json();
      if (data.success) {
        setStats(data.data);
      }
    } catch (error) {
      console.error("Erro ao carregar estatísticas:", error);
    }
  };

  const loadGifts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("page", filters.page.toString());
      params.append("limit", filters.limit.toString());
      if (filters.planId) params.append("planId", filters.planId);
      if (filters.isUsed !== undefined) params.append("isUsed", filters.isUsed.toString());
      if (filters.search) params.append("search", filters.search);

      const response = await fetch(`/api/admin/gifts/list?${params}`, {
        credentials: "include",
      });
      const data: { success: boolean; data: GiftListResponse } = await response.json();
      
      if (data.success) {
        setGifts(data.data.gifts);
        setPagination(data.data.pagination);
      }
    } catch (error) {
      console.error("Erro ao carregar gifts:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGift = async (giftData: any) => {
    try {
      const response = await fetch("/api/admin/gifts/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(giftData),
      });

      const data = await response.json();
      
      if (data.success) {
        setIsCreateModalOpen(false);
        loadGifts();
        loadStats();
        
        // Mostra os códigos gerados
        alert(`${data.data.quantity} gift(s) criado(s) com sucesso!\n\nCódigos:\n${data.data.gifts.map((g: any) => g.code).join("\n")}`);
      } else {
        alert(`Erro: ${data.message}`);
      }
    } catch (error) {
      console.error("Erro ao criar gift:", error);
      alert("Erro ao criar gift");
    }
  };

  const handleDeleteGift = async (id: string) => {
    if (!confirm("Tem certeza que deseja deletar este gift?")) return;

    try {
      const response = await fetch(`/api/admin/gifts/delete/${id}`, {
        method: "DELETE",
        credentials: "include",
      });

      const data = await response.json();
      
      if (data.success) {
        loadGifts();
        loadStats();
      } else {
        alert(`Erro: ${data.message}`);
      }
    } catch (error) {
      console.error("Erro ao deletar gift:", error);
      alert("Erro ao deletar gift");
    }
  };

  const handleDeleteBatch = async (batchId: string) => {
    if (!confirm("Tem certeza que deseja deletar todos os gifts não usados deste lote?")) return;

    try {
      const response = await fetch(`/api/admin/gifts/batch/${batchId}`, {
        method: "DELETE",
        credentials: "include",
      });

      const data = await response.json();
      
      if (data.success) {
        alert(`${data.data.deleted} gift(s) deletado(s) com sucesso!`);
        loadGifts();
        loadStats();
      } else {
        alert(`Erro: ${data.message}`);
      }
    } catch (error) {
      console.error("Erro ao deletar lote:", error);
      alert("Erro ao deletar lote");
    }
  };

  const exportGifts = () => {
    const csv = [
      ["Código", "Plano", "Duração", "Status", "Usado Por", "Data de Uso", "Expira Em"].join(","),
      ...gifts.map(g => [
        g.code,
        g.planName,
        [g.months ? `${g.months} mês(es)` : "", g.days ? `${g.days} dia(s)` : ""].filter(Boolean).join(" + ") || "—",
        g.isUsed ? "Usado" : "Disponível",
        g.usedBy?.globalName || "-",
        g.usedAt ? new Date(g.usedAt).toLocaleDateString() : "-",
        g.expiresAt ? new Date(g.expiresAt).toLocaleDateString() : "Sem expiração",
      ].join(","))
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gifts-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-xl">
            <GiftIcon className="w-7 h-7 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Gerenciar Gifts</h1>
            <p className="text-sm text-foreground/60">
              Crie e gerencie códigos de presente
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={exportGifts}
            className="px-4 py-2.5 bg-foreground/5 hover:bg-foreground/10 border border-foreground/10 rounded-xl flex items-center gap-2 transition-all font-medium"
          >
            <Download className="w-4 h-4" />
            Exportar
          </button>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2.5 bg-primary hover:bg-primary/90 rounded-xl flex items-center gap-2 transition-all font-medium shadow-lg hover:shadow-xl"
          >
            <Plus className="w-4 h-4" />
            Criar Gifts
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && <GiftStatsCards stats={stats} />}

      {/* Filtros */}
      <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="text-sm text-foreground/70 mb-2 block font-medium">Buscar</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/40" />
              <input
                type="text"
                placeholder="Código, descrição..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
                className="w-full pl-10 pr-4 py-2.5 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              />
            </div>
          </div>

          <div>
            <label className="text-sm text-foreground/70 mb-2 block font-medium">Plano</label>
            <select
              value={filters.planId}
              onChange={(e) => setFilters({ ...filters, planId: e.target.value, page: 1 })}
              className="w-full px-4 py-2.5 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
            >
              <option value="">Todos os planos</option>
              {plans.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm text-foreground/70 mb-2 block font-medium">Status</label>
            <select
              value={filters.isUsed === undefined ? "" : filters.isUsed.toString()}
              onChange={(e) => setFilters({ 
                ...filters, 
                isUsed: e.target.value === "" ? undefined : e.target.value === "true",
                page: 1 
              })}
              className="w-full px-4 py-2.5 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
            >
              <option value="">Todos</option>
              <option value="false">Disponíveis</option>
              <option value="true">Usados</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFilters({ page: 1, limit: 20, planId: "", isUsed: undefined, search: "" })}
              className="w-full px-4 py-2.5 bg-foreground/5 hover:bg-foreground/10 border border-foreground/10 rounded-xl transition-all font-medium"
            >
              Limpar Filtros
            </button>
          </div>
        </div>
      </div>

      {/* Tabela */}
      <GiftTable
        gifts={gifts}
        loading={loading}
        pagination={pagination}
        onPageChange={(page) => setFilters({ ...filters, page })}
        onDelete={handleDeleteGift}
        onDeleteBatch={handleDeleteBatch}
      />

      {/* Modal de Criação */}
      <CreateGiftModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateGift}
        plans={plans}
      />
    </div>
  );
}

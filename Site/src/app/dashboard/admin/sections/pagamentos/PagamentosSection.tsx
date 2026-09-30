"use client";

import { useEffect, useState } from "react";
import { Button } from "@heroui/react";
import { SectionHeader } from "@/components/layout/SectionHeader";
import { PaymentsFilters } from "@/features/billing/components/PaymentsFilters";
import { PaymentsTable } from "@/features/billing/components/PaymentsTable";
import type { AdminPayment } from "@/features/billing/types";
import { fetchAdminPayments, fetchAdminPaymentsStats } from "@/features/billing/services/payments";
import { DollarSign, ShoppingCart, TrendingUp, Package } from "lucide-react";

export function PagamentosSection() {
  const [items, setItems] = useState<AdminPayment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [planId, setPlanId] = useState("");
  const [coupon, setCoupon] = useState("");
  const [userQ, setUserQ] = useState("");
  const [stats, setStats] = useState<any>(null);
  const [period, setPeriod] = useState("all");

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAdminPayments({ page, limit, planId, coupon, user: userQ });
      setItems(Array.isArray(data?.payments) ? data.payments : []);
      setTotal(Number(data?.total || 0));
      setTotalPages(Number(data?.totalPages || 0));
    } catch (e: any) {
      setError(e?.message || "Erro ao carregar pagamentos");
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await fetchAdminPaymentsStats(period);
      if (data.success) {
        setStats(data.data);
      }
    } catch (e: any) {
      console.error("Erro ao carregar estatísticas:", e);
    }
  };

  useEffect(() => { load(); }, [page, limit]);
  useEffect(() => { loadStats(); }, [period]);

  return (
    <div className="flex flex-col gap-3">
      {error ? <div className="rounded-lg bg-danger/10 border border-danger/20 text-danger-500 text-sm p-2">{error}</div> : null}
      
      {/* Estatísticas */}
      {stats && (
        <div className="space-y-4">
          {/* Filtro de Período */}
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Estatísticas de Vendas</h2>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="px-4 py-2 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="today">Hoje</option>
              <option value="week">Última Semana</option>
              <option value="month">Último Mês</option>
              <option value="year">Último Ano</option>
              <option value="all">Todo Período</option>
            </select>
          </div>

          {/* Cards de Estatísticas */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total em Reais */}
            <div className="bg-gradient-to-br from-green-500/10 to-green-600/5 border border-green-500/20 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-green-500/10 rounded-lg">
                  <DollarSign className="w-6 h-6 text-green-500" />
                </div>
              </div>
              <p className="text-sm text-foreground/60 mb-1">Total Vendido</p>
              <p className="text-3xl font-bold text-green-500">
                R$ {parseFloat(stats.summary.totalRevenue).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>

            {/* Total de Pagamentos */}
            <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-blue-500/10 rounded-lg">
                  <ShoppingCart className="w-6 h-6 text-blue-500" />
                </div>
              </div>
              <p className="text-sm text-foreground/60 mb-1">Total de Pagamentos</p>
              <p className="text-3xl font-bold text-blue-500">{stats.summary.totalPayments}</p>
            </div>

            {/* Ticket Médio */}
            <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border border-purple-500/20 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-purple-500/10 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-purple-500" />
                </div>
              </div>
              <p className="text-sm text-foreground/60 mb-1">Ticket Médio</p>
              <p className="text-3xl font-bold text-purple-500">
                R$ {parseFloat(stats.summary.averageTicket).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>

            {/* Total de Bots */}
            <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 border border-orange-500/20 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-orange-500/10 rounded-lg">
                  <Package className="w-6 h-6 text-orange-500" />
                </div>
              </div>
              <p className="text-sm text-foreground/60 mb-1">Bots Vendidos</p>
              <p className="text-3xl font-bold text-orange-500">{stats.summary.totalBots}</p>
            </div>
          </div>
        </div>
      )}

      <SectionHeader title="Pagamentos aprovados" />
      <PaymentsFilters
        planId={planId}
        coupon={coupon}
        user={userQ}
        limit={limit}
        onChange={(next) => {
          if (next.planId !== undefined) setPlanId(next.planId);
          if (next.coupon !== undefined) setCoupon(next.coupon);
          if (next.user !== undefined) setUserQ(next.user);
          if (next.limit !== undefined) setLimit(next.limit);
        }}
        actions={<Button size="lg" className="rounded-lg" onPress={load}>Atualizar</Button>}
      />
      <PaymentsTable items={items} loading={loading} />
      <div className="flex items-center justify-between text-xs text-foreground/70">
        <span>Total aprovados: {total} • Páginas: {totalPages || 1}</span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="light" isDisabled={page <= 1} onPress={() => setPage((p) => Math.max(p - 1, 1))}>Anterior</Button>
          <span>Página {page}</span>
          <Button size="sm" variant="light" isDisabled={totalPages > 0 ? page >= totalPages : items.length < limit} onPress={() => setPage((p) => p + 1)}>Próxima</Button>
        </div>
      </div>
    </div>
  );
}



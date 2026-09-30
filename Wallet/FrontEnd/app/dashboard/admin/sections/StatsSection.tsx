'use client'

import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faUsers, faMoneyBill, faArrowUp, faArrowDown, faCoins, faChartLine, faExchangeAlt, faUserPlus } from '@fortawesome/free-solid-svg-icons'
import { getAdminStats, AdminStatsResponse } from '@/lib/admin'

export function StatsSection() {
  const [stats, setStats] = useState<AdminStatsResponse['data'] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await getAdminStats()
      setStats(response.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar estatísticas')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value / 100)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <FontAwesomeIcon icon={faChartLine} className="w-8 h-8 text-primary animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500">
        {error}
      </div>
    )
  }

  if (!stats) {
    return null
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <h2 className="text-xl md:text-2xl font-bold text-foreground">Estatísticas do Sistema</h2>
        <button
          onClick={loadStats}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm md:text-base"
        >
          Atualizar
        </button>
      </div>

      {/* Cards de Estatísticas Principais */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {/* Usuários */}
        <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
          <div className="flex items-center justify-between mb-3 md:mb-4">
            <h3 className="text-xs md:text-sm font-medium text-foreground/70">Usuários</h3>
            <FontAwesomeIcon icon={faUsers} className="w-4 h-4 md:w-5 md:h-5 text-primary" />
          </div>
          <div className="space-y-2">
            <p className="text-xl md:text-2xl font-bold text-foreground">{stats.users.total}</p>
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4 text-xs text-foreground/60">
              <span>Ativos: {stats.users.active}</span>
              <span>Bloqueados: {stats.users.blocked}</span>
            </div>
          </div>
        </div>

        {/* Dinheiro Movimentado */}
        <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
          <div className="flex items-center justify-between mb-3 md:mb-4">
            <h3 className="text-xs md:text-sm font-medium text-foreground/70">Movimentado</h3>
            <FontAwesomeIcon icon={faChartLine} className="w-4 h-4 md:w-5 md:h-5 text-primary" />
          </div>
          <p className="text-xl md:text-2xl font-bold text-foreground">
            {formatCurrency((stats.financial as any).totalMoneyMoved || 0)}
          </p>
        </div>

        {/* Recebido Total */}
        <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
          <div className="flex items-center justify-between mb-3 md:mb-4">
            <h3 className="text-xs md:text-sm font-medium text-foreground/70">Recebido</h3>
            <FontAwesomeIcon icon={faArrowUp} className="w-4 h-4 md:w-5 md:h-5 text-green-500" />
          </div>
          <p className="text-xl md:text-2xl font-bold text-foreground">{formatCurrency(stats.financial.totalReceived)}</p>
        </div>

        {/* Saques Total */}
        <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
          <div className="flex items-center justify-between mb-3 md:mb-4">
            <h3 className="text-xs md:text-sm font-medium text-foreground/70">Sacado</h3>
            <FontAwesomeIcon icon={faArrowDown} className="w-4 h-4 md:w-5 md:h-5 text-red-500" />
          </div>
          <p className="text-xl md:text-2xl font-bold text-foreground">{formatCurrency(stats.financial.totalWithdrawn)}</p>
        </div>
      </div>

      {/* Cards Secundários */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {/* Cadastros */}
        {(stats as any).registrations && (
          <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
            <div className="flex items-center justify-between mb-3 md:mb-4">
              <h3 className="text-xs md:text-sm font-medium text-foreground/70">Cadastros</h3>
              <FontAwesomeIcon icon={faUserPlus} className="w-4 h-4 md:w-5 md:h-5 text-primary" />
            </div>
            <div className="space-y-1 md:space-y-2">
              <p className="text-lg md:text-xl font-bold text-foreground">Total: {(stats as any).registrations.total}</p>
              <div className="text-xs text-foreground/60 space-y-1">
                <div>24h: {(stats as any).registrations.last24h}</div>
                <div>7d: {(stats as any).registrations.last7d}</div>
                <div>30d: {(stats as any).registrations.last30d}</div>
              </div>
            </div>
          </div>
        )}

        {/* Transferências */}
        {(stats as any).transfers && (
          <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
            <div className="flex items-center justify-between mb-3 md:mb-4">
              <h3 className="text-xs md:text-sm font-medium text-foreground/70">Transferências Internas</h3>
              <FontAwesomeIcon icon={faExchangeAlt} className="w-4 h-4 md:w-5 md:h-5 text-blue-500" />
            </div>
            <div className="space-y-1 md:space-y-2">
              <p className="text-lg md:text-xl font-bold text-foreground">{(stats as any).transfers.total}</p>
              <p className="text-xs md:text-sm text-foreground/60">
                {formatCurrency((stats as any).transfers.totalAmount || 0)}
              </p>
            </div>
          </div>
        )}

        {/* Saldo Total */}
        <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
          <div className="flex items-center justify-between mb-3 md:mb-4">
            <h3 className="text-xs md:text-sm font-medium text-foreground/70">Saldo Total</h3>
            <FontAwesomeIcon icon={faCoins} className="w-4 h-4 md:w-5 md:h-5 text-primary" />
          </div>
          <p className="text-xl md:text-2xl font-bold text-foreground">{formatCurrency(stats.users.totalBalance)}</p>
        </div>

        {/* Taxas Coletadas */}
        <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
          <div className="flex items-center justify-between mb-3 md:mb-4">
            <h3 className="text-xs md:text-sm font-medium text-foreground/70">Taxas</h3>
            <FontAwesomeIcon icon={faMoneyBill} className="w-4 h-4 md:w-5 md:h-5 text-primary" />
          </div>
          <p className="text-xl md:text-2xl font-bold text-primary">{formatCurrency(stats.financial.totalFeesCollected)}</p>
        </div>
      </div>

      {/* Estatísticas Detalhadas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Pagamentos */}
        <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
          <h3 className="text-base md:text-lg font-bold text-foreground mb-3 md:mb-4">Pagamentos</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-foreground/70">Total:</span>
              <span className="font-semibold text-foreground">{stats.payments.total}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground/70">Completados:</span>
              <span className="font-semibold text-green-500">{stats.payments.completed}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground/70">Pendentes:</span>
              <span className="font-semibold text-yellow-500">{stats.payments.pending}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground/70">Valor Total:</span>
              <span className="font-semibold text-foreground">{formatCurrency(stats.payments.totalValue)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground/70">Taxas Coletadas:</span>
              <span className="font-semibold text-primary">{formatCurrency(stats.payments.totalFees)}</span>
            </div>
          </div>
        </div>

        {/* Saques */}
        <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
          <h3 className="text-base md:text-lg font-bold text-foreground mb-3 md:mb-4">Saques</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-foreground/70">Total:</span>
              <span className="font-semibold text-foreground">{stats.withdraws.total}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground/70">Completados:</span>
              <span className="font-semibold text-green-500">{stats.withdraws.completed}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground/70">Processando:</span>
              <span className="font-semibold text-yellow-500">{stats.withdraws.processing}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground/70">Falhados:</span>
              <span className="font-semibold text-red-500">{stats.withdraws.failed}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground/70">Valor Total:</span>
              <span className="font-semibold text-foreground">{formatCurrency(stats.withdraws.totalAmount)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Split */}
      <div className="p-4 md:p-6 rounded-xl border border-foreground/10 bg-foreground/2">
        <h3 className="text-base md:text-lg font-bold text-foreground mb-3 md:mb-4">Split Acumulado</h3>
        <p className="text-xl md:text-2xl font-bold text-primary">{formatCurrency(stats.split.totalSplit)}</p>
      </div>
    </div>
  )
}


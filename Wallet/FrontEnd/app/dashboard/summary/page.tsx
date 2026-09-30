'use client'

import { useState, useMemo, useEffect } from 'react'
import { SidebarDashboard } from '@/components/sidebar-dashboard'
import { DashboardTopbar } from '@/components/dashboard-topbar'
import { DashboardHeader } from '@/components/dashboard-header'
import { RippleButton } from '@/components/ripple-button'
import { Skeleton } from '@/components/ui/skeleton'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { format, subDays, startOfDay, endOfDay, startOfYear, parseISO, eachDayOfInterval, isSameDay, eachHourOfInterval, isSameHour } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { listPayments, listWithdraws, getBalance, listTransactions } from '@/lib/wallet'
import { useAuth } from '@/hooks/useAuth'
import { CalendarIcon, Wallet, TrendingUp, TrendingDown } from 'lucide-react'

type PeriodFilter = 'today' | '7days' | '30days' | 'year' | 'all'

interface Transaction {
  id: string
  date: Date
  description: string
  amount: number
  type: 'income' | 'expense'
  status: string
}

export default function SummaryPage() {
  const { user } = useAuth() // Usar useAuth para manter estado do usuário sincronizado
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [periodFilter, setPeriodFilter] = useState<PeriodFilter>('30days')
  const [loading, setLoading] = useState(true)
  const [payments, setPayments] = useState<any[]>([])
  const [withdraws, setWithdraws] = useState<any[]>([])
  const [balance, setBalance] = useState<number | null>(null)

  // Carregar dados reais
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        // Buscar todas as transações (pagamentos, saques, transferências)
        const [transactionsRes, balanceRes] = await Promise.all([
          listTransactions({ limit: 1000 }),
          getBalance()
        ])

        const rawTransactions = transactionsRes.data.transactions || []

        // Converter para o formato interno usado pela página
        const mappedTransactions: Transaction[] = rawTransactions.map(t => {
          const amountInReais = t.amount / 100
          // t.date pode ser Date ou string ISO dependendo da resposta
          const dateValue = typeof t.date === 'string' ? parseISO(t.date) : new Date(t.date)

          return {
            id: t.id,
            date: dateValue,
            description: t.description,
            // Para despesas, manter negativo conforme lógica existente da página
            amount: t.type === 'expense' ? -amountInReais : amountInReais,
            type: t.type,
            status: t.status
          }
        })

        // Filtrar apenas completadas/pagas
        const completedTransactions = mappedTransactions.filter(t =>
          t.status === 'COMPLETED' || t.status === 'PAID'
        )

        // Ordenar por data
        completedTransactions.sort((a, b) => a.date.getTime() - b.date.getTime())

        setPayments(completedTransactions) // Usando state 'payments' temporariamente para armazenar tudo ou refatorar state
        setWithdraws([]) // Não usado mais separadamente

        // Atualizar state de balance
        setBalance(balanceRes.data.balance.total / 100)
      } catch (error) {
        console.error('Erro ao carregar dados:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  // State simplificado: 'payments' agora contém todas as transações processadas
  const allTransactions = useMemo(() => {
    return payments // Já formatado e ordenado no useEffect
  }, [payments])

  // Filtrar transações baseado no período selecionado
  const filteredTransactions = useMemo(() => {
    const now = new Date()
    let startDate: Date

    switch (periodFilter) {
      case 'today':
        startDate = startOfDay(now)
        break
      case '7days':
        startDate = startOfDay(subDays(now, 7))
        break
      case '30days':
        startDate = startOfDay(subDays(now, 30))
        break
      case 'year':
        startDate = startOfYear(now)
        break
      case 'all':
        startDate = new Date(2020, 0, 1) // Data muito antiga para pegar tudo
        break
    }

    return allTransactions.filter(t => t.date >= startDate && t.date <= endOfDay(now))
  }, [periodFilter, allTransactions])

  // Calcular estatísticas
  const stats = useMemo(() => {
    const now = new Date()
    let startDate: Date
    switch (periodFilter) {
      case 'today':
        startDate = startOfDay(now)
        break
      case '7days':
        startDate = startOfDay(subDays(now, 7))
        break
      case '30days':
        startDate = startOfDay(subDays(now, 30))
        break
      case 'year':
        startDate = startOfYear(now)
        break
      case 'all':
        startDate = new Date(2020, 0, 1)
        break
    }

    // Calcular entradas e saídas do período
    const totalIncome = filteredTransactions
      .filter(t => t.type === 'income')
      .reduce((sum, t) => sum + t.amount, 0)

    const totalExpense = Math.abs(filteredTransactions
      .filter(t => t.type === 'expense')
      .reduce((sum, t) => sum + t.amount, 0))

    // Calcular saldo inicial: soma de todas as transações ANTES do período filtrado
    // Isso nos dá o saldo que existia no início do período
    const transactionsBeforePeriod = allTransactions.filter(t => t.date < startDate)
    const incomeBeforePeriod = transactionsBeforePeriod
      .filter(t => t.type === 'income')
      .reduce((sum, t) => sum + t.amount, 0)
    const expenseBeforePeriod = Math.abs(transactionsBeforePeriod
      .filter(t => t.type === 'expense')
      .reduce((sum, t) => sum + t.amount, 0))

    const initialBalance = incomeBeforePeriod - expenseBeforePeriod

    const transactionVolume = totalIncome + totalExpense
    const totalTransactions = filteredTransactions.length
    const averageTicket = totalTransactions > 0 ? transactionVolume / totalTransactions : 0

    // Nota: taxas não estão disponíveis na resposta unificada de transações
    // Para obter taxas, seria necessário buscar os dados originais separadamente
    const totalFees = 0

    return {
      initialBalance,
      totalIncome,
      totalExpense,
      availableBalance: balance || 0,
      transactionVolume,
      totalTransactions,
      averageTicket,
      totalFees,
      totalWithdrawn: totalExpense,
    }
  }, [filteredTransactions, balance, periodFilter, allTransactions])

  // Preparar dados para o gráfico
  const chartData = useMemo(() => {
    const now = new Date()
    let startDate: Date
    let points: Date[] = []
    let mode: 'hour' | 'day' | 'month' = 'day'

    try {
      if (periodFilter === 'today') {
        startDate = startOfDay(now)
        points = eachHourOfInterval({ start: startDate, end: now })
        mode = 'hour'
      } else if (periodFilter === 'year') {
        startDate = startOfYear(now)
        // Usar meses para o filtro de ano
        const { eachMonthOfInterval } = require('date-fns')
        points = eachMonthOfInterval({ start: startDate, end: now })
        mode = 'month'
      } else {
        switch (periodFilter) {
          case '7days':
            startDate = startOfDay(subDays(now, 7))
            break
          case '30days':
            startDate = startOfDay(subDays(now, 30))
            break
          case 'all':
            if (allTransactions.length > 0) {
              startDate = startOfDay(allTransactions[0].date)
            } else {
              startDate = startOfDay(subDays(now, 30))
            }
            break
          default:
            startDate = startOfDay(subDays(now, 30))
        }

        if (startDate > now) startDate = startOfDay(now)
        points = eachDayOfInterval({ start: startDate, end: now })
        mode = 'day'
      }
    } catch (e) {
      console.error('Erro ao gerar pontos do gráfico:', e)
      points = [now]
    }

    let runningBalance = stats.initialBalance

    return points.map(point => {
      let displayDate: string
      if (mode === 'hour') {
        displayDate = format(point, 'HH:mm', { locale: ptBR })
      } else if (mode === 'month') {
        displayDate = format(point, 'MMM/yy', { locale: ptBR })
      } else {
        displayDate = format(point, 'dd/MM', { locale: ptBR })
      }

      // Filtrar transações do ponto
      const { isSameMonth } = require('date-fns')
      const transactionsInPoint = filteredTransactions.filter(t => {
        if (mode === 'hour') return isSameHour(t.date, point)
        if (mode === 'month') return isSameMonth(t.date, point)
        return isSameDay(t.date, point)
      })

      let income = 0
      let expense = 0

      transactionsInPoint.forEach(t => {
        if (t.type === 'income') {
          income += t.amount
        } else {
          expense += Math.abs(t.amount)
        }
      })

      runningBalance += income - expense

      return {
        date: displayDate,
        fullDate: point,
        income,
        expense,
        volume: income + expense,
        runningBalance
      }
    })
  }, [filteredTransactions, stats.initialBalance, periodFilter, allTransactions])

  const formatCurrency = (value: number) => {
    return `R$ ${value.toFixed(2).replace('.', ',')}`
  }

  const periodLabels: Record<PeriodFilter, string> = {
    today: 'Hoje',
    '7days': 'Últimos 7 dias',
    '30days': 'Últimos 30 dias',
    year: 'Último ano',
    all: 'Todo o período',
  }

  return (
    <div className="flex h-screen bg-background">
      <SidebarDashboard open={sidebarOpen} onOpenChange={setSidebarOpen} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <DashboardTopbar onOpenSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main data-dashboard className="flex-1 overflow-auto">
          <div className="p-6 lg:p-8">
            <DashboardHeader loading={loading} />

            {/* Filtros de Período */}
            <div className="mt-6 flex flex-wrap gap-2">
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-9 w-28 rounded-lg" />
                ))
              ) : (
                (Object.keys(periodLabels) as PeriodFilter[]).map((period) => (
                  <RippleButton
                    key={period}
                    onClick={() => setPeriodFilter(period)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${periodFilter === period
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-foreground/5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground'
                      }`}
                  >
                    {periodLabels[period]}
                  </RippleButton>
                ))
              )}
            </div>

            {/* Cards de Estatísticas */}
            {loading ? (
              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(9)].map((_, i) => (
                  <Skeleton key={i} className="h-20 w-full rounded-lg" />
                ))}
              </div>
            ) : (
              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Saldo Inicial */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Saldo Inicial</p>
                  <p className="text-lg font-bold text-foreground">
                    {formatCurrency(stats.initialBalance)}
                  </p>
                </div>

                {/* Total de Entradas */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Total de Entradas</p>
                  <p className="text-lg font-bold text-foreground">
                    {formatCurrency(stats.totalIncome)}
                  </p>
                </div>

                {/* Total de Saídas */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Total de Saídas</p>
                  <p className="text-lg font-bold text-foreground">
                    {formatCurrency(stats.totalExpense)}
                  </p>
                </div>

                {/* Saldo disponível */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Saldo disponível</p>
                  <p className="text-lg font-bold text-foreground">
                    {formatCurrency(stats.availableBalance)}
                  </p>
                </div>

                {/* Volume transacionado */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Volume transacionado</p>
                  <p className="text-lg font-bold text-foreground">
                    {formatCurrency(stats.transactionVolume)}
                  </p>
                </div>

                {/* Ticket Médio */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Ticket Médio</p>
                  <p className="text-lg font-bold text-foreground">
                    {formatCurrency(stats.averageTicket)}
                  </p>
                </div>

                {/* Total de transações */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Total de transações</p>
                  <p className="text-lg font-bold text-foreground">
                    {stats.totalTransactions}
                  </p>
                </div>

                {/* Total de Taxas */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Total de Taxas</p>
                  <p className="text-lg font-bold text-foreground">
                    {formatCurrency(stats.totalFees)}
                  </p>
                </div>

                {/* Total Retirado */}
                <div className="border border-foreground/10 rounded-lg p-4 bg-foreground/5">
                  <p className="text-xs text-foreground/60 mb-1">Total Retirado</p>
                  <p className="text-lg font-bold text-foreground">
                    {formatCurrency(stats.totalWithdrawn)}
                  </p>
                </div>
              </div>
            )}

            {/* Gráfico */}
            <div className="mt-6 border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm p-4 sm:p-6">
              {loading ? (
                <Skeleton className="h-7 w-48 mb-6 rounded-md" />
              ) : (
                <h2 className="text-base sm:text-lg font-semibold text-foreground mb-4 sm:mb-6">Evolução Financeira</h2>
              )}

              {loading ? (
                <Skeleton className="h-[280px] sm:h-[400px] w-full rounded-lg" />
              ) : chartData.length > 0 ? (
                <div className="h-[280px] sm:h-[400px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                      <defs>
                        <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.5} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" vertical={false} />
                      <XAxis
                        dataKey="date"
                        stroke="rgba(255,255,255,0.3)"
                        style={{ fontSize: '10px' }}
                        tick={{ fill: 'rgba(255,255,255,0.5)' }}
                        tickLine={false}
                        axisLine={false}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        stroke="rgba(255,255,255,0.3)"
                        style={{ fontSize: '10px' }}
                        tick={{ fill: 'rgba(255,255,255,0.5)' }}
                        tickLine={false}
                        axisLine={false}
                        width={50}
                        tickFormatter={(value) => {
                          if (value >= 1000) return `${(value / 1000).toFixed(0)}k`
                          return value.toFixed(0)
                        }}
                      />
                      <Tooltip
                        content={({ active, payload, label }) => {
                          if (active && payload && payload.length) {
                            return (
                              <div className="rounded-xl border border-border/50 bg-background/95 backdrop-blur-xl shadow-xl p-3 min-w-[180px]">
                                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-border/50">
                                  <CalendarIcon className="w-4 h-4 text-muted-foreground" />
                                  <span className="text-sm font-medium">{label}</span>
                                </div>
                                <div className="space-y-1.5">
                                  {payload.map((entry: any, index: number) => {
                                    let icon = <Wallet className="w-3.5 h-3.5" />
                                    let label = entry.name
                                    if (entry.name === 'runningBalance') {
                                      icon = <Wallet className="w-3.5 h-3.5" />
                                      label = 'Saldo'
                                    } else if (entry.name === 'income') {
                                      icon = <TrendingUp className="w-3.5 h-3.5" />
                                      label = 'Entradas'
                                    } else if (entry.name === 'expense') {
                                      icon = <TrendingDown className="w-3.5 h-3.5" />
                                      label = 'Saídas'
                                    }

                                    return (
                                      <div key={index} className="flex items-center justify-between gap-4 text-xs">
                                        <div className="flex items-center gap-1.5" style={{ color: entry.stroke }}>
                                          {icon}
                                          <span>{label}</span>
                                        </div>
                                        <span className="font-mono font-medium">
                                          {formatCurrency(entry.value)}
                                        </span>
                                      </div>
                                    )
                                  })}
                                </div>
                              </div>
                            )
                          }
                          return null
                        }}
                      />
                      {/* Linha de Saldo - Principal */}
                      <Area
                        type="monotone"
                        dataKey="runningBalance"
                        stroke="#3b82f6"
                        fillOpacity={1}
                        fill="url(#colorBalance)"
                        strokeWidth={3}
                        dot={{ r: 4, strokeWidth: 2, fill: '#3b82f6', stroke: '#fff' }}
                        activeDot={{ r: 6, fill: '#3b82f6', stroke: '#fff', strokeWidth: 2 }}
                      />
                      {/* Entradas */}
                      <Area
                        type="monotone"
                        dataKey="income"
                        stroke="#22c55e"
                        fillOpacity={0.8}
                        fill="url(#colorIncome)"
                        strokeWidth={2}
                        dot={{ r: 3, strokeWidth: 1, fill: '#22c55e' }}
                        activeDot={{ r: 5, fill: '#22c55e' }}
                      />
                      {/* Saídas */}
                      <Area
                        type="monotone"
                        dataKey="expense"
                        stroke="#ef4444"
                        fillOpacity={0.8}
                        fill="url(#colorExpense)"
                        strokeWidth={2}
                        dot={{ r: 3, strokeWidth: 1, fill: '#ef4444' }}
                        activeDot={{ r: 5, fill: '#ef4444' }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[280px] sm:h-[400px] flex items-center justify-center text-foreground/60">
                  <div className="text-center">
                    <p className="text-lg mb-2">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="w-12 h-12 mx-auto text-foreground/40"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M10.5 6a1.5 1.5 0 113 0v6a1.5 1.5 0 11-3 0V6zM3.75 15.75a1.5 1.5 0 113 0v2.25a1.5 1.5 0 11-3 0v-2.25zM16.5 6a1.5 1.5 0 113 0v6a1.5 1.5 0 11-3 0V6zM3.75 6a1.5 1.5 0 113 0v2.25a1.5 1.5 0 11-3 0V6zM10.5 15.75a1.5 1.5 0 113 0v2.25a1.5 1.5 0 11-3 0v-2.25zM16.5 15.75a1.5 1.5 0 113 0v2.25a1.5 1.5 0 11-3 0v-2.25z"
                        />
                      </svg>
                    </p>
                    <p className="text-sm">Nenhum dado disponível para o período selecionado</p>
                  </div>
                </div>
              )}

              {/* Legenda */}
              {chartData.length > 0 && (
                <div className="flex items-center justify-center gap-4 sm:gap-6 mt-4 sm:mt-6 flex-wrap">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span className="text-xs sm:text-sm text-foreground/70">Saldo</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span className="text-xs sm:text-sm text-foreground/70">Entradas</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <span className="text-xs sm:text-sm text-foreground/70">Saídas</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

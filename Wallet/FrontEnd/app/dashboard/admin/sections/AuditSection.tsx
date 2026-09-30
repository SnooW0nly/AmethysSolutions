'use client'

import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faSearch, faSpinner, faClock, faUser, faServer, faFilter } from '@fortawesome/free-solid-svg-icons'
import { apiGet } from '@/lib/api'

interface AuditLog {
  id: string
  action: string
  entity: string
  entityId: string
  userId?: string
  userEmail?: string
  description?: string
  dataBefore?: any
  dataAfter?: any
  metadata?: any
  ipAddress?: string
  userAgent?: string
  createdAt: string
}

export function AuditSection() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    action: '',
    entity: '',
    userId: '',
    startDate: '',
    endDate: '',
  })
  const [showFilters, setShowFilters] = useState(false)
  const limit = 50

  useEffect(() => {
    loadLogs()
  }, [page, filters])

  const loadLogs = async () => {
    try {
      setLoading(true)
      setError(null)
      const params: any = {
        limit,
        offset: (page - 1) * limit,
      }
      if (filters.action) params.action = filters.action
      if (filters.entity) params.entity = filters.entity
      if (filters.userId) params.userId = filters.userId
      if (filters.startDate) params.startDate = filters.startDate
      if (filters.endDate) params.endDate = filters.endDate

      const query = new URLSearchParams(params).toString()
      const response = await apiGet<{
        success: boolean
        data: {
          logs: AuditLog[]
          pagination: {
            total: number
            limit: number
            offset: number
            hasMore: boolean
          }
        }
      }>(`/v1/admin/audit?${query}`)

      setLogs(response.data.logs)
      setTotal(response.data.pagination.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar logs de auditoria')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatAction = (action: string) => {
    return action
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase())
  }

  const getActionColor = (action: string) => {
    if (action.includes('CREATED') || action.includes('UPGRADED')) return 'text-green-500'
    if (action.includes('DELETED') || action.includes('FAILED')) return 'text-red-500'
    if (action.includes('UPDATED') || action.includes('CHANGED')) return 'text-blue-500'
    if (action.includes('BLOCKED')) return 'text-orange-500'
    return 'text-foreground/70'
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <h2 className="text-xl md:text-2xl font-bold text-foreground">Logs de Auditoria</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="px-4 py-2 rounded-lg bg-foreground/5 text-foreground hover:bg-foreground/10 transition-colors flex items-center gap-2"
          >
            <FontAwesomeIcon icon={faFilter} />
            <span className="hidden sm:inline">Filtros</span>
          </button>
          <button
            onClick={loadLogs}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Atualizar
          </button>
        </div>
      </div>

      {/* Filtros */}
      {showFilters && (
        <div className="p-4 rounded-xl border border-foreground/10 bg-foreground/2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Ação</label>
            <input
              type="text"
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              placeholder="Ex: USER_CREATED"
              className="w-full px-3 py-2 rounded-lg bg-background border border-foreground/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Entidade</label>
            <input
              type="text"
              value={filters.entity}
              onChange={(e) => setFilters({ ...filters, entity: e.target.value })}
              placeholder="Ex: USER, PLAN"
              className="w-full px-3 py-2 rounded-lg bg-background border border-foreground/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">ID do Usuário</label>
            <input
              type="text"
              value={filters.userId}
              onChange={(e) => setFilters({ ...filters, userId: e.target.value })}
              placeholder="ID do usuário"
              className="w-full px-3 py-2 rounded-lg bg-background border border-foreground/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Data Inicial</label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-background border border-foreground/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Data Final</label>
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-background border border-foreground/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={() => {
                setFilters({ action: '', entity: '', userId: '', startDate: '', endDate: '' })
                setPage(1)
              }}
              className="w-full px-4 py-2 rounded-lg bg-foreground/5 text-foreground hover:bg-foreground/10 transition-colors"
            >
              Limpar Filtros
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
          {error}
        </div>
      )}

      {/* Tabela de Logs */}
      <div className="rounded-xl border border-foreground/10 bg-foreground/2 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px]">
            <thead className="bg-foreground/5">
              <tr>
                <th className="px-4 md:px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">
                  Data/Hora
                </th>
                <th className="px-4 md:px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">
                  Ação
                </th>
                <th className="px-4 md:px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">
                  Entidade
                </th>
                <th className="px-4 md:px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">
                  Usuário
                </th>
                <th className="px-4 md:px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">
                  Descrição
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-foreground/10">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center">
                    <FontAwesomeIcon icon={faSpinner} className="w-6 h-6 text-primary animate-spin mx-auto" />
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-foreground/60">
                    Nenhum log encontrado
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-foreground/5 transition-colors">
                    <td className="px-4 md:px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 text-xs md:text-sm text-foreground/70">
                        <FontAwesomeIcon icon={faClock} className="text-foreground/50" />
                        {formatDate(log.createdAt)}
                      </div>
                    </td>
                    <td className="px-4 md:px-6 py-4 whitespace-nowrap">
                      <span className={`text-xs md:text-sm font-medium ${getActionColor(log.action)}`}>
                        {formatAction(log.action)}
                      </span>
                    </td>
                    <td className="px-4 md:px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 text-xs md:text-sm text-foreground/70">
                        <FontAwesomeIcon icon={faServer} className="text-foreground/50" />
                        <span className="font-medium">{log.entity}</span>
                        <span className="text-foreground/50">({log.entityId.slice(0, 8)}...)</span>
                      </div>
                    </td>
                    <td className="px-4 md:px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 text-xs md:text-sm text-foreground/70">
                        <FontAwesomeIcon icon={faUser} className="text-foreground/50" />
                        {log.userEmail || log.userId || 'Sistema'}
                      </div>
                    </td>
                    <td className="px-4 md:px-6 py-4">
                      <div className="text-xs md:text-sm text-foreground/70 max-w-md truncate" title={log.description}>
                        {log.description || '-'}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Paginação */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-sm text-foreground/60">
          Mostrando {logs.length} de {total} logs
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 md:px-4 py-2 rounded-lg bg-foreground/5 text-foreground hover:bg-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          >
            Anterior
          </button>
          <span className="text-sm text-foreground/70">Página {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * limit >= total}
            className="px-3 md:px-4 py-2 rounded-lg bg-foreground/5 text-foreground hover:bg-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          >
            Próxima
          </button>
        </div>
      </div>
    </div>
  )
}


'use client'

import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faSearch, faLock, faUnlock, faEye, faSpinner, faArrowLeft, faWallet, faCoins,
  faReceipt, faArrowUp, faArrowDown, faClock, faCheck, faTimes, faKey, faLink, faCalendar, faPercent, faUser, faShield
} from '@fortawesome/free-solid-svg-icons'
import { getAdminUsers, getAdminUser, blockUser, updateUserPlanAdmin, getAdminUserTransactions, setUserAdmin, AdminUser, AdminUserDetails, AdminTransaction } from '@/lib/admin'

export function UsuariosSection() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [blockedFilter, setBlockedFilter] = useState<string>('')

  // User Detail View
  const [selectedUser, setSelectedUser] = useState<AdminUserDetails | null>(null)
  const [showUserDetail, setShowUserDetail] = useState(false)
  const [loadingUser, setLoadingUser] = useState(false)

  // Plan Update
  const [selectedPlan, setSelectedPlan] = useState<string>('FREE')
  const [planDays, setPlanDays] = useState<string>('30')
  const [updatingPlan, setUpdatingPlan] = useState(false)
  const [updatingAdmin, setUpdatingAdmin] = useState(false)

  // Transactions
  const [transactions, setTransactions] = useState<AdminTransaction[]>([])
  const [loadingTransactions, setLoadingTransactions] = useState(false)
  const [transactionPage, setTransactionPage] = useState(1)
  const [transactionTotal, setTransactionTotal] = useState(0)

  const limit = 20
  const transactionLimit = 10

  // Reset page when search changes
  useEffect(() => {
    setPage(1)
  }, [search, statusFilter, blockedFilter])

  useEffect(() => {
    loadUsers()
  }, [page, statusFilter, blockedFilter, search])

  const loadUsers = async () => {
    try {
      setLoading(true)
      setError(null)
      const params: any = {
        limit,
        offset: (page - 1) * limit,
      }
      if (statusFilter) params.status = statusFilter
      if (blockedFilter) params.blocked = blockedFilter === 'true'
      if (search.trim()) params.search = search.trim()

      const response = await getAdminUsers(params)
      setUsers(response.data.users)
      setTotal(response.data.pagination.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar usuários')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    setPage(1)
    loadUsers()
  }

  const handleViewUser = async (userId: string) => {
    try {
      setLoadingUser(true)
      const response = await getAdminUser(userId)
      setSelectedUser(response.data.user as AdminUserDetails)
      setSelectedPlan(response.data.user.plan || 'FREE')
      setShowUserDetail(true)
      loadTransactions(userId, 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar usuário')
    } finally {
      setLoadingUser(false)
    }
  }

  const loadTransactions = async (userId: string, p: number) => {
    try {
      setLoadingTransactions(true)
      const response = await getAdminUserTransactions(userId, {
        limit: transactionLimit,
        offset: (p - 1) * transactionLimit,
        type: 'all'
      })
      setTransactions(response.data.transactions)
      setTransactionTotal(response.data.pagination.total)
      setTransactionPage(p)
    } catch (err) {
      console.error('Erro ao carregar transações:', err)
    } finally {
      setLoadingTransactions(false)
    }
  }

  const handleBlockUser = async (userId: string, blocked: boolean) => {
    try {
      await blockUser(userId, blocked)
      await loadUsers()
      if (selectedUser && selectedUser.id === userId) {
        const response = await getAdminUser(userId)
        setSelectedUser(response.data.user as AdminUserDetails)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao bloquear/desbloquear usuário')
    }
  }

  const handleUpdatePlan = async () => {
    if (!selectedUser) return
    try {
      setUpdatingPlan(true)
      await updateUserPlanAdmin(selectedUser.id, selectedPlan, parseInt(planDays))
      await loadUsers()
      const response = await getAdminUser(selectedUser.id)
      setSelectedUser(response.data.user as AdminUserDetails)
      alert('Plano atualizado com sucesso!')
    } catch (err: any) {
      alert(err.response?.data?.message || err.message || 'Erro ao atualizar plano')
    } finally {
      setUpdatingPlan(false)
    }
  }

  const handleSetAdmin = async (userId: string, makeAdmin: boolean) => {
    if (!confirm(makeAdmin ? 'Tem certeza que deseja tornar este usuário admin?' : 'Tem certeza que deseja remover o admin deste usuário?')) return
    try {
      setUpdatingAdmin(true)
      await setUserAdmin(userId, makeAdmin)
      const response = await getAdminUser(userId)
      setSelectedUser(response.data.user as AdminUserDetails)
      alert(makeAdmin ? 'Usuário promovido a admin!' : 'Permissão de admin removida!')
    } catch (err: any) {
      alert(err.response?.data?.message || err.message || 'Erro ao alterar status de admin')
    } finally {
      setUpdatingAdmin(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value / 100)
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
    })
  }

  const getStatusBadge = (status: string) => {
    const statusMap: { [key: string]: { color: string; label: string } } = {
      'COMPLETED': { color: 'bg-green-500/10 text-green-500', label: 'Concluído' },
      'PAID': { color: 'bg-green-500/10 text-green-500', label: 'Pago' },
      'PENDING': { color: 'bg-yellow-500/10 text-yellow-500', label: 'Pendente' },
      'ACTIVE': { color: 'bg-blue-500/10 text-blue-500', label: 'Ativo' },
      'PROCESSING': { color: 'bg-blue-500/10 text-blue-500', label: 'Processando' },
      'FAILED': { color: 'bg-red-500/10 text-red-500', label: 'Falhou' },
      'CANCELLED': { color: 'bg-gray-500/10 text-gray-500', label: 'Cancelado' },
      'EXPIRED': { color: 'bg-gray-500/10 text-gray-500', label: 'Expirado' },
    }
    const s = statusMap[status] || { color: 'bg-gray-500/10 text-gray-500', label: status }
    return <span className={`px-2 py-1 text-xs font-semibold rounded-full ${s.color}`}>{s.label}</span>
  }

  // User Detail View
  if (showUserDetail && selectedUser) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowUserDetail(false)}
            className="p-2 rounded-lg bg-foreground/5 hover:bg-foreground/10 text-foreground transition-colors"
          >
            <FontAwesomeIcon icon={faArrowLeft} />
          </button>
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-foreground">{selectedUser.name}</h2>
            <p className="text-foreground/60">{selectedUser.email}</p>
          </div>
          <span className={`px-3 py-1 text-sm font-semibold rounded-full ${selectedUser.blocked ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
            {selectedUser.blocked ? 'Bloqueado' : 'Ativo'}
          </span>
          <span className="px-3 py-1 text-sm font-semibold rounded-full bg-primary/10 text-primary">
            {selectedUser.plan || 'FREE'}
          </span>
          {selectedUser.admin && (
            <span className="px-3 py-1 text-sm font-semibold rounded-full bg-yellow-500/10 text-yellow-500 flex items-center gap-1">
              <FontAwesomeIcon icon={faShield} className="w-3 h-3" />
              Admin
            </span>
          )}
        </div>

        {/* Balance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-foreground/5 border border-foreground/10">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                <FontAwesomeIcon icon={faWallet} className="text-green-500" />
              </div>
              <span className="text-foreground/70 text-sm">Saldo</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{formatCurrency(selectedUser.balance)}</p>
          </div>
          <div className="p-4 rounded-xl bg-foreground/5 border border-foreground/10">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <FontAwesomeIcon icon={faCoins} className="text-blue-500" />
              </div>
              <span className="text-foreground/70 text-sm">Saldo Split</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{formatCurrency(selectedUser.saldo_split)}</p>
          </div>
          <div className="p-4 rounded-xl bg-foreground/5 border border-foreground/10">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <FontAwesomeIcon icon={faArrowDown} className="text-purple-500" />
              </div>
              <span className="text-foreground/70 text-sm">Total Recebido</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{formatCurrency(selectedUser.statistics?.totalReceived || 0)}</p>
          </div>
          <div className="p-4 rounded-xl bg-foreground/5 border border-foreground/10">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                <FontAwesomeIcon icon={faArrowUp} className="text-orange-500" />
              </div>
              <span className="text-foreground/70 text-sm">Total Sacado</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{formatCurrency(selectedUser.statistics?.totalWithdrawn || 0)}</p>
          </div>
        </div>

        {/* Account Info Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* User Info */}
          <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <FontAwesomeIcon icon={faUser} className="text-primary" />
              Informações da Conta
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-foreground/50 uppercase tracking-wide">CPF/CNPJ</label>
                <p className="text-foreground font-medium">{selectedUser.taxID || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-foreground/50 uppercase tracking-wide">Telefone</label>
                <p className="text-foreground font-medium">{selectedUser.phone || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-foreground/50 uppercase tracking-wide">PIX</label>
                <p className="text-foreground font-medium">{selectedUser.pixKey || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-foreground/50 uppercase tracking-wide">Tipo PIX</label>
                <p className="text-foreground font-medium">{selectedUser.pixKeyType || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-foreground/50 uppercase tracking-wide">Criado em</label>
                <p className="text-foreground font-medium">{formatDate(selectedUser.createdAt)}</p>
              </div>
              <div>
                <label className="text-xs text-foreground/50 uppercase tracking-wide">Atualizado</label>
                <p className="text-foreground font-medium">{formatDate(selectedUser.updatedAt)}</p>
              </div>
            </div>
          </div>

          {/* API & Webhook */}
          <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <FontAwesomeIcon icon={faKey} className="text-primary" />
              API & Webhook
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-foreground/50 uppercase tracking-wide">API Key</label>
                <p className="text-foreground font-mono text-sm bg-foreground/5 p-2 rounded break-all">
                  {selectedUser.apiKey ? `${selectedUser.apiKey.slice(0, 20)}...` : 'N/A'}
                </p>
              </div>
              <div>
                <label className="text-xs text-foreground/50 uppercase tracking-wide">Webhook URL</label>
                <p className="text-foreground font-mono text-sm bg-foreground/5 p-2 rounded break-all">
                  {selectedUser.webhookUrl || 'Não configurado'}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <span className={`px-2 py-1 text-xs rounded-full ${selectedUser.isAffiliate ? 'bg-green-500/10 text-green-500' : 'bg-gray-500/10 text-gray-500'}`}>
                  {selectedUser.isAffiliate ? 'Afiliado' : 'Não é afiliado'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Plan Info */}
        <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10">
          <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
            <FontAwesomeIcon icon={faCalendar} className="text-primary" />
            Plano & Taxas
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
            <div>
              <label className="text-xs text-foreground/50 uppercase tracking-wide">Plano</label>
              <p className="text-foreground font-bold text-lg">{selectedUser.plan || 'FREE'}</p>
            </div>
            <div>
              <label className="text-xs text-foreground/50 uppercase tracking-wide">Taxa Pagamento</label>
              <p className="text-foreground font-medium">{formatCurrency(selectedUser.paymentFee || 0)}</p>
            </div>
            <div>
              <label className="text-xs text-foreground/50 uppercase tracking-wide">Taxa Split</label>
              <p className="text-foreground font-medium">{formatCurrency(selectedUser.splitFee || 0)}</p>
            </div>
            <div>
              <label className="text-xs text-foreground/50 uppercase tracking-wide">Início Plano</label>
              <p className="text-foreground font-medium">{selectedUser.planStartDate ? formatDate(selectedUser.planStartDate) : 'N/A'}</p>
            </div>
            <div>
              <label className="text-xs text-foreground/50 uppercase tracking-wide">Fim Plano</label>
              <p className="text-foreground font-medium">{selectedUser.planEndDate ? formatDate(selectedUser.planEndDate) : 'N/A'}</p>
            </div>
            <div>
              <label className="text-xs text-foreground/50 uppercase tracking-wide">Renovação Auto</label>
              <p className={`font-medium ${selectedUser.planAutoRenew ? 'text-green-500' : 'text-red-500'}`}>
                {selectedUser.planAutoRenew ? 'Sim' : 'Não'}
              </p>
            </div>
          </div>

          {/* Update Plan */}
          <div className="pt-4 border-t border-foreground/10">
            <h4 className="text-sm font-bold text-foreground mb-3">Alterar Plano (Manual)</h4>
            <div className="flex flex-col md:flex-row gap-4 items-end">
              <div className="flex-1">
                <label className="text-xs text-foreground/50 mb-1 block">Plano</label>
                <select
                  value={selectedPlan}
                  onChange={(e) => setSelectedPlan(e.target.value)}
                  className="w-full px-4 py-2 rounded-lg bg-background border border-foreground/10 text-foreground"
                >
                  <option value="FREE">FREE</option>
                  <option value="CARBON">CARBON</option>
                  <option value="DIAMOND">DIAMOND</option>
                  <option value="RICH">RICH</option>
                  <option value="ENTERPRISE">ENTERPRISE</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="text-xs text-foreground/50 mb-1 block">Dias</label>
                <input
                  type="number"
                  value={planDays}
                  onChange={(e) => setPlanDays(e.target.value)}
                  className="w-full px-4 py-2 rounded-lg bg-background border border-foreground/10 text-foreground"
                />
              </div>
              <button
                onClick={handleUpdatePlan}
                disabled={updatingPlan}
                className="px-6 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {updatingPlan ? 'Atualizando...' : 'Definir Plano'}
              </button>
            </div>
          </div>
        </div>

        {/* Transactions */}
        <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10">
          <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
            <FontAwesomeIcon icon={faReceipt} className="text-primary" />
            Transações Recentes
          </h3>
          {loadingTransactions ? (
            <div className="flex items-center justify-center py-8">
              <FontAwesomeIcon icon={faSpinner} className="w-6 h-6 text-primary animate-spin" />
            </div>
          ) : transactions.length === 0 ? (
            <p className="text-foreground/60 text-center py-8">Nenhuma transação encontrada</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-foreground/10">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-foreground/70 uppercase">Tipo</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-foreground/70 uppercase">ID</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-foreground/70 uppercase">Valor</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-foreground/70 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-foreground/70 uppercase">Data</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-foreground/10">
                    {transactions.map((tx) => (
                      <tr key={tx.id} className="hover:bg-foreground/5 transition-colors">
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full ${tx.type === 'payment' ? 'bg-green-500/10 text-green-500' : 'bg-orange-500/10 text-orange-500'}`}>
                            <FontAwesomeIcon icon={tx.type === 'payment' ? faArrowDown : faArrowUp} className="w-3 h-3" />
                            {tx.type === 'payment' ? 'Pagamento' : 'Saque'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-foreground/70 font-mono">{tx.id.slice(0, 12)}...</td>
                        <td className="px-4 py-3 text-sm font-medium text-foreground">{formatCurrency(tx.value)}</td>
                        <td className="px-4 py-3">{getStatusBadge(tx.status)}</td>
                        <td className="px-4 py-3 text-sm text-foreground/70">{formatDate(tx.createdAt)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Transaction Pagination */}
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-foreground/10">
                <span className="text-sm text-foreground/60">Total: {transactionTotal}</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => loadTransactions(selectedUser.id, transactionPage - 1)}
                    disabled={transactionPage === 1 || loadingTransactions}
                    className="px-3 py-1 text-sm rounded-lg bg-foreground/5 text-foreground hover:bg-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Anterior
                  </button>
                  <span className="text-sm text-foreground/70">Página {transactionPage}</span>
                  <button
                    onClick={() => loadTransactions(selectedUser.id, transactionPage + 1)}
                    disabled={transactionPage * transactionLimit >= transactionTotal || loadingTransactions}
                    className="px-3 py-1 text-sm rounded-lg bg-foreground/5 text-foreground hover:bg-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Próxima
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-4">
          <button
            onClick={() => handleBlockUser(selectedUser.id, !selectedUser.blocked)}
            className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${selectedUser.blocked ? 'bg-green-500 text-white hover:bg-green-600' : 'bg-red-500 text-white hover:bg-red-600'}`}
          >
            {selectedUser.blocked ? 'Desbloquear Usuário' : 'Bloquear Usuário'}
          </button>
          <button
            onClick={() => handleSetAdmin(selectedUser.id, !selectedUser.admin)}
            disabled={updatingAdmin}
            className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50 ${selectedUser.admin ? 'bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30 border border-yellow-500/30' : 'bg-yellow-500 text-white hover:bg-yellow-600'}`}
          >
            <FontAwesomeIcon icon={faShield} />
            {updatingAdmin ? 'Aguarde...' : selectedUser.admin ? 'Remover Admin' : 'Tornar Admin'}
          </button>
        </div>
      </div>
    )
  }

  // Users List View
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-foreground">Gerenciar Usuários</h2>
        <button
          onClick={loadUsers}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Atualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl border border-foreground/10 bg-foreground/2">
        <div className="flex-1 relative">
          <FontAwesomeIcon icon={faSearch} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/50" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Buscar por nome, email ou ID..."
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-background border border-foreground/10 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 rounded-lg bg-background border border-foreground/10 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        >
          <option value="">Todos os status</option>
          <option value="active">Ativo</option>
          <option value="deleted">Deletado</option>
        </select>
        <select
          value={blockedFilter}
          onChange={(e) => setBlockedFilter(e.target.value)}
          className="px-4 py-2 rounded-lg bg-background border border-foreground/10 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        >
          <option value="">Todos</option>
          <option value="true">Bloqueados</option>
          <option value="false">Não bloqueados</option>
        </select>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500">
          {error}
        </div>
      )}

      {/* Tabela de Usuários */}
      <div className="rounded-xl border border-foreground/10 bg-foreground/2 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-foreground/5">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">Nome</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">Plano</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">Saldo</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-foreground/70 uppercase tracking-wider">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-foreground/10">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center">
                    <FontAwesomeIcon icon={faSpinner} className="w-6 h-6 text-primary animate-spin mx-auto" />
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-foreground/60">
                    Nenhum usuário encontrado
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-foreground/5 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-foreground">{user.name}</div>
                      <div className="text-xs text-foreground/60">{user.id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground/70">{user.email}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-primary/10 text-primary">
                        {user.plan || 'FREE'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                      {formatCurrency(user.balance)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${user.blocked ? 'bg-red-500/10 text-red-500' : user.status === 'active' ? 'bg-green-500/10 text-green-500' : 'bg-gray-500/10 text-gray-500'}`}>
                        {user.blocked ? 'Bloqueado' : user.status === 'active' ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleViewUser(user.id)}
                          className="text-primary hover:text-primary/80 transition-colors"
                          title="Ver detalhes"
                        >
                          <FontAwesomeIcon icon={faEye} />
                        </button>
                        <button
                          onClick={() => handleBlockUser(user.id, !user.blocked)}
                          className={`transition-colors ${user.blocked ? 'text-green-500 hover:text-green-600' : 'text-red-500 hover:text-red-600'}`}
                          title={user.blocked ? 'Desbloquear' : 'Bloquear'}
                        >
                          <FontAwesomeIcon icon={user.blocked ? faUnlock : faLock} />
                        </button>
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
      <div className="flex items-center justify-between">
        <div className="text-sm text-foreground/60">
          Mostrando {users.length} de {total} usuários
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg bg-foreground/5 text-foreground hover:bg-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Anterior
          </button>
          <span className="text-sm text-foreground/70">Página {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * limit >= total}
            className="px-4 py-2 rounded-lg bg-foreground/5 text-foreground hover:bg-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Próxima
          </button>
        </div>
      </div>
    </div>
  )
}

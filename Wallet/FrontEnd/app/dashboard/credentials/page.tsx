'use client'

import { useState, useEffect, useRef } from 'react'
import { SidebarDashboard } from '@/components/sidebar-dashboard'
import { DashboardTopbar } from '@/components/dashboard-topbar'
import { DashboardHeader } from '@/components/dashboard-header'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faKey,
  faCopy,
  faRotate,
  faPlus,
  faTrash,
  faEye,
  faEyeSlash,
  faCheck,
  faSpinner,
  faX,
  faLink,
  faEdit,
  faLock,
  faShieldHalved,
  faInfoCircle
} from '@fortawesome/free-solid-svg-icons'
import { RippleButton } from '@/components/ripple-button'
import { Separator } from '@/components/ui/separator'
import {
  listApiKeys,
  getApiKeyPermissions,
  createApiKey,
  resetApiKey,
  resetSecondaryApiKey,
  updateApiKey,
  deleteApiKey,
  listAuthorizedIPs,
  addAuthorizedIP,
  removeAuthorizedIP,
  clearAuthorizedIPs,
  ApiKey,
  ApiKeyPermission,
  AuthorizedIP
} from '@/lib/apiKeys'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'

export default function CredentialsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [permissions, setPermissions] = useState<Record<string, string>>({})
  const [authorizedIPs, setAuthorizedIPs] = useState<AuthorizedIP[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showResetDialog, setShowResetDialog] = useState<{ key: ApiKey; newKey?: string } | null>(null)
  const [showEditDialog, setShowEditDialog] = useState<ApiKey | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  // Estados do formulário de criação
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyPermissions, setNewKeyPermissions] = useState<string[]>([])
  const [newKeyWebhookUrl, setNewKeyWebhookUrl] = useState('')
  const [newKeyPlan, setNewKeyPlan] = useState<'WHITE' | 'BLACK'>('WHITE')
  const [creating, setCreating] = useState(false)

  // Estados do formulário de edição
  const [editKeyName, setEditKeyName] = useState('')
  const [editKeyPermissions, setEditKeyPermissions] = useState<string[]>([])
  const [editKeyWebhookUrl, setEditKeyWebhookUrl] = useState('')
  const [editKeyActive, setEditKeyActive] = useState(true)
  const [editKeyPlan, setEditKeyPlan] = useState<'WHITE' | 'BLACK'>('WHITE')
  const [updating, setUpdating] = useState(false)

  // Estados para IPs
  const [newIP, setNewIP] = useState('')
  const [addingIP, setAddingIP] = useState(false)

  const dataLoaded = useRef(false)

  useEffect(() => {
    if (!dataLoaded.current) {
      loadData()
      dataLoaded.current = true
    }
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [keysRes, permsRes, ipsRes, mainKeyRes] = await Promise.all([
        listApiKeys(),
        getApiKeyPermissions(),
        listAuthorizedIPs().catch(() => ({ success: true, data: { authorizedIPs: [], total: 0, hasRestriction: false } })),
        // Buscar a chave da API key principal para poder copiar
        import('@/lib/apiKeys').then(m => m.getMainApiKey()).catch(() => ({ success: true, data: { apiKey: '', webhookUrl: null } }))
      ])

      // Adicionar a chave à API key principal se não tiver
      const keys = keysRes.data.apiKeys.map(key => {
        if (key.type === 'main' && !key.key) {
          return { ...key, key: mainKeyRes.data.apiKey }
        }
        return key
      })

      setApiKeys(keys)
      setPermissions(permsRes.data.permissions)
      setAuthorizedIPs(ipsRes.data.authorizedIPs)
    } catch (error) {
      console.error('Erro ao carregar credenciais:', error)
      alert('Erro ao carregar credenciais')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (key: string, id: string) => {
    navigator.clipboard.writeText(key)
    setCopiedKey(id)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const handleReset = async (key: ApiKey) => {
    if (!confirm(`Tem certeza que deseja resetar a chave "${key.name || 'API Key'}"? A chave anterior será invalidada.`)) {
      return
    }

    try {
      setLoading(true)
      let response
      if (key.type === 'main') {
        response = await resetApiKey()
      } else {
        // Resetar API key secundária pelo índice
        if (key.id === undefined) {
          alert('Não é possível resetar esta chave')
          return
        }
        response = await resetSecondaryApiKey(key.id)
      }
      setShowResetDialog({ key, newKey: response.data.apiKey })
      await loadData()
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Erro ao resetar chave')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!newKeyName.trim() || newKeyPermissions.length === 0) {
      alert('Preencha o nome e selecione pelo menos uma permissão')
      return
    }

    try {
      setCreating(true)
      const response = await createApiKey({
        name: newKeyName.trim(),
        permissions: newKeyPermissions,
        webhookUrl: newKeyWebhookUrl.trim() || undefined,
        plan: newKeyPlan
      })

      setShowResetDialog({
        key: {
          type: 'secondary',
          name: response.data.name,
          permissions: response.data.permissions,
          active: true,
          createdAt: new Date().toISOString()
        } as ApiKey,
        newKey: response.data.apiKey
      })

      setNewKeyName('')
      setNewKeyPermissions([])
      setNewKeyWebhookUrl('')
      setNewKeyPlan('WHITE')
      setShowCreateDialog(false)
      await loadData()
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Erro ao criar chave')
    } finally {
      setCreating(false)
    }
  }

  const handleUpdate = async () => {
    if (!showEditDialog) return

    if (showEditDialog.type === 'main') {
      // Atualizar apenas webhook da principal
      try {
        setUpdating(true)
        const { updateMainApiKey } = await import('@/lib/apiKeys')
        await updateMainApiKey({
          webhookUrl: editKeyWebhookUrl.trim() || undefined
        })

        setShowEditDialog(null)
        await loadData()
      } catch (error) {
        alert(error instanceof Error ? error.message : 'Erro ao atualizar chave')
      } finally {
        setUpdating(false)
      }
      return
    }

    if (showEditDialog.id === undefined) {
      alert('Não é possível atualizar esta chave')
      return
    }

    if (!editKeyName.trim() || editKeyPermissions.length === 0) {
      alert('Preencha o nome e selecione pelo menos uma permissão')
      return
    }

    try {
      setUpdating(true)
      await updateApiKey(showEditDialog.id, {
        name: editKeyName.trim(),
        permissions: editKeyPermissions,
        active: editKeyActive,
        webhookUrl: editKeyWebhookUrl.trim() || undefined,
        plan: editKeyPlan
      })

      setShowEditDialog(null)
      await loadData()
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Erro ao atualizar chave')
    } finally {
      setUpdating(false)
    }
  }

  const handleDelete = async (key: ApiKey) => {
    if (key.type === 'main') {
      if (!confirm('Tem certeza que deseja resetar esta API Key? Uma nova chave será gerada e a anterior será invalidada.')) {
        return
      }
      // Para a principal, apenas resetar (não deletar completamente)
      try {
        setLoading(true)
        await resetApiKey()
        await loadData()
        alert('API Key foi resetada. Uma nova chave foi gerada.')
      } catch (error) {
        alert(error instanceof Error ? error.message : 'Erro ao resetar chave')
      } finally {
        setLoading(false)
      }
      return
    }

    if (key.id === undefined) {
      alert('Não é possível deletar esta chave')
      return
    }

    if (!confirm(`Tem certeza que deseja deletar a chave "${key.name}"?`)) {
      return
    }

    try {
      setLoading(true)
      await deleteApiKey(key.id)
      await loadData()
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Erro ao deletar chave')
    } finally {
      setLoading(false)
    }
  }

  const togglePermission = (permission: string, isEdit: boolean = false) => {
    if (isEdit) {
      setEditKeyPermissions(prev =>
        prev.includes(permission)
          ? prev.filter(p => p !== permission)
          : [...prev, permission]
      )
    } else {
      setNewKeyPermissions(prev =>
        prev.includes(permission)
          ? prev.filter(p => p !== permission)
          : [...prev, permission]
      )
    }
  }

  const openEditDialog = async (key: ApiKey) => {
    if (key.type === 'main') {
      // Para a principal, buscar a chave atual e webhook
      try {
        const { getMainApiKey, updateMainApiKey } = await import('@/lib/apiKeys')
        const mainKeyRes = await getMainApiKey()
        setEditKeyName('API Key')
        setEditKeyPermissions(['admin:all'])
        setEditKeyWebhookUrl(mainKeyRes.data.webhookUrl || '')
        setEditKeyActive(true)
        setShowEditDialog({ ...key, key: mainKeyRes.data.apiKey } as ApiKey)
      } catch (error) {
        alert('Erro ao carregar dados da API Key')
      }
    } else {
      setEditKeyName(key.name || '')
      setEditKeyPermissions(key.permissions || [])
      setEditKeyWebhookUrl(key.webhookUrl || '')
      setEditKeyActive(key.active !== false)
      setEditKeyPlan(((key as any).plan as 'WHITE' | 'BLACK') || 'WHITE')
      setShowEditDialog(key)
    }
  }

  const handleAddIP = async () => {
    if (!newIP.trim()) {
      alert('Digite um IP válido')
      return
    }

    try {
      setAddingIP(true)
      const response = await addAuthorizedIP(newIP.trim())
      setNewIP('')
      // Atualizar estado imediatamente sem esperar loadData
      if (response.data) {
        setAuthorizedIPs(prev => [...prev, {
          ip: response.data.ip,
          active: response.data.active,
          createdAt: response.data.createdAt
        }])
      }
      // Recarregar dados para garantir sincronização
      await loadData()
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Erro ao adicionar IP')
    } finally {
      setAddingIP(false)
    }
  }

  const handleRemoveIP = async (ip: string) => {
    if (!confirm(`Tem certeza que deseja remover o IP "${ip}"?`)) {
      return
    }

    try {
      await removeAuthorizedIP(ip)
      // Atualizar estado imediatamente
      setAuthorizedIPs(prev => prev.filter(ipData => ipData.ip !== ip))
      // Recarregar dados para garantir sincronização
      await loadData()
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Erro ao remover IP')
    }
  }

  const handleClearAllIPs = async () => {
    // Adicionar IP 0.0.0.0 que libera todos os IPs
    try {
      // Verificar se já existe
      const hasWildcard = authorizedIPs.some(ip => ip.ip === '0.0.0.0')
      if (!hasWildcard) {
        const response = await addAuthorizedIP('0.0.0.0')
        // Atualizar estado imediatamente
        if (response.data) {
          setAuthorizedIPs(prev => [...prev, {
            ip: response.data.ip,
            active: response.data.active,
            createdAt: response.data.createdAt
          }])
        }
        // Recarregar dados para garantir sincronização
        await loadData()
      } else {
        alert('O IP 0.0.0.0 já está na lista. Ele permite requisições de qualquer IP.')
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Erro ao adicionar IP')
    }
  }

  return (
    <div className="flex h-screen bg-background">
      <SidebarDashboard open={sidebarOpen} onOpenChange={setSidebarOpen} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <DashboardTopbar onOpenSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main data-dashboard className="flex-1 overflow-auto">
          <div className="p-6 lg:p-8 w-full">
            <DashboardHeader loading={loading} />

            {/* Seção: Suas Credenciais */}
            <div className="mt-6 mb-8">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-4 mb-4">
                {loading ? (
                  <Skeleton className="h-10 w-36 rounded-lg" />
                ) : (
                  <RippleButton
                    onClick={() => setShowCreateDialog(true)}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors w-full sm:w-auto"
                  >
                    <FontAwesomeIcon icon={faPlus} className="w-4 h-4" />
                    <span>Nova API Key</span>
                  </RippleButton>
                )}
              </div>

              {loading ? (
                <div className="space-y-4">
                  {[1, 2].map((i) => (
                    <div key={i} className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm p-4 sm:p-6">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          {/* Título e badge */}
                          <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2">
                            <Skeleton className="w-5 h-5 rounded" />
                            <Skeleton className="h-6 w-40 rounded" />
                          </div>

                          <div className="space-y-3 mt-4">
                            {/* Permissões */}
                            <div>
                              <Skeleton className="h-3 w-20 mb-2 rounded" />
                              <div className="flex flex-wrap gap-2">
                                <Skeleton className="h-6 w-24 rounded" />
                                <Skeleton className="h-6 w-28 rounded" />
                                <Skeleton className="h-6 w-20 rounded" />
                              </div>
                            </div>

                            {/* Datas */}
                            <div className="flex flex-col gap-1">
                              <Skeleton className="h-3 w-48 rounded" />
                              <Skeleton className="h-3 w-44 rounded" />
                            </div>
                          </div>
                        </div>

                        {/* Botões de ação */}
                        <div className="flex items-center gap-2 flex-shrink-0 sm:ml-4">
                          <Skeleton className="w-9 h-9 rounded-lg" />
                          <Skeleton className="w-9 h-9 rounded-lg" />
                          <Skeleton className="w-9 h-9 rounded-lg" />
                          <Skeleton className="w-9 h-9 rounded-lg" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  {apiKeys.map((key) => (
                    <div
                      key={key.type === 'main' ? 'main' : key.id}
                      className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm p-4 sm:p-6"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2">
                            <FontAwesomeIcon icon={faKey} className="w-5 h-5 text-primary flex-shrink-0" />
                            <h3 className="text-base sm:text-lg font-bold text-foreground break-words">
                              {key.name || `API Key ${key.type === 'main' ? '' : `#${key.id}`}`}
                            </h3>
                            {(key as any).plan && (
                              <span className={`px-2 py-0.5 text-xs font-bold rounded flex-shrink-0 ${
                                (key as any).plan === 'BLACK'
                                  ? 'bg-zinc-800 text-zinc-200 border border-zinc-600'
                                  : 'bg-slate-200/10 text-slate-300 border border-slate-500/30'
                              }`}>
                                {(key as any).plan}
                              </span>
                            )}
                            {key.active === false && (
                              <span className="px-2 py-1 bg-red-500/20 text-red-500 text-xs font-semibold rounded flex-shrink-0">
                                Desativada
                              </span>
                            )}
                          </div>

                          <div className="space-y-2 mt-4">
                            <div>
                              <span className="text-xs text-muted-foreground">Permissões: </span>
                              <div className="flex flex-wrap gap-2 mt-1">
                                {key.permissions.map((perm) => (
                                  <span
                                    key={perm}
                                    className="px-2 py-1 bg-foreground/5 text-foreground text-xs rounded break-words"
                                  >
                                    {permissions[perm] || perm}
                                  </span>
                                ))}
                              </div>
                            </div>

                            {key.webhookUrl && (
                              <div className="break-all">
                                <span className="text-xs text-muted-foreground">Webhook: </span>
                                <span className="text-xs text-foreground font-mono break-all">{key.webhookUrl}</span>
                              </div>
                            )}

                            <div className="flex flex-col gap-0.5">
                              <span className="text-xs text-muted-foreground">
                                Criada em: {format(new Date(key.createdAt), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                              </span>
                              {key.lastUsedAt && (
                                <span className="text-xs text-muted-foreground">
                                  Último uso: {format(new Date(key.lastUsedAt), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0 sm:ml-4">
                          {key.key && (
                            <RippleButton
                              onClick={() => handleCopy(key.key!, key.type === 'main' ? 'main' : String(key.id))}
                              className="p-2 hover:bg-foreground/10 rounded-lg transition-colors"
                              title="Copiar chave"
                            >
                              <FontAwesomeIcon
                                icon={copiedKey === (key.type === 'main' ? 'main' : String(key.id)) ? faCheck : faCopy}
                                className={`w-4 h-4 ${copiedKey === (key.type === 'main' ? 'main' : String(key.id)) ? 'text-green-500' : 'text-foreground'}`}
                              />
                            </RippleButton>
                          )}

                          <RippleButton
                            onClick={() => openEditDialog(key)}
                            className="p-2 hover:bg-foreground/10 rounded-lg transition-colors"
                            title="Editar"
                          >
                            <FontAwesomeIcon icon={faEdit} className="w-4 h-4 text-foreground" />
                          </RippleButton>

                          <RippleButton
                            onClick={() => handleDelete(key)}
                            className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
                            title="Deletar"
                          >
                            <FontAwesomeIcon icon={faTrash} className="w-4 h-4 text-red-500" />
                          </RippleButton>

                          <RippleButton
                            onClick={() => handleReset(key)}
                            className="p-2 hover:bg-foreground/10 rounded-lg transition-colors"
                            title="Resetar chave"
                          >
                            <FontAwesomeIcon icon={faRotate} className="w-4 h-4 text-foreground" />
                          </RippleButton>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Separator className="my-8" />

            {/* Seção: Seus IPs */}
            <div className="mb-8">
              {loading ? (
                <>
                  <div className="mb-4">
                    <Skeleton className="h-7 w-28 mb-2 rounded" />
                    <Skeleton className="h-4 w-full max-w-xl rounded" />
                  </div>
                  <div className="flex flex-col sm:flex-row gap-3 mb-4">
                    <Skeleton className="h-10 flex-1 rounded-lg" />
                    <div className="flex gap-2 sm:gap-3">
                      <Skeleton className="h-10 w-32 rounded-lg" />
                      <Skeleton className="h-10 w-40 rounded-lg" />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="mb-4">
                    <h2 className="text-xl font-bold text-foreground mb-1">Seus IPs</h2>
                    <p className="text-sm text-muted-foreground">
                      Adicione IPs autorizados para aumentar a segurança da sua integração. Apenas requisições provenientes destes IPs serão aceitas.
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-3 mb-4">
                    <Input
                      type="text"
                      value={newIP}
                      onChange={(e) => setNewIP(e.target.value)}
                      placeholder="Digite o IP para adicionar (ex: 192.168.1.1)"
                      className="flex-1 min-w-0"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          handleAddIP()
                        }
                      }}
                    />
                    <div className="flex gap-2 sm:gap-3">
                      <RippleButton
                        onClick={handleAddIP}
                        disabled={addingIP || !newIP.trim()}
                        className="flex-1 sm:flex-initial px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        <FontAwesomeIcon icon={addingIP ? faSpinner : faPlus} className={addingIP ? 'animate-spin' : ''} />
                        <span className="hidden sm:inline">Adicionar IP</span>
                        <span className="sm:hidden">Adicionar</span>
                      </RippleButton>
                      <RippleButton
                        onClick={handleClearAllIPs}
                        disabled={authorizedIPs.some(ip => ip.ip === '0.0.0.0')}
                        className="flex-1 sm:flex-initial px-3 sm:px-4 py-2 bg-red-500/20 text-red-500 rounded-lg hover:bg-red-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      >
                        <FontAwesomeIcon icon={faLock} className="w-4 h-4" />
                        <span className="hidden sm:inline">Liberar Todos os IPs</span>
                        <span className="sm:hidden">Liberar</span>
                      </RippleButton>
                    </div>
                  </div>
                </>
              )}

              {loading ? (
                <div className="border border-foreground/10 rounded-lg overflow-hidden">
                  {/* Header skeleton */}
                  <div className="bg-foreground/5 px-3 sm:px-4 py-3 flex">
                    <Skeleton className="h-4 w-12 rounded" />
                    <Skeleton className="h-4 w-16 rounded ml-auto mr-16" />
                    <Skeleton className="h-4 w-12 rounded" />
                  </div>
                  {/* Rows skeleton */}
                  {[1, 2].map((i) => (
                    <div key={i} className="px-3 sm:px-4 py-3 flex items-center border-t border-foreground/10">
                      <Skeleton className="h-4 w-28 rounded" />
                      <Skeleton className="h-6 w-14 rounded ml-auto mr-12" />
                      <Skeleton className="h-8 w-8 rounded-lg" />
                    </div>
                  ))}
                </div>
              ) : authorizedIPs.length === 0 ? (
                <div className="p-6 rounded-lg bg-foreground/5 border border-foreground/10 text-center">
                  <p className="text-sm text-muted-foreground">
                    Nenhum IP autorizado. Adicione IPs para restringir o acesso às suas credenciais.
                  </p>
                </div>
              ) : (
                <div className="border border-foreground/10 rounded-lg overflow-hidden overflow-x-auto">
                  <table className="w-full min-w-[400px]">
                    <thead className="bg-foreground/5">
                      <tr>
                        <th className="px-3 sm:px-4 py-3 text-left text-sm font-medium text-foreground">IP</th>
                        <th className="px-3 sm:px-4 py-3 text-left text-sm font-medium text-foreground">Status</th>
                        <th className="px-3 sm:px-4 py-3 text-right text-sm font-medium text-foreground">Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {authorizedIPs.map((ipData, idx) => (
                        <tr key={ipData.ip} className={idx < authorizedIPs.length - 1 ? 'border-b border-foreground/10' : ''}>
                          <td className="px-3 sm:px-4 py-3 text-sm text-foreground font-mono break-all">{ipData.ip}</td>
                          <td className="px-3 sm:px-4 py-3">
                            <span className={`text-xs font-semibold px-2 py-1 rounded whitespace-nowrap ${ipData.active ? 'bg-green-500/20 text-green-500' : 'bg-gray-500/20 text-gray-500'
                              }`}>
                              {ipData.active ? 'Ativo' : 'Inativo'}
                            </span>
                          </td>
                          <td className="px-3 sm:px-4 py-3 text-right">
                            <RippleButton
                              onClick={() => handleRemoveIP(ipData.ip)}
                              className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
                              title="Remover IP"
                            >
                              <FontAwesomeIcon icon={faTrash} className="w-4 h-4 text-red-500" />
                            </RippleButton>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

          </div>
        </main>
      </div>

      {/* Dialog de criação */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto w-[95vw] sm:w-full mx-4 sm:mx-auto">
          <DialogHeader>
            <DialogTitle>Criar Nova API Key</DialogTitle>
            <DialogDescription>
              Crie uma nova API Key com permissões específicas
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            <div>
              <Label htmlFor="keyName">Nome</Label>
              <Input
                id="keyName"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="Ex: API Key para produção"
                className="mt-1"
              />
            </div>

            <div>
              <Label>Rota / Plano</Label>
              <div className="flex gap-2 mt-1">
                {(['WHITE', 'BLACK'] as const).map((plan) => (
                  <button
                    key={plan}
                    type="button"
                    onClick={() => setNewKeyPlan(plan)}
                    className={`flex-1 py-2 px-3 rounded-lg border text-sm font-semibold transition-colors ${
                      newKeyPlan === plan
                        ? plan === 'BLACK'
                          ? 'bg-zinc-800 border-zinc-600 text-zinc-100'
                          : 'bg-primary/10 border-primary text-primary'
                        : 'bg-transparent border-foreground/10 text-foreground/50 hover:border-foreground/30'
                    }`}
                  >
                    {plan}
                    <span className="block text-xs font-normal opacity-70 mt-0.5">
                      {plan === 'WHITE' ? '4% por transação · R$\u00a00,30 saque' : '6% por transação · R$\u00a00,30 saque'}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <Label>Permissões</Label>
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                {Object.entries(permissions).filter(([perm]) => perm !== 'admin:all').map(([perm, desc]) => (
                  <div key={perm} className="flex items-center space-x-2">
                    <Checkbox
                      id={`perm-${perm}`}
                      checked={newKeyPermissions.includes(perm)}
                      onCheckedChange={() => togglePermission(perm)}
                    />
                    <label
                      htmlFor={`perm-${perm}`}
                      className="text-sm text-foreground cursor-pointer flex-1"
                    >
                      <span className="font-medium">{perm}</span>
                      <span className="text-muted-foreground ml-2">- {desc}</span>
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <Label htmlFor="webhookUrl">Webhook URL (opcional)</Label>
              <Input
                id="webhookUrl"
                type="url"
                value={newKeyWebhookUrl}
                onChange={(e) => setNewKeyWebhookUrl(e.target.value)}
                placeholder="https://seusite.com/webhook"
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                URL para receber notificações de eventos desta API Key
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-2 pt-4">
              <RippleButton
                onClick={() => setShowCreateDialog(false)}
                className="flex-1 px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg transition-colors w-full sm:w-auto"
              >
                Cancelar
              </RippleButton>
              <RippleButton
                onClick={handleCreate}
                disabled={creating || !newKeyName.trim() || newKeyPermissions.length === 0}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 w-full sm:w-auto"
              >
                {creating ? (
                  <>
                    <FontAwesomeIcon icon={faSpinner} className="animate-spin mr-2" />
                    Criando...
                  </>
                ) : (
                  'Criar'
                )}
              </RippleButton>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog de reset */}
      {showResetDialog && (
        <Dialog open={!!showResetDialog} onOpenChange={() => setShowResetDialog(null)}>
          <DialogContent className="w-[95vw] sm:w-full mx-4 sm:mx-auto max-w-2xl">
            <DialogHeader>
              <DialogTitle>API Key Resetada</DialogTitle>
              <DialogDescription>
                {showResetDialog.newKey
                  ? 'Sua nova API Key foi gerada. Copie e guarde em local seguro.'
                  : 'Resetando API Key...'}
              </DialogDescription>
            </DialogHeader>

            {showResetDialog.newKey && (
              <div className="space-y-4 mt-4">
                <div>
                  <Label>Nova API Key</Label>
                  <div className="flex flex-col sm:flex-row gap-2 mt-1">
                    <Input
                      value={showResetDialog.newKey}
                      readOnly
                      className="font-mono flex-1 min-w-0"
                    />
                    <RippleButton
                      onClick={() => handleCopy(showResetDialog.newKey!, 'reset')}
                      className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex-shrink-0 w-full sm:w-auto flex items-center justify-center"
                    >
                      <FontAwesomeIcon icon={copiedKey === 'reset' ? faCheck : faCopy} />
                    </RippleButton>
                  </div>
                  <p className="text-xs text-red-500 mt-2">
                    ⚠️ Esta chave não será exibida novamente. Guarde em local seguro!
                  </p>
                </div>

                <RippleButton
                  onClick={() => setShowResetDialog(null)}
                  className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Entendi
                </RippleButton>
              </div>
            )}
          </DialogContent>
        </Dialog>
      )}

      {/* Dialog de edição */}
      {showEditDialog && (
        <Dialog open={!!showEditDialog} onOpenChange={() => setShowEditDialog(null)}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto w-[95vw] sm:w-full mx-4 sm:mx-auto">
            <DialogHeader>
              <DialogTitle>Editar API Key</DialogTitle>
              <DialogDescription>
                Atualize as configurações desta API Key
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              {showEditDialog.type === 'main' ? (
                // Para API Key principal, mostrar apenas webhook
                <div>
                  <Label htmlFor="editWebhookUrl">Webhook URL (opcional)</Label>
                  <Input
                    id="editWebhookUrl"
                    type="url"
                    value={editKeyWebhookUrl}
                    onChange={(e) => setEditKeyWebhookUrl(e.target.value)}
                    placeholder="https://seusite.com/webhook"
                    className="mt-1"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Esta API Key tem permissão total (admin:all)
                  </p>
                </div>
              ) : (
                <>
                  <div>
                    <Label htmlFor="editKeyName">Nome</Label>
                    <Input
                      id="editKeyName"
                      value={editKeyName}
                      onChange={(e) => setEditKeyName(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <Label>Permissões</Label>
                    <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                      {Object.entries(permissions).filter(([perm]) => perm !== 'admin:all').map(([perm, desc]) => (
                        <div key={perm} className="flex items-center space-x-2">
                          <Checkbox
                            id={`edit-perm-${perm}`}
                            checked={editKeyPermissions.includes(perm)}
                            onCheckedChange={() => togglePermission(perm, true)}
                          />
                          <label
                            htmlFor={`edit-perm-${perm}`}
                            className="text-sm text-foreground cursor-pointer flex-1"
                          >
                            <span className="font-medium">{perm}</span>
                            <span className="text-muted-foreground ml-2">- {desc}</span>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="editWebhookUrl">Webhook URL (opcional)</Label>
                    <Input
                      id="editWebhookUrl"
                      type="url"
                      value={editKeyWebhookUrl}
                      onChange={(e) => setEditKeyWebhookUrl(e.target.value)}
                      placeholder="https://seusite.com/webhook"
                      className="mt-1"
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="editActive"
                      checked={editKeyActive}
                      onCheckedChange={(checked) => setEditKeyActive(checked === true)}
                    />
                    <label htmlFor="editActive" className="text-sm text-foreground cursor-pointer">
                      API Key ativa
                    </label>
                  </div>

                  <div>
                    <Label>Rota / Plano</Label>
                    <div className="flex gap-2 mt-1">
                      {(['WHITE', 'BLACK'] as const).map((plan) => (
                        <button
                          key={plan}
                          type="button"
                          onClick={() => setEditKeyPlan(plan)}
                          className={`flex-1 py-2 px-3 rounded-lg border text-sm font-semibold transition-colors ${
                            editKeyPlan === plan
                              ? plan === 'BLACK'
                                ? 'bg-zinc-800 border-zinc-600 text-zinc-100'
                                : 'bg-primary/10 border-primary text-primary'
                              : 'bg-transparent border-foreground/10 text-foreground/50 hover:border-foreground/30'
                          }`}
                        >
                          {plan}
                          <span className="block text-xs font-normal opacity-70 mt-0.5">
                            {plan === 'WHITE' ? '4% por transação · R$\u00a00,30 saque' : '6% por transação · R$\u00a00,30 saque'}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <div className="flex flex-col sm:flex-row gap-2 pt-4">
                <RippleButton
                  onClick={() => setShowEditDialog(null)}
                  className="flex-1 px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg transition-colors w-full sm:w-auto"
                >
                  Cancelar
                </RippleButton>
                <RippleButton
                  onClick={handleUpdate}
                  disabled={updating || (showEditDialog.type !== 'main' && (!editKeyName.trim() || editKeyPermissions.length === 0))}
                  className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 w-full sm:w-auto"
                >
                  {updating ? (
                    <>
                      <FontAwesomeIcon icon={faSpinner} className="animate-spin mr-2" />
                      Atualizando...
                    </>
                  ) : (
                    'Salvar'
                  )}
                </RippleButton>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}

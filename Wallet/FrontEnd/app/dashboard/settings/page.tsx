'use client'

import { useState, useEffect } from 'react'
import { SidebarDashboard } from '@/components/sidebar-dashboard'
import { DashboardTopbar } from '@/components/dashboard-topbar'
import { DashboardHeader } from '@/components/dashboard-header'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faPhone, faEnvelope, faUser, faImage, faLock, faSpinner, faCheck, faArrowRight, faArrowLeft, faCalendar, faBell, faDownload, faShieldAlt, faCreditCard, faIdCard, faDesktop, faMobile, faTrash } from '@fortawesome/free-solid-svg-icons'
import { RippleButton } from '@/components/ripple-button'
import { useAuth } from '@/hooks/useAuth'
import { changePhone, requestEmailChangeCode, changeEmail, changeName, changeAvatar, requestPasswordChangeCode, changePassword, getTrustedDevices, removeTrustedDevice, removeAllTrustedDevices, TrustedDevice, getSessions, revokeSession, revokeAllSessions, Session } from '@/lib/auth'
import { validatePassword } from '@/lib/passwordValidator'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { apiPut } from '@/lib/api'
import { useNotifications } from '@/hooks/useNotifications'
import { usePWA } from '@/hooks/usePWA'
import { Checkbox } from '@/components/ui/checkbox'
import { getSecurityStatus, enableTransferSecurity, requestDisableSecurityCode, disableTransferSecurity } from '@/lib/security'
import { getUserData } from '@/lib/wallet'
import { PlanSettings } from './PlanSettings'
import { toastSuccess, toastError } from '@/lib/toast'

export default function SettingsPage() {
  const { user, refreshUser } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const {
    isSupported: notificationsSupported,
    permission: notificationPermission,
    preferences: notificationPreferences,
    isSubscribed: isPushSubscribed,
    loading: pushLoading,
    requestPermission: requestNotificationPermission,
    updatePreferences: updateNotificationPreferences,
    subscribeToPush,
    unsubscribeFromPush,
  } = useNotifications()
  const { isInstallable, isInstalled, install: installPWA } = usePWA()

  // Estado para controlar aba ativa
  type SettingsTab = 'info' | 'plans' | 'security' | 'notifications'
  const [activeTab, setActiveTab] = useState<SettingsTab>('info')

  // Estados para cada seção
  const [activeSection, setActiveSection] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Estados dos formulários
  const [phone, setPhone] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [emailCode, setEmailCode] = useState('')
  const [emailStep, setEmailStep] = useState<'form' | 'code'>('form')
  const [fullName, setFullName] = useState('')
  const [fullNameError, setFullNameError] = useState<string | null>(null)
  const [birthDate, setBirthDate] = useState('')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordCode, setPasswordCode] = useState('')
  const [passwordStep, setPasswordStep] = useState<'form' | 'code'>('form')
  const [forgotPassword, setForgotPassword] = useState(false)
  const [passwordValidation, setPasswordValidation] = useState<{ valid: boolean; errors: string[] }>({ valid: true, errors: [] })

  // Limites de caracteres
  const MAX_NAME_LENGTH = 100
  const MAX_PHONE_LENGTH = 15

  // Validar nome completo (pelo menos primeiro e último nome)
  const validateFullName = (name: string): { valid: boolean; error: string | null } => {
    const trimmed = name.trim()
    if (!trimmed) {
      return { valid: false, error: 'Nome é obrigatório' }
    }
    const nameParts = trimmed.split(/\s+/).filter(part => part.length > 0)
    if (nameParts.length < 2) {
      return { valid: false, error: 'Informe nome e sobrenome' }
    }
    if (nameParts.some(part => part.length < 2)) {
      return { valid: false, error: 'Cada parte do nome deve ter pelo menos 2 caracteres' }
    }
    return { valid: true, error: null }
  }

  // Estados de segurança de transferências
  const [transferSecurityEnabled, setTransferSecurityEnabled] = useState(false)
  const [securityStep, setSecurityStep] = useState<'form' | 'code'>('form')
  const [securityCode, setSecurityCode] = useState('')



  // Estado de dispositivos confiáveis
  const [trustedDevices, setTrustedDevices] = useState<TrustedDevice[]>([])
  const [loadingDevices, setLoadingDevices] = useState(false)

  // Estado de sessões ativas
  const [sessions, setSessions] = useState<Session[]>([])
  const [loadingSessions, setLoadingSessions] = useState(false)

  // Inicializar valores quando o usuário carregar
  useEffect(() => {
    if (user) {
      setPhone(user.phone || '')
      setFullName(user.fullName || '')
      if (user.birthDate) {
        const date = new Date(user.birthDate)
        setBirthDate(date.toISOString().split('T')[0])
      }

      // Sincronizar configurações do usuário


      if (user.transferSecurityEnabled !== undefined) {
        setTransferSecurityEnabled(user.transferSecurityEnabled)
      }
    }
  }, [user])

  // Carregar dispositivos confiáveis e sessões
  useEffect(() => {
    // Aguardar um pouco e só carregar se o usuário estiver disponível
    const loadData = async () => {
      // Pequeno delay para garantir que o token foi processado após login
      await new Promise(resolve => setTimeout(resolve, 300))

      if (user) {
        loadTrustedDevices()
        loadSessions()
      }
    }

    loadData()
  }, [user?._id])

  const loadTrustedDevices = async () => {
    try {
      setLoadingDevices(true)
      const response = await getTrustedDevices()
      if (response.success) {
        setTrustedDevices(response.data)
      }
    } catch (error: any) {
      // Ignorar erros 401 silenciosamente (token ainda sendo processado)
      if (error?.status === 401) {
        return
      }
      console.error('Erro ao carregar dispositivos confiáveis:', error)
    } finally {
      setLoadingDevices(false)
    }
  }

  const handleRemoveDevice = async (deviceId: string) => {
    try {
      setLoading(true)
      await removeTrustedDevice(deviceId)
      await loadTrustedDevices()
      toastSuccess('Dispositivo removido com sucesso')
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erro ao remover dispositivo')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveAllDevices = async () => {
    if (!confirm('Tem certeza que deseja remover todos os dispositivos confiáveis? Você precisará inserir código em todos os dispositivos novamente.')) {
      return
    }

    try {
      setLoading(true)
      await removeAllTrustedDevices()
      await loadTrustedDevices()
      toastSuccess('Todos os dispositivos foram removidos')
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erro ao remover dispositivos')
    } finally {
      setLoading(false)
    }
  }

  const loadSessions = async () => {
    try {
      setLoadingSessions(true)
      const response = await getSessions()
      if (response.success) {
        setSessions(response.data)
      }
    } catch (error: any) {
      // Ignorar erros 401 silenciosamente (token ainda sendo processado)
      if (error?.status === 401) {
        return
      }
      console.error('Erro ao carregar sessões:', error)
    } finally {
      setLoadingSessions(false)
    }
  }

  const handleRevokeSession = async (sessionId: string) => {
    if (!confirm('Tem certeza que deseja encerrar esta sessão? O usuário será desconectado deste dispositivo.')) {
      return
    }

    try {
      setLoading(true)
      await revokeSession(sessionId)
      await loadSessions()
      toastSuccess('Sessão encerrada com sucesso')
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erro ao encerrar sessão')
    } finally {
      setLoading(false)
    }
  }

  const handleRevokeAllSessions = async () => {
    if (!confirm('Tem certeza que deseja encerrar todas as outras sessões? Você permanecerá logado apenas neste dispositivo.')) {
      return
    }

    try {
      setLoading(true)
      const response = await revokeAllSessions()
      await loadSessions()
      toastSuccess(response.revokedCount ? `${response.revokedCount} sessão(ões) encerrada(s)` : 'Todas as outras sessões foram encerradas')
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erro ao encerrar sessões')
    } finally {
      setLoading(false)
    }
  }



  // Construir URL do avatar
  const getAvatarUrl = () => {
    if (!user?.avatar) return undefined
    if (user.avatar.startsWith('http://') || user.avatar.startsWith('https://')) {
      return user.avatar
    }
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:3001'
    return `${backendUrl}${user.avatar.startsWith('/') ? user.avatar : `/${user.avatar}`}`
  }

  // Obter iniciais do nome
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  const handleChangePhone = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await changePhone(phone)
      await refreshUser()
      toastSuccess('Telefone atualizado com sucesso!')
      setActiveSection(null)
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao atualizar telefone')
    } finally {
      setLoading(false)
    }
  }

  const handleRequestEmailCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await requestEmailChangeCode(newEmail)
      setEmailStep('code')
      toastSuccess('Código enviado para o novo e-mail!')
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao solicitar código')
    } finally {
      setLoading(false)
    }
  }

  const handleChangeEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await changeEmail(newEmail, emailCode)
      await refreshUser()
      toastSuccess('E-mail atualizado com sucesso!')
      setActiveSection(null)
      setEmailStep('form')
      setNewEmail('')
      setEmailCode('')
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao atualizar e-mail')
    } finally {
      setLoading(false)
    }
  }

  const handleChangeName = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validar nome
    const validation = validateFullName(fullName)
    if (!validation.valid) {
      setFullNameError(validation.error)
      return
    }

    setLoading(true)

    try {
      await changeName(fullName)
      await refreshUser()
      toastSuccess('Nome atualizado com sucesso!')
      setActiveSection(null)
      setFullNameError(null)
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao atualizar nome')
    } finally {
      setLoading(false)
    }
  }

  const handleNameChange = (value: string) => {
    // Limitar caracteres
    if (value.length <= MAX_NAME_LENGTH) {
      setFullName(value)
      // Validar em tempo real
      const validation = validateFullName(value)
      setFullNameError(value.length > 0 ? validation.error : null)
    }
  }

  const handlePhoneChange = (value: string) => {
    // Limitar caracteres e permitir apenas números e caracteres de formatação
    const formatted = value.replace(/[^0-9()\s-]/g, '')
    if (formatted.length <= MAX_PHONE_LENGTH) {
      setPhone(formatted)
    }
  }

  const handleChangeBirthDate = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await apiPut('/v1/user/update', { birthDate })
      await refreshUser()
      toastSuccess('Data de nascimento atualizada com sucesso!')
      setActiveSection(null)
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao atualizar data de nascimento')
    } finally {
      setLoading(false)
    }
  }

  const handleChangeAvatar = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!avatarFile) return

    setLoading(true)

    try {
      const response = await changeAvatar(avatarFile)
      // Aguardar um pouco para garantir que o servidor processou
      await new Promise(resolve => setTimeout(resolve, 500))
      // Atualizar o usuário
      await refreshUser()
      // Forçar re-render do avatar adicionando um pequeno delay
      await new Promise(resolve => setTimeout(resolve, 100))
      toastSuccess('Avatar atualizado com sucesso!')
      setActiveSection(null)
      setAvatarFile(null)
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao atualizar avatar')
    } finally {
      setLoading(false)
    }
  }

  const handleRequestPasswordCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    if (!forgotPassword && !oldPassword) {
      toastError('Senha antiga é obrigatória')
      setLoading(false)
      return
    }

    try {
      await requestPasswordChangeCode(forgotPassword ? undefined : oldPassword, forgotPassword)
      setPasswordStep('code')
      toastSuccess('Código enviado para seu e-mail!')
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao solicitar código')
    } finally {
      setLoading(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    const validation = validatePassword(newPassword)
    if (!validation.valid) {
      toastError(validation.errors.join(', '))
      setLoading(false)
      return
    }

    try {
      await changePassword(newPassword, passwordCode)
      await refreshUser()
      toastSuccess('Senha atualizada com sucesso!')
      setActiveSection(null)
      setPasswordStep('form')
      setOldPassword('')
      setNewPassword('')
      setPasswordCode('')
      setForgotPassword(false)
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao atualizar senha')
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordChange = (value: string) => {
    setNewPassword(value)
    setPasswordValidation(validatePassword(value))
  }

  const handleEnableTransferSecurity = async () => {
    setLoading(true)

    try {
      await enableTransferSecurity()
      setTransferSecurityEnabled(true)
      toastSuccess('Segurança de transferências ativada com sucesso!')
      setActiveSection(null)
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao ativar segurança')
    } finally {
      setLoading(false)
    }
  }

  const handleRequestDisableCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await requestDisableSecurityCode()
      setSecurityStep('code')
      toastSuccess('Código enviado para seu e-mail!')
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao solicitar código')
    } finally {
      setLoading(false)
    }
  }

  const handleDisableTransferSecurity = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await disableTransferSecurity(securityCode)
      setTransferSecurityEnabled(false)
      toastSuccess('Segurança de transferências desativada com sucesso!')
      setActiveSection(null)
      setSecurityStep('form')
      setSecurityCode('')
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao desativar segurança')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-background">
      <SidebarDashboard open={sidebarOpen} onOpenChange={setSidebarOpen} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <DashboardTopbar onOpenSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main data-dashboard className="flex-1 overflow-auto">
          <div className="p-6 lg:p-8">
            <DashboardHeader />

            {/* Navegação por Abas */}
            <div className="mt-6 flex flex-wrap gap-2 border-b border-foreground/10 pb-4">
              <button
                onClick={() => setActiveTab('info')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'info'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-foreground/5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground'
                  }`}
              >
                <FontAwesomeIcon icon={faUser} className="h-4 w-4" />
                Informações
              </button>
              <button
                onClick={() => setActiveTab('plans')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'plans'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-foreground/5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground'
                  }`}
              >
                <FontAwesomeIcon icon={faCreditCard} className="h-4 w-4" />
                Taxas e Planos
              </button>
              <button
                onClick={() => setActiveTab('security')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'security'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-foreground/5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground'
                  }`}
              >
                <FontAwesomeIcon icon={faShieldAlt} className="h-4 w-4" />
                Segurança
              </button>
              <button
                onClick={() => setActiveTab('notifications')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'notifications'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-foreground/5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground'
                  }`}
              >
                <FontAwesomeIcon icon={faBell} className="h-4 w-4" />
                Notificações
              </button>
            </div>

            <div className="mt-6 w-full space-y-6">
              {/* Aba: Informações */}
              {activeTab === 'info' && (
                <div className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm overflow-hidden">
                  <div className="p-4 sm:p-6 border-b border-foreground/10">
                    <h2 className="text-lg font-bold text-foreground">Informações Pessoais</h2>
                    <p className="text-sm text-foreground/60 mt-1">Gerencie suas informações pessoais</p>
                  </div>
                  <div className="p-4 sm:p-6 space-y-6">
                    {/* Avatar Section */}
                    <div>
                      <div className="flex items-center gap-4 mb-3">
                        <Avatar className="h-16 w-16 rounded-xl border-2 border-primary/20">
                          <AvatarImage src={getAvatarUrl()} alt={user?.fullName || 'User'} />
                          <AvatarFallback className="bg-primary/20 text-primary rounded-xl text-lg font-semibold">
                            {user?.fullName ? getInitials(user.fullName) : 'U'}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <h3 className="text-sm font-semibold text-foreground">Avatar</h3>
                          <p className="text-xs text-foreground/60">Altere sua foto de perfil</p>
                        </div>
                        <RippleButton
                          onClick={() => setActiveSection(activeSection === 'avatar' ? null : 'avatar')}
                          className="px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors"
                        >
                          {activeSection === 'avatar' ? 'Cancelar' : 'Alterar'}
                        </RippleButton>
                      </div>
                      {activeSection === 'avatar' && (
                        <form onSubmit={handleChangeAvatar} className="space-y-3">
                          <input
                            type="file"
                            accept="image/*"
                            onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
                            className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary file:text-primary-foreground file:cursor-pointer hover:file:bg-primary/90"
                            disabled={loading}
                            required
                          />
                          {avatarFile && (
                            <p className="text-xs text-foreground/60">Arquivo selecionado: {avatarFile.name}</p>
                          )}
                          <button
                            type="submit"
                            disabled={loading || !avatarFile}
                            className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                          >
                            {loading ? (
                              <>
                                <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                <span>Enviando...</span>
                              </>
                            ) : (
                              <>
                                <FontAwesomeIcon icon={faCheck} />
                                <span>Salvar</span>
                              </>
                            )}
                          </button>
                        </form>
                      )}
                    </div>

                    <Separator />
                    {/* Nome */}
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <FontAwesomeIcon icon={faUser} className="text-foreground/60 w-5 h-5" />
                          <div>
                            <h3 className="text-sm font-semibold text-foreground">Nome</h3>
                            <p className="text-xs text-foreground/60">{user?.fullName || 'Não informado'}</p>
                          </div>
                        </div>
                        <RippleButton
                          onClick={() => setActiveSection(activeSection === 'name' ? null : 'name')}
                          className="px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors"
                        >
                          {activeSection === 'name' ? 'Cancelar' : 'Alterar'}
                        </RippleButton>
                      </div>
                      {activeSection === 'name' && (
                        <form onSubmit={handleChangeName} className="space-y-3">
                          <div>
                            <input
                              type="text"
                              value={fullName}
                              onChange={(e) => handleNameChange(e.target.value)}
                              placeholder="Seu nome completo"
                              maxLength={MAX_NAME_LENGTH}
                              className={`w-full px-4 py-2 rounded-lg bg-foreground/5 border text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 ${fullNameError ? 'border-red-500' : 'border-foreground/10'}`}
                              disabled={loading}
                              required
                            />
                            <div className="flex justify-between mt-1">
                              {fullNameError ? (
                                <p className="text-xs text-red-500">{fullNameError}</p>
                              ) : (
                                <p className="text-xs text-foreground/40">Informe nome e sobrenome</p>
                              )}
                              <p className="text-xs text-foreground/40">{fullName.length}/{MAX_NAME_LENGTH}</p>
                            </div>
                          </div>
                          <button
                            type="submit"
                            disabled={loading || !!fullNameError}
                            className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                          >
                            {loading ? (
                              <>
                                <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                <span>Salvando...</span>
                              </>
                            ) : (
                              <>
                                <FontAwesomeIcon icon={faCheck} />
                                <span>Salvar</span>
                              </>
                            )}
                          </button>
                        </form>
                      )}
                    </div>

                    <Separator />

                    {/* Data de Nascimento */}
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <FontAwesomeIcon icon={faCalendar} className="text-foreground/60 w-5 h-5" />
                          <div>
                            <h3 className="text-sm font-semibold text-foreground">Data de Nascimento</h3>
                            <p className="text-xs text-foreground/60">
                              {user?.birthDate ? new Date(user.birthDate).toLocaleDateString('pt-BR') : 'Não informado'}
                            </p>
                          </div>
                        </div>
                        <RippleButton
                          onClick={() => setActiveSection(activeSection === 'birthdate' ? null : 'birthdate')}
                          className="px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors"
                        >
                          {activeSection === 'birthdate' ? 'Cancelar' : 'Alterar'}
                        </RippleButton>
                      </div>
                      {activeSection === 'birthdate' && (
                        <form onSubmit={handleChangeBirthDate} className="space-y-3">
                          <input
                            type="date"
                            value={birthDate}
                            onChange={(e) => setBirthDate(e.target.value)}
                            className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
                            disabled={loading}
                            required
                          />
                          <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                          >
                            {loading ? (
                              <>
                                <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                <span>Salvando...</span>
                              </>
                            ) : (
                              <>
                                <FontAwesomeIcon icon={faCheck} />
                                <span>Salvar</span>
                              </>
                            )}
                          </button>
                        </form>
                      )}
                    </div>

                    <Separator />

                    {/* Telefone */}
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <FontAwesomeIcon icon={faPhone} className="text-foreground/60 w-5 h-5" />
                          <div>
                            <h3 className="text-sm font-semibold text-foreground">Telefone</h3>
                            <p className="text-xs text-foreground/60">{user?.phone || 'Não informado'}</p>
                          </div>
                        </div>
                        <RippleButton
                          onClick={() => setActiveSection(activeSection === 'phone' ? null : 'phone')}
                          className="px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors"
                        >
                          {activeSection === 'phone' ? 'Cancelar' : 'Alterar'}
                        </RippleButton>
                      </div>
                      {activeSection === 'phone' && (
                        <form onSubmit={handleChangePhone} className="space-y-3">
                          <div>
                            <input
                              type="tel"
                              value={phone}
                              onChange={(e) => handlePhoneChange(e.target.value)}
                              placeholder="(00) 00000-0000"
                              maxLength={MAX_PHONE_LENGTH}
                              className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
                              disabled={loading}
                              required
                            />
                            <div className="flex justify-end mt-1">
                              <p className="text-xs text-foreground/40">{phone.length}/{MAX_PHONE_LENGTH}</p>
                            </div>
                          </div>
                          <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                          >
                            {loading ? (
                              <>
                                <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                <span>Salvando...</span>
                              </>
                            ) : (
                              <>
                                <FontAwesomeIcon icon={faCheck} />
                                <span>Salvar</span>
                              </>
                            )}
                          </button>
                        </form>
                      )}
                    </div>

                    <Separator />

                    {/* CPF */}
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <FontAwesomeIcon icon={faIdCard} className="text-foreground/60 w-5 h-5" />
                          <div>
                            <h3 className="text-sm font-semibold text-foreground">CPF</h3>
                            <p className="text-xs text-foreground/60">
                              {user?.taxID
                                ? (() => {
                                  const numbers = user.taxID.replace(/\D/g, '')
                                  if (numbers.length === 11) {
                                    return numbers.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
                                  } else if (numbers.length === 14) {
                                    return numbers.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')
                                  }
                                  return user.taxID
                                })()
                                : 'Não informado'}
                            </p>
                          </div>
                        </div>
                        <div className="px-3 py-1 bg-foreground/5 rounded-lg text-xs text-foreground/60">
                          Somente leitura
                        </div>
                      </div>
                    </div>

                    <Separator />

                    {/* E-mail */}
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <FontAwesomeIcon icon={faEnvelope} className="text-foreground/60 w-5 h-5" />
                          <div>
                            <h3 className="text-sm font-semibold text-foreground">E-mail</h3>
                            <p className="text-xs text-foreground/60">{user?.email || 'Não informado'}</p>
                          </div>
                        </div>
                        <RippleButton
                          onClick={() => {
                            setActiveSection(activeSection === 'email' ? null : 'email')
                            setEmailStep('form')
                            setNewEmail('')
                            setEmailCode('')
                          }}
                          className="px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors"
                        >
                          {activeSection === 'email' ? 'Cancelar' : 'Alterar'}
                        </RippleButton>
                      </div>
                      {activeSection === 'email' && (
                        <div className="space-y-3">
                          {emailStep === 'form' ? (
                            <form onSubmit={handleRequestEmailCode} className="space-y-3">
                              <input
                                type="email"
                                value={newEmail}
                                onChange={(e) => setNewEmail(e.target.value)}
                                placeholder="novo@email.com"
                                className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
                                disabled={loading}
                                required
                              />
                              <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                              >
                                {loading ? (
                                  <>
                                    <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                    <span>Enviando...</span>
                                  </>
                                ) : (
                                  <>
                                    <FontAwesomeIcon icon={faArrowRight} />
                                    <span>Enviar Código</span>
                                  </>
                                )}
                              </button>
                            </form>
                          ) : (
                            <form onSubmit={handleChangeEmail} className="space-y-3">
                              <p className="text-xs text-foreground/60">Código enviado para {newEmail}</p>
                              <input
                                type="text"
                                value={emailCode}
                                onChange={(e) => setEmailCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                placeholder="000000"
                                className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 text-center text-2xl tracking-widest"
                                disabled={loading}
                                maxLength={6}
                                required
                              />
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEmailStep('form')
                                    setEmailCode('')
                                  }}
                                  disabled={loading}
                                  className="flex-1 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                  <FontAwesomeIcon icon={faArrowLeft} />
                                  <span>Voltar</span>
                                </button>
                                <button
                                  type="submit"
                                  disabled={loading}
                                  className="flex-1 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                  {loading ? (
                                    <>
                                      <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                      <span>Verificando...</span>
                                    </>
                                  ) : (
                                    <>
                                      <FontAwesomeIcon icon={faCheck} />
                                      <span>Verificar</span>
                                    </>
                                  )}
                                </button>
                              </div>
                            </form>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

              )}

              {/* Aba: Taxas e Planos */}
              {activeTab === 'plans' && (
                <div className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm overflow-hidden">
                  <div className="p-4 sm:p-6 border-b border-foreground/10">
                    <h2 className="text-lg font-bold text-foreground">Taxas e Planos</h2>
                    <p className="text-sm text-foreground/60 mt-1">Gerencie seu plano e configurações automáticas</p>
                  </div>
                  <div className="p-4 sm:p-6">
                    <PlanSettings />
                  </div>
                </div>
              )}

              {/* Aba: Notificações */}
              {activeTab === 'notifications' && (
                <div className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm overflow-hidden">
                  <div className="p-4 sm:p-6 border-b border-foreground/10">
                    <h2 className="text-lg font-bold text-foreground">Notificações</h2>
                    <p className="text-sm text-foreground/60 mt-1">Configure suas preferências de notificações</p>
                  </div>
                  <div className="p-4 sm:p-6">
                    <div>

                      {!notificationsSupported && (
                        <p className="text-xs text-foreground/60 mb-3">
                          Seu navegador não suporta notificações.
                        </p>
                      )}

                      {notificationsSupported && notificationPermission !== 'granted' && (
                        <div className="mb-4 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                          <p className="text-sm text-foreground/80 mb-2">
                            Para receber notificações, você precisa permitir o acesso.
                          </p>
                          <RippleButton
                            onClick={async () => {
                              const granted = await requestNotificationPermission()
                              if (granted) {
                                toastSuccess('Permissão concedida! Agora você pode ativar as notificações.')
                              } else {
                                toastError('Permissão negada. Por favor, permita notificações nas configurações do navegador.')
                              }
                            }}
                            className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
                          >
                            Solicitar Permissão
                          </RippleButton>
                        </div>
                      )}

                      {notificationsSupported && notificationPermission === 'granted' && (
                        <div className="space-y-4">
                          <div className="flex items-center justify-between p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                            <div className="flex items-center gap-3">
                              <FontAwesomeIcon icon={faBell} className="text-foreground/60 w-5 h-5" />
                              <div>
                                <p className="text-sm font-medium text-foreground">Ativar Notificações</p>
                                <p className="text-xs text-foreground/60">Receba notificações sobre suas transações</p>
                              </div>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                              <input
                                type="checkbox"
                                checked={notificationPreferences.enabled}
                                onChange={(e) => {
                                  updateNotificationPreferences({ enabled: e.target.checked })
                                  toastSuccess('Preferências salvas!')
                                }}
                                className="sr-only peer"
                              />
                              <div className="w-11 h-6 bg-foreground/20 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                            </label>
                          </div>

                          {notificationPreferences.enabled && (
                            <div className="space-y-3 pl-4 border-l-2 border-primary/20">
                              <div className="flex items-center justify-between p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                                <div>
                                  <p className="text-sm font-medium text-foreground">Pagamento Recebido</p>
                                  <p className="text-xs text-foreground/60">Notificar quando receber um pagamento</p>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={notificationPreferences.paymentReceived}
                                    onChange={(e) => {
                                      updateNotificationPreferences({ paymentReceived: e.target.checked })
                                      toastSuccess('Preferências salvas!')
                                    }}
                                    className="sr-only peer"
                                  />
                                  <div className="w-11 h-6 bg-foreground/20 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                                </label>
                              </div>

                              <div className="flex items-center justify-between p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                                <div>
                                  <p className="text-sm font-medium text-foreground">Transferência Realizada</p>
                                  <p className="text-xs text-foreground/60">Notificar quando um saque for concluído</p>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={notificationPreferences.withdrawCompleted}
                                    onChange={(e) => {
                                      updateNotificationPreferences({ withdrawCompleted: e.target.checked })
                                      toastSuccess('Preferências salvas!')
                                    }}
                                    className="sr-only peer"
                                  />
                                  <div className="w-11 h-6 bg-foreground/20 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                                </label>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Aba: Segurança */}
              {activeTab === 'security' && (
                <>
                  <div className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm overflow-hidden">
                    <div className="p-4 sm:p-6 border-b border-foreground/10">
                      <h2 className="text-lg font-bold text-foreground">Segurança da Conta</h2>
                      <p className="text-sm text-foreground/60 mt-1">Gerencie a segurança da sua conta</p>
                    </div>
                    <div className="p-4 sm:p-6 space-y-6">
                      {/* Senha */}
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <FontAwesomeIcon icon={faLock} className="text-foreground/60 w-5 h-5" />
                            <div>
                              <h3 className="text-sm font-semibold text-foreground">Senha</h3>
                              <p className="text-xs text-foreground/60">••••••••</p>
                            </div>
                          </div>
                          <RippleButton
                            onClick={() => {
                              setActiveSection(activeSection === 'password' ? null : 'password')
                              setPasswordStep('form')
                              setOldPassword('')
                              setNewPassword('')
                              setPasswordCode('')
                              setForgotPassword(false)
                            }}
                            className="px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors"
                          >
                            {activeSection === 'password' ? 'Cancelar' : 'Alterar'}
                          </RippleButton>
                        </div>
                        {activeSection === 'password' && (
                          <div className="space-y-3">
                            {passwordStep === 'form' ? (
                              <form onSubmit={handleRequestPasswordCode} className="space-y-3">
                                {!forgotPassword && (
                                  <input
                                    type="password"
                                    value={oldPassword}
                                    onChange={(e) => setOldPassword(e.target.value)}
                                    placeholder="Senha antiga"
                                    autoComplete="current-password"
                                    className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    disabled={loading}
                                    required={!forgotPassword}
                                  />
                                )}
                                <div className="p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                                  <Checkbox
                                    id="forgotPassword"
                                    checked={forgotPassword}
                                    onCheckedChange={(checked) => setForgotPassword(checked === true)}
                                    label="Esqueci minha senha"
                                    disabled={loading}
                                  />
                                </div>
                                <button
                                  type="submit"
                                  disabled={loading}
                                  className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                  {loading ? (
                                    <>
                                      <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                      <span>Enviando...</span>
                                    </>
                                  ) : (
                                    <>
                                      <FontAwesomeIcon icon={faArrowRight} />
                                      <span>Enviar Código</span>
                                    </>
                                  )}
                                </button>
                              </form>
                            ) : (
                              <form onSubmit={handleChangePassword} className="space-y-3">
                                <p className="text-xs text-foreground/60">Código enviado para {user?.email}</p>
                                <input
                                  type="text"
                                  value={passwordCode}
                                  onChange={(e) => setPasswordCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                  placeholder="000000"
                                  className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 text-center text-2xl tracking-widest"
                                  disabled={loading}
                                  maxLength={6}
                                  required
                                />
                                <input
                                  type="password"
                                  value={newPassword}
                                  onChange={(e) => handlePasswordChange(e.target.value)}
                                  placeholder="Nova senha"
                                  autoComplete="new-password"
                                  className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
                                  disabled={loading}
                                  required
                                />
                                {!passwordValidation.valid && passwordValidation.errors.length > 0 && (
                                  <div className="text-xs text-red-500 space-y-1">
                                    {passwordValidation.errors.map((err, idx) => (
                                      <p key={idx}>• {err}</p>
                                    ))}
                                  </div>
                                )}
                                <div className="flex gap-2">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setPasswordStep('form')
                                      setPasswordCode('')
                                      setNewPassword('')
                                    }}
                                    disabled={loading}
                                    className="flex-1 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                  >
                                    <FontAwesomeIcon icon={faArrowLeft} />
                                    <span>Voltar</span>
                                  </button>
                                  <button
                                    type="submit"
                                    disabled={loading || !passwordValidation.valid}
                                    className="flex-1 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                  >
                                    {loading ? (
                                      <>
                                        <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                        <span>Verificando...</span>
                                      </>
                                    ) : (
                                      <>
                                        <FontAwesomeIcon icon={faCheck} />
                                        <span>Verificar</span>
                                      </>
                                    )}
                                  </button>
                                </div>
                              </form>
                            )}
                          </div>
                        )}
                      </div>

                      <Separator />

                      {/* Segurança de Transferências */}
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <FontAwesomeIcon icon={faShieldAlt} className="text-foreground/60 w-5 h-5" />
                            <div>
                              <h3 className="text-sm font-semibold text-foreground">Segurança de Transferências</h3>
                              <p className="text-xs text-foreground/60">
                                {transferSecurityEnabled
                                  ? 'Ativada - Todas as transferências requerem código por e-mail'
                                  : 'Desativada - Transferências são processadas sem verificação'}
                              </p>
                            </div>
                          </div>
                          <RippleButton
                            onClick={() => {
                              if (transferSecurityEnabled) {
                                setActiveSection(activeSection === 'transfer-security' ? null : 'transfer-security')
                                setSecurityStep('form')
                                setSecurityCode('')
                              } else {
                                handleEnableTransferSecurity()
                              }
                            }}
                            className="px-4 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors"
                          >
                            {transferSecurityEnabled
                              ? (activeSection === 'transfer-security' ? 'Cancelar' : 'Desativar')
                              : 'Ativar'}
                          </RippleButton>
                        </div>
                        {activeSection === 'transfer-security' && transferSecurityEnabled && (
                          <div className="space-y-3">
                            {securityStep === 'form' ? (
                              <form onSubmit={handleRequestDisableCode} className="space-y-3">
                                <p className="text-xs text-foreground/60">
                                  Para desativar a segurança de transferências, você precisa confirmar com um código enviado por e-mail.
                                </p>
                                <button
                                  type="submit"
                                  disabled={loading}
                                  className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                  {loading ? (
                                    <>
                                      <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                      <span>Enviando...</span>
                                    </>
                                  ) : (
                                    <>
                                      <FontAwesomeIcon icon={faArrowRight} />
                                      <span>Enviar Código</span>
                                    </>
                                  )}
                                </button>
                              </form>
                            ) : (
                              <form onSubmit={handleDisableTransferSecurity} className="space-y-3">
                                <p className="text-xs text-foreground/60">Código enviado para {user?.email}</p>
                                <input
                                  type="text"
                                  value={securityCode}
                                  onChange={(e) => setSecurityCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                  placeholder="000000"
                                  className="w-full px-4 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 text-center text-2xl tracking-widest"
                                  disabled={loading}
                                  maxLength={6}
                                  required
                                />
                                <div className="flex gap-2">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSecurityStep('form')
                                      setSecurityCode('')
                                    }}
                                    disabled={loading}
                                    className="flex-1 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                  >
                                    <FontAwesomeIcon icon={faArrowLeft} />
                                    <span>Voltar</span>
                                  </button>
                                  <button
                                    type="submit"
                                    disabled={loading}
                                    className="flex-1 py-2 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                  >
                                    {loading ? (
                                      <>
                                        <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                                        <span>Desativando...</span>
                                      </>
                                    ) : (
                                      <>
                                        <FontAwesomeIcon icon={faCheck} />
                                        <span>Desativar</span>
                                      </>
                                    )}
                                  </button>
                                </div>
                              </form>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Dispositivos Confiáveis */}
                  <div className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm overflow-hidden">
                    <div className="p-4 sm:p-6 border-b border-foreground/10">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <h2 className="text-lg font-bold text-foreground">Dispositivos Confiáveis</h2>
                          <p className="text-sm text-foreground/60 mt-1">Gerencie os dispositivos que não precisam de código de verificação</p>
                        </div>
                        {trustedDevices.length > 0 && (
                          <RippleButton
                            onClick={handleRemoveAllDevices}
                            className="w-full sm:w-auto px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-lg text-sm transition-colors"
                            disabled={loading}
                          >
                            Remover Todos
                          </RippleButton>
                        )}
                      </div>
                    </div>
                    <div className="p-4 sm:p-6">
                      {loadingDevices ? (
                        <div className="flex items-center justify-center py-8">
                          <FontAwesomeIcon icon={faSpinner} className="w-5 h-5 animate-spin text-foreground/60" />
                        </div>
                      ) : trustedDevices.length === 0 ? (
                        <div className="text-center py-8">
                          <FontAwesomeIcon icon={faDesktop} className="w-12 h-12 text-foreground/30 mb-3" />
                          <p className="text-sm text-foreground/60">Nenhum dispositivo confiável</p>
                          <p className="text-xs text-foreground/40 mt-1">Ao fazer login e marcar "Confiar neste dispositivo", ele aparecerá aqui</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {trustedDevices.map((device) => (
                            <div
                              key={device.id}
                              className="flex items-center justify-between p-4 rounded-lg bg-foreground/5 border border-foreground/10 overflow-hidden">
                              <div className="flex items-center gap-3 flex-1 min-w-0 overflow-hidden">
                                <FontAwesomeIcon
                                  icon={device.userAgent?.includes('Mobile') ? faMobile : faDesktop}
                                  className="w-5 h-5 text-foreground/60 flex-shrink-0"
                                />
                                <div className="flex-1 min-w-0">
                                  <h3 className="text-sm font-semibold text-foreground truncate">
                                    {device.deviceName || 'Dispositivo desconhecido'}
                                  </h3>
                                  <p className="text-xs text-foreground/60 truncate">
                                    {device.userAgent || 'N/A'}
                                  </p>
                                  <p className="text-xs text-foreground/40 mt-1 truncate">
                                    Último uso: {new Date(device.lastUsedAt).toLocaleDateString('pt-BR', {
                                      day: '2-digit',
                                      month: '2-digit',
                                      year: 'numeric'
                                    })}
                                  </p>
                                </div>
                              </div>
                              <button
                                onClick={() => handleRemoveDevice(device.id)}
                                disabled={loading}
                                className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 ml-2"
                                title="Remover dispositivo"
                              >
                                <FontAwesomeIcon icon={faTrash} className="w-4 h-4" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Sessões Ativas */}
                  <div className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm overflow-hidden">
                    <div className="p-4 sm:p-6 border-b border-foreground/10">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <h2 className="text-lg font-bold text-foreground">Sessões Ativas</h2>
                          <p className="text-sm text-foreground/60 mt-1">Gerencie suas sessões logadas em diferentes dispositivos</p>
                        </div>
                        {sessions.filter(s => !s.isCurrent).length > 0 && (
                          <RippleButton
                            onClick={handleRevokeAllSessions}
                            className="w-full sm:w-auto px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-lg text-sm transition-colors"
                            disabled={loading}
                          >
                            Encerrar Outras Sessões
                          </RippleButton>
                        )}
                      </div>
                    </div>
                    <div className="p-4 sm:p-6">
                      {loadingSessions ? (
                        <div className="flex items-center justify-center py-8">
                          <FontAwesomeIcon icon={faSpinner} className="w-5 h-5 animate-spin text-foreground/60" />
                        </div>
                      ) : sessions.length === 0 ? (
                        <div className="text-center py-8">
                          <FontAwesomeIcon icon={faDesktop} className="w-12 h-12 text-foreground/30 mb-3" />
                          <p className="text-sm text-foreground/60">Nenhuma sessão ativa</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {sessions.map((session) => (
                            <div
                              key={session.id}
                              className={`flex items-center justify-between p-4 rounded-lg border overflow-hidden ${session.isCurrent
                                ? 'bg-primary/10 border-primary/30'
                                : 'bg-foreground/5 border-foreground/10'
                                }`}>
                              <div className="flex items-center gap-3 flex-1 min-w-0 overflow-hidden">
                                <FontAwesomeIcon
                                  icon={session.userAgent?.includes('Mobile') ? faMobile : faDesktop}
                                  className={`w-5 h-5 flex-shrink-0 ${session.isCurrent ? 'text-primary' : 'text-foreground/60'}`}
                                />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <h3 className="text-sm font-semibold text-foreground truncate max-w-[150px] sm:max-w-none">
                                      {session.deviceName || 'Dispositivo desconhecido'}
                                    </h3>
                                    {session.isCurrent && (
                                      <span className="px-2 py-0.5 text-xs font-medium bg-primary/20 text-primary rounded flex-shrink-0">
                                        Atual
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-xs text-foreground/60 truncate">
                                    {session.userAgent || 'N/A'}
                                  </p>
                                  <p className="text-xs text-foreground/40 mt-1 truncate">
                                    <span className="hidden sm:inline">IP: {session.ip} • </span>{new Date(session.lastActivity).toLocaleDateString('pt-BR', {
                                      day: '2-digit',
                                      month: '2-digit',
                                      year: 'numeric'
                                    })}
                                  </p>
                                </div>
                              </div>
                              {!session.isCurrent && (
                                <button
                                  onClick={() => handleRevokeSession(session.id)}
                                  disabled={loading}
                                  className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 ml-2"
                                  title="Encerrar sessão"
                                >
                                  <FontAwesomeIcon icon={faTrash} className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                </>
              )}
            </div>
          </div>
        </main>
      </div >
    </div >
  )
}


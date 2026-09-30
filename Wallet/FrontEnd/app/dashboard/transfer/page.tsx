'use client'

import { useState, useEffect } from 'react'
import { SidebarDashboard } from '@/components/sidebar-dashboard'
import { DashboardTopbar } from '@/components/dashboard-topbar'
import { DashboardHeader } from '@/components/dashboard-header'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faQrcode, faSpinner, faWallet, faArrowUp, faEnvelope, faExchangeAlt, faKey, faDollarSign, faAlignLeft, faEye, faEyeSlash } from '@fortawesome/free-solid-svg-icons'
import { RippleButton } from '@/components/ripple-button'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { createWithdraw, createInternalTransfer, getBalance } from '@/lib/wallet'
import { useRouter } from 'next/navigation'
import { TransactionModal } from '@/components/transaction-modal'
import { Checkbox } from '@/components/ui/checkbox'
import { TransferVerificationModal } from '@/components/transfer-verification-modal'
import { getSecurityStatus, type SecurityStatusResponse } from '@/lib/security'
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuth } from '@/hooks/useAuth'

export default function TransferPage() {
  const { user } = useAuth() // Usar useAuth para manter estado do usuário sincronizado
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [transferType, setTransferType] = useState<'pix' | 'internal'>('pix')
  const [recipientEmail, setRecipientEmail] = useState('')
  const [pixKey, setPixKey] = useState('')
  const [pixKeyType, setPixKeyType] = useState<'CPF' | 'CNPJ' | 'EMAIL' | 'PHONE' | 'RANDOM'>('CPF')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [coverFee, setCoverFee] = useState(false)
  const [balance, setBalance] = useState<number | null>(null)
  const [showBalance, setShowBalance] = useState(true)
  const [transactionFee, setTransactionFee] = useState<number | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalStatus, setModalStatus] = useState<'success' | 'error' | 'loading'>('loading')
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [withdrawData, setWithdrawData] = useState<any>(null)
  const [verificationModalOpen, setVerificationModalOpen] = useState(false)
  const [transferSecurityEnabled, setTransferSecurityEnabled] = useState(false)
  const [verificationCode, setVerificationCode] = useState<string | null>(null)
  const [pendingWithdraw, setPendingWithdraw] = useState<{
    id: string
    status: string
    value: number
    createdAt: string
  } | null>(null)
  const router = useRouter()

  const parseAmount = (value: string) => {
    if (!value) return 0
    // Remover separadores de milhar e normalizar vírgula para ponto
    const cleaned = value.replace(/\./g, '').replace(',', '.')
    const num = parseFloat(cleaned)
    return Number.isFinite(num) ? num : 0
  }

  useEffect(() => {
    const loadData = async () => {
      try {
        // Verificar se há código PIX salvo do chat da IA (apenas no cliente)
        if (typeof window !== 'undefined') {
          const savedPixKey = localStorage.getItem('amethys_pix_key_to_transfer')
          const savedPixKeyType = localStorage.getItem('amethys_pix_key_type_to_transfer')

          if (savedPixKey) {
            setPixKey(savedPixKey)
            if (savedPixKeyType) {
              setPixKeyType(savedPixKeyType as 'CPF' | 'CNPJ' | 'EMAIL' | 'PHONE' | 'RANDOM')
            } else {
              // Detectar tipo automaticamente se for chave aleatória (32 caracteres)
              if (savedPixKey.length === 32 && /^[a-zA-Z0-9]+$/.test(savedPixKey)) {
                setPixKeyType('RANDOM')
              }
            }
            // Limpar após usar
            localStorage.removeItem('amethys_pix_key_to_transfer')
            localStorage.removeItem('amethys_pix_key_type_to_transfer')
          }
        }

        const [balanceRes, securityRes] = await Promise.all([
          getBalance(),
          getSecurityStatus().catch(() => ({ data: { transferSecurityEnabled: false } }))
        ])

        setBalance(balanceRes.data.balance.total / 100)
        if (balanceRes.data.plan) {
          setTransactionFee(balanceRes.data.plan.transactionFee / 100)
        }

        setTransferSecurityEnabled(securityRes.data.transferSecurityEnabled)
      } catch (error) {
        console.error('Erro ao carregar dados:', error)
      } finally {
        // Sincronizar com tempo de loading da página
        setTimeout(() => {
          setPageLoading(false)
        }, 800)
      }
    }
    loadData()
  }, [])


  const handleTransfer = async (e: React.FormEvent) => {
    e.preventDefault()

    // Se segurança estiver ativada e não tiver código, pedir código primeiro
    if (transferSecurityEnabled && !verificationCode) {
      setVerificationModalOpen(true)
      return
    }

    // Prosseguir com a transferência
    await executeTransfer()
  }

  const executeTransfer = async () => {
    setLoading(true)
    setModalOpen(true)
    setModalStatus('loading')

    try {
      // Garantir valor em número
      const amountNumber = parseAmount(amount)

      let response: any

      if (transferType === 'internal') {
        // Transferência interna (sem taxa, sem limite)
        response = await createInternalTransfer({
          email: recipientEmail,
          amount: amountNumber,
          description: description || undefined
        })
      } else {
        // Transferência PIX
        let keyToSend = pixKey
        if (pixKeyType === 'CPF' || pixKeyType === 'CNPJ' || pixKeyType === 'PHONE') {
          keyToSend = pixKey.replace(/\D/g, '')
        }

        response = await createWithdraw({
          amount: amountNumber,
          pixKey: keyToSend || undefined,
          pixKeyType: pixKeyType,
          description: description || undefined,
          coverFee: coverFee,
          verificationCode: verificationCode || undefined
        })
      }

      setWithdrawData(response.data)
      setModalStatus('success')
      setPixKey('')
      setRecipientEmail('')
      setAmount('')
      setDescription('')
      setCoverFee(false)
      setVerificationCode(null)
      setPendingWithdraw(null)

      // Recarregar saldo
      const res = await getBalance()
      setBalance(res.data.balance.total / 100)
    } catch (error: any) {
      // Verificar se é erro de saque/transferência pendente
      if (error?.pendingWithdrawId || error?.pendingTransferId || error?.message?.includes('em processamento')) {
        setPendingWithdraw({
          id: error.pendingWithdrawId || error.pendingTransferId || 'N/A',
          status: error.pendingWithdrawStatus || 'PROCESSING',
          value: error.pendingWithdrawValue || error.pendingTransferAmount || 0,
          createdAt: error.pendingWithdrawCreatedAt || error.pendingTransferCreatedAt || new Date().toISOString()
        })
        setModalOpen(false)
        setLoading(false)
        return
      }

      setModalStatus('error')
      setErrorMessage(error instanceof Error ? error.message : (error?.message || 'Erro ao realizar transferência'))

      // Se erro for de código inválido, reabrir modal
      if (error instanceof Error && error.message.includes('código')) {
        setVerificationCode(null)
        setVerificationModalOpen(true)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCodeVerified = (code: string) => {
    setVerificationCode(code)
    setVerificationModalOpen(false)
    // Executar transferência após código verificado
    setTimeout(() => {
      executeTransfer()
    }, 100)
  }

  const handleVerificationCancel = () => {
    setVerificationModalOpen(false)
    setVerificationCode(null)
  }

  const formatCurrency = (value: string) => {
    // Remove tudo exceto números, vírgula e ponto
    let cleaned = value.replace(/[^\d,.]/g, '')

    // Garantir apenas um separador decimal
    // Se tiver tanto ponto quanto vírgula, manter apenas o último como decimal
    const lastComma = cleaned.lastIndexOf(',')
    const lastDot = cleaned.lastIndexOf('.')

    // Determinar qual é o separador decimal (o último)
    if (lastComma > lastDot) {
      // Vírgula é decimal, remover pontos de milhar
      cleaned = cleaned.replace(/\./g, '')
    } else if (lastDot > lastComma) {
      // Ponto é decimal, remover vírgulas de milhar e converter para vírgula
      cleaned = cleaned.replace(/,/g, '').replace('.', ',')
    }

    // Garantir máximo 2 casas decimais
    const parts = cleaned.split(',')
    if (parts.length > 1 && parts[1].length > 2) {
      cleaned = parts[0] + ',' + parts[1].substring(0, 2)
    }

    return cleaned
  }

  return (
    <div className="flex h-screen bg-background">
      <TransferVerificationModal
        open={verificationModalOpen}
        onOpenChange={setVerificationModalOpen}
        amount={amount}
        onVerified={handleCodeVerified}
        onCancel={handleVerificationCancel}
      />
      <TransactionModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        type="withdraw"
        status={modalStatus}
        message={modalStatus === 'error' ? errorMessage : undefined}
        details={withdrawData ? {
          amount: withdrawData.value || withdrawData.amount,
          fee: withdrawData.fee || 0,
          netAmount: withdrawData.sent || withdrawData.amount,
          transactionId: withdrawData.id,
          recipientName: withdrawData.recipient?.name,
          recipientEmail: withdrawData.recipient?.email
        } : undefined}
      />
      <SidebarDashboard open={sidebarOpen} onOpenChange={setSidebarOpen} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <DashboardTopbar onOpenSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main data-dashboard className="flex-1 overflow-auto">
          <div className="p-6 lg:p-8 space-y-5">
            <DashboardHeader loading={pageLoading} />

            {pageLoading ? (
              <div className="space-y-5">
                <Skeleton className="h-16 w-full rounded-lg" />
                <Skeleton className="h-12 w-full rounded-lg" />
                <Skeleton className="h-12 w-full rounded-lg" />
                <Skeleton className="h-12 w-full rounded-lg" />
                <Skeleton className="h-12 w-full rounded-lg" />
              </div>
            ) : (
              <>
                {balance !== null && (
                  <div className="bg-foreground/5 p-6 rounded-xl border border-foreground/10 mb-6">
                    <div className="flex items-center justify-between">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <FontAwesomeIcon icon={faWallet} className="w-4 h-4" />
                          <span className="text-sm font-medium">Saldo Disponível</span>
                        </div>
                        <div className="flex items-start">
                          {showBalance ? (
                            <>
                              <span className="text-4xl font-bold text-foreground">
                                R$ {Math.floor(balance).toLocaleString('pt-BR')}
                              </span>
                              <span className="text-lg font-bold text-foreground/70 ml-0.5">
                                ,{String(Math.round((balance % 1) * 100)).padStart(2, '0')}
                              </span>
                            </>
                          ) : (
                            <span className="text-4xl font-bold text-foreground">••••••</span>
                          )}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowBalance(!showBalance)}
                        className="p-2 hover:bg-muted rounded-lg transition-colors"
                      >
                        <FontAwesomeIcon
                          icon={showBalance ? faEye : faEyeSlash}
                          className="w-4 h-4 text-muted-foreground"
                        />
                      </button>
                    </div>
                  </div>
                )}

                {/* Aviso de saque pendente */}
                {pendingWithdraw && (
                  <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-yellow-500/20 flex items-center justify-center">
                        <span className="text-yellow-500 text-sm">⏳</span>
                      </div>
                      <div className="flex-1 space-y-2">
                        <p className="text-sm font-medium text-yellow-500">
                          Transferência em processamento
                        </p>
                        <p className="text-xs text-yellow-500/80">
                          Você já possui uma transferência de <strong>R$ {(pendingWithdraw.value / 100).toFixed(2).replace('.', ',')}</strong> em processamento.
                          Aguarde a conclusão antes de solicitar um novo saque.
                        </p>
                        <div className="flex items-center gap-2 text-xs text-yellow-500/60">
                          <span>ID: {pendingWithdraw.id.substring(0, 8)}...</span>
                          <span>•</span>
                          <span>Status: {pendingWithdraw.status}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => router.push('/dashboard/transactions')}
                          className="text-xs text-yellow-500 hover:text-yellow-400 underline"
                        >
                          Ver extrato completo
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                <div className="bg-foreground/5 p-6 rounded-xl border border-foreground/10">
                  <form onSubmit={handleTransfer} className="space-y-5">
                    {/* Toggle PIX / Interna */}
                    <div className="flex gap-2 mb-4">
                      <button
                        type="button"
                        onClick={() => setTransferType('pix')}
                        className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${transferType === 'pix'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-foreground/10 text-muted-foreground hover:bg-foreground/15'
                          }`}
                      >
                        <FontAwesomeIcon icon={faQrcode} className="w-4 h-4" />
                        PIX
                      </button>
                      <button
                        type="button"
                        onClick={() => setTransferType('internal')}
                        className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${transferType === 'internal'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-foreground/10 text-muted-foreground hover:bg-foreground/15'
                          }`}
                      >
                        <FontAwesomeIcon icon={faExchangeAlt} className="w-4 h-4" />
                        Interna
                      </button>
                    </div>



                    {/* Campos de destino */}
                    <div className="space-y-4">
                      {transferType === 'pix' ? (
                        <>
                          <div className="space-y-2">
                            <label className="text-sm font-medium text-foreground flex items-center gap-2">
                              <FontAwesomeIcon icon={faKey} className="w-3.5 h-3.5 text-muted-foreground" />
                              Tipo de chave PIX
                            </label>
                            <Select value={pixKeyType} onValueChange={(v) => setPixKeyType(v as any)}>
                              <SelectTrigger className="w-full">
                                <SelectValue placeholder="Selecione o tipo" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectGroup>
                                  <SelectLabel>Tipo de chave</SelectLabel>
                                  <SelectItem value="CPF" textValue="CPF">CPF</SelectItem>
                                  <SelectItem value="CNPJ" textValue="CNPJ">CNPJ</SelectItem>
                                  <SelectItem value="EMAIL" textValue="E-mail">E-mail</SelectItem>
                                  <SelectItem value="PHONE" textValue="Telefone">Telefone</SelectItem>
                                  <SelectItem value="RANDOM" textValue="Chave aleatória">Chave aleatória</SelectItem>
                                </SelectGroup>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <label className="text-sm font-medium text-foreground flex items-center gap-2">
                              <FontAwesomeIcon icon={faQrcode} className="w-3.5 h-3.5 text-muted-foreground" />
                              Chave PIX
                            </label>
                            <div className="relative">
                              <FontAwesomeIcon
                                icon={faQrcode}
                                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
                              />
                              <input
                                type="text"
                                value={pixKey}
                                onChange={(e) => setPixKey(e.target.value)}
                                placeholder={
                                  pixKeyType === 'CPF' ? '000.000.000-00' :
                                    pixKeyType === 'CNPJ' ? '00.000.000/0000-00' :
                                      pixKeyType === 'EMAIL' ? 'exemplo@email.com' :
                                        pixKeyType === 'PHONE' ? '(00) 00000-0000' :
                                          'Chave aleatória'
                                }
                                className="w-full pl-10 pr-3 py-3 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 transition-all text-sm"
                                required
                              />
                            </div>
                          </div>
                        </>
                      ) : (
                        /* Transferência interna - email */
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-foreground flex items-center gap-2">
                            <FontAwesomeIcon icon={faEnvelope} className="w-3.5 h-3.5 text-muted-foreground" />
                            Email do destinatário
                          </label>
                          <div className="relative">
                            <FontAwesomeIcon
                              icon={faEnvelope}
                              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
                            />
                            <input
                              type="email"
                              value={recipientEmail}
                              onChange={(e) => setRecipientEmail(e.target.value)}
                              placeholder="usuario@email.com"
                              className="w-full pl-10 pr-3 py-3 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 transition-all text-sm"
                              required
                            />
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Transfira para outra conta Amethys Wallet usando o email
                          </p>
                        </div>
                      )}
                    </div>

                    <Separator />

                    {/* Valor e descrição */}
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground flex items-center gap-2">
                          <FontAwesomeIcon icon={faDollarSign} className="w-3.5 h-3.5 text-muted-foreground" />
                          Valor
                        </label>
                        <div className="relative">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground font-medium">
                            R$
                          </span>
                          <input
                            type="text"
                            value={amount}
                            onChange={(e) => {
                              const formatted = formatCurrency(e.target.value)
                              setAmount(formatted)
                            }}
                            placeholder="0,00"
                            className="w-full pl-10 pr-3 py-3 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 transition-all text-sm"
                            required
                          />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {transferType === 'internal' ? 'Sem valor mínimo para transferências internas' : 'Valor mínimo: R$ 5,00'}
                        </p>
                        {transferType === 'internal' && (
                          <p className="text-xs text-green-400 !mt-0">Sem taxa • Sem limite • Instantânea</p>
                        )}
                        {amount && transactionFee !== null && transferType === 'pix' && (
                          <div className="p-3 rounded-lg bg-foreground/5 border border-foreground/10 space-y-1">
                            {(() => {
                              const fee = Number.isFinite(transactionFee) ? (transactionFee as number) : 0
                              const amountNum = parseAmount(amount)
                              const feeDisplay = `R$ ${fee.toFixed(2).replace('.', ',')}`
                              const sentDisplay = `R$ ${Math.max(0, amountNum - fee).toFixed(2).replace('.', ',')}`
                              const amountDisplay = `R$ ${amountNum.toFixed(2).replace('.', ',')}`
                              const totalDebitedDisplay = `R$ ${(amountNum + fee).toFixed(2).replace('.', ',')}`
                              return (
                                <>
                                  {coverFee ? (
                                    <>
                                      <div className="flex justify-between items-center text-sm">
                                        <span className="text-muted-foreground">Valor enviado:</span>
                                        <span className="text-foreground font-medium">
                                          {amountDisplay}
                                        </span>
                                      </div>
                                      <div className="flex justify-between items-center text-sm">
                                        <span className="text-muted-foreground">Taxa:</span>
                                        <span className="text-foreground font-medium">
                                          {feeDisplay}
                                        </span>
                                      </div>
                                      <div className="flex justify-between items-center pt-2 border-t border-foreground/10">
                                        <span className="text-sm font-medium text-foreground">Total debitado:</span>
                                        <span className="text-sm font-bold text-foreground">
                                          {totalDebitedDisplay}
                                        </span>
                                      </div>
                                    </>
                                  ) : (
                                    <>
                                      <div className="flex justify-between items-center text-sm">
                                        <span className="text-muted-foreground">Taxa:</span>
                                        <span className="text-foreground font-medium">
                                          {feeDisplay}
                                        </span>
                                      </div>
                                      <div className="flex justify-between items-center pt-2 border-t border-foreground/10">
                                        <span className="text-sm font-medium text-foreground">Valor enviado:</span>
                                        <span className="text-sm font-bold text-green-500">
                                          {sentDisplay}
                                        </span>
                                      </div>
                                    </>
                                  )}
                                </>
                              )
                            })()}
                          </div>
                        )}
                      </div>

                      {transferType === 'pix' && (
                        <div className="p-4 rounded-lg bg-foreground/5 border border-foreground/10">
                          <Checkbox
                            id="coverFee"
                            checked={coverFee}
                            onCheckedChange={(checked) => setCoverFee(checked === true)}
                            label="Cobrir taxa"
                            description="O valor digitado será o valor enviado. A taxa será adicionada ao total debitado."
                          />
                        </div>
                      )}

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground flex items-center gap-2">
                          <FontAwesomeIcon icon={faAlignLeft} className="w-3.5 h-3.5 text-muted-foreground" />
                          Descrição <span className="text-muted-foreground font-normal text-xs">(opcional)</span>
                        </label>
                        <input
                          type="text"
                          value={description}
                          onChange={(e) => setDescription(e.target.value)}
                          placeholder="Ex: Pagamento almoço"
                          className="w-full px-3 py-3 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 transition-all text-sm"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={
                        loading ||
                        !amount ||
                        (transferType === 'pix' ? !pixKey : !recipientEmail) ||
                        !!pendingWithdraw ||
                        (transferType === 'pix' && balance !== null && transactionFee !== null && (() => {
                          const fee = Number.isFinite(transactionFee) ? (transactionFee as number) : 0
                          const amountNum = parseAmount(amount)
                          return coverFee ? amountNum + fee > balance : amountNum > balance
                        })()) ||
                        (transferType === 'internal' && balance !== null && parseAmount(amount) > balance)
                      }
                      className="w-full py-3 bg-foreground/10 text-foreground border border-foreground/10 rounded-lg font-medium hover:bg-primary hover:text-white hover:border-primary transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {loading ? (
                        <>
                          <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                          <span>Processando...</span>
                        </>
                      ) : pendingWithdraw ? (
                        <span>Aguarde a transferência pendente</span>
                      ) : (
                        <>
                          <FontAwesomeIcon icon={faArrowUp} className="w-4 h-4" />
                          <span>Transferir</span>
                        </>
                      )}
                    </button>
                  </form>
                </div>

                {/* Espaço após o botão */}
                <div className="h-8" />
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

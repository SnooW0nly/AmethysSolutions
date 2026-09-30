'use client'

import { useState, useEffect, useRef } from 'react'
import { SidebarDashboard } from '@/components/sidebar-dashboard'
import { DashboardTopbar } from '@/components/dashboard-topbar'
import { DashboardHeader } from '@/components/dashboard-header'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faQrcode, faCopy, faSpinner, faCheck, faArrowLeft, faArrowDown, faAlignLeft, faWallet, faEye, faEyeSlash } from '@fortawesome/free-solid-svg-icons'
import { RippleButton } from '@/components/ripple-button'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Checkbox } from '@/components/ui/checkbox'
import { createPayment, CreatePaymentResponse, listPayments, getBalance } from '@/lib/wallet'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { TransactionModal } from '@/components/transaction-modal'
import { useAuth } from '@/hooks/useAuth'

export default function DepositPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [coverFee, setCoverFee] = useState(false)
  const [paymentData, setPaymentData] = useState<CreatePaymentResponse['data'] | null>(null)
  const [copied, setCopied] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalStatus, setModalStatus] = useState<'success' | 'error' | 'loading'>('loading')
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [transactionFee, setTransactionFee] = useState<number | null>(null)
  const [balance, setBalance] = useState<number | null>(null)
  const [showBalance, setShowBalance] = useState(true)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const router = useRouter()
  const { user } = useAuth()

  useEffect(() => {
    const loadData = async () => {
      try {
        const balanceRes = await getBalance()
        if (balanceRes.data.plan?.transactionFee) {
          setTransactionFee(balanceRes.data.plan.transactionFee / 100)
        }
        setBalance(balanceRes.data.balance.total / 100)
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

  const handleDeposit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setPaymentData(null)
    setModalOpen(true)
    setModalStatus('loading')

    try {
      const response = await createPayment({
        value: amount,
        description: description || undefined,
        coverFee: coverFee || undefined
      })

      setPaymentData(response.data)
      setModalStatus('success')
    } catch (error) {
      setModalStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Erro ao criar pagamento')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyPix = () => {
    if (paymentData?.copyPaste) {
      navigator.clipboard.writeText(paymentData.copyPaste)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
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

  const parseAmount = (value: string): number => {
    if (!value) return 0
    const cleaned = value.replace(/\./g, '').replace(',', '.')
    const num = parseFloat(cleaned)
    return isNaN(num) ? 0 : num
  }

  // Polling para verificar status do pagamento
  useEffect(() => {
    if (!paymentData || paymentData.status === 'COMPLETED' || paymentData.status === 'PAID') {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
      return
    }

    // Verificar status a cada 2 segundos para resposta mais rápida
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await listPayments({ limit: 10 })
        const payment = response.data.payments.find(p => p.id === paymentData.id)

        if (payment && (payment.status === 'COMPLETED' || payment.status === 'PAID')) {
          // Atualizar dados do pagamento
          setPaymentData(prev => prev ? {
            ...prev,
            status: 'COMPLETED'
          } : null)

          // Parar polling
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
        }
      } catch (error) {
        console.error('Erro ao verificar status do pagamento:', error)
      }
    }, 2000)

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [paymentData])

  return (
    <div className="flex h-screen bg-background">
      <TransactionModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        type="deposit"
        status={modalStatus}
        message={modalStatus === 'error' ? errorMessage : undefined}
        details={paymentData ? {
          amount: paymentData.value,
          fee: paymentData.fee,
          netAmount: paymentData.netValue,
          transactionId: paymentData.id
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
            ) : paymentData ? (
              <div className="space-y-6">
                <div className="border border-foreground/10 rounded-xl bg-foreground/2 backdrop-blur-sm p-6">
                  <div className="text-center space-y-4">
                    <h2 className="text-xl font-bold text-foreground">
                      {paymentData.status === 'COMPLETED' || paymentData.status === 'PAID'
                        ? 'Pagamento Confirmado!'
                        : 'Pagamento PIX Criado'}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      {paymentData.status === 'COMPLETED' || paymentData.status === 'PAID'
                        ? 'Seu pagamento foi confirmado com sucesso!'
                        : 'Escaneie o QR Code ou copie o código PIX para pagar'}
                    </p>

                    {paymentData.qrcodeUrl && (paymentData.status !== 'COMPLETED' && paymentData.status !== 'PAID') && (
                      <div className="flex justify-center my-6">
                        <div className="p-4 bg-white rounded-lg">
                          <Image
                            src={paymentData.qrcodeUrl}
                            alt="QR Code PIX"
                            width={256}
                            height={256}
                            className="w-64 h-64"
                          />
                        </div>
                      </div>
                    )}

                    {(paymentData.status === 'COMPLETED' || paymentData.status === 'PAID') && (
                      <div className="flex justify-center my-6">
                        <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center">
                          <FontAwesomeIcon icon={faCheck} className="w-10 h-10 text-green-500" />
                        </div>
                      </div>
                    )}

                    {paymentData.copyPaste && (paymentData.status !== 'COMPLETED' && paymentData.status !== 'PAID') && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-foreground">
                          Código PIX (Copiar e Colar)
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={paymentData.copyPaste}
                            readOnly
                            className="flex-1 px-4 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground text-sm font-mono"
                          />
                          <RippleButton
                            onClick={handleCopyPix}
                            className="px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                          >
                            <FontAwesomeIcon icon={copied ? faCheck : faCopy} className="w-4 h-4" />
                          </RippleButton>
                        </div>
                        {copied && (
                          <p className="text-xs text-green-500">Código copiado!</p>
                        )}
                      </div>
                    )}

                    <div className="pt-4 border-t border-foreground/10 space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Valor:</span>
                        <span className="text-sm font-bold text-foreground">
                          R$ {(paymentData.value / 100).toFixed(2).replace('.', ',')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Taxa:</span>
                        <span className="text-sm text-foreground">
                          R$ {(paymentData.fee / 100).toFixed(2).replace('.', ',')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Valor líquido:</span>
                        <span className="text-sm font-bold text-green-500">
                          R$ {(paymentData.netValue / 100).toFixed(2).replace('.', ',')}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Status:</span>
                        <div className="flex items-center gap-2">
                          {paymentData.status === 'COMPLETED' || paymentData.status === 'PAID' ? (
                            <>
                              <FontAwesomeIcon icon={faCheck} className="w-4 h-4 text-green-500" />
                              <span className="text-sm font-semibold text-green-500">
                                Pagamento confirmado!
                              </span>
                            </>
                          ) : (
                            <>
                              <FontAwesomeIcon icon={faSpinner} className="w-4 h-4 text-yellow-500 animate-spin" />
                              <span className="text-sm font-semibold text-yellow-500">
                                Aguardando pagamento...
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <RippleButton
                      onClick={() => {
                        setPaymentData(null)
                        setAmount('')
                        setDescription('')
                        setCoverFee(false)
                      }}
                      className="w-full mt-4 py-3 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
                    >
                      <FontAwesomeIcon icon={faArrowLeft} className="w-4 h-4" />
                      <span>Criar novo pagamento</span>
                    </RippleButton>
                  </div>
                </div>
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

                <div className="bg-foreground/5 p-6 rounded-xl border border-foreground/10">
                  <form onSubmit={handleDeposit} className="space-y-5">
                    {/* Valor e descrição */}
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground flex items-center gap-2">
                          <FontAwesomeIcon icon={faArrowDown} className="w-3.5 h-3.5 text-muted-foreground" />
                          Valor a receber
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
                          Valor mínimo: R$ 1,00 | Valor máximo: R$ 1.000,00
                        </p>
                        {amount && transactionFee !== null && (
                          <div className="p-3 rounded-lg bg-foreground/5 border border-foreground/10 space-y-1 mt-2">
                            {(() => {
                              const fee = Number.isFinite(transactionFee) ? (transactionFee as number) : 0
                              const amountNum = parseAmount(amount)
                              const feeDisplay = `R$ ${fee.toFixed(2).replace('.', ',')}`
                              const receivedDisplay = `R$ ${Math.max(0, amountNum - fee).toFixed(2).replace('.', ',')}`
                              const amountDisplay = `R$ ${amountNum.toFixed(2).replace('.', ',')}`
                              const totalDisplay = `R$ ${(amountNum + fee).toFixed(2).replace('.', ',')}`
                              return (
                                <>
                                  {coverFee ? (
                                    <>
                                      <div className="flex justify-between items-center text-sm">
                                        <span className="text-muted-foreground">Valor a receber:</span>
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
                                        <span className="text-sm font-medium text-foreground">Total do QR Code:</span>
                                        <span className="text-sm font-bold text-foreground">
                                          {totalDisplay}
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
                                        <span className="text-sm font-medium text-foreground">Valor líquido a receber:</span>
                                        <span className="text-sm font-bold text-green-500">
                                          {receivedDisplay}
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

                      <div className="p-4 rounded-lg bg-foreground/5 border border-foreground/10">
                        <Checkbox
                          id="coverFee"
                          checked={coverFee}
                          onCheckedChange={(checked) => setCoverFee(checked === true)}
                          label="Cobrir taxa"
                          description="O valor digitado será o valor líquido recebido. A taxa será adicionada ao total do pagamento."
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground flex items-center gap-2">
                          <FontAwesomeIcon icon={faAlignLeft} className="w-3.5 h-3.5 text-muted-foreground" />
                          Descrição <span className="text-muted-foreground font-normal text-xs">(opcional)</span>
                        </label>
                        <input
                          type="text"
                          value={description}
                          onChange={(e) => setDescription(e.target.value)}
                          placeholder="Ex: Pagamento de serviço"
                          className="w-full px-3 py-3 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 transition-all text-sm"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={loading || !amount}
                      className="w-full py-3 bg-foreground/10 text-foreground border border-foreground/10 rounded-lg font-medium hover:bg-primary hover:text-white hover:border-primary transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {loading ? (
                        <>
                          <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                          <span>Criando pagamento...</span>
                        </>
                      ) : (
                        <>
                          <FontAwesomeIcon icon={faQrcode} />
                          <span>Gerar pagamento</span>
                        </>
                      )}
                    </button>
                  </form>
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

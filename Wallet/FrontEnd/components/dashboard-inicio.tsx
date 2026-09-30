'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faWallet, faArrowUp, faArrowDown, faEye, faEyeSlash, faReceipt, faArrowRight, faPaperPlane, faInbox, faSpinner, faCopy, faCheck, faTimes, faTrash, faHandHoldingDollar, faExchangeAlt, faQrcode } from '@fortawesome/free-solid-svg-icons'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { RippleButton } from './ripple-button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { createPayment, createWithdraw } from '@/lib/wallet'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { TransactionDetailsModal } from './transaction-details-modal'
import { PixModal } from './pix-modal'
import { useNotifications } from '@/hooks/useNotifications'
import { sendAIMessage, parseAIAction, buildSystemContext, cleanContentForDisplay } from '@/lib/ai'
import { useAuth } from '@/hooks/useAuth'
import { useWallet } from '@/components/providers/wallet-provider'

interface DashboardInicioProps {
  loading?: boolean
}

interface TransactionDisplay {
  id: string
  type: 'received' | 'sent'
  transactionType: 'payment' | 'withdraw' | 'internal_transfer_sent' | 'internal_transfer_received' | 'commission'
  description: string
  amount: number
  date: string
  status: string
}

export function DashboardInicio({ loading: externalLoading }: DashboardInicioProps) {
  const { user, loading: authLoading } = useAuth()
  const { balance: walletBalance, payments, withdraws, internalTransfers, loading: walletLoading, refreshWallet } = useWallet()

  const [showBalance, setShowBalance] = useState(true)
  const [aiInput, setAiInput] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [pendingAction, setPendingAction] = useState<{ type: 'create_payment' | 'create_transfer'; data?: any } | null>(null)
  const [aiMessages, setAiMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; copyPaste?: string }>>([])
  const [aiPlaceholderResponse, setAiPlaceholderResponse] = useState('')

  const [transactions, setTransactions] = useState<TransactionDisplay[]>([])
  const [detailsModalOpen, setDetailsModalOpen] = useState(false)
  const [selectedTransactionId, setSelectedTransactionId] = useState<string>('')
  const [selectedTransactionType, setSelectedTransactionType] = useState<'payment' | 'withdraw' | 'internal_transfer_sent' | 'internal_transfer_received' | 'commission'>('payment')
  const [pixModalOpen, setPixModalOpen] = useState(false)
  const [lastPaymentIds, setLastPaymentIds] = useState<Set<string>>(new Set())
  const [lastWithdrawIds, setLastWithdrawIds] = useState<Set<string>>(new Set())
  const [copiedPixKey, setCopiedPixKey] = useState<string | null>(null)
  const [aiEnabled, setAiEnabled] = useState<boolean>(true) // Default true
  const { notifyPaymentReceived, notifyWithdrawCompleted } = useNotifications()

  // Refs for auto-scrolling or other needs could go here
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load AI messages from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedMessages = localStorage.getItem('amethys_ai_messages')
      if (savedMessages) {
        try {
          setAiMessages(JSON.parse(savedMessages))
        } catch (e) {
          console.error('Erro ao carregar mensagens da IA:', e)
        }
      }
    }
  }, [])

  // Save AI messages to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined' && aiMessages.length > 0) {
      localStorage.setItem('amethys_ai_messages', JSON.stringify(aiMessages))
    }
  }, [aiMessages])

  // Process transactions from WalletContext
  useEffect(() => {
    if (!walletLoading && (payments.length > 0 || withdraws.length > 0 || internalTransfers.length > 0)) {
      // Combinar pagamentos e saques em uma lista de transações
      const allTransactions: TransactionDisplay[] = []

      // Adicionar pagamentos completados como recebidos
      payments
        .filter(p => p.status === 'COMPLETED' || p.status === 'PAID' || p.status === 'PENDING' || p.status === 'CANCELLED' || p.status === 'FAILED')
        .forEach(p => {
          allTransactions.push({
            id: p.id,
            type: 'received',
            transactionType: 'payment',
            description: p.description || 'Pagamento recebido',
            amount: (p.netValue || p.value) / 100,
            date: p.createdAt,
            status: p.status
          })
        })

      // Adicionar saques como enviados (incluir todos os status exceto FAILED e EXPIRED)
      withdraws
        .filter(w => w.status !== 'FAILED' && w.status !== 'EXPIRED')
        .forEach(w => {
          allTransactions.push({
            id: w.id,
            type: 'sent',
            transactionType: 'withdraw',
            description: w.description || 'Transferência realizada',
            amount: w.value / 100,
            date: w.createdAt,
            status: w.status
          })
        })


      // Adicionar transferências internas
      internalTransfers.forEach(t => {
        allTransactions.push({
          id: t.id,
          type: t.transactionType === 'internal_transfer_received' ? 'received' : 'sent',
          transactionType: t.transactionType,
          description: t.description || (t.transactionType === 'internal_transfer_received' ? 'Transferência recebida' : 'Transferência enviada'),
          amount: t.amount / 100,
          date: t.date,
          status: t.status
        })
      })

      // Verificar novos pagamentos para notificações
      payments
        .filter(p => (p.status === 'COMPLETED' || p.status === 'PAID') && !lastPaymentIds.has(p.id))
        .forEach(p => {
          notifyPaymentReceived(p.netValue || p.value, p.description)
        })

      // Verificar novos saques para notificações
      withdraws
        .filter(w => w.status === 'COMPLETED' && !lastWithdrawIds.has(w.id))
        .forEach(w => {
          notifyWithdrawCompleted(w.value, w.description)
        })

      // Atualizar IDs conhecidos
      const newPaymentIds = new Set(payments.map(p => p.id))
      const newWithdrawIds = new Set(withdraws.map(w => w.id))
      setLastPaymentIds(newPaymentIds)
      setLastWithdrawIds(newWithdrawIds)

      // Ordenar por data (mais recente primeiro) e pegar as últimas 5
      allTransactions.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      const sortedTransactions = allTransactions.slice(0, 5).map(t => ({
        ...t,
        date: format(new Date(t.date), "dd/MM/yyyy HH:mm", { locale: ptBR })
      }))
      setTransactions(sortedTransactions)
    }
  }, [payments, withdraws, internalTransfers, walletLoading])

  const handleClearHistory = () => {
    setAiMessages([])
    localStorage.removeItem('amethys_ai_messages')
    setAiPlaceholderResponse('')
  }

  const handleAISubmit = async () => {
    if (!aiInput.trim() || aiLoading) return

    const userMessage = aiInput.trim()
    setAiInput('')
    setAiLoading(true)

    try {
      // Construir contexto do sistema completo usando dados do Context
      const userBalance = walletBalance ? walletBalance.balance.total : undefined
      const userPlan = walletBalance?.plan?.name || 'FREE'

      const systemContext = buildSystemContext({
        name: user?.fullName,
        balance: userBalance,
        plan: userPlan,
      })

      // Enviar mensagem para IA
      // Incluir histórico recente para contexto (opcional, mas bom para conversas contínuas)
      const recentMessages = aiMessages.slice(-6).map(m => ({ role: m.role, content: m.content }))

      const response = await sendAIMessage([
        { role: 'assistant', content: systemContext },
        ...recentMessages,
        { role: 'user', content: userMessage },
      ])

      // Adicionar mensagem do usuário ao chat
      setAiMessages(prev => [...prev, { role: 'user', content: userMessage }])

      // Processar ação automaticamente
      const action = response.action || parseAIAction(response.content)

      // Limpar conteúdo removendo JSON para exibição
      const cleanedContent = cleanContentForDisplay(response.content)

      // Se a ação for 'explain', apenas mostrar a resposta da IA sem processar ação
      if (action && action.type === 'explain') {
        // Se houver conteúdo limpo (sem JSON), mostrar. Caso contrário, mostrar mensagem padrão
        const displayContent = cleanedContent || 'Como posso ajudá-lo hoje?'
        setAiMessages(prev => [...prev, { role: 'assistant', content: displayContent }])
        setAiPlaceholderResponse(displayContent)
        setAiLoading(false)
        return
      }

      // Ações informacionais
      if (action && action.type === 'show_balance') {
        // Usar dados do cache se possível, ou forçar refresh
        await refreshWallet()

        if (walletBalance) {
          const current = walletBalance.balance.total / 100
          const msg = `💰 Seu saldo atual é de R$ ${current.toFixed(2).replace('.', ',')}`
          setAiMessages(prev => [...prev, { role: 'assistant', content: msg }])
          setAiPlaceholderResponse(msg)
        } else {
          const msg = 'Não consegui obter seu saldo agora.'
          setAiMessages(prev => [...prev, { role: 'assistant', content: msg }])
          setAiPlaceholderResponse(msg)
        }
      } else if (action && action.type === 'show_last_transactions') {
        await refreshWallet()

        const recentPayments = payments.slice(0, 3).map(p => `+ R$ ${((p.netValue || p.value) / 100).toFixed(2)} ${p.description ? `- ${p.description}` : ''}`)
        const recentWithdraws = withdraws.slice(0, 3).map(w => `- R$ ${(w.value / 100).toFixed(2)} ${w.description ? `- ${w.description}` : ''}`)
        const lines = [...recentPayments, ...recentWithdraws]
        const msg = lines.length ? `🧾 Últimas transações:\n${lines.join('\n')}` : 'Você ainda não possui transações.'
        setAiMessages(prev => [...prev, { role: 'assistant', content: msg }])
        setAiPlaceholderResponse(lines.length ? '🧾 Últimas transações exibidas no console.' : 'Você ainda não possui transações.')

      } else if (action && (action.type === 'create_payment' || action.type === 'create_transfer')) {
        // Verificar se há dados suficientes antes de pedir confirmação
        // Validar valor para pagamento: deve existir, não ser vazio, e ser um número válido
        const paymentValue = action.type === 'create_payment' ? action.data?.value : null
        const isValidPaymentValue = paymentValue &&
          paymentValue !== '' &&
          paymentValue !== null &&
          !isNaN(parseFloat(paymentValue.toString().replace(/\./g, '').replace(',', '.')))

        // Validar transferência: deve ter valor E chave PIX
        const transferAmount = action.type === 'create_transfer' ? action.data?.amount : null
        const transferPixKey = action.type === 'create_transfer' ? action.data?.pixKey : null
        const isValidTransferAmount = transferAmount &&
          transferAmount !== '' &&
          transferAmount !== null &&
          !isNaN(parseFloat(transferAmount.toString().replace(/\./g, '').replace(',', '.')))
        const isValidTransferPixKey = transferPixKey &&
          transferPixKey !== '' &&
          transferPixKey !== null

        const hasPaymentData = action.type === 'create_payment' && isValidPaymentValue
        const hasTransferData = action.type === 'create_transfer' && isValidTransferAmount && isValidTransferPixKey

        if (!hasPaymentData && !hasTransferData) {
          // Se não houver dados suficientes, mostrar conteúdo limpo ou mensagem padrão
          const displayContent = cleanedContent || 'Preciso de mais informações para realizar essa ação. Por favor, informe o valor e a chave PIX.'
          setAiMessages(prev => [...prev, { role: 'assistant', content: displayContent }])
          setAiPlaceholderResponse(displayContent)
        } else {
          // Requer confirmação do usuário apenas se houver dados válidos
          setPendingAction(action as { type: 'create_payment' | 'create_transfer'; data?: any })

          // Formatar valores para exibição
          const formatValue = (val: string | number) => {
            const num = parseFloat(val.toString().replace(/\./g, '').replace(',', '.'))
            return num.toFixed(2).replace('.', ',')
          }

          const confirmText = action.type === 'create_payment'
            ? `Você confirma que a Amethys AI irá gerar um pagamento de R$ ${formatValue(paymentValue!)}${action.data?.description ? `\n\nDescrição: ${action.data.description}` : ''}?`
            : `Você confirma que a Amethys AI irá transferir R$ ${formatValue(transferAmount!)} para a chave PIX ${transferPixKey}${action.data?.description ? `\n\nDescrição: ${action.data.description}` : ''}?`

          const msg = `⚠️ ${confirmText}\n\nClique em Sim para confirmar ou Não para cancelar.`
          setAiMessages(prev => [...prev, { role: 'assistant', content: msg }])
          setAiPlaceholderResponse(action.type === 'create_payment'
            ? `Confirmar pagamento de R$ ${formatValue(paymentValue!)}?`
            : `Confirmar transferência de R$ ${formatValue(transferAmount!)} para ${transferPixKey}?`)
        }
      } else {
        // Adicionar resposta da IA ao chat (sem JSON)
        const displayContent = cleanedContent || 'Como posso ajudá-lo hoje?'
        setAiMessages(prev => [...prev, { role: 'assistant', content: displayContent }])
        setAiPlaceholderResponse(displayContent)
      }
    } catch (error) {
      const errorMsg = `❌ Erro: ${error instanceof Error ? error.message : 'Erro ao processar sua solicitação'}`
      setAiMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMsg
      }])
      setAiPlaceholderResponse(errorMsg)
    } finally {
      setAiLoading(false)
    }
  }

  const confirmPendingAction = async (confirm: boolean) => {
    if (!pendingAction) return
    const action = pendingAction
    setPendingAction(null)
    if (!confirm) {
      const msg = 'Operação cancelada.'
      setAiMessages(prev => [...prev, { role: 'assistant', content: msg }])
      setAiPlaceholderResponse(msg)
      return
    }
    await executeAIAction(action)
  }

  const executeAIAction = async (action: { type: 'create_payment' | 'create_transfer'; data?: any }) => {
    try {
      if (action.type === 'create_payment') {
        const { value, description } = action.data || {}

        if (!value) {
          setAiMessages(prev => [...prev, {
            role: 'assistant',
            content: 'Por favor, informe o valor do pagamento. Exemplo: "Gerar pagamento de R$ 100"'
          }])
          setAiPlaceholderResponse('Por favor, informe o valor do pagamento.')
          return
        }

        const numericValue = parseFloat(value.toString().replace(/\./g, '').replace(',', '.'))

        if (isNaN(numericValue) || numericValue <= 0) {
          setAiMessages(prev => [...prev, {
            role: 'assistant',
            content: 'Valor inválido. Por favor, informe um valor válido. Exemplo: "Gerar pagamento de R$ 100"'
          }])
          setAiPlaceholderResponse('Valor inválido. Por favor, informe um valor válido.')
          return
        }

        const paymentResponse = await createPayment({
          value: numericValue,
          description: description || undefined,
        })

        const copyPaste = paymentResponse.data?.copyPaste
        const successMessage = `✅ Pagamento gerado com sucesso!\n\nValor: R$ ${numericValue.toFixed(2)}\n${description ? `Descrição: ${description}\n` : ''}${copyPaste ? `\n📋 Código PIX copiado! Use o botão abaixo para colar na área de transferência.` : 'Você pode visualizar o QR Code na página de Extrato.'}`

        setAiMessages(prev => [...prev, {
          role: 'assistant',
          content: successMessage,
          copyPaste: copyPaste || undefined // Adicionar código PIX à mensagem
        }])
        setAiPlaceholderResponse('✅ Pagamento gerado com sucesso!')

        // Recarregar dados
        await refreshWallet()
      } else if (action.type === 'create_transfer') {
        const { amount, pixKey, pixKeyType, description } = action.data || {}

        if (!amount) {
          setAiMessages(prev => [...prev, {
            role: 'assistant',
            content: 'Por favor, informe o valor da transferência. Exemplo: "Enviar R$ 100 para 12345678900"'
          }])
          setAiPlaceholderResponse('Por favor, informe o valor da transferência.')
          return
        }

        if (!pixKey) {
          setAiMessages(prev => [...prev, {
            role: 'assistant',
            content: 'Por favor, informe a chave PIX do destinatário. Exemplo: "Enviar R$ 100 para 12345678900"'
          }])
          setAiPlaceholderResponse('Por favor, informe a chave PIX do destinatário.')
          return
        }

        if (!pixKeyType) {
          setAiMessages(prev => [...prev, {
            role: 'assistant',
            content: 'Não foi possível identificar o tipo da chave PIX. Por favor, informe claramente: CPF, CNPJ, EMAIL, PHONE ou RANDOM'
          }])
          setAiPlaceholderResponse('Não foi possível identificar o tipo da chave PIX.')
          return
        }

        const numericAmount = parseFloat(amount.toString().replace(/\./g, '').replace(',', '.'))

        if (isNaN(numericAmount) || numericAmount <= 0) {
          setAiMessages(prev => [...prev, {
            role: 'assistant',
            content: 'Valor inválido. Por favor, informe um valor válido. Exemplo: "Enviar R$ 100 para 12345678900"'
          }])
          setAiPlaceholderResponse('Valor inválido. Por favor, informe um valor válido.')
          return
        }

        await createWithdraw({
          amount: numericAmount,
          pixKey: pixKey,
          pixKeyType: pixKeyType as 'CPF' | 'CNPJ' | 'EMAIL' | 'PHONE' | 'RANDOM',
          description: description || undefined,
        })

        const successMessage = `✅ Transferência enviada com sucesso!\n\nValor: R$ ${numericAmount.toFixed(2)}\nDestinatário: ${pixKey}\nTipo: ${pixKeyType}\n${description ? `Descrição: ${description}\n` : ''}A transferência está sendo processada.`
        setAiMessages(prev => [...prev, { role: 'assistant', content: successMessage }])
        setAiPlaceholderResponse('✅ Transferência enviada com sucesso!')

        // Recarregar dados
        await refreshWallet()
      }
    } catch (error) {
      const errorMsg = `❌ Erro: ${error instanceof Error ? error.message : 'Erro ao executar ação'}`
      setAiMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMsg
      }])
      setAiPlaceholderResponse(errorMsg)
    }
  }

  const handleAIKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAISubmit()
    }
  }

  const handleCopyPixToTransfer = (copyPaste: string) => {
    // Verificar se está no cliente
    if (typeof window === 'undefined') return

    // Salvar código PIX no localStorage para a página de transferência
    try {
      localStorage.setItem('amethys_pix_key_to_transfer', copyPaste)
      localStorage.setItem('amethys_pix_key_type_to_transfer', 'RANDOM') // Código PIX é sempre chave aleatória
    } catch (error) {
      console.error('Erro ao salvar no localStorage:', error)
    }

    // Copiar para área de transferência
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(copyPaste).then(() => {
        setCopiedPixKey(copyPaste)
        setTimeout(() => setCopiedPixKey(null), 2000)

        // Mostrar mensagem de sucesso
        setAiMessages(prev => [...prev, {
          role: 'assistant',
          content: '✅ Código PIX copiado! Vá para a página de Transferências para usar.'
        }])
      }).catch((error) => {
        console.error('Erro ao copiar:', error)
        setAiMessages(prev => [...prev, {
          role: 'assistant',
          content: '❌ Erro ao copiar código PIX. Tente novamente.'
        }])
      })
    } else {
      // Fallback para navegadores sem clipboard API
      setAiMessages(prev => [...prev, {
        role: 'assistant',
        content: '✅ Código PIX salvo! Vá para a página de Transferências para usar.'
      }])
    }
  }

  // Garantir que sempre renderize algo, mesmo durante loading ou erro
  if (authLoading && !user) {
    return (
      <div className="space-y-6">
        {/* AI Assistant Skeleton */}
        {aiEnabled && (
          <div className="relative">
            <Skeleton className="w-full h-12 rounded-xl" />
          </div>
        )}

        {/* Saldo e Botões Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10">
            <div className="flex items-center justify-between mb-6">
              <Skeleton className="h-16 w-64" />
              <Skeleton className="w-10 h-10 rounded-lg" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-12 w-full rounded-lg" />
              <Skeleton className="h-12 w-full rounded-lg" />
            </div>
          </div>
          <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10 flex flex-col justify-between">
            <div className="mb-4">
              <Skeleton className="h-6 w-48 mb-2" />
              <Skeleton className="h-10 w-24" />
            </div>
            <Skeleton className="h-10 w-full rounded-lg" />
          </div>
        </div>

        {/* Últimas Transações Skeleton */}
        <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2 text-muted-foreground">
              <FontAwesomeIcon icon={faReceipt} className="w-4 h-4" />
              <span className="text-sm font-medium">Últimas Transações</span>
            </div>
            <Skeleton className="h-6 w-24" />
          </div>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="w-10 h-10 rounded-full" />
                <div className="flex-1">
                  <Skeleton className="h-4 w-32 mb-2" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-5 w-20" />
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* AI Assistant - Moved outside container */}
      {aiEnabled && (
        <div className="relative">
          <TooltipProvider>
            <Tooltip delayDuration={300}>
              <TooltipTrigger asChild>
                <input
                  type="text"
                  value={aiInput}
                  onChange={(e) => setAiInput(e.target.value)}
                  onKeyPress={handleAIKeyPress}
                  placeholder={aiPlaceholderResponse || "Peça para IA que ela faz por você!"}
                  disabled={aiLoading || !!pendingAction}
                  className={`w-full pl-4 pr-24 py-3 rounded-xl bg-foreground/5 border border-foreground/10 text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all text-sm disabled:opacity-70 ${aiPlaceholderResponse ? 'placeholder:text-primary/80' : ''
                    }`}
                />
              </TooltipTrigger>
              {aiPlaceholderResponse && (
                <TooltipContent side="bottom" align="start" className="max-w-[400px] bg-background border-foreground/10 text-foreground p-3 shadow-lg rounded-xl">
                  <p className="text-sm whitespace-pre-wrap">{aiPlaceholderResponse}</p>
                </TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            {pendingAction ? (
              <>
                <button
                  onClick={() => confirmPendingAction(true)}
                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-green-500/10 text-green-500 hover:bg-green-500/20 transition-colors"
                  title="Confirmar"
                >
                  <FontAwesomeIcon icon={faCheck} className="w-4 h-4" />
                </button>
                <button
                  onClick={() => confirmPendingAction(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors"
                  title="Cancelar"
                >
                  <FontAwesomeIcon icon={faTimes} className="w-4 h-4" />
                </button>
              </>
            ) : (
              <>
                {aiMessages.length > 0 && (
                  <button
                    onClick={handleClearHistory}
                    className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors"
                    title="Limpar histórico"
                  >
                    <FontAwesomeIcon icon={faTrash} className="w-3 h-3" />
                  </button>
                )}
                <button
                  onClick={handleAISubmit}
                  disabled={aiLoading || !aiInput.trim()}
                  className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <FontAwesomeIcon
                    icon={aiLoading ? faSpinner : faPaperPlane}
                    className={`w-4 h-4 ${aiLoading ? 'animate-spin' : ''}`}
                  />
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Seção Principal: Saldo e Estatísticas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Saldo */}
        <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10 relative overflow-hidden group">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <FontAwesomeIcon icon={faWallet} className="w-4 h-4" />
              <span className="text-sm font-medium">Saldo Disponível</span>
            </div>
            <RippleButton
              onClick={() => setShowBalance(!showBalance)}
              className="p-2 hover:bg-muted rounded-lg transition-colors z-10"
            >
              <FontAwesomeIcon
                icon={showBalance ? faEyeSlash : faEye}
                className="w-4 h-4 text-muted-foreground"
              />
            </RippleButton>
          </div>

          <div className="flex items-start mb-6">
            {walletLoading ? (
              <Skeleton className="h-10 w-48" />
            ) : !showBalance ? (
              <span className="text-3xl lg:text-4xl font-bold text-foreground">••••••</span>
            ) : walletBalance ? (
              <div className="flex items-baseline">
                <span className="text-3xl lg:text-4xl font-bold text-foreground">
                  R$ {walletBalance.balance.total < 0 ? '-' : ''}{Math.floor(Math.abs(walletBalance.balance.total) / 100).toLocaleString('pt-BR')}
                </span>
                <span className="text-lg lg:text-xl font-bold text-foreground/70 ml-0.5">
                  ,{String(Math.abs(walletBalance.balance.total) % 100).padStart(2, '0')}
                </span>
              </div>
            ) : (
              <span className="text-3xl lg:text-4xl font-bold text-foreground">R$ 0,00</span>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <Link href="/dashboard/transfer" className="w-full">
              <RippleButton className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-foreground/10 text-foreground hover:bg-primary hover:text-white border border-foreground/10 hover:border-primary transition-colors text-sm">
                <FontAwesomeIcon icon={faArrowUp} className="w-3.5 h-3.5" />
                <span className="font-medium">Transferir</span>
              </RippleButton>
            </Link>
            <Link href="/dashboard/deposit" className="w-full">
              <RippleButton className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-foreground/10 text-foreground hover:bg-primary hover:text-white border border-foreground/10 hover:border-primary transition-colors text-sm">
                <FontAwesomeIcon icon={faArrowDown} className="w-3.5 h-3.5" />
                <span className="font-medium">Depositar</span>
              </RippleButton>
            </Link>
            <RippleButton
              onClick={() => setPixModalOpen(true)}
              className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-foreground/10 text-foreground hover:bg-primary hover:text-white border border-foreground/10 hover:border-primary transition-colors text-sm"
            >
              <FontAwesomeIcon icon={faQrcode} className="w-3.5 h-3.5" />
              <span className="font-medium">Gerar PIX</span>
            </RippleButton>
          </div>
        </div>

        {/* Transações Completas */}
        <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10 flex flex-col justify-between">
          <div className="flex items-center gap-2 text-muted-foreground mb-4 h-8">
            <FontAwesomeIcon icon={faExchangeAlt} className="w-4 h-4" />
            <span className="text-sm font-medium">Transações Completas</span>
          </div>

          <div className="flex items-start mb-6">
            {walletLoading ? (
              <Skeleton className="h-10 w-24" />
            ) : showBalance ? (
              <span className="text-3xl lg:text-4xl font-bold text-foreground">
                {walletBalance?.statistics?.totalCompletedTransactions || 0}
              </span>
            ) : (
              <span className="text-3xl lg:text-4xl font-bold text-foreground">••••••</span>
            )}
          </div>

          <Link href="/dashboard/summary" className="w-full mt-auto">
            <RippleButton className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-foreground/10 text-foreground hover:bg-primary hover:text-white border border-foreground/10 hover:border-primary transition-colors text-sm">
              <span className="font-medium">Ver em detalhes</span>
              <FontAwesomeIcon icon={faArrowRight} className="w-3.5 h-3.5" />
            </RippleButton>
          </Link>
        </div>
      </div>

      {/* Últimas Transações */}
      <div className="p-6 rounded-xl bg-foreground/5 border border-foreground/10">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2 text-muted-foreground">
            <FontAwesomeIcon icon={faReceipt} className="w-4 h-4" />
            <span className="text-sm font-medium">Últimas Transações</span>
          </div>
          <Link href="/dashboard/transactions">
            <RippleButton className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2 px-3 py-1 rounded">
              Ver todas
              <FontAwesomeIcon icon={faArrowRight} className="w-3 h-3" />
            </RippleButton>
          </Link>
        </div>

        {walletLoading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="w-10 h-10 rounded-full" />
                <div className="flex-1">
                  <Skeleton className="h-4 w-32 mb-2" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-5 w-20" />
              </div>
            ))}
          </div>
        ) : transactions.length > 0 ? (
          <div className="space-y-0">
            {transactions.map((transaction, idx) => (
              <div key={transaction.id}>
                <div
                  className={`flex items-center gap-4 cursor-pointer hover:opacity-80 transition-opacity py-4 ${idx < transactions.length - 1 ? 'border-b border-border' : ''
                    }`}
                  onClick={() => {
                    setSelectedTransactionId(transaction.id)
                    setSelectedTransactionType(transaction.transactionType)
                    setDetailsModalOpen(true)
                  }}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${transaction.status === 'PENDING' ? 'bg-yellow-500/10' : (transaction.status === 'CANCELLED' || transaction.status === 'FAILED') ? 'bg-white/10' : (transaction.type === 'received' ? 'bg-green-500/10' : 'bg-red-500/10')
                    }`}>
                    <FontAwesomeIcon
                      icon={
                        (transaction.status === 'CANCELLED' || transaction.status === 'FAILED') ? faTimes :
                          transaction.transactionType === 'commission' ? faHandHoldingDollar :
                            (transaction.type === 'received' ? faArrowDown : faArrowUp)
                      }
                      className={`w-4 h-4 ${transaction.status === 'PENDING' ? 'text-yellow-500' : (transaction.status === 'CANCELLED' || transaction.status === 'FAILED') ? 'text-white' : (transaction.type === 'received' ? 'text-green-500' : 'text-red-500')
                        }`}
                    />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">
                      {(transaction.status === 'CANCELLED' || transaction.status === 'FAILED') && transaction.type === 'received'
                        ? 'Depósito cancelado'
                        : transaction.status === 'PENDING'
                          ? (transaction.type === 'received' ? 'Depósito pendente' : 'Transferência pendente')
                          : transaction.transactionType === 'internal_transfer_received'
                            ? 'Depósito interno'
                            : transaction.transactionType === 'internal_transfer_sent'
                              ? 'Transferência interna'
                              : transaction.transactionType === 'commission'
                                ? 'Comissão de Afiliado'
                                : (transaction.type === 'received' ? 'Depósito' : 'Transferência')
                      }
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {transaction.date}
                    </p>
                  </div>
                  <p className={`text-sm font-bold ${transaction.status === 'PENDING' ? 'text-yellow-500' : (transaction.status === 'CANCELLED' || transaction.status === 'FAILED') ? 'text-white' : (transaction.type === 'received' ? 'text-green-500' : 'text-red-500')
                    }`}>
                    {showBalance
                      ? `${transaction.type === 'received' ? '+' : '-'}R$ ${Math.abs(transaction.amount).toFixed(2).replace('.', ',')}`
                      : '••••••'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-12 text-center">
            <div className="flex flex-col items-center justify-center gap-3">
              <div className="w-16 h-16 rounded-full bg-foreground/5 flex items-center justify-center">
                <FontAwesomeIcon icon={faInbox} className="w-6 h-6 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Nenhuma transação encontrada</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Suas transações aparecerão aqui quando você fizer depósitos ou transferências
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      <PixModal
        open={pixModalOpen}
        onOpenChange={setPixModalOpen}
        onSuccess={() => refreshWallet()}
      />

      <TransactionDetailsModal
        open={detailsModalOpen}
        onOpenChange={setDetailsModalOpen}
        transactionId={selectedTransactionId}
        transactionType={selectedTransactionType}
      />
    </div>
  )
}

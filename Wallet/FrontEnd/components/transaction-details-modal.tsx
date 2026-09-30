'use client'

import { useWallet } from '@/components/providers/wallet-provider'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCopy, faCheckCircle, faTimesCircle, faClock, faSpinner } from '@fortawesome/free-solid-svg-icons'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { getPaymentById, getWithdrawById } from '@/lib/wallet'
import { useState, useEffect } from 'react'

interface TransactionDetailsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  transactionId: string
  transactionType: 'payment' | 'withdraw' | 'internal_transfer_sent' | 'internal_transfer_received' | 'commission'
}

export function TransactionDetailsModal({
  open,
  onOpenChange,
  transactionId,
  transactionType
}: TransactionDetailsModalProps) {
  const { internalTransfers } = useWallet()
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [details, setDetails] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && transactionId) {
      loadDetails()
    } else {
      setDetails(null)
      setError(null)
    }
  }, [open, transactionId])

  const loadDetails = async () => {
    try {
      setLoading(true)
      setError(null)

      // For internal transfers, get details from wallet context
      if (transactionType === 'internal_transfer_sent' || transactionType === 'internal_transfer_received') {
        const tx = internalTransfers.find(t => t.id === transactionId)
        if (tx) {
          setDetails({
            id: tx.id,
            status: tx.status,
            type: transactionType,
            description: tx.description,
            recipient: tx.originalData?.recipient,
            sender: tx.originalData?.sender,
            value: tx.amount,
            netValue: tx.amount, // Sem taxa
            createdAt: tx.date,
          })
        } else {
          setDetails({ id: transactionId, status: 'UNKNOWN', type: transactionType })
        }
        return
      }

      if (transactionType === 'payment' || transactionType === 'commission') {
        const response = await getPaymentById(transactionId)
        if (response.success) {
          setDetails(response.data)
        } else {
          setError('Erro ao carregar detalhes do pagamento')
        }
      } else {
        const response = await getWithdrawById(transactionId)
        if (response.success) {
          setDetails(response.data)
        } else {
          setError('Erro ao carregar detalhes do saque')
        }
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar detalhes da transação')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return `R$ ${(value / 100).toFixed(2).replace('.', ',')}`
  }

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), "dd 'de' MMMM 'de' yyyy 'às' HH:mm", { locale: ptBR })
    } catch {
      return dateString
    }
  }

  const getStatusInfo = (status: string) => {
    const statusUpper = status.toUpperCase()
    if (statusUpper === 'COMPLETED' || statusUpper === 'PAID' || statusUpper === 'COMPLETO') {
      return { icon: faCheckCircle, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Concluída' }
    } else if (statusUpper === 'PENDING' || statusUpper === 'PENDENTE' || statusUpper === 'ACTIVE') {
      return { icon: faClock, color: 'text-yellow-500', bg: 'bg-yellow-500/10', label: 'Pendente' }
    } else if (statusUpper === 'FAILED' || statusUpper === 'FALHA' || statusUpper === 'CANCELLED' || statusUpper === 'CANCELADO') {
      return { icon: faTimesCircle, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Falhou' }
    } else if (statusUpper === 'EXPIRED' || statusUpper === 'EXPIRADO') {
      return { icon: faTimesCircle, color: 'text-orange-500', bg: 'bg-orange-500/10', label: 'Expirado' }
    }
    return { icon: faClock, color: 'text-gray-500', bg: 'bg-gray-500/10', label: status }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Erro ao copiar:', err)
    }
  }

  if (!open) return null

  const statusInfo = details ? getStatusInfo(details.status) : null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto w-[calc(100%-2rem)] mx-auto">
        {loading ? (
          <>
            <DialogHeader>
              <DialogTitle className="sr-only">Carregando detalhes da transação</DialogTitle>
            </DialogHeader>
            <div className="flex flex-col items-center justify-center py-12">
              <FontAwesomeIcon icon={faSpinner} className="w-12 h-12 text-primary animate-spin mb-4" />
              <p className="text-muted-foreground">Carregando detalhes da transação...</p>
            </div>
          </>
        ) : error ? (
          <>
            <DialogHeader>
              <DialogTitle className="sr-only">Erro ao carregar transação</DialogTitle>
            </DialogHeader>
            <div className="flex flex-col items-center justify-center py-12">
              <FontAwesomeIcon icon={faTimesCircle} className="w-12 h-12 text-red-500 mb-4" />
              <p className="text-foreground font-medium mb-2">Erro</p>
              <p className="text-muted-foreground text-sm">{error}</p>
            </div>
          </>
        ) : details ? (
          <>
            <DialogHeader>
              <div className="flex items-center justify-center mb-4">
                {statusInfo && (
                  <div className={`w-16 h-16 rounded-full ${statusInfo.bg} flex items-center justify-center`}>
                    <FontAwesomeIcon
                      icon={statusInfo.icon}
                      className={`w-10 h-10 ${statusInfo.color}`}
                    />
                  </div>
                )}
              </div>
              <DialogTitle className="text-center text-2xl font-bold">
                {transactionType === 'payment' ? 'Comprovante de Depósito' : transactionType === 'commission' ? 'Comprovante de Comissão' : 'Comprovante de Transferência'}
              </DialogTitle>
              <DialogDescription className="text-center pt-2">
                {statusInfo?.label}
              </DialogDescription>
            </DialogHeader>

            <div className="mt-6 space-y-4">
              {/* Informações principais */}
              <div className="p-4 sm:p-6 rounded-xl bg-foreground/5 border border-foreground/10 space-y-4">
                <div className={`flex flex-col sm:flex-row sm:justify-between sm:items-center ${transactionType === 'internal_transfer_sent' || transactionType === 'internal_transfer_received'
                  ? ''
                  : 'pb-3 border-b border-foreground/10'
                  } gap-1`}>
                  <span className="text-sm font-medium text-muted-foreground">Valor:</span>
                  <span className="text-2xl font-bold text-foreground">
                    {formatCurrency(details.value || details.netValue || 0)}
                  </span>
                </div>

                {(transactionType === 'payment' || transactionType === 'commission') && details.netValue && details.netValue !== details.value && (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Taxa:</span>
                      <span className="text-sm text-foreground">
                        {formatCurrency((details.value || 0) - (details.netValue || 0))}
                      </span>
                    </div>
                    <div className="flex justify-between items-center pt-2 border-t border-foreground/10">
                      <span className="text-sm font-medium text-muted-foreground">Valor líquido:</span>
                      <span className="text-sm font-bold text-green-500">
                        {formatCurrency(details.netValue)}
                      </span>
                    </div>
                  </div>
                )}

                {transactionType === 'withdraw' && (
                  <div className="space-y-2">
                    {(() => {
                      // Calcular taxa: se não tiver fee direto, calcular pela diferença entre value e sent
                      const fee = details.fee !== undefined && details.fee !== null
                        ? details.fee
                        : (details.value && details.sent !== undefined)
                          ? details.value - details.sent
                          : 0

                      const sent = details.sent !== undefined && details.sent !== null
                        ? details.sent
                        : (details.value && fee > 0)
                          ? details.value - fee
                          : details.value || 0

                      if (fee > 0) {
                        return (
                          <>
                            <div className="flex justify-between items-center">
                              <span className="text-sm text-muted-foreground">Taxa:</span>
                              <span className="text-sm text-foreground">
                                {formatCurrency(fee)}
                              </span>
                            </div>
                            <div className="flex justify-between items-center pt-2 border-t border-foreground/10">
                              <span className="text-sm font-medium text-muted-foreground">Valor enviado:</span>
                              <span className="text-sm font-bold text-green-500">
                                {formatCurrency(sent)}
                              </span>
                            </div>
                          </>
                        )
                      }
                      return null
                    })()}
                  </div>
                )}
              </div>

              {/* Detalhes da transação */}
              <div className="p-4 sm:p-6 rounded-xl bg-foreground/5 border border-foreground/10 space-y-3">
                <h3 className="text-sm font-semibold text-foreground mb-3">Detalhes da Transação</h3>

                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                  <span className="text-sm text-muted-foreground">ID da Transação:</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono text-foreground break-all sm:max-w-[180px] sm:truncate">
                      {details.id || details.transactionId || details.correlationID}
                    </span>
                    <button
                      onClick={() => copyToClipboard(details.id || details.transactionId || details.correlationID || '')}
                      className="p-1 hover:bg-foreground/10 rounded transition-colors flex-shrink-0 focus:outline-none focus:ring-0"
                      title="Copiar ID"
                    >
                      <FontAwesomeIcon
                        icon={copied ? faCheckCircle : faCopy}
                        className={`w-4 h-4 ${copied ? 'text-green-500' : 'text-muted-foreground'}`}
                      />
                    </button>
                  </div>
                </div>

                {details.description && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Descrição:</span>
                    <span className="text-sm text-foreground sm:text-right sm:max-w-[60%] break-words">
                      {details.description}
                    </span>
                  </div>
                )}

                {transactionType === 'withdraw' && details.pixKey && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Chave PIX:</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-foreground break-all sm:max-w-[180px] sm:truncate">
                        {details.pixKey}
                      </span>
                      <button
                        onClick={() => copyToClipboard(details.pixKey)}
                        className="p-1 hover:bg-foreground/10 rounded transition-colors flex-shrink-0 focus:outline-none focus:ring-0"
                        title="Copiar chave PIX"
                      >
                        <FontAwesomeIcon
                          icon={copied ? faCheckCircle : faCopy}
                          className={`w-4 h-4 ${copied ? 'text-green-500' : 'text-muted-foreground'}`}
                        />
                      </button>
                    </div>
                  </div>
                )}

                {transactionType === 'withdraw' && details.pixKeyType && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Tipo de Chave PIX:</span>
                    <span className="text-sm text-foreground">
                      {details.pixKeyType}
                    </span>
                  </div>
                )}

                {/* Sender/Recipient for Internal Transfers */}
                {transactionType === 'internal_transfer_sent' && details.recipient && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Destinatário:</span>
                    <div className="text-sm text-foreground sm:text-right">
                      {details.recipient.name} <span className="text-muted-foreground">({details.recipient.email})</span>
                    </div>
                  </div>
                )}

                {transactionType === 'internal_transfer_received' && details.sender && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Remetente:</span>
                    <div className="text-sm text-foreground sm:text-right">
                      {details.sender.name} <span className="text-muted-foreground">({details.sender.email})</span>
                    </div>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                  <span className="text-sm text-muted-foreground">Data de criação:</span>
                  <span className="text-sm text-foreground">
                    {formatDate(details.createdAt)}
                  </span>
                </div>

                {details.updatedAt && details.updatedAt !== details.createdAt && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Última atualização:</span>
                    <span className="text-sm text-foreground">
                      {formatDate(details.updatedAt)}
                    </span>
                  </div>
                )}

                {details.completedAt && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Data de conclusão:</span>
                    <span className="text-sm text-foreground">
                      {formatDate(details.completedAt)}
                    </span>
                  </div>
                )}

                {details.failedAt && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Data de falha:</span>
                    <span className="text-sm text-foreground">
                      {formatDate(details.failedAt)}
                    </span>
                  </div>
                )}

                {details.failureReason && (
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                    <span className="text-sm text-muted-foreground">Motivo da falha:</span>
                    <span className="text-sm text-red-500 sm:text-right sm:max-w-[60%] break-words">
                      {details.failureReason}
                    </span>
                  </div>
                )}
              </div>

              {/* QR Code se disponível */}
              {transactionType === 'payment' && details.qrCode && (
                <div className="p-4 sm:p-6 rounded-xl bg-foreground/5 border border-foreground/10">
                  <h3 className="text-sm font-semibold text-foreground mb-3">QR Code</h3>
                  <div className="flex justify-center mb-4">
                    <img
                      src={details.qrCode}
                      alt="QR Code PIX"
                      className="max-w-[180px] w-full"
                    />
                  </div>
                  {details.copyPaste && (
                    <div className="space-y-2">
                      <label className="text-sm text-muted-foreground">Código PIX (Copia e Cola):</label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={details.copyPaste}
                          readOnly
                          className="flex-1 px-3 py-2 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground text-xs font-mono truncate"
                        />
                        <button
                          onClick={() => copyToClipboard(details.copyPaste)}
                          className="px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex-shrink-0 focus:outline-none focus:ring-0"
                          title="Copiar código PIX"
                        >
                          <FontAwesomeIcon
                            icon={copied ? faCheckCircle : faCopy}
                            className="w-4 h-4"
                          />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}


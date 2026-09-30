'use client'

import { useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCheckCircle, faTimesCircle, faSpinner } from '@fortawesome/free-solid-svg-icons'

interface TransactionModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  type: 'deposit' | 'withdraw'
  status: 'success' | 'error' | 'loading'
  title?: string
  message?: string
  details?: {
    amount?: number
    fee?: number
    netAmount?: number
    transactionId?: string
    recipientName?: string
    recipientEmail?: string
  }
}

export function TransactionModal({
  open,
  onOpenChange,
  type,
  status,
  title,
  message,
  details
}: TransactionModalProps) {
  useEffect(() => {
    if (status === 'success' && open) {
      // Fechar automaticamente após 5 segundos se for sucesso
      const timer = setTimeout(() => {
        onOpenChange(false)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [status, open, onOpenChange])

  const getTitle = () => {
    if (title) return title

    if (status === 'success') {
      return type === 'deposit' ? 'Depósito Criado!' : 'Transferência Realizada!'
    } else if (status === 'error') {
      return type === 'deposit' ? 'Erro ao Criar Depósito' : 'Erro ao Realizar Saque'
    } else {
      return type === 'deposit' ? 'Criando Depósito...' : 'Processando Saque...'
    }
  }

  const getMessage = () => {
    if (message) return message

    if (status === 'success') {
      return type === 'deposit'
        ? 'Seu QR Code PIX foi gerado com sucesso! Escaneie ou copie o código para pagar.'
        : (details?.recipientName ? `Transferência para ${details.recipientName} realizada com sucesso!` : 'Sua transferência foi processada com sucesso!')
    } else if (status === 'error') {
      return 'Ocorreu um erro ao processar sua solicitação. Tente novamente.'
    } else {
      return 'Aguarde enquanto processamos sua solicitação...'
    }
  }

  const formatCurrency = (value: number) => {
    return `R$ ${(value / 100).toFixed(2).replace('.', ',')}`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center justify-center mb-4">
            {status === 'success' && (
              <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center">
                <FontAwesomeIcon
                  icon={faCheckCircle}
                  className="w-10 h-10 text-green-500"
                />
              </div>
            )}
            {status === 'error' && (
              <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center">
                <FontAwesomeIcon
                  icon={faTimesCircle}
                  className="w-10 h-10 text-red-500"
                />
              </div>
            )}
            {status === 'loading' && (
              <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
                <FontAwesomeIcon
                  icon={faSpinner}
                  className="w-10 h-10 text-primary animate-spin"
                />
              </div>
            )}
          </div>
          <DialogTitle className="text-center text-xl font-bold">
            {getTitle()}
          </DialogTitle>
          <DialogDescription className="text-center pt-2">
            {getMessage()}
          </DialogDescription>
        </DialogHeader>

        {details && status === 'success' && (
          <div className="mt-4 space-y-3 p-4 rounded-lg bg-foreground/5 border border-foreground/10">
            {details.amount && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Valor:</span>
                <span className="text-sm font-bold text-foreground">
                  {formatCurrency(details.amount)}
                </span>
              </div>
            )}
            {details.fee && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Taxa:</span>
                <span className="text-sm text-foreground">
                  {formatCurrency(details.fee)}
                </span>
              </div>
            )}
            {details.netAmount && (
              <div className="flex justify-between items-center pt-2 border-t border-foreground/10">
                <span className="text-sm text-muted-foreground">Valor líquido:</span>
                <span className="text-sm font-bold text-green-500">
                  {formatCurrency(details.netAmount)}
                </span>
              </div>
            )}
            {details.recipientName && (
              <div className="flex justify-between items-center pt-2 border-t border-foreground/10">
                <span className="text-sm text-muted-foreground">Destinatário:</span>
                <div className="text-right">
                  <div className="text-sm font-bold text-foreground">{details.recipientName}</div>
                  {details.recipientEmail && <div className="text-xs text-muted-foreground">{details.recipientEmail}</div>}
                </div>
              </div>
            )}
            {details.transactionId && (
              <div className="flex justify-between items-center pt-2 border-t border-foreground/10">
                <span className="text-xs text-muted-foreground">ID da transação:</span>
                <span className="text-xs font-mono text-foreground/70">
                  {details.transactionId.slice(0, 8)}...
                </span>
              </div>
            )}
          </div>
        )}

        {status === 'error' && (
          <div className="mt-4">
            <button
              onClick={() => onOpenChange(false)}
              className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors focus:outline-none focus:ring-0"
            >
              Fechar
            </button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}


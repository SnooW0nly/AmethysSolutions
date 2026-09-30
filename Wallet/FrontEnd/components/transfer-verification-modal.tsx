'use client'

import { useState, useEffect } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faSpinner, faCheck, faArrowRight, faTimes, faEnvelope } from '@fortawesome/free-solid-svg-icons'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { RippleButton } from './ripple-button'

interface TransferVerificationModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  amount: number | string
  onVerified: (code: string) => void
  onCancel: () => void
}

export function TransferVerificationModal({
  open,
  onOpenChange,
  amount,
  onVerified,
  onCancel
}: TransferVerificationModalProps) {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [sendingCode, setSendingCode] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [codeSent, setCodeSent] = useState(false)

  useEffect(() => {
    if (open) {
      setCode('')
      setError(null)
      setCodeSent(false)
      handleRequestCode()
    }
  }, [open, amount])

  const handleRequestCode = async () => {
    setSendingCode(true)
    setError(null)
    
    try {
      const { requestTransferCode } = await import('@/lib/security')
      await requestTransferCode(amount)
      setCodeSent(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao enviar código')
    } finally {
      setSendingCode(false)
    }
  }

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const { verifyTransferCode } = await import('@/lib/security')
      await verifyTransferCode(code, amount)
      onVerified(code)
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Código inválido ou expirado')
    } finally {
      setLoading(false)
    }
  }

  const formatAmount = (value: number | string) => {
    const num = typeof value === 'string' ? parseFloat(value.replace(',', '.')) : value
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(num)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FontAwesomeIcon icon={faEnvelope} className="w-5 h-5 text-primary" />
            Verificação de Transferência
          </DialogTitle>
          <DialogDescription>
            Uma transferência de <strong>{formatAmount(amount)}</strong> foi solicitada.
            Digite o código enviado para seu e-mail para confirmar.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
              {error}
            </div>
          )}

          {codeSent && (
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-500 text-sm">
              Código enviado para seu e-mail!
            </div>
          )}

          {sendingCode ? (
            <div className="flex items-center justify-center py-8">
              <FontAwesomeIcon icon={faSpinner} className="animate-spin text-primary w-6 h-6" />
              <span className="ml-2 text-sm text-muted-foreground">Enviando código...</span>
            </div>
          ) : (
            <form onSubmit={handleVerify} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Código de Verificação
                </label>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000"
                  className="w-full px-4 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 text-center text-2xl tracking-widest"
                  disabled={loading}
                  maxLength={6}
                  required
                  autoFocus
                />
                <p className="text-xs text-muted-foreground mt-2 text-center">
                  Digite o código de 6 dígitos enviado para seu e-mail
                </p>
              </div>

              <div className="flex gap-2">
                <RippleButton
                  type="button"
                  onClick={() => {
                    onCancel()
                    onOpenChange(false)
                  }}
                  disabled={loading}
                  className="flex-1 py-2 bg-foreground/5 hover:bg-foreground/10 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancelar
                </RippleButton>
                <RippleButton
                  type="submit"
                  disabled={loading || code.length !== 6}
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
                      <span>Confirmar</span>
                    </>
                  )}
                </RippleButton>
              </div>

              <button
                type="button"
                onClick={handleRequestCode}
                disabled={loading || sendingCode}
                className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
              >
                Não recebeu o código? Reenviar
              </button>
            </form>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}


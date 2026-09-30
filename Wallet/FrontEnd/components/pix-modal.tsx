'use client'

import { useState, useEffect } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faQrcode,
  faSpinner,
  faCopy,
  faCheck,
  faTimes,
  faChevronRight,
  faArrowLeft,
  faCircleInfo,
  faBolt,
  faShield,
  faUser,
  faStore,
} from '@fortawesome/free-solid-svg-icons'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { RippleButton } from './ripple-button'
import { createPayment } from '@/lib/wallet'

interface PixModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

const QUICK_VALUES = [5, 10, 25, 50, 100, 200]

// Taxas conforme a API: WHITE=4%, BLACK=6%, + R$ 0,50 fixo da Mistic por transação
const MISTIC_FIXED = 0.5
const ROUTE_INFO = {
  WHITE: { percent: 4, label: 'WHITE', desc: 'Rota padrão · 4% + R$ 0,50' },
  BLACK: { percent: 6, label: 'BLACK', desc: 'Rota premium · 6% + R$ 0,50' },
}

type Route = 'WHITE' | 'BLACK'
type FeePayer = 'client' | 'merchant'
type Step = 'input' | 'loading' | 'result'

function calcFees(value: number, route: Route, feePayer: FeePayer) {
  const platformFee = Math.round(value * ROUTE_INFO[route].percent) / 100
  const totalFee = Math.round((platformFee + MISTIC_FIXED) * 100) / 100
  if (feePayer === 'client') {
    // coverFee=false: QR = valor + taxa, você recebe o valor exato
    return { qrValue: Math.round((value + totalFee) * 100) / 100, youReceive: value, feeAmount: totalFee, coverFee: false }
  } else {
    // coverFee=true: QR = valor, você recebe valor - taxa
    return { qrValue: value, youReceive: Math.max(0, Math.round((value - totalFee) * 100) / 100), feeAmount: totalFee, coverFee: true }
  }
}

function fmt(n: number) { return n.toFixed(2).replace('.', ',') }

export function PixModal({ open, onOpenChange, onSuccess }: PixModalProps) {
  const [step, setStep] = useState<Step>('input')
  const [rawValue, setRawValue] = useState('')
  const [description, setDescription] = useState('')
  const [route, setRoute] = useState<Route>('WHITE')
  const [feePayer, setFeePayer] = useState<FeePayer>('client')
  const [error, setError] = useState<string | null>(null)
  const [copyPaste, setCopyPaste] = useState<string | null>(null)
  const [qrCodeImage, setQrCodeImage] = useState<string | null>(null)
  const [generatedValue, setGeneratedValue] = useState<number>(0)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!open) {
      setTimeout(() => {
        setStep('input')
        setRawValue('')
        setDescription('')
        setRoute('WHITE')
        setFeePayer('client')
        setError(null)
        setCopyPaste(null)
        setQrCodeImage(null)
        setCopied(false)
      }, 300)
    }
  }, [open])

  const parsedValue = parseFloat(rawValue.replace(',', '.')) || 0

  const handleQuickValue = (val: number) => {
    setRawValue(val.toFixed(2).replace('.', ','))
    setError(null)
  }

  const handleValueInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Permite apenas números e vírgula
    const v = e.target.value.replace(/[^0-9,]/g, '')
    setRawValue(v)
    setError(null)
  }

  const handleGenerate = async () => {
    if (parsedValue <= 0) {
      setError('Informe um valor válido para gerar o PIX.')
      return
    }
    if (parsedValue < 1) {
      setError('O valor mínimo é R$ 1,00.')
      return
    }

    const { coverFee, qrValue } = calcFees(parsedValue, route, feePayer)

    setStep('loading')
    setError(null)

    try {
      const response = await createPayment({
        value: parsedValue,
        description: description.trim() || undefined,
        route,
        coverFee,
      })

      setCopyPaste(response.data?.copyPaste || null)
      // A API retorna qrcodeUrl (não qrCodeImage)
      setQrCodeImage(response.data?.qrcodeUrl || response.data?.qrCodeBase64 || null)
      setGeneratedValue(qrValue)
      setStep('result')
      onSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao gerar PIX. Tente novamente.')
      setStep('input')
    }
  }

  const handleCopy = async () => {
    if (!copyPaste) return
    try {
      await navigator.clipboard.writeText(copyPaste)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch {
      // fallback silencioso
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && step === 'input') handleGenerate()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm p-0 overflow-hidden bg-background border border-foreground/10 rounded-2xl">

        {/* Header */}
        <DialogHeader className="px-6 pt-6 pb-0">
          <div className="flex items-center gap-3 mb-1">
            {step === 'result' && (
              <button
                onClick={() => setStep('input')}
                className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-foreground/5 transition-colors text-muted-foreground hover:text-foreground"
              >
                <FontAwesomeIcon icon={faArrowLeft} className="w-3.5 h-3.5" />
              </button>
            )}
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <FontAwesomeIcon icon={faQrcode} className="w-4 h-4 text-primary" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold leading-tight">
                {step === 'result' ? 'PIX gerado!' : 'Gerar cobrança PIX'}
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground leading-tight mt-0.5">
                {step === 'result'
                  ? `QR: R$ ${generatedValue.toFixed(2).replace('.', ',')} · Compartilhe o código abaixo`
                  : 'Cole o código Copia e Cola no app do banco'}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="px-6 pb-6 pt-4 space-y-4">

          {/* ─── STEP: INPUT ─── */}
          {step === 'input' && (
            <>
              {/* Valores rápidos */}
              <div>
                <p className="text-xs text-muted-foreground mb-2 font-medium">Valor rápido</p>
                <div className="grid grid-cols-3 gap-2">
                  {QUICK_VALUES.map((v) => (
                    <button
                      key={v}
                      onClick={() => handleQuickValue(v)}
                      className={`py-2 rounded-lg text-sm font-medium border transition-all ${
                        parsedValue === v
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-foreground/5 border-foreground/10 text-foreground hover:bg-foreground/10'
                      }`}
                    >
                      R$ {v}
                    </button>
                  ))}
                </div>
              </div>

              {/* Input de valor */}
              <div>
                <p className="text-xs text-muted-foreground mb-2 font-medium">Ou digite o valor</p>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-muted-foreground select-none">
                    R$
                  </span>
                  <input
                    type="text"
                    inputMode="decimal"
                    value={rawValue}
                    onChange={handleValueInput}
                    onKeyDown={handleKeyDown}
                    placeholder="0,00"
                    className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/30 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all text-sm font-medium"
                  />
                </div>
              </div>

              {/* Descrição (opcional) */}
              <div>
                <p className="text-xs text-muted-foreground mb-2 font-medium">Descrição <span className="opacity-50">(opcional)</span></p>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ex: racha do almoço"
                  maxLength={60}
                  className="w-full px-3 py-2.5 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/30 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all text-sm"
                />
              </div>

              {/* Rota de pagamento */}
              <div>
                <p className="text-xs text-muted-foreground mb-2 font-medium">Rota de pagamento</p>
                <div className="grid grid-cols-2 gap-2">
                  {(['WHITE', 'BLACK'] as Route[]).map((r) => (
                    <button
                      key={r}
                      onClick={() => setRoute(r)}
                      className={`flex flex-col items-start gap-0.5 px-3 py-2.5 rounded-lg border transition-all text-left ${
                        route === r
                          ? r === 'BLACK'
                            ? 'bg-zinc-900 border-zinc-600 text-white'
                            : 'bg-primary/10 border-primary text-primary'
                          : 'bg-foreground/5 border-foreground/10 text-foreground hover:bg-foreground/10'
                      }`}
                    >
                      <span className="flex items-center gap-1.5 text-sm font-semibold">
                        <FontAwesomeIcon icon={r === 'BLACK' ? faShield : faBolt} className="w-3 h-3" />
                        {r}
                      </span>
                      <span className="text-[10px] opacity-60">{ROUTE_INFO[r].desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Quem paga a taxa */}
              <div>
                <p className="text-xs text-muted-foreground mb-2 font-medium">Quem paga a taxa?</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setFeePayer('client')}
                    className={`flex flex-col items-start gap-0.5 px-3 py-2.5 rounded-lg border transition-all text-left ${
                      feePayer === 'client'
                        ? 'bg-primary/10 border-primary text-primary'
                        : 'bg-foreground/5 border-foreground/10 text-foreground hover:bg-foreground/10'
                    }`}
                  >
                    <span className="flex items-center gap-1.5 text-sm font-semibold">
                      <FontAwesomeIcon icon={faUser} className="w-3 h-3" />
                      Cliente paga
                    </span>
                    <span className="text-[10px] opacity-60">Taxa somada ao QR Code</span>
                  </button>
                  <button
                    onClick={() => setFeePayer('merchant')}
                    className={`flex flex-col items-start gap-0.5 px-3 py-2.5 rounded-lg border transition-all text-left ${
                      feePayer === 'merchant'
                        ? 'bg-primary/10 border-primary text-primary'
                        : 'bg-foreground/5 border-foreground/10 text-foreground hover:bg-foreground/10'
                    }`}
                  >
                    <span className="flex items-center gap-1.5 text-sm font-semibold">
                      <FontAwesomeIcon icon={faStore} className="w-3 h-3" />
                      Eu absorvo
                    </span>
                    <span className="text-[10px] opacity-60">Taxa descontada do recebido</span>
                  </button>
                </div>
              </div>

              {/* Preview de taxas (só mostra se tiver valor) */}
              {parsedValue > 0 && (() => {
                const { qrValue, youReceive, feeAmount } = calcFees(parsedValue, route, feePayer)
                return (
                  <div className="rounded-lg bg-foreground/5 border border-foreground/10 px-3 py-2.5 space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Valor digitado</span>
                      <span className="font-medium">R$ {fmt(parsedValue)}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Taxa ({ROUTE_INFO[route].percent}% + R$ 0,50)</span>
                      <span className="text-red-400 font-medium">- R$ {fmt(feeAmount)}</span>
                    </div>
                    <div className="flex justify-between text-xs border-t border-foreground/10 pt-1.5">
                      <span className="text-muted-foreground">QR Code gerado por</span>
                      <span className="font-semibold">R$ {fmt(qrValue)}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Você recebe</span>
                      <span className="font-semibold text-green-500">R$ {fmt(youReceive)}</span>
                    </div>
                  </div>
                )
              })()}

              {/* Aviso valor aberto */}
              <div className="flex items-start gap-2 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                <FontAwesomeIcon icon={faCircleInfo} className="w-3.5 h-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                  O PIX será gerado com o valor acima. Alguns bancos (Nubank, C6) permitem que o pagador edite o valor antes de confirmar.
                </p>
              </div>

              {error && (
                <p className="text-xs text-red-500 bg-red-500/10 border border-red-500/20 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}

              <RippleButton
                onClick={handleGenerate}
                disabled={parsedValue <= 0}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <FontAwesomeIcon icon={faQrcode} className="w-4 h-4" />
                Gerar PIX
                <FontAwesomeIcon icon={faChevronRight} className="w-3 h-3 opacity-70" />
              </RippleButton>
            </>
          )}

          {/* ─── STEP: LOADING ─── */}
          {step === 'loading' && (
            <div className="flex flex-col items-center justify-center py-10 gap-3">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                <FontAwesomeIcon icon={faSpinner} className="w-5 h-5 text-primary animate-spin" />
              </div>
              <p className="text-sm text-muted-foreground">Gerando seu PIX...</p>
            </div>
          )}

          {/* ─── STEP: RESULT ─── */}
          {step === 'result' && (
            <>
              {/* QR Code se disponível */}
              {qrCodeImage && (
                <div className="flex justify-center">
                  <div className="p-3 rounded-xl bg-white border border-foreground/10">
                    <img
                      src={qrCodeImage}
                      alt="QR Code PIX"
                      className="w-44 h-44 object-contain"
                    />
                  </div>
                </div>
              )}

              {/* Código Copia e Cola */}
              {copyPaste && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Copia e Cola PIX</p>
                  <div className="relative group">
                    <div className="w-full px-3 py-2.5 pr-10 rounded-lg bg-foreground/5 border border-foreground/10 text-xs font-mono text-foreground/60 break-all leading-relaxed select-all">
                      {copyPaste.slice(0, 80)}…
                    </div>
                    <button
                      onClick={handleCopy}
                      className={`absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center rounded-md transition-all ${
                        copied
                          ? 'bg-green-500/20 text-green-500'
                          : 'bg-foreground/10 text-muted-foreground hover:bg-primary/10 hover:text-primary'
                      }`}
                      title="Copiar código PIX"
                    >
                      <FontAwesomeIcon
                        icon={copied ? faCheck : faCopy}
                        className="w-3.5 h-3.5"
                      />
                    </button>
                  </div>
                </div>
              )}

              {/* Instrução */}
              <div className="flex items-start gap-2 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                <FontAwesomeIcon icon={faCircleInfo} className="w-3.5 h-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Compartilhe o código acima. O pagador vai em <strong className="text-foreground/70">PIX → Copia e Cola</strong> no app do banco dele, cola e paga. O saldo cai automaticamente na sua conta.
                </p>
              </div>

              {/* Botão copiar grande */}
              <RippleButton
                onClick={handleCopy}
                className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm transition-all ${
                  copied
                    ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                    : 'bg-primary text-primary-foreground hover:bg-primary/90'
                }`}
              >
                <FontAwesomeIcon icon={copied ? faCheck : faCopy} className="w-4 h-4" />
                {copied ? 'Código copiado!' : 'Copiar código PIX'}
              </RippleButton>

              <button
                onClick={() => onOpenChange(false)}
                className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors py-1"
              >
                Fechar
              </button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
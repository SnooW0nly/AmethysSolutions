'use client'

import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faSearch, faSpinner, faPlus, faEdit, faTrash, faSave,
  faTimes, faToggleOn, faToggleOff, faUndo, faChevronDown, faChevronUp,
  faPercent, faCoins, faExchangeAlt, faLayerGroup, faCalculator, faArrowRight,
} from '@fortawesome/free-solid-svg-icons'
import {
  getAdminPlans, createPlan, updatePlan, deletePlan, restorePlan,
  Plan, PlanCreateRequest, PlanUpdateRequest,
} from '@/lib/admin'

// ─── helpers ────────────────────────────────────────────────────────────────

const fmt = (cents: number) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100)

const emptyForm = (): Partial<PlanCreateRequest> => ({
  id: '',
  name: '',
  description: '',
  transactionFee: 70,
  monthlyFee: 0,
  minTransactions: 0,
  maxTransactions: null,
  downgradeTo: '',
  order: 0,
  transactionFeePercent: undefined,
  transactionFeeFixed: undefined,
  splitFee: undefined,
  useSeparateMistic: false,
})

// ─── FieldRow ────────────────────────────────────────────────────────────────

function FieldRow({
  label, hint, children,
}: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="block text-xs font-semibold text-foreground/70 uppercase tracking-wider">
        {label}
      </label>
      {hint && <p className="text-xs text-foreground/40">{hint}</p>}
      {children}
    </div>
  )
}

const inputCls =
  'w-full px-3 py-2 rounded-lg bg-background border border-foreground/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-foreground/30'

// ─── FeeSimulator ─────────────────────────────────────────────────────────────

const GATEWAY_FEE = 50 // R$ 0,50 fixo do gateway (Mistic) por saque

interface SimulatorProps {
  form: Partial<PlanCreateRequest>
}

function FeeSimulator({ form }: SimulatorProps) {
  const [simValue, setSimValue] = useState(10000) // R$ 100,00 em centavos

  const isBlack = !!(form.transactionFeePercent && form.transactionFeePercent > 0)

  // ── Taxa de transação (cobrada na cobrança/pagamento) ──────────────────────
  let txFee = 0
  if (isBlack) {
    const pct = Math.ceil((simValue * (form.transactionFeePercent ?? 0)) / 100)
    const fix = form.transactionFeeFixed ?? 0
    txFee = pct + fix
  } else {
    txFee = form.transactionFee ?? 0
  }

  const clientReceives = Math.max(0, simValue - txFee)   // líquido que cai no saldo

  // ── Taxa de saque (cobrada quando o usuário saca o saldo) ─────────────────
  const yourWithdrawCut = form.splitFee ?? 0             // sua parte
  const totalWithdrawFee = yourWithdrawCut + GATEWAY_FEE // total descontado do saldo
  const userGets = Math.max(0, clientReceives - totalWithdrawFee) // pix que cai na conta

  // ── Seu lucro ─────────────────────────────────────────────────────────────
  // Na transação: splitFee da transação (= txFee - GATEWAY_FEE para WHITE, ou valor configurado)
  // No saque: yourWithdrawCut
  // Aqui mostramos os dois separados
  const txSplit = isBlack
    ? (form.splitFee ?? 0)  // BLACK usa splitFee configurado
    : Math.max(0, txFee - GATEWAY_FEE) // WHITE: taxa fixa - custo gateway

  return (
    <div className="border border-primary/20 rounded-xl overflow-hidden bg-primary/3">
      <div className="px-4 py-3 bg-primary/8 border-b border-primary/15 flex items-center gap-2">
        <FontAwesomeIcon icon={faCalculator} className="text-primary text-sm" />
        <span className="text-sm font-semibold text-foreground/80">Simulador ao vivo</span>
        <span className="text-xs text-foreground/40 ml-auto">Muda em tempo real</span>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Input do valor */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-foreground/60 uppercase tracking-wider whitespace-nowrap">
            Valor da cobrança
          </label>
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40 text-sm font-medium">R$</span>
            <input
              type="number"
              min={0}
              step={1}
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-background border border-foreground/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              value={(simValue / 100).toFixed(2)}
              onChange={(e) => setSimValue(Math.round(parseFloat(e.target.value || '0') * 100))}
            />
          </div>
        </div>

        {/* Fluxo */}
        <div className="space-y-2 text-sm">
          {/* Cobrança */}
          <div className="flex items-center gap-2 p-3 rounded-lg bg-background border border-foreground/8">
            <div className="flex-1">
              <p className="text-xs text-foreground/50">Valor cobrado do cliente</p>
              <p className="font-bold text-foreground">{fmt(simValue)}</p>
            </div>
            <FontAwesomeIcon icon={faArrowRight} className="text-foreground/20 text-xs" />
            <div className="flex-1">
              <p className="text-xs text-foreground/50">
                {isBlack
                  ? `Taxa ${form.transactionFeePercent}%${form.transactionFeeFixed ? ` + ${fmt(form.transactionFeeFixed)}` : ''}`
                  : `Taxa fixa`}
              </p>
              <p className="font-bold text-red-400">− {fmt(txFee)}</p>
            </div>
            <FontAwesomeIcon icon={faArrowRight} className="text-foreground/20 text-xs" />
            <div className="flex-1 text-right">
              <p className="text-xs text-foreground/50">Cai no saldo</p>
              <p className="font-bold text-green-400">{fmt(clientReceives)}</p>
            </div>
          </div>

          {/* Saque */}
          {(yourWithdrawCut > 0 || true) && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-background border border-foreground/8">
              <div className="flex-1">
                <p className="text-xs text-foreground/50">Saldo disponível</p>
                <p className="font-bold text-foreground">{fmt(clientReceives)}</p>
              </div>
              <FontAwesomeIcon icon={faArrowRight} className="text-foreground/20 text-xs" />
              <div className="flex-1">
                <p className="text-xs text-foreground/50">
                  Taxa saque ({yourWithdrawCut > 0 ? `${fmt(yourWithdrawCut)} seu` : 'R$ 0,00 seu'} + R$ 0,50 gateway)
                </p>
                <p className="font-bold text-red-400">− {fmt(totalWithdrawFee)}</p>
              </div>
              <FontAwesomeIcon icon={faArrowRight} className="text-foreground/20 text-xs" />
              <div className="flex-1 text-right">
                <p className="text-xs text-foreground/50">PIX recebido</p>
                <p className="font-bold text-green-400">{fmt(Math.max(0, userGets))}</p>
              </div>
            </div>
          )}

          {/* Seu lucro */}
          <div className="grid grid-cols-2 gap-2 mt-1">
            <div className="p-3 rounded-lg bg-primary/8 border border-primary/15 text-center">
              <p className="text-xs text-foreground/50">Seu lucro na transação</p>
              <p className="font-bold text-primary text-base">{fmt(txSplit)}</p>
            </div>
            <div className="p-3 rounded-lg bg-primary/8 border border-primary/15 text-center">
              <p className="text-xs text-foreground/50">Seu lucro no saque</p>
              <p className="font-bold text-primary text-base">{fmt(yourWithdrawCut)}</p>
            </div>
          </div>
          <div className="p-3 rounded-lg bg-green-500/8 border border-green-500/15 text-center">
            <p className="text-xs text-foreground/50">Total que você lucra nessa operação</p>
            <p className="font-bold text-green-400 text-lg">{fmt(txSplit + yourWithdrawCut)}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Modal ───────────────────────────────────────────────────────────────────

interface ModalProps {
  plan: Plan | null   // null = criar novo
  onClose: () => void
  onSaved: () => void
}

function PlanModal({ plan, onClose, onSaved }: ModalProps) {
  const isEdit = !!plan
  const [form, setForm] = useState<Partial<PlanCreateRequest>>(
    plan
      ? {
          id: plan.id,
          name: plan.name,
          description: plan.description ?? '',
          transactionFee: plan.transactionFee,
          monthlyFee: plan.monthlyFee,
          minTransactions: plan.minTransactions,
          maxTransactions: plan.maxTransactions,
          downgradeTo: plan.downgradeTo ?? '',
          order: plan.order,
          transactionFeePercent: plan.transactionFeePercent ?? undefined,
          transactionFeeFixed: plan.transactionFeeFixed ?? undefined,
          splitFee: plan.splitFee ?? undefined,
          useSeparateMistic: plan.useSeparateMistic ?? false,
        }
      : emptyForm()
  )
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [feeMode, setFeeMode] = useState<'fixed' | 'percent'>(
    plan?.transactionFeePercent != null ? 'percent' : 'fixed'
  )

  const set = (k: keyof typeof form, v: any) => setForm((f) => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.id || !form.name) { setErr('ID e Nome são obrigatórios'); return }
    setSaving(true); setErr(null)
    try {
      if (isEdit) {
        const payload: PlanUpdateRequest = { ...form, downgradeTo: form.downgradeTo || null }
        await updatePlan(plan!.id, payload)
      } else {
        await createPlan({ ...(form as PlanCreateRequest), id: (form.id ?? '').toUpperCase(), downgradeTo: form.downgradeTo || null })
      }
      onSaved()
    } catch (e: any) {
      setErr(e.message || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-2xl border border-foreground/10 w-full max-w-2xl max-h-[92vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-foreground/10 flex-shrink-0">
          <h3 className="text-lg font-bold text-foreground">
            {isEdit ? `Editar — ${plan!.id}` : 'Novo Plano'}
          </h3>
          <button onClick={onClose} className="text-foreground/50 hover:text-foreground p-1 rounded-lg hover:bg-foreground/10">
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-6 py-5 space-y-5">
          {err && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{err}</div>
          )}

          {/* ID — apenas criação */}
          {!isEdit && (
            <FieldRow label="ID do Plano *" hint="Maiúsculas automáticas, ex: PREMIUM">
              <input
                className={inputCls}
                value={form.id}
                onChange={(e) => set('id', e.target.value.toUpperCase().replace(/\s/g, '_'))}
                placeholder="PREMIUM"
              />
            </FieldRow>
          )}

          {/* Nome */}
          <FieldRow label="Nome *">
            <input className={inputCls} value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Ex: Premium" />
          </FieldRow>

          {/* Descrição */}
          <FieldRow label="Descrição">
            <textarea className={inputCls + ' resize-none'} rows={2} value={form.description} onChange={(e) => set('description', e.target.value)} placeholder="Descrição opcional..." />
          </FieldRow>

          {/* Taxas principais */}
          <div className="space-y-4">
            {/* Toggle de modo */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-foreground/60 uppercase tracking-wider">Taxa por transação</span>
              <div className="flex rounded-lg border border-foreground/10 overflow-hidden text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setFeeMode('fixed')}
                  className={`px-3 py-1.5 transition-colors ${feeMode === 'fixed' ? 'bg-primary text-primary-foreground' : 'text-foreground/50 hover:bg-foreground/5'}`}
                >
                  Fixo (¢)
                </button>
                <button
                  type="button"
                  onClick={() => setFeeMode('percent')}
                  className={`px-3 py-1.5 transition-colors ${feeMode === 'percent' ? 'bg-primary text-primary-foreground' : 'text-foreground/50 hover:bg-foreground/5'}`}
                >
                  Percentual (%)
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {feeMode === 'fixed' ? (
                <FieldRow label="Valor fixo (¢)" hint={form.transactionFee ? fmt(form.transactionFee) : ''}>
                  <input
                    type="number"
                    min={0}
                    className={inputCls}
                    value={form.transactionFee ?? ''}
                    onChange={(e) => {
                      set('transactionFee', Number(e.target.value))
                      set('transactionFeePercent', null)
                      set('transactionFeeFixed', null)
                    }}
                    placeholder="70"
                  />
                </FieldRow>
              ) : (
                <FieldRow label="Percentual (%)" hint="Ex: 4 = 4% do valor">
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type="number"
                        min={0}
                        step={0.1}
                        className={inputCls + ' pr-7'}
                        value={form.transactionFeePercent ?? ''}
                        onChange={(e) => {
                          set('transactionFeePercent', e.target.value === '' ? null : Number(e.target.value))
                          set('transactionFee', 0)
                        }}
                        placeholder="4"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/40 text-xs font-bold">%</span>
                    </div>
                  </div>
                </FieldRow>
              )}
              <FieldRow label="Mensalidade (¢)" hint={form.monthlyFee ? fmt(form.monthlyFee) : 'Grátis'}>
                <input type="number" min={0} className={inputCls} value={form.monthlyFee ?? ''} onChange={(e) => set('monthlyFee', Number(e.target.value))} placeholder="0" />
              </FieldRow>
            </div>
          </div>

          {/* Limites de transação */}
          <div className="grid grid-cols-2 gap-4">
            <FieldRow label="Mín. transações / mês">
              <input type="number" min={0} className={inputCls} value={form.minTransactions ?? ''} onChange={(e) => set('minTransactions', Number(e.target.value))} placeholder="0" />
            </FieldRow>
            <FieldRow label="Máx. transações (vazio = ∞)">
              <input type="number" min={0} className={inputCls}
                value={form.maxTransactions === null || form.maxTransactions === undefined ? '' : form.maxTransactions}
                onChange={(e) => set('maxTransactions', e.target.value === '' ? null : Number(e.target.value))}
                placeholder="Ilimitado"
              />
            </FieldRow>
          </div>

          {/* Downgrade & Ordem */}
          <div className="grid grid-cols-2 gap-4">
            <FieldRow label="Plano de downgrade (ID)">
              <input className={inputCls} value={form.downgradeTo ?? ''} onChange={(e) => set('downgradeTo', e.target.value.toUpperCase())} placeholder="FREE" />
            </FieldRow>
            <FieldRow label="Ordem de exibição">
              <input type="number" className={inputCls} value={form.order ?? ''} onChange={(e) => set('order', Number(e.target.value))} placeholder="0" />
            </FieldRow>
          </div>

          {/* Taxa de saque fixa */}
          <div className="border border-foreground/10 rounded-xl p-4 space-y-3 bg-foreground/1">
            <p className="text-xs font-semibold text-foreground/60 uppercase tracking-wider flex items-center gap-2">
              <FontAwesomeIcon icon={faCoins} className="text-primary" />
              Taxa de Saque
            </p>
            <FieldRow
              label="Taxa fixa de saque (¢)"
              hint={`Sua parte. Total cobrado do usuário = esse valor + R$\u00a00,50 (gateway). ${form.splitFee ? `Seu lucro por saque: ${fmt(form.splitFee)}` : ''}`}
            >
              <input
                type="number"
                min={0}
                className={inputCls}
                value={form.splitFee ?? ''}
                onChange={(e) => set('splitFee', e.target.value === '' ? null : Number(e.target.value))}
                placeholder="Ex: 15 = R$ 0,15 seu + R$ 0,50 gateway = R$ 0,65 total"
              />
            </FieldRow>
          </div>

          {/* Avançado (taxa dinâmica / BLACK) */}
          <div className="border border-foreground/10 rounded-xl overflow-hidden">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between px-4 py-3 bg-foreground/3 hover:bg-foreground/5 transition-colors text-sm font-medium text-foreground/70"
            >
              <span className="flex items-center gap-2">
                <FontAwesomeIcon icon={faPercent} className="text-primary" />
                Configurações avançadas (taxa dinâmica / BLACK)
              </span>
              <FontAwesomeIcon icon={showAdvanced ? faChevronUp : faChevronDown} />
            </button>

            {showAdvanced && (
              <div className="px-4 py-4 space-y-4 bg-foreground/1">
                {feeMode === 'percent' && (
                  <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 text-xs text-primary/80">
                    Taxa percentual já configurada acima. Aqui você pode adicionar uma taxa fixa adicional por transação.
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  {feeMode === 'fixed' && (
                    <FieldRow label="Taxa percentual sobre transação (%)" hint="Ex: 6 = 6% do valor da transação">
                      <input type="number" min={0} step={0.1} className={inputCls}
                        value={form.transactionFeePercent ?? ''}
                        onChange={(e) => set('transactionFeePercent', e.target.value === '' ? null : Number(e.target.value))}
                        placeholder="Vazio = desabilitado"
                      />
                    </FieldRow>
                  )}
                  <FieldRow label="Taxa fixa adicional por transação (¢)" hint={form.transactionFeeFixed ? `= ${fmt(form.transactionFeeFixed)}` : 'Somada à taxa %'}>
                    <input type="number" min={0} className={inputCls}
                      value={form.transactionFeeFixed ?? ''}
                      onChange={(e) => set('transactionFeeFixed', e.target.value === '' ? null : Number(e.target.value))}
                      placeholder="200 = R$ 2,00"
                    />
                  </FieldRow>
                </div>
                <FieldRow label="Usar conta Mistic separada">
                  <button
                    type="button"
                    onClick={() => set('useSeparateMistic', !form.useSeparateMistic)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
                      form.useSeparateMistic
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-foreground/10 text-foreground/50 hover:border-foreground/20'
                    }`}
                  >
                    <FontAwesomeIcon icon={form.useSeparateMistic ? faToggleOn : faToggleOff} className="text-lg" />
                    {form.useSeparateMistic ? 'Ativado' : 'Desativado'}
                  </button>
                </FieldRow>
              </div>
            )}
          </div>

          {/* Simulador ao vivo */}
          <FeeSimulator form={form} />
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 py-4 border-t border-foreground/10 flex-shrink-0">
          <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-foreground/10 text-foreground/70 hover:bg-foreground/5 transition-colors text-sm">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-2 text-sm font-semibold"
          >
            {saving ? <FontAwesomeIcon icon={faSpinner} className="animate-spin" /> : <FontAwesomeIcon icon={faSave} />}
            {saving ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main Section ─────────────────────────────────────────────────────────────

export function PlanosSection() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [modal, setModal] = useState<{ open: boolean; plan: Plan | null }>({ open: false, plan: null })

  const load = async () => {
    setLoading(true); setErr(null)
    try {
      const res = await getAdminPlans({ includeInactive: showInactive })
      setPlans(res.data.plans)
    } catch (e: any) {
      setErr(e.message || 'Erro ao carregar planos')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [showInactive])

  const showSuccess = (msg: string) => {
    setSuccess(msg)
    setTimeout(() => setSuccess(null), 3000)
  }

  const handleDelete = async (plan: Plan) => {
    if (!confirm(`Desativar o plano "${plan.name}" (${plan.id})?`)) return
    try {
      await deletePlan(plan.id)
      showSuccess('Plano desativado.')
      load()
    } catch (e: any) { setErr(e.message) }
  }

  const handleRestore = async (plan: Plan) => {
    try {
      await restorePlan(plan.id)
      showSuccess('Plano reativado.')
      load()
    } catch (e: any) { setErr(e.message) }
  }

  const filtered = plans.filter((p) => {
    if (!search) return true
    const q = search.toLowerCase()
    return p.id.toLowerCase().includes(q) || p.name.toLowerCase().includes(q) || (p.description ?? '').toLowerCase().includes(q)
  })

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <h2 className="text-xl font-bold text-foreground">Gerenciar Planos</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowInactive(!showInactive)}
            className={`px-3 py-2 rounded-lg text-sm border transition-colors flex items-center gap-2 ${
              showInactive ? 'border-primary/40 bg-primary/10 text-primary' : 'border-foreground/10 text-foreground/60 hover:bg-foreground/5'
            }`}
          >
            <FontAwesomeIcon icon={faLayerGroup} />
            {showInactive ? 'Mostrando inativos' : 'Só ativos'}
          </button>
          <button onClick={load} className="px-3 py-2 rounded-lg border border-foreground/10 text-foreground/70 hover:bg-foreground/5 transition-colors text-sm">
            Atualizar
          </button>
          <button
            onClick={() => setModal({ open: true, plan: null })}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center gap-2 text-sm font-semibold"
          >
            <FontAwesomeIcon icon={faPlus} /> Novo Plano
          </button>
        </div>
      </div>

      {/* Alerts */}
      {success && <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm">{success}</div>}
      {err && <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{err}</div>}

      {/* Search */}
      <div className="relative">
        <FontAwesomeIcon icon={faSearch} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40 text-sm" />
        <input
          className="w-full pl-9 pr-4 py-2 rounded-lg bg-foreground/3 border border-foreground/10 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-foreground/30"
          placeholder="Buscar por ID, nome ou descrição…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-foreground/10 bg-foreground/2 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-sm">
            <thead className="bg-foreground/5 border-b border-foreground/10">
              <tr>
                {['ID', 'Nome', 'Taxa Transação', 'Mensalidade', 'Transações', 'Taxa Dinâmica', 'Split', 'Ordem', 'Status', 'Ações'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-foreground/50 uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-foreground/5">
              {loading ? (
                <tr><td colSpan={10} className="py-10 text-center"><FontAwesomeIcon icon={faSpinner} className="text-primary animate-spin text-xl" /></td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={10} className="py-10 text-center text-foreground/40">Nenhum plano encontrado</td></tr>
              ) : filtered.map((p) => (
                <tr key={p.id} className={`hover:bg-foreground/5 transition-colors ${!p.active ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3 font-mono font-bold text-foreground/80">{p.id}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-foreground">{p.name}</div>
                    {p.description && <div className="text-xs text-foreground/40 mt-0.5 max-w-[160px] truncate">{p.description}</div>}
                  </td>
                  <td className="px-4 py-3 text-foreground/70">{fmt(p.transactionFee)}</td>
                  <td className="px-4 py-3 text-foreground/70">{p.monthlyFee ? fmt(p.monthlyFee) : <span className="text-foreground/30">—</span>}</td>
                  <td className="px-4 py-3 text-foreground/60 text-xs">
                    {p.minTransactions} – {p.maxTransactions === null ? '∞' : p.maxTransactions}
                  </td>
                  <td className="px-4 py-3 text-xs text-foreground/60">
                    {p.transactionFeePercent != null
                      ? <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">{p.transactionFeePercent}% {p.transactionFeeFixed ? `+ ${fmt(p.transactionFeeFixed)}` : ''}</span>
                      : <span className="text-foreground/25">—</span>}
                  </td>
                  <td className="px-4 py-3 text-foreground/60 text-xs">
                    {p.splitFee != null ? fmt(p.splitFee) : <span className="text-foreground/25">—</span>}
                  </td>
                  <td className="px-4 py-3 text-foreground/50">{p.order}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${p.active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                      {p.active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => setModal({ open: true, plan: p })}
                        title="Editar"
                        className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors"
                      >
                        <FontAwesomeIcon icon={faEdit} />
                      </button>
                      {p.active ? (
                        <button
                          onClick={() => handleDelete(p)}
                          title="Desativar"
                          className="p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                        >
                          <FontAwesomeIcon icon={faTrash} />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleRestore(p)}
                          title="Reativar"
                          className="p-1.5 rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors"
                        >
                          <FontAwesomeIcon icon={faUndo} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-foreground/30">{filtered.length} plano(s) exibido(s)</p>

      {/* Modal */}
      {modal.open && (
        <PlanModal
          plan={modal.plan}
          onClose={() => setModal({ open: false, plan: null })}
          onSaved={() => { setModal({ open: false, plan: null }); showSuccess(modal.plan ? 'Plano atualizado!' : 'Plano criado!'); load() }}
        />
      )}
    </div>
  )
}

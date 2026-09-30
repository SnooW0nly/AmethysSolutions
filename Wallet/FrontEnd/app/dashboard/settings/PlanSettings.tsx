'use client'

import { useState, useEffect, useCallback } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faSpinner, faCheck, faCreditCard, faSync, faArrowUp } from '@fortawesome/free-solid-svg-icons'
import { getMyPlan, updatePlanSettings, getAvailablePlans, upgradePlan, AvailablePlan } from '@/lib/user-plan'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { toastSuccess, toastError } from '@/lib/toast'
import { useWallet } from '@/components/providers/wallet-provider'
import { useAuth } from '@/hooks/useAuth'

export function PlanSettings() {
  const { balance, refreshWallet } = useWallet()
  const { refreshUser } = useAuth()
  const [planInfo, setPlanInfo] = useState<any>(null)
  const [availablePlans, setAvailablePlans] = useState<AvailablePlan[]>([])
  const [loading, setLoading] = useState(false)
  const [autoRenew, setAutoRenew] = useState(true)
  const [autoUpgrade, setAutoUpgrade] = useState(false)
  const [upgrading, setUpgrading] = useState(false)
  const [selectedPlan, setSelectedPlan] = useState<string>('')

  const loadPlanInfo = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true)
      const [planResponse, plansResponse] = await Promise.all([
        getMyPlan(),
        getAvailablePlans(),
      ])
      setPlanInfo(planResponse.data)
      setAvailablePlans(plansResponse.data?.plans ?? [])
      setAutoRenew(planResponse.data.settings.autoRenew)
      setAutoUpgrade(planResponse.data.settings.autoUpgrade)
    } catch (err) {
      if (showLoading) {
        toastError(err instanceof Error ? err.message : 'Erro ao carregar informações do plano')
      }
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPlanInfo()

    // Atualizar dados quando a aba voltar ao foco
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        loadPlanInfo(false) // Não mostrar loading ao voltar para a aba
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [loadPlanInfo])

  const handleToggleAutoRenew = async (checked: boolean) => {
    try {
      setLoading(true)
      await updatePlanSettings({ autoRenew: checked })
      setAutoRenew(checked)
      toastSuccess('Renovação automática atualizada com sucesso!')
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao atualizar renovação automática')
      setAutoRenew(!checked) // Reverter
    } finally {
      setLoading(false)
    }
  }

  const handleToggleAutoUpgrade = async (checked: boolean) => {
    try {
      setLoading(true)
      await updatePlanSettings({ autoUpgrade: checked })
      setAutoUpgrade(checked)
      toastSuccess('Upgrade automático atualizado com sucesso!')
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao atualizar upgrade automático')
      setAutoUpgrade(!checked) // Reverter
    } finally {
      setLoading(false)
    }
  }

  const handleUpgrade = async () => {
    if (!selectedPlan) return

    try {
      setUpgrading(true)
      await upgradePlan(selectedPlan)
      toastSuccess('Plano atualizado com sucesso!')

      // Atualizar dados em paralelo para refletir mudanças imediatamente
      await Promise.all([
        loadPlanInfo(),
        refreshUser(),
        refreshWallet()
      ])

      setSelectedPlan('')
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erro ao fazer upgrade do plano')
    } finally {
      setUpgrading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value / 100)
  }

  const currentPlanId = planInfo?.currentPlan?.id || 'FREE'
  const currentPlanIndex = availablePlans.findIndex((p) => p.id === currentPlanId)
  const upgradeablePlans = availablePlans.filter((p, index) => index > currentPlanIndex)

  if (loading && !planInfo) {
    return (
      <div className="flex items-center justify-center py-8">
        <FontAwesomeIcon icon={faSpinner} className="w-6 h-6 text-primary animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Plano Atual */}
      <div className="border border-foreground/10 rounded-xl bg-foreground/2 p-6">
        <div className="flex items-center gap-3 mb-4">
          <FontAwesomeIcon icon={faCreditCard} className="text-foreground/60 w-5 h-5" />
          <div>
            <h3 className="text-sm font-semibold text-foreground">Plano Atual</h3>
            <p className="text-xs text-foreground/60">Informações do seu plano atual</p>
          </div>
        </div>

        {planInfo && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground/70">Plano</span>
              <span className="text-sm font-semibold text-foreground">{planInfo.currentPlan.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground/70">Taxa por Transação</span>
              <span className="text-sm font-semibold text-foreground">
                {planInfo.currentPlan.transactionFeeInReais}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground/70">Mensalidade</span>
              <span className="text-sm font-semibold text-foreground">
                {planInfo.currentPlan.monthlyFeeInReais}
              </span>
            </div>
            {planInfo.planDates.daysRemaining !== null && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-foreground/70">Dias Restantes</span>
                <span className="text-sm font-semibold text-foreground">
                  {planInfo.planDates.daysRemaining} dias
                </span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground/70">Saldo Disponível</span>
              <span className="text-sm font-semibold text-foreground">
                {balance ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(balance.balance.total / 100) : 'R$ 0,00'}
              </span>
            </div>
          </div>
        )}
      </div>

      <Separator />

      {/* Configurações */}
      <div className="border border-foreground/10 rounded-xl bg-foreground/2 p-6">
        <div className="flex items-center gap-3 mb-4">
          <FontAwesomeIcon icon={faSync} className="text-foreground/60 w-5 h-5" />
          <div>
            <h3 className="text-sm font-semibold text-foreground">Configurações Automáticas</h3>
            <p className="text-xs text-foreground/60">Gerencie as configurações automáticas do seu plano</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">Renovação Automática</p>
              <p className="text-xs text-foreground/60 mt-1">
                Renova automaticamente o plano quando expirar
              </p>
            </div>
            <Switch checked={autoRenew} onCheckedChange={handleToggleAutoRenew} disabled={loading} />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">Upgrade Automático</p>
              <p className="text-xs text-foreground/60 mt-1">
                Faz upgrade automaticamente quando atingir o limite de transações
              </p>
            </div>
            <Switch checked={autoUpgrade} onCheckedChange={handleToggleAutoUpgrade} disabled={loading} />
          </div>
        </div>
      </div>

      {/* Planos Disponíveis */}
      {
        upgradeablePlans.length > 0 && (
          <>
            <Separator />
            <div className="border border-foreground/10 rounded-xl bg-foreground/2 p-6">
              <div className="flex items-center gap-3 mb-4">
                <FontAwesomeIcon icon={faArrowUp} className="text-foreground/60 w-5 h-5" />
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Planos Disponíveis</h3>
                  <p className="text-xs text-foreground/60">Escolha um plano superior para fazer upgrade</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                {upgradeablePlans.map((plan) => (
                  <div
                    key={plan.id}
                    onClick={() => setSelectedPlan(plan.id)}
                    className={`border rounded-xl p-4 cursor-pointer transition-all ${selectedPlan === plan.id
                      ? 'border-primary bg-primary/10'
                      : 'border-foreground/10 bg-foreground/5 hover:border-foreground/20 hover:bg-foreground/10'
                      }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-lg font-bold text-foreground">{plan.name}</h4>
                      {selectedPlan === plan.id && (
                        <FontAwesomeIcon icon={faCheck} className="text-primary w-5 h-5" />
                      )}
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-foreground/60">Taxa por Transação</span>
                        <span className="text-sm font-semibold text-foreground">
                          R$ {plan.transactionFeeInReais}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-foreground/60">Mensalidade</span>
                        <span className="text-sm font-semibold text-foreground">
                          R$ {plan.monthlyFeeInReais}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-foreground/60">Limite Mínimo de Transações</span>
                        <span className="text-sm font-semibold text-foreground">
                          {plan.minTransactions.toLocaleString('pt-BR')}/mês
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-foreground/60">Limite Máximo Sugerido</span>
                        <span className="text-sm font-semibold text-foreground">
                          {plan.maxTransactions !== null
                            ? `${plan.maxTransactions.toLocaleString('pt-BR')}/mês`
                            : 'Sem Limite'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {selectedPlan && (
                <>
                  <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 mb-4">
                    <p className="text-sm text-yellow-600">
                      <strong>Atenção:</strong> O valor da mensalidade será debitado do seu saldo. Se o saldo
                      for insuficiente, a operação falhará.
                    </p>
                    {planInfo && (
                      <p className="text-sm text-foreground/70 mt-2">
                        Saldo atual: {planInfo.balanceInReais}
                      </p>
                    )}
                  </div>

                  <button
                    onClick={handleUpgrade}
                    disabled={upgrading}
                    className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                  >
                    {upgrading ? (
                      <>
                        <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
                        Fazendo upgrade...
                      </>
                    ) : (
                      <>
                        <FontAwesomeIcon icon={faArrowUp} />
                        Fazer Upgrade para {upgradeablePlans.find(p => p.id === selectedPlan)?.name}
                      </>
                    )}
                  </button>
                </>
              )}
            </div>
          </>
        )
      }
    </div >
  )
}


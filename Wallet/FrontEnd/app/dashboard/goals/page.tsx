'use client'

import { useState, useEffect } from 'react'
import { SidebarDashboard } from '@/components/sidebar-dashboard'
import { DashboardTopbar } from '@/components/dashboard-topbar'
import { DashboardHeader } from '@/components/dashboard-header'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faGift, faTrophy, faRocket, faLock, faCheckCircle, faStar } from '@fortawesome/free-solid-svg-icons'
import { getBalance } from '@/lib/wallet'
import { RippleButton } from '@/components/ripple-button'
import { useAuth } from '@/hooks/useAuth'

const rewards = [
  { value: 10000, label: 'R$ 10.000', title: 'Pulseira Amethys', description: 'Exclusividade para quem começa a brilhar.', icon: faStar },
  { value: 30000, label: 'R$ 30.000', title: 'Placa 30k', description: 'O primeiro grande marco da sua jornada.', icon: faTrophy },
  { value: 50000, label: 'R$ 50.000', title: 'Placa 50k', description: 'Consolidando seu sucesso no digital.', icon: faTrophy },
  { value: 100000, label: 'R$ 100.000', title: 'Placa 100k', description: 'Bem-vindo à elite dos 6 dígitos.', icon: faTrophy },
  { value: 500000, label: 'R$ 500.000', title: 'Placa 500k', description: 'Meio milhão faturado. Incrível.', icon: faTrophy },
  { value: 1000000, label: 'R$ 1.000.000', title: 'Placa 1M', description: 'O clube do milhão é para poucos.', icon: faRocket },
  { value: 5000000, label: 'R$ 5.000.000', title: 'Placa 5M', description: 'Lenda viva do mercado.', icon: faRocket },
  { value: 10000000, label: 'R$ 10.000.000', title: 'Placa 10M', description: 'O topo absoluto.', icon: faRocket },
]

export default function GoalsPage() {
  const { user } = useAuth() // Usar useAuth para manter estado do usuário sincronizado
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [totalReceived, setTotalReceived] = useState<number | null>(null) // Total recebido (entradas), não saldo atual
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await getBalance()
        if (res.success) {
          // Usar totalReceived (entradas) ao invés de balance.total (saldo atual)
          // Isso garante que as metas reflitam apenas o faturamento/recebimentos
          const received = res.data.statistics?.totalReceived || 0
          setTotalReceived(received / 100) // Converter de centavos para reais
        }
      } catch (error) {
        console.error('Erro ao buscar dados de metas', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  // Calculate progress to next goal usando total recebido (entradas)
  const nextGoal = rewards.find(r => r.value > (totalReceived || 0)) || rewards[rewards.length - 1]
  const progress = totalReceived !== null ? Math.min(100, (totalReceived / nextGoal.value) * 100) : 0

  return (
    <div className="flex h-screen bg-background text-foreground">
      <SidebarDashboard open={sidebarOpen} onOpenChange={setSidebarOpen} />

      <div className="flex-1 flex flex-col overflow-hidden relative">
        <DashboardTopbar onOpenSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main className="flex-1 overflow-y-auto bg-background/50 backdrop-blur-sm">
          <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
            <DashboardHeader />

            {/* Rewards Grid */}
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="h-10 w-1 bg-primary rounded-full" />
                <h2 className="text-2xl font-bold">Galeria de Prêmios</h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {rewards.map((reward, index) => {
                  const isUnlocked = (totalReceived || 0) >= reward.value
                  const isNext = !isUnlocked && reward === nextGoal

                  return (
                    <div
                      key={reward.value}
                      className={`group relative overflow-hidden rounded-2xl border transition-all duration-300 ${isUnlocked
                        ? 'bg-primary/5 border-primary/30 hover:border-primary/50'
                        : isNext
                          ? 'bg-card border-primary/20 shadow-[0_0_30px_-10px_rgba(var(--primary),0.3)] scale-[1.02]'
                          : 'bg-card/50 border-border/50 opacity-70 hover:opacity-100'
                        }`}
                    >
                      {/* Status Badge */}
                      <div className="absolute top-4 right-4">
                        {isUnlocked ? (
                          <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center text-green-500">
                            <FontAwesomeIcon icon={faCheckCircle} />
                          </div>
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-muted/20 flex items-center justify-center text-muted-foreground">
                            <FontAwesomeIcon icon={faLock} className="w-3 h-3" />
                          </div>
                        )}
                      </div>

                      <div className="p-6 space-y-4">
                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl transition-transform group-hover:scale-110 ${isUnlocked ? 'bg-primary/20 text-primary' : 'bg-muted/20 text-muted-foreground'
                          }`}>
                          <FontAwesomeIcon icon={reward.icon} />
                        </div>

                        <div>
                          <h3 className={`text-xl font-bold mb-1 ${isUnlocked ? 'text-primary' : 'text-foreground'}`}>
                            {reward.title}
                          </h3>
                          <p className="text-sm font-medium text-muted-foreground mb-3">
                            {reward.label} em vendas
                          </p>
                          <p className="text-xs text-muted-foreground/80 leading-relaxed">
                            {reward.description}
                          </p>
                        </div>
                      </div>

                      {/* Background Glow */}
                      {isUnlocked && (
                        <div className="absolute -bottom-10 -right-10 w-32 h-32 bg-primary/10 rounded-full blur-2xl" />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Support CTA */}
            <div className="rounded-2xl bg-card border border-border p-8 flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-6">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary text-2xl">
                  <FontAwesomeIcon icon={faGift} />
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2">Já atingiu uma meta?</h3>
                  <p className="text-muted-foreground max-w-xl">
                    Se você já alcançou o faturamento necessário para uma das placas, entre em contato com nosso time de suporte para solicitar o envio do seu prêmio.
                  </p>
                </div>
              </div>
              <RippleButton
                onClick={() => window.open('https://discord.gg/9vBqJj45gV', '_blank')}
                className="whitespace-nowrap px-4 py-2 text-sm bg-primary text-primary-foreground font-medium rounded-xl hover:bg-primary/90 transition-all shadow-lg shadow-primary/20"
              >
                Solicitar Prêmio
              </RippleButton>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

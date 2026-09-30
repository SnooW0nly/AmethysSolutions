'use client'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBullseye } from '@fortawesome/free-solid-svg-icons'
import { useRouter } from 'next/navigation'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

interface NextGoalProps {
  currentValue: number // em centavos
  goalValue: number // em centavos
  goalName?: string
}

export function NextGoal({ currentValue = 0, goalValue, goalName }: NextGoalProps) {
  const router = useRouter()

  // Converter para reais para cálculo
  const currentInReais = currentValue / 100
  const goalInReais = goalValue / 100
  const percentage = goalInReais > 0 ? Math.min((currentInReais / goalInReais) * 100, 100) : 0
  const remaining = Math.max(goalInReais - currentInReais, 0)

  const formatCurrency = (value: number) => {
    // value já está em reais
    if (value >= 1000000) {
      return `R$ ${(value / 1000000).toFixed(1)}M`
    }
    if (value >= 1000) {
      return `R$ ${(value / 1000).toFixed(0)}K`
    }
    return `R$ ${value.toFixed(0)}`
  }

  const handleClick = () => {
    router.push('/dashboard/goals')
  }

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <div
            onClick={handleClick}
            className="hidden md:flex items-center gap-3 px-2 py-1.5 cursor-pointer hover:opacity-80 transition-all group"
          >
            <div className="flex items-center gap-2">
              <div className="flex flex-col justify-center">
                <span className="text-[10px] text-foreground/50 uppercase tracking-wider font-medium leading-none mb-0.5">Próxima Meta</span>
                <span className="text-[11px] font-bold text-foreground leading-none">{goalName || 'Conquistar o Mundo'}</span>
              </div>
            </div>

            <div className="flex flex-col gap-1 min-w-[100px]">
              <div className="flex items-center justify-between w-full">
                <span className="text-[10px] font-bold text-primary">
                  {Math.round(percentage)}%
                </span>
                <span className="text-[10px] text-foreground/40">
                  {formatCurrency(goalInReais)}
                </span>
              </div>
              <div className="h-1.5 w-full bg-foreground/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary/80 to-primary rounded-full transition-all duration-500 ease-out relative"
                  style={{ width: `${percentage}%` }}
                >
                  <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite]" />
                </div>
              </div>
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="center" className="p-4 bg-background/80 backdrop-blur-md border border-foreground/10 shadow-2xl rounded-2xl w-64">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-foreground/5 pb-2">
              <p className="text-xs font-bold text-foreground uppercase tracking-wider">Progresso da Meta</p>
              <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full">{Math.round(percentage)}%</span>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Atual</span>
                <span className="font-mono font-medium text-foreground">R$ {currentInReais.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="w-full h-1 bg-foreground/5 rounded-full overflow-hidden">
                <div className="h-full bg-primary/50" style={{ width: `${percentage}%` }} />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Objetivo</span>
                <span className="font-mono font-medium text-foreground">R$ {goalInReais.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>

            <div className="pt-2 mt-2 border-t border-foreground/5 flex items-center justify-between text-xs bg-foreground/2 p-2 rounded-lg">
              <span className="text-muted-foreground font-medium">Falta apenas</span>
              <span className="font-mono font-bold text-primary">R$ {remaining.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

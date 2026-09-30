'use client'

import { useState, useEffect } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBars } from '@fortawesome/free-solid-svg-icons'
import { UserMenu } from './user-menu'
import { NextGoal } from './next-goal'
import { useAuth } from '@/hooks/useAuth'
import { getGoals } from '@/lib/goals'

interface DashboardTopbarProps {
  onOpenSidebar?: () => void
}

export function DashboardTopbar({ onOpenSidebar }: DashboardTopbarProps) {
  const { user } = useAuth()
  const [goalsData, setGoalsData] = useState<{ currentValue: number; goalValue: number; goalLabel: string } | null>(null)

  useEffect(() => {
    const loadNextGoal = async () => {
      try {
        const data = await getGoals()
        if (data.currentGoal) {
          setGoalsData({
            currentValue: data.currentValue,
            goalValue: data.currentGoal.value,
            goalLabel: data.currentGoal.label
          })
        } else if (data.nextGoal) {
          setGoalsData({
            currentValue: data.currentValue,
            goalValue: data.nextGoal.value,
            goalLabel: data.nextGoal.label
          })
        }
      } catch (error) {
        console.error('Erro ao carregar próxima meta:', error)
      }
    }

    if (user) {
      loadNextGoal()
    }
  }, [user?._id])

  return (
    <header className="flex items-center justify-between h-14 px-4 lg:px-6 border-b border-foreground/10 bg-background sticky top-0 z-50">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <button
          className="lg:hidden p-2 rounded-md hover:bg-foreground/5 transition-colors flex-shrink-0"
          aria-label="Abrir menu"
          onClick={onOpenSidebar}
        >
          <FontAwesomeIcon icon={faBars} className="w-4 h-4 text-foreground" />
        </button>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        {user && goalsData && (
          <>
            <NextGoal
              currentValue={goalsData.currentValue}
              goalValue={goalsData.goalValue}
              goalName={goalsData.goalLabel}
            />
            <div className="h-6 w-px bg-foreground/10 mx-2 hidden md:block" />
          </>
        )}
        <UserMenu />
      </div>
    </header>
  )
}


'use client'

import { useState } from 'react'
import { SidebarDashboard } from '@/components/sidebar-dashboard'
import { DashboardTopbar } from '@/components/dashboard-topbar'
import { DashboardHeader } from '@/components/dashboard-header'
import { DashboardInicio } from '@/components/dashboard-inicio'
import { ErrorBoundary } from '@/components/error-boundary'

export default function DashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <ErrorBoundary>
      <div className="flex h-screen bg-background">
        <SidebarDashboard open={sidebarOpen} onOpenChange={setSidebarOpen} />

        <div className="flex-1 flex flex-col overflow-hidden">
          <DashboardTopbar onOpenSidebar={() => setSidebarOpen(!sidebarOpen)} />

          <main data-dashboard className="flex-1 overflow-auto">
            <div className="p-6 lg:p-8 w-full">
              <ErrorBoundary>
                <DashboardHeader />
              </ErrorBoundary>
              <ErrorBoundary>
                <DashboardInicio />
              </ErrorBoundary>
            </div>
          </main>
        </div>
      </div>
    </ErrorBoundary>
  )
}

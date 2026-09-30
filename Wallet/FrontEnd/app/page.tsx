'use client'

// Force rebuild

import { Hero } from '@/components/home/hero'
import { CTASection } from '@/components/home/cta'
import { BenefitsSecuritySection } from '@/components/home/benefits-security'
import { BenefitsPrivacySection } from '@/components/home/benefits-privacy'
import { BenefitsPraticiadeSection } from '@/components/home/benefits-praticidade'
import { BenefitsCheckoutSection } from '@/components/home/benefits-checkout'
import { SecurityFeaturesSection } from '@/components/home/security-features'
import { DashboardPreview } from '@/components/home/dashboard-preview'
import { StatsSection } from '@/components/home/stats-section'
import { DiscordBotSection } from '@/components/home/discord-bot-section'
import { ErrorBoundary } from '@/components/error-boundary'

export default function Home() {
  return (
    <main className="flex flex-col">
      <Hero />

      <DashboardPreview />

      <ErrorBoundary fallback={null}>
        <StatsSection />
      </ErrorBoundary>

      <BenefitsPrivacySection /> {/* Esquerda */}

      <SecurityFeaturesSection /> {/* Esquerda */}

      <BenefitsPraticiadeSection /> {/* Direita */}

      <BenefitsSecuritySection /> {/* Esquerda */}

      {/* <BenefitsCheckoutSection /> */} {/* Esquerda */}

      <DiscordBotSection /> {/* Direita */}

      <CTASection />
    </main>
  )
}

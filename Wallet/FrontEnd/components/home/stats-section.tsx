'use client'

import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

interface Stats {
    totalMoneyMoved: number
    activeRegistrations: number
    totalTransactions: number
    generatedAt: string
}

function useCountUp(end: number, duration: number = 2000, delay: number = 0) {
    const [count, setCount] = useState(0)
    const countRef = useRef(0)
    const startTimeRef = useRef<number | null>(null)
    const [hasStarted, setHasStarted] = useState(false)

    useEffect(() => {
        if (end === 0) return

        // Wait for delay before starting
        const delayTimer = setTimeout(() => {
            setHasStarted(true)
        }, delay)

        return () => clearTimeout(delayTimer)
    }, [end, delay])

    useEffect(() => {
        if (!hasStarted || end === 0) return

        const animate = (timestamp: number) => {
            if (!startTimeRef.current) startTimeRef.current = timestamp
            const progress = Math.min((timestamp - startTimeRef.current) / duration, 1)

            // Easing function for smooth animation
            const easeOutQuart = 1 - Math.pow(1 - progress, 4)
            countRef.current = Math.floor(easeOutQuart * end)
            setCount(countRef.current)

            if (progress < 1) {
                requestAnimationFrame(animate)
            }
        }

        startTimeRef.current = null
        requestAnimationFrame(animate)
    }, [hasStarted, end, duration])

    return count
}

function formatCurrency(value: number): string {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(value / 100)
}

function formatNumber(value: number): string {
    return new Intl.NumberFormat('pt-BR').format(value)
}

export function StatsSection() {
    const [stats, setStats] = useState<Stats | null>(null)
    const [loading, setLoading] = useState(true)
    const [isInView, setIsInView] = useState(false)

    const fetchStats = async () => {
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:3001'
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), 5000)

            const response = await fetch(`${backendUrl}/api/v1/public-stats`, {
                cache: 'no-store',
                signal: controller.signal
            })

            clearTimeout(timeoutId)

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }
            const data = await response.json()
            if (data.success) {
                setStats(data.data)
            }
        } catch (error: any) {
            // Ignorar erros silenciosamente para não quebrar a página
            if (error.name !== 'AbortError') {
                console.error('Erro ao buscar estatísticas:', error)
            }
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchStats()
        // Refresh every 30 seconds
        const interval = setInterval(fetchStats, 30000)
        return () => clearInterval(interval)
    }, [])

    // Only start counting when in view
    const animatedMoney = useCountUp(isInView ? (stats?.totalMoneyMoved || 0) : 0, 2500, 300)
    const animatedRegistrations = useCountUp(isInView ? (stats?.activeRegistrations || 0) : 0, 2000, 400)
    const animatedTransactions = useCountUp(isInView ? (stats?.totalTransactions || 0) : 0, 2200, 500)

    // Se ainda está carregando, não mostrar nada
    if (loading) {
        return null
    }

    // Se não conseguiu carregar as estatísticas, não mostrar nada
    if (!stats) {
        return null
    }

    return (
        <motion.section
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            onViewportEnter={() => setIsInView(true)}
            className="mt-8 md:mt-12 flex flex-col items-center justify-center"
        >
            {/* Header with divider lines */}
            <div className="w-full flex flex-col items-center">
                <div className="flex items-center w-full">
                    <div className="flex-grow border-t border-foreground/10"></div>
                    <span className="mx-4 text-primary font-bold text-sm uppercase tracking-wider">
                        Estatísticas em tempo real
                    </span>
                    <div className="flex-grow border-t border-foreground/10"></div>
                </div>
                <span className="block text-foreground/60 text-xs text-center mt-1">
                    Informações atualizadas a cada 30 segundos
                </span>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 gap-8 md:grid-cols-3 w-full justify-center items-center text-center mt-8">
                {/* Total Money Moved */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
                >
                    <p className="text-foreground text-4xl md:text-5xl font-bold mb-2">
                        {formatCurrency(animatedMoney)}
                    </p>
                    <span className="text-foreground/70 text-sm">movimentados</span>
                </motion.div>

                {/* Active Registrations */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
                >
                    <p className="text-foreground text-4xl md:text-5xl font-bold mb-2">
                        {formatNumber(animatedRegistrations)}
                    </p>
                    <span className="text-foreground/70 text-sm">contas ativas</span>
                </motion.div>

                {/* Total Transactions */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
                >
                    <p className="text-foreground text-4xl md:text-5xl font-bold mb-2">
                        {formatNumber(animatedTransactions)}
                    </p>
                    <span className="text-foreground/70 text-sm">transações</span>
                </motion.div>
            </div>

            {/* Decorative corner lines */}
            <div className="flex items-start w-full justify-between mt-4">
                <div className="flex flex-col items-start">
                    <div className="w-[1px] h-8 bg-foreground/10"></div>
                    <div className="w-8 h-[1px] bg-foreground/10"></div>
                </div>
                <div />
                <div className="flex flex-col items-end">
                    <div className="w-[1px] h-8 bg-foreground/10"></div>
                    <div className="w-8 h-[1px] bg-foreground/10"></div>
                </div>
            </div>
        </motion.section>
    )
}

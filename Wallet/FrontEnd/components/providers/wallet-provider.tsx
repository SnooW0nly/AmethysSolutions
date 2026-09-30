'use client'

import { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react'
import { getBalance, listPayments, listWithdraws, getUserData, listTransactions, Transaction, BalanceData, Payment, Withdraw, UserData } from '@/lib/wallet'
import { useAuth } from '@/hooks/useAuth'

interface WalletContextType {
    balance: BalanceData | null
    userData: UserData | null
    payments: Payment[]
    withdraws: Withdraw[]
    internalTransfers: Transaction[]
    loading: boolean
    refreshWallet: () => Promise<void>
}

const WalletContext = createContext<WalletContextType | undefined>(undefined)

// Intervalo de polling em ms (10 segundos para atualização mais rápida)
const POLL_INTERVAL = 10000

export function WalletProvider({ children }: { children: ReactNode }) {
    const { user, isAuthenticated } = useAuth()
    const [balance, setBalance] = useState<BalanceData | null>(null)
    const [userData, setUserData] = useState<UserData | null>(null)
    const [payments, setPayments] = useState<Payment[]>([])
    const [withdraws, setWithdraws] = useState<Withdraw[]>([])
    const [internalTransfers, setInternalTransfers] = useState<Transaction[]>([])
    const [loading, setLoading] = useState(false)

    const fetchingRef = useRef(false)
    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

    const loadWalletData = useCallback(async (showLoading = true) => {
        if (!isAuthenticated || !user) return
        if (fetchingRef.current) return

        try {
            fetchingRef.current = true
            if (showLoading) setLoading(true)

            const [balanceRes, userDataRes, paymentsRes, withdrawsRes, transactionsRes] = await Promise.all([
                getBalance(),
                getUserData(),
                listPayments({ limit: 20 }),
                listWithdraws({ limit: 20 }),
                listTransactions({ limit: 50 })
            ])

            if (balanceRes.success) setBalance(balanceRes.data)
            if (userDataRes.success) setUserData(userDataRes.data)
            if (paymentsRes.success) setPayments(paymentsRes.data.payments)
            if (withdrawsRes.success) setWithdraws(withdrawsRes.data.withdraws)
            if (transactionsRes.success) {
                const internal = transactionsRes.data.transactions.filter(t =>
                    t.transactionType === 'internal_transfer_sent' || t.transactionType === 'internal_transfer_received'
                )
                setInternalTransfers(internal)
            }

        } catch (error) {
            console.error('Erro ao carregar dados da carteira:', error)
        } finally {
            if (showLoading) setLoading(false)
            fetchingRef.current = false
        }
    }, [isAuthenticated, user])

    // Carregar dados iniciais quando autenticado
    useEffect(() => {
        if (isAuthenticated && user) {
            loadWalletData()
        } else {
            setBalance(null)
            setUserData(null)
            setPayments([])
            setWithdraws([])
        }
    }, [isAuthenticated, user, loadWalletData])

    // Polling automático - continua em segundo plano para notificações
    useEffect(() => {
        if (!isAuthenticated || !user) return

        const BACKGROUND_POLL_INTERVAL = 30000 // 30 segundos em segundo plano

        const startPolling = (interval: number) => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current)
            }
            pollIntervalRef.current = setInterval(() => {
                loadWalletData(false) // Não mostrar loading no polling
            }, interval)
        }

        const stopPolling = () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current)
                pollIntervalRef.current = null
            }
        }

        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                loadWalletData(false) // Atualizar ao voltar para a aba
                startPolling(POLL_INTERVAL) // Polling mais rápido quando visível
            } else {
                // Continuar polling em segundo plano com intervalo maior para notificações
                startPolling(BACKGROUND_POLL_INTERVAL)
            }
        }

        // Iniciar polling com intervalo apropriado
        startPolling(document.visibilityState === 'visible' ? POLL_INTERVAL : BACKGROUND_POLL_INTERVAL)

        document.addEventListener('visibilitychange', handleVisibilityChange)

        return () => {
            stopPolling()
            document.removeEventListener('visibilitychange', handleVisibilityChange)
        }
    }, [isAuthenticated, user, loadWalletData])

    const refreshWallet = useCallback(async () => {
        await loadWalletData(true)
    }, [loadWalletData])

    return (
        <WalletContext.Provider value={{
            balance,
            userData,
            payments,
            withdraws,
            internalTransfers,
            loading,
            refreshWallet
        }}>
            {children}
        </WalletContext.Provider>
    )
}

export function useWallet() {
    const context = useContext(WalletContext)
    if (context === undefined) {
        throw new Error('useWallet must be used within a WalletProvider')
    }
    return context
}


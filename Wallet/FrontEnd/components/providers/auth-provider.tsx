'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { getMe, logout as apiLogout, isAuthenticated as checkIsAuthenticated, User } from '@/lib/auth'
import { useRouter } from 'next/navigation'

interface AuthContextType {
    user: User | null
    loading: boolean
    logout: () => Promise<void>
    refreshUser: () => Promise<void>
    isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const router = useRouter()

    const loadUser = async () => {
        if (typeof window === 'undefined') {
            setLoading(false)
            return
        }

        if (!checkIsAuthenticated()) {
            setUser(null)
            setLoading(false)
            return
        }

        try {
            const response = await getMe()

            if (response.success && response.user) {
                setUser(response.user)
            } else {
                // Backend respondeu com sucesso=false → token inválido → deslogar
                localStorage.removeItem('token')
                setUser(null)
            }
        } catch (error: any) {
            const status = error?.status ?? null

            if (status === 401 || status === 403) {
                // Token rejeitado pelo backend → deslogar
                localStorage.removeItem('token')
                setUser(null)
            } else {
                // Erro de rede, timeout, backend offline, etc.
                // Mantém o usuário logado com os dados anteriores (ou null se for a primeira carga)
                // O token continua salvo — na próxima tentativa pode funcionar
                console.warn('[AuthProvider] Erro ao carregar usuário (mantendo sessão):', error?.message ?? error)
            }
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadUser()

        // Logout em outras abas
        const handleStorageChange = (e: StorageEvent) => {
            if (e.key === 'token' && !e.newValue) {
                setUser(null)
                router.push('/')
            }
        }

        window.addEventListener('storage', handleStorageChange)
        return () => window.removeEventListener('storage', handleStorageChange)
    }, [])

    const logout = async () => {
        try {
            await apiLogout()
        } catch {
            // Ignorar erros no logout
        } finally {
            setUser(null)
            localStorage.removeItem('token')
            router.push('/')
        }
    }

    const refreshUser = async () => {
        await loadUser()
    }

    return (
        <AuthContext.Provider value={{
            user,
            loading,
            logout,
            refreshUser,
            isAuthenticated: !!user
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuthContext() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuthContext must be used within an AuthProvider')
    }
    return context
}

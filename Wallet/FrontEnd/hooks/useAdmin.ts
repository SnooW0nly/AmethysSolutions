'use client'

import { useState, useEffect, useRef } from 'react'
import { useAuth } from './useAuth'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/auth'

export function useRequireAdmin() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [isAdmin, setIsAdmin] = useState(false)
  const [isChecking, setIsChecking] = useState(true)
  const [backendVerified, setBackendVerified] = useState(false)
  const hasRedirected = useRef(false)

  useEffect(() => {
    if (hasRedirected.current) return

    const verifyAdmin = async () => {
      if (loading) {
        setIsChecking(true)
        return
      }

      if (!user) {
        hasRedirected.current = true
        router.replace('/login')
        setIsChecking(false)
        return
      }

      try {
        const response = await getMe()

        if (!response.success || !response.user || !response.user.admin) {
          hasRedirected.current = true
          router.replace('/dashboard')
          setIsChecking(false)
          setIsAdmin(false)
          setBackendVerified(false)
          return
        }

        setBackendVerified(true)
        setIsAdmin(true)
        setIsChecking(false)
      } catch (error) {
        console.error('Erro ao verificar admin com backend:', error)
        hasRedirected.current = true
        router.replace('/dashboard')
        setIsChecking(false)
        setIsAdmin(false)
        setBackendVerified(false)
      }
    }

    verifyAdmin()
  }, [user, loading, router])

  return {
    user,
    loading: loading || isChecking || !isAdmin || !backendVerified,
    isAdmin: isAdmin && backendVerified,
  }
}

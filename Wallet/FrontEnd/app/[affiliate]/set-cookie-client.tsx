'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function SetCookieAndRedirect({ code, name }: { code: string, name: string }) {
    const router = useRouter()

    useEffect(() => {
        // Definir cookie de 7 dias
        const date = new Date()
        date.setTime(date.getTime() + (7 * 24 * 60 * 60 * 1000))
        const expires = "expires=" + date.toUTCString()
        document.cookie = `affiliate_code=${code}; ${expires}; path=/; SameSite=Lax`

        // Opcional: Mostrar toast ou notificação de boas vindas
        // Mas para ser rápido, apenas redireciona
        router.replace(`/?ref=${code}`)
    }, [code, router])

    return (
        <div className="flex flex-col items-center justify-center h-screen bg-gray-950 text-white">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500 mb-4"></div>
            <p className="text-gray-400">Redirecionando para Amethys Wallet...</p>
            {name && <p className="text-sm text-emerald-500 mt-2">Convite de {name}</p>}
        </div>
    )
}

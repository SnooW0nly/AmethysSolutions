'use client'

import { useState, useEffect } from 'react'
import { SidebarDashboard } from '@/components/sidebar-dashboard'
import { DashboardTopbar } from '@/components/dashboard-topbar'
import { DashboardHeader } from '@/components/dashboard-header'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faUsers, faMoneyBillWave, faLink, faExchangeAlt, faCopy, faCheck, faChartLine, faPercentage, faSignature, faArrowRight } from '@fortawesome/free-solid-svg-icons'
import { getAffiliateData, registerAsAffiliate, updateAffiliateCode, AffiliateData } from '@/lib/wallet'
import { RippleButton } from '@/components/ripple-button'
import { useAuth } from '@/hooks/useAuth'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export default function AffiliatesPage() {
    const { user } = useAuth()
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [loading, setLoading] = useState(true)
    const [isAffiliate, setIsAffiliate] = useState(false)
    const [affiliateData, setAffiliateData] = useState<AffiliateData | null>(null)

    // States para formulários
    const [newCode, setNewCode] = useState('')
    const [updatingCode, setUpdatingCode] = useState(false)
    const [joining, setJoining] = useState(false)

    // UI States
    const [copied, setCopied] = useState(false)

    const fetchAffiliateData = async () => {
        try {
            setLoading(true)
            const res = await getAffiliateData()
            if (res.success && res.data) {
                setIsAffiliate(true)
                setAffiliateData(res.data)
                setNewCode(res.data.code)
            } else {
                setIsAffiliate(false)
            }
        } catch (error: any) {
            // Silently handle "not affiliate" error as it is expected for new users
            if (error?.message?.includes('afiliado') || error?.status === 404 || error?.status === 400) {
                setIsAffiliate(false)
                return
            }
            console.error('Erro ao buscar dados de afiliado', error)
            setIsAffiliate(false)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchAffiliateData()
    }, [])

    const handleJoin = async () => {
        try {
            setJoining(true)
            const res = await registerAsAffiliate()
            if (res.success) {
                toast.success(res.message || 'Agora você é um afiliado!')
                fetchAffiliateData()
            } else {
                toast.error('Não foi possível entrar no programa.')
            }
        } catch (error: any) {
            toast.error(error.message || 'Erro ao entrar no programa.')
        } finally {
            setJoining(false)
        }
    }

    const handleUpdateCode = async () => {
        if (!newCode || newCode === affiliateData?.code) return;

        try {
            setUpdatingCode(true)
            const res = await updateAffiliateCode(newCode)
            if (res.success) {
                toast.success(res.message)
                // Atualizar link localmente
                if (affiliateData) {
                    setAffiliateData({
                        ...affiliateData,
                        code: res.data.code,
                        link: res.data.link
                    })
                }
            }
        } catch (error: any) {
            toast.error(error.message || 'Erro ao atualizar código.')
        } finally {
            setUpdatingCode(false)
        }
    }

    const copyToClipboard = () => {
        if (!affiliateData?.link) return
        navigator.clipboard.writeText(affiliateData.link)
        setCopied(true)
        toast.success('Link copiado para a área de transferência!')
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div className="flex h-screen bg-background text-foreground">
            <SidebarDashboard open={sidebarOpen} onOpenChange={setSidebarOpen} />

            <div className="flex-1 flex flex-col overflow-hidden relative">
                <DashboardTopbar onOpenSidebar={() => setSidebarOpen(!sidebarOpen)} />

                <main className="flex-1 overflow-y-auto bg-background/50 backdrop-blur-sm">
                    <div className="p-6 lg:p-8 space-y-6">
                        {/* Header Condicional */}
                        {!loading && isAffiliate ? (
                            <header className="border-b border-foreground/10 mb-8 pb-4">
                                <h1 className="text-2xl font-bold">Programa de Afiliados</h1>
                                <p className="text-foreground/70 text-sm mt-1">Gerencie seus links e acompanhe seus resultados.</p>
                            </header>
                        ) : null}

                        {loading ? (
                            <div className="space-y-8">
                                <header className="border-b border-foreground/10 mb-8 pb-4">
                                    <Skeleton className="h-8 w-64 mb-2" />
                                    <Skeleton className="h-4 w-96" />
                                </header>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                                    {[1, 2, 3, 4].map((i) => (
                                        <Card key={i} className="bg-foreground/5 border border-foreground/10 shadow-none h-32">
                                            <CardContent className="p-6">
                                                <Skeleton className="h-4 w-32 mb-4" />
                                                <Skeleton className="h-8 w-16" />
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none h-48">
                                        <CardContent className="p-6">
                                            <Skeleton className="h-6 w-48 mb-2" />
                                            <Skeleton className="h-4 w-full mb-6" />
                                            <div className="flex gap-2">
                                                <Skeleton className="h-12 flex-1 rounded-xl" />
                                                <Skeleton className="h-12 w-12 rounded-xl" />
                                            </div>
                                        </CardContent>
                                    </Card>
                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none h-48">
                                        <CardContent className="p-6">
                                            <Skeleton className="h-6 w-48 mb-2" />
                                            <Skeleton className="h-4 w-full mb-6" />
                                            <div className="flex gap-2">
                                                <Skeleton className="h-12 flex-1 rounded-xl" />
                                                <Skeleton className="h-12 w-24 rounded-xl" />
                                            </div>
                                        </CardContent>
                                    </Card>
                                </div>
                            </div>
                        ) : !isAffiliate ? (
                            // NÃO AFILIADO - TELA DE "JOIN"
                            <div className="space-y-6">
                                {/* Header consistente com o dashboard */}
                                <header className="border-b border-foreground/10 mb-4 pb-4">
                                    <h1 className="text-2xl font-bold">Programa de Afiliados</h1>
                                    <p className="text-foreground/70 text-sm mt-1">Transforme sua influência em renda recorrente.</p>
                                </header>

                                {/* Card principal de boas-vindas */}
                                <div className="bg-foreground/5 p-6 rounded-xl border border-foreground/10">
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                                        <div className="space-y-2">
                                            <h2 className="text-xl font-bold text-foreground flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                                    <FontAwesomeIcon icon={faUsers} className="w-5 h-5 text-primary" />
                                                </div>
                                                Torne-se um Afiliado Amethys
                                            </h2>
                                            <p className="text-sm text-muted-foreground max-w-lg">
                                                Ganhe comissões por cada transação realizada pelos seus indicados.<br />Seus indicados recebem 30 dias de plano Carbon gratuito!
                                            </p>
                                        </div>
                                        <RippleButton
                                            onClick={handleJoin}
                                            disabled={joining}
                                            className="h-11 px-6 rounded-lg bg-foreground/10 text-foreground hover:bg-primary hover:text-white border border-foreground/10 hover:border-primary transition-all flex items-center gap-2 font-medium disabled:opacity-50 whitespace-nowrap justify-center"
                                        >
                                            {joining ? (
                                                <>
                                                    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                                    <span>Ativando...</span>
                                                </>
                                            ) : (
                                                <>
                                                    <span>Quero ser Afiliado</span>
                                                    <FontAwesomeIcon icon={faArrowRight} className="w-4 h-4" />
                                                </>
                                            )}
                                        </RippleButton>
                                    </div>
                                </div>

                                {/* Cards de benefícios - estilo consistente com stats do dashboard */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardContent className="p-6">
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
                                                    <FontAwesomeIcon icon={faMoneyBillWave} className="w-4 h-4 text-green-500" />
                                                </div>
                                                <p className="text-sm font-medium text-muted-foreground">Comissão por Transação</p>
                                            </div>
                                            <h3 className="text-2xl font-bold text-green-500 mb-1">R$ 0,05</h3>
                                            <p className="text-xs text-muted-foreground">Por cada transação dos seus indicados <br />Essa comissão pode aumentar com mais indicados</p>
                                        </CardContent>
                                    </Card>

                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardContent className="p-6">
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                                                    <FontAwesomeIcon icon={faChartLine} className="w-4 h-4 text-blue-500" />
                                                </div>
                                                <p className="text-sm font-medium text-muted-foreground">Ganhos Ilimitados</p>
                                            </div>
                                            <h3 className="text-2xl font-bold text-foreground mb-1">Sem Limite</h3>
                                            <p className="text-xs text-muted-foreground">Quanto mais indicados, mais você ganha</p>
                                        </CardContent>
                                    </Card>

                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardContent className="p-6">
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
                                                    <FontAwesomeIcon icon={faPercentage} className="w-4 h-4 text-purple-500" />
                                                </div>
                                                <p className="text-sm font-medium text-muted-foreground">Pagamento</p>
                                            </div>
                                            <h3 className="text-2xl font-bold text-foreground mb-1">Instantâneo</h3>
                                            <p className="text-xs text-muted-foreground">Direto na sua Amethys Wallet! Sem burocracia!</p>
                                        </CardContent>
                                    </Card>
                                </div>

                                {/* Como funciona */}
                                <div className="bg-foreground/5 p-6 rounded-xl border border-foreground/10">
                                    <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                                        <FontAwesomeIcon icon={faLink} className="w-4 h-4 text-muted-foreground" />
                                        Como Funciona
                                    </h3>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <div className="flex items-start gap-3">
                                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-sm font-bold text-primary">1</div>
                                            <div>
                                                <p className="text-sm font-medium text-foreground">Gere seu link</p>
                                                <p className="text-xs text-muted-foreground">Receba um link personalizado para compartilhar</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3">
                                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-sm font-bold text-primary">2</div>
                                            <div>
                                                <p className="text-sm font-medium text-foreground">Indique amigos</p>
                                                <p className="text-xs text-muted-foreground">Eles ganham 30 dias de plano Carbon</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3">
                                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-sm font-bold text-primary">3</div>
                                            <div>
                                                <p className="text-sm font-medium text-foreground">Receba comissões</p>
                                                <p className="text-xs text-muted-foreground">Ganhe R$ 0,05 por transação deles</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            // AFILIADO - DASHBOARD
                            <div className="space-y-8">
                                {/* Stats Cards */}
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardContent className="p-6">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="flex items-center justify-center text-muted-foreground w-4">
                                                    <FontAwesomeIcon icon={faUsers} />
                                                </div>
                                                <p className="text-sm font-medium text-muted-foreground">Total de Indicados</p>
                                            </div>
                                            <h3 className="text-3xl font-bold">{affiliateData?.totalReferrals || 0}</h3>
                                        </CardContent>
                                    </Card>

                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardContent className="p-6">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="flex items-center justify-center text-muted-foreground w-4">
                                                    <FontAwesomeIcon icon={faMoneyBillWave} />
                                                </div>
                                                <p className="text-sm font-medium text-muted-foreground">Ganhos Totais</p>
                                            </div>
                                            <h3 className="text-3xl font-bold text-green-500">
                                                {affiliateData?.totalEarningsInReais || `R$ ${((affiliateData?.totalEarnings || 0) / 100).toFixed(2).replace('.', ',')}`}
                                            </h3>
                                        </CardContent>
                                    </Card>

                                    {/* Placeholder Stats */}
                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardContent className="p-6">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="flex items-center justify-center text-muted-foreground w-4">
                                                    <FontAwesomeIcon icon={faChartLine} />
                                                </div>
                                                <p className="text-sm font-medium text-muted-foreground">Cliques no Link</p>
                                            </div>
                                            <h3 className="text-3xl font-bold">{(affiliateData as any)?.stats?.clicks || 0}</h3>
                                        </CardContent>
                                    </Card>

                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardContent className="p-6">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="flex items-center justify-center text-muted-foreground w-4">
                                                    <FontAwesomeIcon icon={faPercentage} />
                                                </div>
                                                <p className="text-sm font-medium text-muted-foreground">Sua Comissão</p>
                                            </div>
                                            <h3 className="text-3xl font-bold text-blue-500">
                                                {affiliateData?.commissionRateInReais || 'R$ 0,05'}
                                            </h3>
                                        </CardContent>
                                    </Card>
                                </div>

                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                    {/* Link Card */}
                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardHeader>
                                            <CardTitle className="text-lg flex items-center gap-2">
                                                <FontAwesomeIcon icon={faLink} className="text-muted-foreground" />
                                                Seu Link de Indicação
                                            </CardTitle>
                                            <CardDescription>
                                                Compartilhe este link para convidar novos usuários.
                                            </CardDescription>
                                        </CardHeader>
                                        <CardContent className="space-y-4">
                                            <div className="flex items-center gap-2">
                                                <div className="bg-muted/50 border border-border rounded-xl px-4 py-3 flex-1 font-mono text-sm truncate">
                                                    {affiliateData?.link}
                                                </div>
                                                <RippleButton
                                                    onClick={copyToClipboard}
                                                    className={`shrink-0 h-12 w-12 rounded-xl flex items-center justify-center transition-colors ${copied ? 'bg-green-500 text-white' : 'bg-primary text-primary-foreground hover:bg-primary/90'}`}
                                                >
                                                    <FontAwesomeIcon icon={copied ? faCheck : faCopy} />
                                                </RippleButton>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    {/* Code Editor Card */}
                                    <Card className="bg-foreground/5 border border-foreground/10 shadow-none">
                                        <CardHeader>
                                            <CardTitle className="text-lg flex items-center gap-2">
                                                <FontAwesomeIcon icon={faSignature} className="text-muted-foreground" />
                                                Personalizar Código
                                            </CardTitle>
                                            <CardDescription>
                                                Altere seu código de identificação (ex: amethys.lat/signup?ref=SEUCODIGO).
                                            </CardDescription>
                                        </CardHeader>
                                        <CardContent className="space-y-4">
                                            <div className="flex items-center gap-2">
                                                <div className="relative flex-1">
                                                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground font-mono text-sm">ref=</span>
                                                    <Input
                                                        value={newCode}
                                                        onChange={(e) => setNewCode(e.target.value.replace(/[^a-zA-Z0-9]/g, '').toLowerCase())}
                                                        className="pl-11.5 font-mono" // Increased padding-left to prevent overlap with "ref="
                                                        placeholder="seucodigo"
                                                        maxLength={20}
                                                    />
                                                </div>
                                                <RippleButton
                                                    onClick={handleUpdateCode}
                                                    disabled={updatingCode || newCode === affiliateData?.code || newCode.length < 3}
                                                    className="shrink-0 h-10 px-4 bg-secondary text-secondary-foreground font-medium rounded-md hover:bg-secondary/80 disabled:opacity-50"
                                                >
                                                    {updatingCode ? 'Salvando...' : 'Salvar'}
                                                </RippleButton>
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                                * Apenas letras e números. Mínimo 3 caracteres.
                                            </p>
                                        </CardContent>
                                    </Card>
                                </div>
                            </div>
                        )}
                    </div>
                </main>
            </div>
        </div>
    )
}

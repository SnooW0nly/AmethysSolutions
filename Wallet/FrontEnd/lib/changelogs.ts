import { faRocket, faBug, faGem, faShieldAlt, faWrench, faPalette, IconDefinition } from '@fortawesome/free-solid-svg-icons'

// Force rebuild

export type ChangelogType = 'feature' | 'fix' | 'improvement' | 'security' | 'style'

export interface Changelog {
    version: string
    date: string
    title: string
    description: string
    type: ChangelogType
    changes: string[]
}

export const changelogs: Changelog[] = [
    {
        version: '1.3.0',
        date: '2025-12-09',
        title: 'Programa de Afiliados e Novas Funcionalidades',
        description: 'Grande atualização com o lançamento do programa de afiliados, novas funcionalidades de pagamento e melhorias gerais na plataforma.',
        type: 'feature',
        changes: [
            'Lançamento do Programa de Afiliados Amethys Wallet.',
            'Atualização da logo da plataforma.',
            'Adição de Splits em pagamentos via API.',
            'Implementação de Transferências Internas entre usuários.',
            'Refatoração completa de várias seções da Dashboard.',
            'Melhorias nas páginas de Configurações.'
        ]
    },
    {
        version: '1.2.0',
        date: '2025-12-03',
        title: 'Refinamentos Visuais e Segurança',
        description: 'Atualizações focadas na experiência do usuário e segurança da plataforma.',
        type: 'improvement',
        changes: [
            'Refatoração da página de Preços para melhor clareza e design premium.',
            'Atualização da Home Page com novas seções de Segurança e Privacidade.',
            'Implementação de bloqueador de DevTools para maior proteção.',
            'Refinamentos na Sidebar para melhor navegação e estética.',
            'Ajustes de layout e remoção de elementos visuais desnecessários.'
        ]
    },
    {
        version: '1.1.0',
        date: '2025-12-03',
        title: 'Otimizações de Performance',
        description: 'Melhorias significativas na performance do dashboard e correções de bugs.',
        type: 'fix',
        changes: [
            'Correção de requisições duplicadas no carregamento da carteira.',
            'Otimização do carregamento de dados do usuário.',
            'Ajustes na responsividade do dashboard.',
            'Melhorias na estabilidade da conexão com o backend.'
        ]
    },
    {
        version: '1.0.0',
        date: '2025-12-01',
        title: 'Lançamento Oficial',
        description: 'Lançamento da primeira versão estável do Amethys Wallet.',
        type: 'rocket',
        changes: [
            'Sistema completo de pagamentos via PIX.',
            'Dashboard intuitivo para gestão financeira.',
            'Integração com Discord para notificações.',
            'Sistema de segurança avançado com criptografia.',
            'Suporte a múltiplos planos de assinatura.'
        ]
    }
] as any

export const getTypeIcon = (type: ChangelogType | 'rocket'): IconDefinition => {
    switch (type) {
        case 'feature': return faGem
        case 'fix': return faBug
        case 'improvement': return faWrench
        case 'security': return faShieldAlt
        case 'style': return faPalette
        case 'rocket': return faRocket
        default: return faGem
    }
}

export const getTypeColor = (type: ChangelogType | 'rocket'): string => {
    switch (type) {
        case 'feature': return 'text-purple-500 bg-purple-500/10 border-purple-500/20'
        case 'fix': return 'text-red-500 bg-red-500/10 border-red-500/20'
        case 'improvement': return 'text-blue-500 bg-blue-500/10 border-blue-500/20'
        case 'security': return 'text-green-500 bg-green-500/10 border-green-500/20'
        case 'style': return 'text-pink-500 bg-pink-500/10 border-pink-500/20'
        case 'rocket': return 'text-primary bg-primary/10 border-primary/20'
        default: return 'text-gray-500 bg-gray-500/10 border-gray-500/20'
    }
}

export const getTypeLabel = (type: ChangelogType | 'rocket'): string => {
    switch (type) {
        case 'feature': return 'Nova Funcionalidade'
        case 'fix': return 'Correção'
        case 'improvement': return 'Melhoria'
        case 'security': return 'Segurança'
        case 'style': return 'Visual'
        case 'rocket': return 'Lançamento'
        default: return 'Update'
    }
}

export const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: 'long',
        year: 'numeric'
    })
}

export const getChangelogById = (version: string): Changelog | undefined => {
    return changelogs.find((c: Changelog) => c.version === version)
}

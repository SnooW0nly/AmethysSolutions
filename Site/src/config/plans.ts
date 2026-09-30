import { faCartShopping, faCloud } from "@fortawesome/free-solid-svg-icons"

export const plans = [
    {
        name: "Amethys Pro",
        id: "amethys-pro",
        icon: faCartShopping,
        description: "O plano completo desenvolvido para quem precisa de qualidade e segurança no Discord.",
        primary: true,
        features: [
            { title: "11 formas de pagamento disponíveis" },
            { title: "Sistema anti-fraude para bancos" },
            { title: "Comandos úteis para o seu servidor" },
            { title: "Sistema de proteção e moderação" },
            { title: "Sistema de Tickets completo com IA" },
            { title: "AmethysCloud & backup incluso" },
            { title: "Logs completas e detalhadas" },
            { title: "Mensagens de boas vindas" },
            { title: "Restreio e logs de convites" },
            { title: "Sistema de Automações completo" },
            { title: "Avatar/Nome/Status personalizáveis" },
            { title: "QR Code de pagamento personalizável" },
        ],
        plans: [
            {
                name: "Mensal",
                value: 15.00,
                discount: 0,
                months: 1,
                id: "amethys-pro-mensal",
                description: "mês",
            },
            {
                name: "Trimestral",
                months: 3,
                value: 39.99,
                discount: 11,
                id: "amethys-pro-trimestral",
                description: "trimestre",
            },
            {
                name: "Anual",
                months: 12,
                value: 119.99,
                discount: 33,
                id: "amethys-pro-anual",
                description: "ano",
            }
        ]
    },
    {
        name: "Amethys Cloud",
        id: "amethys-cloud",
        icon: faCloud,
        description: "Proteja seu servidor com OAuth2 e restaure seus membros facilmente. Mais segurança, mais confiança.",
        primary: false,
        features: [
            { title: "Autenticação via OAuth2" },
            { title: "Configuração fácil e rápida" },
            { title: "Análise avançada de membros" },
            { title: "Proteção contra fraudes e contas falsas" },
            { title: "Rastreio por IP e informações do usuário" },
            { title: "Logs completas e detalhadas" },
            { title: "Recuperação de membros rápida e automática" },
        ],
        plans: [
            {
                name: "Mensal",
                value: 6.00,
                discount: 0,
                months: 1,
                id: "amethys-cloud-mensal",
                description: "mês",
            },
            {
                name: "Trimestral",
                months: 3,
                value: 15.99,
                discount: 11,
                id: "amethys-cloud-trimestral",
                description: "trimestre",
            },
            {
                name: "Anual",
                months: 12,
                value: 48.24,
                discount: 33,
                id: "amethys-cloud-anual",
                description: "ano",
            }
        ]
    }
] 

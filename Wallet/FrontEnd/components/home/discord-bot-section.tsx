'use client'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faRobot, faTicket, faCartShopping, faBolt, faUpRightFromSquare } from '@fortawesome/free-solid-svg-icons'
import { faDiscord } from '@fortawesome/free-brands-svg-icons'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'

const features = [
    {
        icon: faRobot,
        title: 'Automação Total',
        description: 'Receba pagamentos e faça transferências automaticamente.',
    },
    {
        icon: faCartShopping,
        title: 'Vendas Automáticas',
        description: 'Sistema completo de vendas de produtos e serviços.',
    },
    {
        icon: faTicket,
        title: 'Gestão de Tickets',
        description: 'Organize o suporte da sua comunidade no Discord.',
    },
    {
        icon: faBolt,
        title: 'Totalmente Gratuito',
        description: 'Sem taxas mensais ou custos ocultos para usar o bot.',
    },
]

export function DiscordBotSection() {
    return (
        <motion.section
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6 }}
            className="relative mt-8 mb-8 py-8 md:mt-12 md:mb-16 md:py-16"
        >
            <div className="relative z-10">
                {/* Split layout: Content left, Image right */}
                <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16">

                    {/* Left side - Content */}
                    <div className="flex-1 lg:max-w-[55%]">
                        {/* Header */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5 }}
                            className="inline-flex items-center gap-3 mb-5"
                        >
                            <span className="w-8 h-px bg-primary/30" />
                            <span className="text-primary text-xs font-medium uppercase tracking-[0.2em]">Integração</span>
                        </motion.div>

                        <motion.h2
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.6, delay: 0.1 }}
                            className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground leading-tight mb-5"
                        >
                            Potencialize seu{' '}
                            <span className="relative inline-block">
                                <span className="text-primary">Discord</span>
                                <span className="absolute -bottom-1 left-0 right-0 h-[3px] bg-gradient-to-r from-primary via-primary to-primary/30 rounded-full" />
                            </span>
                        </motion.h2>

                        <motion.p
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5, delay: 0.2 }}
                            className="text-foreground/50 text-base md:text-lg max-w-xl mb-10"
                        >
                            Nosso bot exclusivo transforma seu servidor em uma potência financeira.
                            Gerencie vendas, tickets e transações PIX diretamente do seu chat,
                            com logs detalhados e segurança total.
                        </motion.p>

                        {/* Features grid - 2x2 */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5, delay: 0.3 }}
                            className="grid grid-cols-2 gap-6 mb-8"
                        >
                            {features.map((feature, index) => (
                                <div
                                    key={index}
                                    className="flex items-start gap-3"
                                >
                                    <FontAwesomeIcon
                                        icon={feature.icon}
                                        className="text-primary text-xl mt-0.5"
                                    />
                                    <div>
                                        <h3 className="text-foreground text-sm font-semibold mb-0.5">
                                            {feature.title}
                                        </h3>
                                        <p className="text-foreground/40 text-xs leading-relaxed">
                                            {feature.description}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </motion.div>

                        {/* CTA */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5, delay: 0.4 }}
                            className="flex gap-3"
                        >
                            <Button
                                className="bg-transparent border border-foreground/10 text-foreground hover:bg-foreground/5 text-sm px-5"
                                onClick={() => { window.open("https://discord.gg/9vBqJj45gV", "_blank") }}
                            >
                                <span className="flex items-center gap-2">
                                    Comunidade Discord
                                    <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[10px]" />
                                </span>
                            </Button>
                        </motion.div>
                    </div>

                    {/* Right side - Illustration */}
                    <motion.div
                        initial={{ opacity: 0, x: 40 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.7, delay: 0.3 }}
                        className="flex-1 hidden lg:flex justify-center lg:justify-end"
                    >
                        <img
                            src="/undraw_chat-bot_c8iw.svg"
                            alt="Discord Bot Amethys Wallet"
                            className="w-full max-w-sm lg:max-w-md h-auto"
                        />
                    </motion.div>
                </div>
            </div>
        </motion.section>
    )
}

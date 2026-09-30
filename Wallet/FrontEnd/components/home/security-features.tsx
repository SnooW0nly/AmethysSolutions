'use client'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faLock, faShieldHalved, faBell, faFingerprint, faDesktop, faUpRightFromSquare, faArrowRight } from '@fortawesome/free-solid-svg-icons'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'

const features = [
    {
        icon: faLock,
        title: 'Criptografia AES-256',
        description: 'Dados protegidos com padrão bancário',
    },
    {
        icon: faFingerprint,
        title: 'Autenticação 2FA',
        description: 'Camada extra de proteção',
    },
    {
        icon: faDesktop,
        title: 'Controle de sessões',
        description: 'Gerencie dispositivos conectados',
    },
    {
        icon: faBell,
        title: 'Alertas em Tempo Real',
        description: 'Seja notificado em atividades suspeitas',
    },
]

export function SecurityFeaturesSection() {
    return (
        <motion.section
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6 }}
            className="relative mt-8 mb-8 py-8 md:mt-12 md:mb-16 md:py-16"
        >


            <div className="relative z-10">
                {/* Split layout: Image left, Content right */}
                <div className="flex flex-col-reverse lg:flex-row items-center gap-12 lg:gap-16">

                    {/* Left side - Illustration */}
                    <motion.div
                        initial={{ opacity: 0, x: -40 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.7, delay: 0.2 }}
                        className="flex-1 hidden lg:flex justify-center lg:justify-start"
                    >
                        <img
                            src="/undraw_firewall_cfej.svg"
                            alt="Segurança"
                            className="w-full max-w-sm lg:max-w-md h-auto"
                        />
                    </motion.div>

                    {/* Right side - Content */}
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
                            <span className="text-primary text-xs font-medium uppercase tracking-[0.2em]">Segurança</span>
                        </motion.div>

                        <motion.h2
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.6, delay: 0.1 }}
                            className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground leading-tight mb-5"
                        >
                            Sua conta{' '}
                            <span className="relative inline-block">
                                <span className="text-primary">blindada</span>
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
                            Proteção multinível para suas transações. Criptografia de ponta a ponta,
                            autenticação de dois fatores e controle total sobre seus dispositivos.
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
                            className="flex gap-2 sm:gap-3"
                        >
                            <Button
                                className="bg-primary text-primary-foreground hover:bg-primary/90 text-sm px-5"
                                onClick={() => { window.location.href = "/login" }}
                            >
                                <span className="flex items-center gap-2">
                                    Começar agora
                                    <FontAwesomeIcon icon={faArrowRight} className="text-sm" />
                                </span>
                            </Button>
                            <Button
                                className="bg-transparent border border-foreground/10 text-foreground hover:bg-foreground/5 text-sm px-5"
                                onClick={() => { window.location.href = "/about" }}
                            >
                                <span className="flex items-center gap-2">
                                    Saiba mais
                                    <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[10px]" />
                                </span>
                            </Button>
                        </motion.div>
                    </div>
                </div>
            </div>
        </motion.section>
    )
}

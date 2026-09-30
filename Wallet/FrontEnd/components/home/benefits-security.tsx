'use client'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCode, faBolt, faShieldHalved, faRocket, faUpRightFromSquare } from '@fortawesome/free-solid-svg-icons'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'

const features = [
  {
    icon: faCode,
    title: 'API simples',
    description: 'Integração em minutos',
  },
  {
    icon: faBolt,
    title: 'Receba em segundos',
    description: 'PIX instantâneo 24/7',
  },
  {
    icon: faShieldHalved,
    title: 'AES-256',
    description: 'Criptografia bancária',
  },
  {
    icon: faRocket,
    title: 'Sem limites',
    description: 'Opere quanto precisar',
  },
]

export function BenefitsSecuritySection() {
  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.6 }}
      className="relative mt-8 mb-6 py-8 md:mt-16 md:mb-12 md:py-16"
    >
      {/* Organic background */}


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
              src="/undraw_product-iteration_r2wg.svg"
              alt="API Integration"
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
              <span className="text-primary text-xs font-medium uppercase tracking-[0.2em]">Para desenvolvedores</span>
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground leading-tight mb-5"
            >
              API{' '}
              <span className="relative inline-block">
                <span className="text-primary">poderosa</span>
                <span className="absolute -bottom-1 left-0 right-0 h-[3px] bg-gradient-to-r from-primary via-primary to-primary/30 rounded-full" />
              </span>
              {' '}e simples
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="text-foreground/50 text-base md:text-lg max-w-xl mb-8"
            >
              Integre pagamentos PIX à sua aplicação com poucas linhas de código.
              Webhooks em tempo real, documentação completa e suporte técnico dedicado.
            </motion.p>

            {/* Code preview - curl example */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="mb-8"
            >
              <div className="bg-[#0c0d0e] border border-foreground/[0.06] rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-3 border-b border-foreground/[0.04]">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]" />
                    <div className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]" />
                    <div className="w-2.5 h-2.5 rounded-full bg-[#28C840]" />
                  </div>
                  <span className="text-foreground/25 text-[11px] font-mono ml-2">terminal</span>
                </div>
                <div className="p-4 font-mono text-[12px] leading-relaxed overflow-x-auto">
                  <div className="text-foreground/50">
                    <span className="text-green-400/70">curl</span>
                    <span className="text-foreground/30"> -X POST </span>
                    <span className="text-yellow-400/70">'https://api.amethys.lat/...'</span>
                  </div>
                  <div className="text-foreground/50 pl-2">
                    <span className="text-foreground/30">-d </span>
                    <span className="text-foreground/40">{'{'}</span>
                    <span className="text-foreground/50">"value"</span>
                    <span className="text-foreground/30">: </span>
                    <span className="text-orange-400/80">100.00</span>
                    <span className="text-foreground/40">{'}'}</span>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Features grid - 2x2 */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="grid grid-cols-2 gap-5 mb-8"
            >
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3"
                >
                  <FontAwesomeIcon
                    icon={feature.icon}
                    className="text-primary text-lg mt-0.5"
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
              transition={{ duration: 0.5, delay: 0.5 }}
              className="flex gap-2 sm:gap-3"
            >
              <Button
                className="bg-primary text-primary-foreground hover:bg-primary/90 text-sm px-5"
                onClick={() => { window.location.href = "/pricing" }}
              >
                <span className="flex items-center gap-2">
                  <FontAwesomeIcon icon={faCode} className="text-sm" />
                  Começar a integrar
                </span>
              </Button>
              <Button
                className="bg-transparent border border-foreground/10 text-foreground hover:bg-foreground/5 text-sm px-5"
                onClick={() => { window.open("https://docs.amethys.lat", "_blank") }}
              >
                <span className="flex items-center gap-2">
                  Ver documentação
                  <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[10px]" />
                </span>
              </Button>
            </motion.div>
          </div>
        </div>
      </div>
    </motion.section >
  )
}

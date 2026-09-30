'use client'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faEyeSlash, faIdCard, faGavel, faUserShield, faUpRightFromSquare, faUserPlus } from '@fortawesome/free-solid-svg-icons'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'

const benefits = [
  {
    icon: faIdCard,
    title: 'Sem documentos',
    description: 'Cadastro sem KYC',
  },
  {
    icon: faGavel,
    title: 'Sem MEDs',
    description: 'Zero reembolsos por fraude',
  },
  {
    icon: faUserShield,
    title: 'Qualquer idade',
    description: 'Menores de 18 operam normal',
  },
  {
    icon: faEyeSlash,
    title: 'Anonimato real',
    description: 'Seu nome nunca aparece',
  },
]

export function BenefitsPrivacySection() {
  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.6 }}
      className="relative mt-8 mb-6 py-8 md:mt-12 md:mb-12 md:py-16"
    >
      {/* Organic background */}


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
              <span className="text-primary text-xs font-medium uppercase tracking-[0.2em]">Liberdade total</span>
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground leading-tight mb-5"
            >
              Conta{' '}
              <span className="relative inline-block">
                <span className="text-primary">sem burocracia</span>
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
              Esqueça a burocracia dos bancos tradicionais. Cadastro instantâneo,
              sem documentos, sem aprovação e sem idade mínima. Opere com total liberdade.
            </motion.p>

            {/* Benefits grid - 2x2 */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="grid grid-cols-2 gap-6 mb-8"
            >
              {benefits.map((benefit, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3"
                >
                  <FontAwesomeIcon
                    icon={benefit.icon}
                    className="text-primary text-xl mt-0.5"
                  />
                  <div>
                    <h3 className="text-foreground text-sm font-semibold mb-0.5">
                      {benefit.title}
                    </h3>
                    <p className="text-foreground/40 text-xs leading-relaxed">
                      {benefit.description}
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
                onClick={() => { window.location.href = "/pricing" }}
              >
                <span className="flex items-center gap-2">
                  <FontAwesomeIcon icon={faUserPlus} className="text-sm" />
                  Criar conta grátis
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

          {/* Right side - Illustration */}
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.3 }}
            className="flex-1 hidden lg:flex justify-center lg:justify-end"
          >
            <img
              src="/undraw_personal-settings_8xv3.svg"
              alt="Liberdade e Privacidade"
              className="w-full max-w-sm lg:max-w-md h-auto"
            />
          </motion.div>
        </div>
      </div>
    </motion.section>
  )
}

'use client'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCreditCard, faShieldAlt, faChartLine, faBolt, faLock, faChevronRight, faUserSecret } from '@fortawesome/free-solid-svg-icons'
import { motion } from 'framer-motion'
import Link from 'next/link'

const whyChoose = [
  {
    icon: faShieldAlt,
    title: 'Segurança Total',
    description: 'Seus dados protegidos com criptografia de ponta e autenticação em duas etapas.',
  },
  {
    icon: faBolt,
    title: 'Rapidez',
    description: 'Transações processadas em segundos, sem esperas ou burocracias.',
  },
  {
    icon: faLock,
    title: 'Privacidade',
    description: 'Seus dados nunca são compartilhados. Opere com total discrição.',
  },
  {
    icon: faChartLine,
    title: 'Análises Detalhadas',
    description: 'Acompanhe suas transações e tenha controle total sobre suas finanças.',
  },
  {
    icon: faCreditCard,
    title: 'Múltiplas Formas',
    description: 'Aceite PIX, Cartão e Crypto em uma única plataforma integrada.',
  },
]

export function FeaturesSection() {
  return (
    <>
      {/* Why Choose Section */}
      <section className="mt-40 mb-20 flex flex-col lg:flex-row justify-between w-full gap-8">
        {/* Left Column - Text Content */}
        <div className="w-full lg:w-1/2 flex flex-col gap-2">
          <div className="flex items-center gap-1">
            <FontAwesomeIcon icon={faShieldAlt} className="text-primary text-[12px]" />
            <span className="text-primary/50 text-[12px]">|</span>
            <span className="text-primary font-semibold text-[12px]">Por que escolher</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-foreground">
            Por que escolher a Amethys Wallet?
          </h1>
          <div className="flex flex-col gap-1">
            <p className="text-foreground/70 text-sm md:text-base max-w-xl leading-relaxed">
              Tudo que você precisa para operar com segurança, privacidade e liberdade total. Uma plataforma completa para suas necessidades financeiras.
            </p>
            <Link
              href="/login"
              className="text-foreground flex items-center gap-1 w-fit px-4 py-2 bg-foreground/2 border border-foreground/10 rounded-lg hover:bg-foreground/10 duration-100 transition-all cursor-pointer my-2"
            >
              <span className="text-[12px] text-foreground/80">Começar agora</span>
              <FontAwesomeIcon icon={faChevronRight} className="text-foreground/70 text-[12px]" />
            </Link>
          </div>
          <hr className="border-foreground/10 my-4" />

          {/* Why Choose List */}
          <div className="flex flex-col gap-6 mt-2">
            {whyChoose.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="flex flex-row gap-4 justify-between items-start"
              >
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center">
                    <FontAwesomeIcon icon={feature.icon} className="text-primary text-sm" />
                  </div>
                  <p className="text-foreground/90 text-sm font-semibold whitespace-nowrap">
                    {feature.title}
                  </p>
                </div>
                <p className="text-foreground/60 text-xs md:text-sm leading-tight md:max-w-xs max-w-1/2 text-right lg:text-left">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Right Column - Visual Elements with Dashed Lines */}
        <div className="w-full lg:w-2/5 h-auto rounded-lg p-7 border border-dashed border-foreground/10 lg:block hidden">
          <div className="flex flex-col">
            <p className="text-foreground/60 uppercase text-xs font-[monospace]">Sua escolha</p>
            <p className="text-foreground/60 text-xs leading-tight md:max-w-sm mt-2">
              Uma plataforma completa que oferece tudo que você precisa para operar com segurança e liberdade.
            </p>
          </div>

          <div className="mt-5 flex flex-row gap-4">
            {/* Dashed vertical line */}
            <div className="h-auto w-[1px] border-l border-dashed border-foreground/10" />

            <div className="flex flex-col gap-6 flex-1">
              {/* Security Card */}
              <div className="flex flex-col gap-2">
                <p className="text-foreground/60 uppercase text-xs font-[monospace]">Segurança</p>
                <div className="p-4 border border-foreground/10 rounded-lg bg-foreground/2">
                  <div className="flex flex-row gap-3 items-center">
                    <div className="w-16 h-16 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                      <FontAwesomeIcon icon={faShieldAlt} className="text-primary text-2xl" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <p className="text-foreground/70 text-[10px] uppercase font-[monospace]">Proteção Total</p>
                      <p className="text-foreground/70 text-[11px] leading-tight">
                        Criptografia de nível bancário para todas as suas transações.
                      </p>
                    </div>
                  </div>
                  <div className="h-[40%] w-full rounded-md bg-[repeating-linear-gradient(45deg,rgba(255,107,53,0.10)_0,rgba(255,107,53,0.10)_1,transparent_1px,transparent_8px)] mt-3" />
                </div>
              </div>

              {/* Privacy Card */}
              <div className="flex flex-col gap-2">
                <p className="text-foreground/60 uppercase text-xs font-[monospace]">Privacidade</p>
                <div className="p-4 border border-foreground/10 rounded-lg bg-foreground/2">
                  <div className="flex flex-row gap-3 items-center">
                    <div className="w-16 h-16 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                      <FontAwesomeIcon icon={faUserSecret} className="text-primary text-2xl" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <p className="text-foreground/70 text-[10px] uppercase font-[monospace]">Anonimato</p>
                      <p className="text-foreground/70 text-[11px] leading-tight">
                        Venda sem usar seu nome real. Mantenha sua identidade protegida.
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-row gap-2 mt-3">
                    <div className="h-[1px] w-full border-b border-dashed border-foreground/10 self-center" />
                    <FontAwesomeIcon icon={faLock} className="text-primary/30 text-xs" />
                    <div className="h-[1px] w-full border-b border-dashed border-foreground/10 self-center" />
                  </div>
                </div>
              </div>

              {/* Speed Card */}
              <div className="flex flex-col gap-2">
                <p className="text-foreground/60 uppercase text-xs font-[monospace]">Velocidade</p>
                <div className="p-4 border border-foreground/10 rounded-lg bg-foreground/2">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <FontAwesomeIcon icon={faBolt} className="text-primary text-sm" />
                      <p className="text-foreground/70 text-[11px] font-semibold">Instantâneo</p>
                    </div>
                    <p className="text-foreground/70 text-[11px] leading-tight">
                      Transações processadas em segundos, sem esperas ou burocracias.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}

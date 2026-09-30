'use client'

import { motion } from 'framer-motion'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faShieldAlt, faChartLine, faBolt, faLock, faCreditCard, faChevronRight, faUpRightFromSquare, faQrcode } from '@fortawesome/free-solid-svg-icons'
import { RippleButton } from '@/components/ripple-button'
import Link from 'next/link'

type Venda = { valor: number; data: string; metodo: 'pix' | 'cartao' }

function formatarValor(valor: number) {
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

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

export default function About() {
  const vendas: Venda[] = [
    { valor: 100, data: '50s atrás', metodo: 'pix' },
    { valor: 100, data: '1h atrás', metodo: 'pix' },
    { valor: 50, data: '2h atrás', metodo: 'cartao' },
    { valor: 20, data: '3h atrás', metodo: 'pix' },
    { valor: 100, data: '3h atrás', metodo: 'cartao' },
  ]

  return (
    <main>
      {/* Hero Section */}
      <section className="relative w-full flex flex-col items-center justify-center gap-12 md:px-8 md:py-12 overflow-hidden rounded-xl mb-20">
        {/* Background effects */}
        <div className="hidden md:block absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,107,53,0.06)_0%,rgba(0,0,0,0)_70%)] pointer-events-none" />
        <div className="hidden md:block absolute inset-0 backdrop-blur-[120px] bg-[rgba(20,20,20,0.25)]" />

        <div className="gap-12 flex flex-col justify-between w-full md:flex-row relative z-10">
          {/* Text */}
          <div className="flex flex-col max-w-lg text-left">
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="text-4xl md:text-5xl font-bold tracking-tight text-foreground mb-3"
            >
              Gerencie, pague e cresça
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: 0.1, ease: "easeOut" }}
              className="text-foreground/60 text-sm md:text-base leading-relaxed mb-5"
            >
              Transforme seus pagamentos em uma experiência simples e eficiente. Mais tempo para você, mais controle para o seu negócio.
            </motion.p>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: 0.2, ease: "easeOut" }}
              className="text-foreground/70 text-sm leading-relaxed mb-3"
            >
              Com a{' '}
              <span className="font-semibold text-primary">Amethys Wallet</span>, gerenciar pagamentos é tão simples que você pode fazer tudo enquanto trabalha, descansa ou aproveita seu tempo livre.
            </motion.p>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: 0.3, ease: "easeOut" }}
              className="text-foreground/70 text-sm leading-relaxed mb-6"
            >
              Nós cuidamos de tudo:{' '}
              <span className="font-semibold text-primary">
                PIX, Cartão, Crypto, segurança e automação
              </span>
              . Assim, você pode focar no que realmente importa:{' '}
              <span className="font-semibold text-primary">
                crescer e lucrar.
              </span>
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: 0.4, ease: "easeOut" }}
              className="flex flex-row gap-3"
            >
              <Link href="/login">
                <RippleButton className="bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm px-6 py-2 rounded-lg">
                  Começar agora
                </RippleButton>
              </Link>
              <Link href="/dashboard">
                <RippleButton className="bg-transparent border border-foreground/10 text-foreground hover:bg-foreground/[0.05] transition-colors text-sm px-6 py-2 rounded-lg inline-flex items-center gap-1">
                  <span>Acessar Dashboard</span>
                  <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[11px]" />
                </RippleButton>
              </Link>
            </motion.div>
          </div>

          {/* Card de vendas */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.4, delay: 0.2, ease: "easeOut" }}
            className="relative flex flex-col justify-between z-10 w-full max-w-sm rounded-2xl border border-foreground/5 bg-foreground/[0.03] shadow-[0_0_40px_-10px_rgba(0,0,0,0.4)] p-5 backdrop-blur-xl"
          >
            <p className="text-xs uppercase tracking-widest text-foreground/40 font-semibold mb-2">
              Últimas vendas
            </p>
            <div className="flex flex-col gap-2">
              {vendas.map((venda, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  className="flex items-center gap-3 border border-foreground/[0.06] bg-foreground/[0.04] hover:bg-foreground/[0.07] transition-colors rounded-xl px-3 py-2"
                >
                  <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex-shrink-0">
                    <FontAwesomeIcon
                      icon={venda.metodo === 'pix' ? faQrcode : faCreditCard}
                      className="text-primary text-sm w-4 h-4"
                    />
                  </div>
                  <div className="flex flex-col flex-1 min-w-0">
                    <div className="flex justify-between text-xs text-foreground/60">
                      <span>Venda concluída</span>
                      <span>{venda.data}</span>
                    </div>
                    <p className="text-sm text-foreground/80 font-medium">
                      {formatarValor(venda.valor)}{' '}
                      <span className="text-foreground/50 font-normal">
                        disponíveis
                      </span>
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

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
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.4, delay: index * 0.08, ease: "easeOut" }}
                className="flex flex-row gap-4 justify-between items-start"
              >
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                    <FontAwesomeIcon icon={feature.icon} className="text-primary text-sm w-4 h-4" />
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
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="w-full lg:w-2/5 h-auto rounded-lg p-7 border border-dashed border-foreground/10 lg:block hidden"
        >
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="flex flex-col"
          >
            <p className="text-foreground/60 uppercase text-xs font-[monospace]">Sua escolha</p>
            <p className="text-foreground/60 text-xs leading-tight md:max-w-sm mt-2">
              Uma plataforma completa que oferece tudo que você precisa para operar com segurança e liberdade.
            </p>
          </motion.div>

          <div className="mt-5 flex flex-row gap-4">
            {/* Dashed vertical line */}
            <div className="h-auto w-[1px] border-l border-dashed border-foreground/10" />

            <div className="flex flex-col gap-6 flex-1">
              {/* Security Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: 0.2, ease: "easeOut" }}
                className="flex flex-col gap-2"
              >
                <p className="text-foreground/60 uppercase text-xs font-[monospace]">Segurança</p>
                <div className="p-4 border border-foreground/10 rounded-lg bg-foreground/2">
                  <div className="flex flex-row gap-3 items-center">
                    <div className="w-16 h-16 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                      <FontAwesomeIcon icon={faShieldAlt} className="text-primary w-6 h-6" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <p className="text-foreground/70 text-[10px] uppercase font-[monospace]">Proteção Total</p>
                      <p className="text-foreground/70 text-[11px] leading-tight">
                        Criptografia de nível bancário para todas as suas transações.
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Privacy Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: 0.3, ease: "easeOut" }}
                className="flex flex-col gap-2"
              >
                <p className="text-foreground/60 uppercase text-xs font-[monospace]">Privacidade</p>
                <div className="p-4 border border-foreground/10 rounded-lg bg-foreground/2">
                  <div className="flex flex-row gap-3 items-center">
                    <div className="w-16 h-16 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                      <FontAwesomeIcon icon={faLock} className="text-primary w-6 h-6" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <p className="text-foreground/70 text-[10px] uppercase font-[monospace]">Total</p>
                      <p className="text-foreground/70 text-[11px] leading-tight">
                        Seus dados nunca são compartilhados. Opere com total discrição.
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-row gap-2 mt-3">
                    <div className="h-[1px] w-full border-b border-dashed border-foreground/10 self-center" />
                    <FontAwesomeIcon icon={faLock} className="text-primary/30 w-3 h-3" />
                    <div className="h-[1px] w-full border-b border-dashed border-foreground/10 self-center" />
                  </div>
                </div>
              </motion.div>

              {/* Speed Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: 0.4, ease: "easeOut" }}
                className="flex flex-col gap-2"
              >
                <p className="text-foreground/60 uppercase text-xs font-[monospace]">Velocidade</p>
                <div className="p-4 border border-foreground/10 rounded-lg bg-foreground/2">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <FontAwesomeIcon icon={faBolt} className="text-primary w-3 h-3" />
                      <p className="text-foreground/70 text-[11px] font-semibold">Instantâneo</p>
                    </div>
                    <p className="text-foreground/70 text-[11px] leading-tight">
                      Transações processadas em segundos, sem esperas ou burocracias.
                    </p>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </section>
    </main>
  )
}

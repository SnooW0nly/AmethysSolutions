'use client'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faChevronRight, faUpRightFromSquare } from '@fortawesome/free-solid-svg-icons'
import { motion } from 'framer-motion'
import GridLines from '@/components/grid-lines'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

const HERO_LINE_ONE_WORDS: { text: string; highlight: boolean }[] = [
  { text: "Sua", highlight: false },
  { text: "carteira", highlight: true },
  { text: "digital", highlight: true },
]
const HERO_LINE_TWO_WORDS: { text: string; highlight: boolean }[] = [
  { text: "completa", highlight: false },
  { text: "em", highlight: false },
  { text: "um", highlight: false },
  { text: "só", highlight: false },
  { text: "lugar", highlight: false },
]

export function Hero() {
  return (
    <section className="flex flex-col justify-center md:items-center md:text-center pt-16 md:pt-24">
      <GridLines
        className="z-0 opacity-20"
        style={{
          WebkitMaskImage:
            "radial-gradient(60% 60% at 50% 40%, #000 60%, transparent 100%)",
          maskImage:
            "radial-gradient(60% 60% at 50% 40%, #000 60%, transparent 100%)",
        }}
      />
      <section className="relative flex flex-col gap-2 w-full">
        <motion.div
          initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ delay: 1.5, duration: 0.2, ease: "easeOut" }}
          className="w-full md:w-fit text-center items-center justify-center px-5 py-1 bg-primary/30 backdrop-blur-[32px] border border-primary/20 rounded-full text-foreground text-[12px] self-center flex flex-row gap-2"
        >
          <p>
            Conta gratuita <span className="font-semibold">para sempre</span>
          </p>
          <p className="text-primary/50">|</p>
          <Link href="/login" className="text-xs text-foreground p-1 hover:text-primary transition-colors inline-flex items-center gap-1">
            Começar agora
            <FontAwesomeIcon icon={faUpRightFromSquare} className="text-[10px]" />
          </Link>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(64px)" }}
          transition={{ delay: 1.5, duration: 0.2, ease: "easeOut" }}
          className="pointer-events-none absolute top-20 left-1/2 -translate-x-1/2 h-40 md:h-50 w-[60%] max-w-sm rounded-full bg-primary/20 blur-[80px]"
        />
        <h1 className="text-[2.5rem] md:text-7xl font-bold leading-[1.1]">
          {HERO_LINE_ONE_WORDS.map((item, index) => (
            <motion.span
              key={`l1-${index}`}
              initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ delay: index * 0.1, duration: 0.4, ease: "easeOut" }}
              className={`inline-block mr-2.5 ${item.highlight ? "text-primary" : ""}`}
            >
              {item.text}
            </motion.span>
          ))}
          <br />
          {HERO_LINE_TWO_WORDS.map((item, index) => (
            <motion.span
              key={`l2-${index}`}
              initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ delay: (index + 4) * 0.1, duration: 0.4, ease: "easeOut" }}
              className={`inline-block mr-2.5 ${item.highlight ? "text-primary" : ""}`}
            >
              {item.text}
            </motion.span>
          ))}
        </h1>
        <motion.p
          initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ delay: 1.2, duration: 0.5, ease: "easeOut" }}
          className="text-foreground/70 font-normal text-[15px] max-w-2xl self-center"
        >
          Receba e transfira PIX de forma anônima, sem MEDs ou bloqueios e sem idade mínima. <span className="font-semibold text-primary">Privacidade, liberdade e segurança</span> para você operar com tranquilidade.
        </motion.p>
        <div className="flex gap-2 md:gap-5 flex-col md:flex-row md:items-center md:justify-center mt-2">
          <motion.div
            initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ delay: 1.6, duration: 0.5, ease: "easeOut" }}
            className="flex gap-2"
          >
            <Button
              className="w-fit bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => {
                window.location.href = "/pricing";
              }}
            >
              <span>Começar agora</span>
            </Button>
            <Button
              className="w-fit bg-background border border-foreground/10 rounded-lg text-foreground hover:bg-foreground/10 md:hidden"
              onClick={() => {
                window.location.href = "/about";
              }}
            >
              <span className="flex items-center justify-center gap-1">
                Saiba mais <FontAwesomeIcon icon={faChevronRight} className="text-[11px] duration-200 transition-all hover:text-foreground text-foreground/80" />
              </span>
            </Button>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ delay: 1.7, duration: 0.5, ease: "easeOut" }}
          >
            <Button
              className="w-fit bg-transparent hover:bg-foreground/10 rounded-xl text-foreground hidden md:flex"
              onClick={() => {
                window.location.href = "/about";
              }}
            >
              <span className="flex items-center justify-center gap-1">
                Saiba mais <FontAwesomeIcon icon={faChevronRight} className="text-[11px] duration-200 transition-all hover:text-foreground text-foreground/80" />
              </span>
            </Button>
          </motion.div>
        </div>
      </section>
    </section>
  )
}

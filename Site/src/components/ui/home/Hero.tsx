"use client";

import { Button, Link } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { motion } from "framer-motion";
import GridLines from "@/components/GridLines";

const HERO_LINE_ONE_WORDS: string[] = ["Potencialize", "sua", "comunidade"];
const HERO_LINE_TWO_WORDS: { text: string; highlight: boolean }[] = [
  { text: "com", highlight: false },
  { text: "tecnologia", highlight: true },
  { text: "de", highlight: false },
  { text: "ponta", highlight: false },
];

export function Hero() {
  return (
    <section className="flex flex-col justify-center md:items-center md:text-center">
      <GridLines
        className="z-0 opacity-20"
        style={{
          WebkitMaskImage:
            "radial-gradient(60% 60% at 50% 40%, #000 60%, transparent 100%)",
          maskImage:
            "radial-gradient(60% 60% at 50% 40%, #000 60%, transparent 100%)",
        }}
      />
      <section className="relative flex flex-col gap-2">
        <motion.div
          initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ delay: 1.5, duration: 0.2, ease: "easeOut" }}
          className="w-full md:w-fit text-center items-center justify-center px-5 py-1 bg-primary/30 backdrop-blur-[32px] border border-primary/20 rounded-full text-foreground text-[12px] self-center flex flex-row gap-2"
        >
          <p>
            Cupom AMETHYS <span className="font-semibold">50% OFF</span>
          </p>
          <p className="text-primary/50">|</p>
          <Link href="/pricing" showAnchorIcon className="text-xs text-foreground bg p-1">
            Conferir
          </Link>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(64px)" }}
          transition={{ delay: 1.5, duration: 0.2, ease: "easeOut" }}
          className="pointer-events-none absolute top-20 left-25 h-40 md:left-50 md:h-50 w-1/2 max-w-sm rounded-full bg-primary/20 blur-[80px]"
        />
        <h1 className="text-[2.5rem] md:text-7xl font-bold leading-[1.1]">
          {HERO_LINE_ONE_WORDS.map((word, index) => (
            <motion.span
              key={`l1-${index}`}
              initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ delay: index * 0.1, duration: 0.4, ease: "easeOut" }}
              className="inline-block mr-2.5"
            >
              {word}
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
          Eleve o padrão do seu negócio e aumente seus resultados com as nossas soluções. <span className="font-semibold text-foreground/90">Performance, segurança e inovação</span> para o crescimento do seu negócio.
        </motion.p>
        <div className="flex gap-2 md:gap-5 flex-col md:flex-row md:items-center md:justify-center mt-2">
          <motion.div
            initial={{ opacity: 0, y: 8, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ delay: 1.6, duration: 0.5, ease: "easeOut" }}
            className="flex gap-2"
          >
            <Button
              className="w-fit bg-foreground text-background hover:bg-foreground/90"
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
                Conheça nossos produtos <FontAwesomeIcon icon={faChevronRight} className="text-[11px] duration-200 transition-all hover:text-foreground text-foreground/80" />
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
                Conheça nossos produtos <FontAwesomeIcon icon={faChevronRight} className="text-[11px] duration-200 transition-all hover:text-foreground text-foreground/80" />
              </span>
            </Button>
          </motion.div>
        </div>
      </section>
    </section>
  );
}



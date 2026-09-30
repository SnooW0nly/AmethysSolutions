"use client";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronRight } from "@fortawesome/free-solid-svg-icons";

export function SaibaMaisSection() {
  return (
    <section className="mt-40 mb-20">
      <div
        className="group relative overflow-hidden bg-[url('/browse.png')] bg-cover md:bg-center bg-no-repeat rounded-xl p-4 border border-foreground/10 cursor-pointer h-50 flex items-end justify-between before:absolute before:inset-0 before:pointer-events-none hover:border-foreground/15 duration-100 transition-all"
        onClick={() => {
          window.location.href = "/about";
        }}
      >
        <div className="max-w-1xl flex flex-col gap-1">
          <div className="flex flex-row gap-1 items-center">
            <span className="text-primary font-semibold text-[12px]">Saiba mais</span>
          </div>
          <h1 className="text-2xl font-[500] max-w-[300px] leading-[1.1]">Descubra o potencial que temos a oferecer</h1>
        </div>
        <div className="flex flex-row gap-2">
          <div className="border border-foreground/10 rounded-full p-3 w-10 h-10 flex items-center justify-center text-sm text-primary duration-100 transition-all group-hover:bg-foreground/5">
            <FontAwesomeIcon icon={faChevronRight} className="text-foreground/70 text-[12px] ml-[0.4]" />
          </div>
        </div>
      </div>
    </section>
  );
}



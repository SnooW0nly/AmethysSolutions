"use client";

import { useEffect, useState } from "react";

type Stats = { faturamento: number; totalProdutos: number; totalClientes: number };

const DEFAULT_STATS: Stats = { faturamento: 0, totalProdutos: 0, totalClientes: 0 };

export function StatsSection() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    fetch("/api/info/stats")
      .then((res) => res.json())
      .then((data) => setStats(data as Stats))
      .catch(() => setStats(DEFAULT_STATS));
  }, []);

  return (
    <section className="mt-20 flex flex-col items-center justify-center">
      <div className="w-full flex flex-col items-center">
        <div className="flex items-center w-full">
          <div className="flex-grow border-t border-foreground/10"></div>
          <span className="mx-4 text-primary font-[700] text-sm uppercase">Estatísticas reais</span>
          <div className="flex-grow border-t border-foreground/10"></div>
        </div>
        <span className="block text-foreground/60 text-[12px] text-center mt-[-3px]">Informações atualizadas diariamente</span>
      </div>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3 w-full justify-center items-center text-center mt-8">
        {stats ? (
          <>
            <div>
              <p className="text-foreground text-4xl font-bold">R$ {Number(stats.faturamento).toFixed(2)}</p>
              <span className="text-foreground/70 text-sm">Faturamento total das lojas</span>
            </div>
            <div>
              <p className="text-foreground text-4xl font-bold">{stats.totalProdutos}</p>
              <span className="text-foreground/70 text-sm">Produtos vendidos no mercado</span>
            </div>
            <div>
              <p className="text-foreground text-4xl font-bold">{stats.totalClientes}</p>
              <span className="text-foreground/70 text-sm">Clientes ativos e satisfeitos</span>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-col items-center">
              <div className="h-10 w-40 rounded-md bg-foreground/10 animate-pulse" />
              <div className="h-3 w-56 rounded-md bg-foreground/5 animate-pulse mt-2" />
            </div>
            <div className="flex flex-col items-center">
              <div className="h-10 w-40 rounded-md bg-foreground/10 animate-pulse" />
              <div className="h-3 w-56 rounded-md bg-foreground/5 animate-pulse mt-2" />
            </div>
            <div className="flex flex-col items-center">
              <div className="h-10 w-40 rounded-md bg-foreground/10 animate-pulse" />
              <div className="h-3 w-56 rounded-md bg-foreground/5 animate-pulse mt-2" />
            </div>
          </>
        )}
      </div>
      <div className="flex items-start w-full justify-between mt-2">
        <div className="flex flex-col items-start">
          <div className="w-[1px] h-8 bg-foreground/10"></div>
          <div className="w-8 h-[1px] bg-foreground/10"></div>
        </div>
        <div />
        <div className="flex flex-col items-end">
          <div className="w-[1px] h-8 bg-foreground/10"></div>
          <div className="w-8 h-[1px] bg-foreground/10"></div>
        </div>
      </div>
    </section>
  );
}



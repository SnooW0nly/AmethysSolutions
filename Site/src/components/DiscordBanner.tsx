"use client";

import { Button } from "@heroui/button";
import NextLink from "next/link";
import { useEffect, useState } from "react";

export const DiscordBanner = () => {
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Começa a sumir a partir de 10px, some completamente em 50px
  const progress = Math.min(1, scrollY / 50); // 0 = visível, 1 = sumiu
  const opacity = 1 - progress;
  const height = Math.round(40 * (1 - progress)); // 40px → 0px

  return (
    <div
      className="fixed top-0 left-0 right-0 z-[60] flex justify-center items-center bg-purple-600 text-white px-4 text-center shadow-md overflow-hidden transition-none"
      style={{
        opacity,
        height: `${height}px`,
        pointerEvents: opacity === 0 ? "none" : "auto",
      }}
    >
      <span className="text-sm font-medium mr-4 whitespace-nowrap">Entre no servidor do Discord</span>
      <Button
        asChild
        variant="outline"
        size="sm"
        className="bg-white text-purple-600 hover:bg-purple-100 shrink-0"
      >
        <NextLink href="/socials/discord">Entrar</NextLink>
      </Button>
    </div>
  );
};
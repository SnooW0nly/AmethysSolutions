"use client";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBars } from "@fortawesome/free-solid-svg-icons";
import { useCallback } from "react";
import { NavbarUserMenu } from "@/components/DiscordButton";
import { DiscordIcon, Logo } from "@/components/Icons";
import { Link } from "@heroui/link";

type TopbarProps = {
  onOpenSidebar?: () => void;
};

export function Topbar({ onOpenSidebar }: TopbarProps) {
  const handleOpen = useCallback(() => {
    onOpenSidebar?.();
  }, [onOpenSidebar]);
  return (
    <header className="flex items-center justify-between h-14 px-4 border-b border-foreground/10 bg-background/90 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <button className="md:hidden p-2 rounded-md hover:bg-foreground/5" aria-label="Abrir menu" onClick={handleOpen}>
          <FontAwesomeIcon icon={faBars} size="sm" />
        </button>
        <div
            className="md:flex hidden justify-start items-center gap-3 cursor-pointer select-none"
            onClick={() => {
              window.location.href = "/dashboard";
            }}
          >
            <Logo size={38} width={38} height={38} />
            <div className="flex flex-col leading-[15px]">
              <span className="text-foreground/90 font-normal font-sans text-[13px]">
                Amethys
              </span>
              <span className="text-foreground/60 font-normal font-sans text-[12px]">
                Applications
              </span>
            </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Link isExternal aria-label="Discord" href="/socials/discord">
            <DiscordIcon className="text-foreground" />
        </Link>
        <NavbarUserMenu />
      </div>
    </header>
  );
}

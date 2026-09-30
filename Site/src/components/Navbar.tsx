"use client";

import {
  Navbar as HeroUINavbar,
  NavbarContent,
  NavbarMenu,
  NavbarMenuToggle,
  NavbarBrand,
  NavbarItem,
  NavbarMenuItem,
} from "@heroui/navbar";
import { Link } from "@heroui/link";
import { link as linkStyles } from "@heroui/theme";
import NextLink from "next/link";
import clsx from "clsx";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { DiscordIcon, Logo } from "@/components/Icons";
import { navItems } from "@/config/navbar";
import { NavbarUserMenu } from "@/components/DiscordButton";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronRight } from "@fortawesome/free-solid-svg-icons";

export const Navbar = ({
  className,
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) => {
  const pathname = usePathname();
  const isHomepage = pathname === "/";
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <HeroUINavbar
      maxWidth="full"
      className={clsx(
        "fixed z-50 border border-foreground/10 bg-background/70 backdrop-blur-md supports-[backdrop-filter]:bg-background/75",
        "shadow-[0_8px_32px_rgba(0,0,0,0.12)] rounded-2xl",
        className ?? "top-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-7xl"
      )}
      style={style}
      classNames={{
        wrapper: "max-w-7xl mx-auto px-6",
        menu: clsx(
          "w-full pt-2 pb-6 rounded-b-2xl",
          isHomepage ? "top-[calc(var(--navbar-height,64px)+40px)]" : "top-[var(--navbar-height,64px)]"
        ),
      }}
      disableAnimation
      isMenuOpen={isMenuOpen}
      onMenuOpenChange={setIsMenuOpen}
    >
      {/* Esquerda: Logo */}
      <NavbarContent className="basis-1/5 sm:basis-full" justify="start">
        <NavbarBrand as="li" className="gap-3 max-w-fit">
          <NextLink
            className="flex justify-start items-center gap-3"
            href="/"
          >
            <Logo size={38} width={38} height={38} />
            <div className="flex flex-col leading-[15px]">
              <span className="text-foreground/90 font-normal font-sans text-[13px]">
                Amethys
              </span>
              <span className="text-foreground/60 font-normal font-sans text-[12px]">
                Solutions
              </span>
            </div>
          </NextLink>
        </NavbarBrand>
      </NavbarContent>

      {/* Centro: Links */}
      <NavbarContent className="hidden lg:flex" justify="center">
        <ul className="flex justify-center items-center gap-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <NavbarItem key={item.href}>
                <Link
                  className={clsx(
                    linkStyles({ color: "foreground" }),
                    "group relative font-normal font-sans text-[13px] flex gap-1 items-center justify-center py-1 px-3 rounded-md transition-all duration-150",
                    isActive
                      ? "text-foreground"
                      : "text-foreground/75 hover:text-foreground hover:bg-foreground/5"
                  )}
                  color="foreground"
                  showAnchorIcon={item.external}
                  isExternal={item.external}
                  href={item.href}
                >
                  <span>{item.label}</span>
                  <span
                    className={clsx(
                      "pointer-events-none absolute -bottom-0.5 left-2 right-2 h-[1.5px] rounded-full transition-all duration-200",
                      isActive
                        ? "bg-primary opacity-100"
                        : "bg-primary/70 opacity-0"
                    )}
                  />
                </Link>
              </NavbarItem>
            );
          })}
        </ul>
      </NavbarContent>

      {/* Direita: Ícones */}
      <NavbarContent
        className="hidden sm:flex basis-1/5 sm:basis-full"
        justify="end"
      >
        <NavbarItem className="hidden sm:flex gap-3 items-center">
          <Link isExternal aria-label="Discord" href="/socials/discord">
            <DiscordIcon className="text-foreground" />
          </Link>

          <NavbarUserMenu />
        </NavbarItem>
      </NavbarContent>

      {/* Mobile */}
      <NavbarContent className="sm:hidden basis-1 pl-4" justify="end">
        <Link isExternal aria-label="Discord" href="/socials/discord">
          <DiscordIcon className="text-foreground" />
        </Link>
        <NavbarMenuToggle
          className="p-2"
          aria-label={isMenuOpen ? "Fechar menu" : "Abrir menu"}
        />
      </NavbarContent>

      <NavbarMenu className="w-full">
        <div className="ml-0 mx-4 mt-2 flex flex-col gap-4">
          <NavbarUserMenu />
          {navItems.map((item, index) => (
            <NavbarMenuItem
              key={`${item}-${index}`}
              className="flex flex-col items-start justify-start"
            >
              <Link
                href={item.href}
                size="lg"
                className="font-sans text-lg font-medium text-foreground flex flex-col gap-1 items-start justify-start"
                onPress={() => setIsMenuOpen(false)}
              >
                <div className="flex flex-row items-center justify-start gap-1">
                  {item.label}
                  <FontAwesomeIcon
                    icon={faChevronRight}
                    className="text-foreground/50 text-[11px]"
                  />
                </div>
                <span className="text-foreground/50 text-sm font-normal">
                  {item.description}
                </span>
              </Link>
            </NavbarMenuItem>
          ))}
        </div>
      </NavbarMenu>
    </HeroUINavbar>
  );
};
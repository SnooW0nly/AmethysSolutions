'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBars, faXmark } from '@fortawesome/free-solid-svg-icons'
import { RippleButton } from './ripple-button'
import { UserMenu } from './user-menu'
import { Logo } from './icons'
import { navItems } from '@/config/navbar'

export function Navbar() {
  const pathname = usePathname()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const isExternalLink = (href: string) => href.startsWith('http://') || href.startsWith('https://')

  return (
    <header className="py-4 sticky top-0 z-50 bg-background/60 backdrop-blur supports-[backdrop-filter]:bg-background/85 border-b border-foreground/10">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between w-full">
          {/* Logo - Left */}
          <div className="flex items-center flex-shrink-0">
            <Link href="/" className="flex items-center gap-3">
              <Logo size={38} width={38} height={38} />
              <div className="flex flex-col leading-[15px]">
                <span className="text-foreground/90 font-normal font-sans text-[13px]">
                  Amethys
                </span>
                <span className="text-foreground/60 font-normal font-sans text-[12px]">
                  Wallet
                </span>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation - Center */}
          <nav className="hidden lg:flex items-center justify-center flex-1">
            <ul className="flex justify-center items-center gap-2">
              {navItems.map((item) => {
                const isActive = pathname === item.href
                const external = isExternalLink(item.href)
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      target={external ? '_blank' : undefined}
                      rel={external ? 'noopener noreferrer' : undefined}
                      className={`group relative font-normal text-[13px] flex gap-1 items-center justify-center py-2 px-4 rounded-md transition-all duration-200 ${
                        isActive
                          ? 'text-foreground'
                          : 'text-foreground/75 hover:text-foreground hover:bg-foreground/10'
                      }`}
                    >
                      <span>{item.label}</span>
                      <span className={`pointer-events-none absolute -bottom-0.5 left-2 right-2 h-[1.5px] rounded-full transition-all duration-200 ${
                        isActive ? 'bg-primary opacity-100' : 'bg-primary/70 opacity-0'
                      }`} />
                    </Link>
                  </li>
                )
              })}
            </ul>
          </nav>

          {/* Right Side - User Menu & Mobile Menu */}
          <div className="flex items-center justify-end gap-4 flex-shrink-0">
            <div className="hidden md:block">
              <UserMenu />
            </div>

            {/* Mobile Menu Button */}
            <RippleButton
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="lg:hidden p-2 text-foreground hover:bg-foreground/5 rounded-lg transition-colors"
            >
              <FontAwesomeIcon icon={isMenuOpen ? faXmark : faBars} className="w-5 h-5" />
            </RippleButton>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMenuOpen && (
        <div className="md:hidden border-t border-foreground/10 bg-background/95 backdrop-blur">
          <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col gap-4">
            {navItems.map((item) => {
              const isActive = pathname === item.href
              const external = isExternalLink(item.href)
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  target={external ? '_blank' : undefined}
                  rel={external ? 'noopener noreferrer' : undefined}
                  onClick={() => setIsMenuOpen(false)}
                  className={`text-base font-medium transition-colors ${
                    isActive
                      ? 'text-primary'
                      : 'text-foreground/70 hover:text-foreground'
                  }`}
                >
                  {item.label}
                </Link>
              )
            })}
            <div className="mt-2">
              <UserMenu />
            </div>
          </div>
        </div>
      )}
    </header>
  )
}


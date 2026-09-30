'use client'

import Link from 'next/link'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faExternalLink } from '@fortawesome/free-solid-svg-icons'
import { faYoutube, faInstagram, faDiscord, faTelegram } from '@fortawesome/free-brands-svg-icons'
import { footer } from '@/config/footer'
import { RippleButton } from './ripple-button'
import { Logo } from './icons'
import { PWAInstallButton } from './pwa-install-button'

export function Footer() {
  const isExternalLink = (href: string) => href.startsWith('http://') || href.startsWith('https://')

  return (
    <footer className="flex flex-col py-10 border-t border-foreground/10 w-full">
      <section className="flex w-full flex-col md:flex-row gap-5 md:gap-20 max-w-7xl mx-auto px-6 md:justify-between">
        <div className="flex flex-col gap-2 md:justify-center">
          <div className="flex items-center justify-start gap-3">
            <Link href="/" className="flex flex-row gap-2 items-center select-none w-fit">
              <Logo size={40} width={40} height={40} />
              <div className="flex flex-col leading-[15px]">
                <span className="text-foreground/90 font-normal font-sans text-[13px]">
                  Amethys
                </span>
                <span className="text-foreground/60 font-normal font-sans text-[12px]">
                  Wallet
                </span>
              </div>
            </Link>
            <div className="h-6 w-px bg-foreground/20" />
            <PWAInstallButton />
          </div>
          <div className="flex flex-col gap-2">
            <p className="text-foreground/60 text-[12px]">© 2026 Amethys Wallet. Todos os direitos reservados.</p>
            <div className="flex flex-col gap-0.5">
              <p className="text-foreground/60 text-[12px]">
                Fintech administrada por <span className="font-semibold">AMETHYS GROUP LTDA</span>
              </p>
              <p className="text-foreground/60 text-[12px]">CNPJ: xx.xxx.xxx/xxxx-xx</p>
            </div>
            <div className="flex flex-row gap-1">
              <Link 
                href="https://discord.gg/pxMbjuh4BK" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-foreground/60 hover:text-foreground transition-colors"
                aria-label="YouTube"
              >
                <FontAwesomeIcon icon={faYoutube} className="text-[18px]" />
              </Link>
              <Link 
                href="https://discord.gg/pxMbjuh4BK" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-foreground/60 hover:text-foreground transition-colors"
                aria-label="Instagram"
              >
                <FontAwesomeIcon icon={faInstagram} className="text-[18px]" />
              </Link>
              <Link 
                href="https://discord.gg/pxMbjuh4BK" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-foreground/60 hover:text-foreground transition-colors"
                aria-label="Discord"
              >
                <FontAwesomeIcon icon={faDiscord} className="text-[18px]" />
              </Link>
              <Link 
                href="https://discord.gg/pxMbjuh4BK" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-foreground/60 hover:text-foreground transition-colors"
                aria-label="Telegram"
              >
                <FontAwesomeIcon icon={faTelegram} className="text-[18px]" />
              </Link>
            </div>
          </div>
        </div>
        <hr className="border-foreground/10 md:hidden my-0" />
        <div className="grid grid-cols-2 md:grid-cols-2 gap-5 md:gap-10">
          {footer.map((category, categoryIdx) => (
            <div key={categoryIdx} className="flex flex-col gap-3">
              <span className="text-foreground/70 text-[12px] font-semibold">{category.category}</span>
              <div key={categoryIdx} className="flex flex-col gap-1">
                {category.links.map((link, linkIdx) => {
                  const external = isExternalLink(link.href)
                  return (
                    <Link
                      key={linkIdx}
                      href={link.href}
                      target={external ? '_blank' : undefined}
                      rel={external ? 'noopener noreferrer' : undefined}
                      className="text-foreground/70 hover:text-foreground hover:underline text-[14px] transition-colors"
                    >
                      {link.label}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </section>
    </footer>
  )
}


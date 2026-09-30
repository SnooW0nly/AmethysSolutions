'use client'

import { useState, useEffect } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faChevronRight } from '@fortawesome/free-solid-svg-icons'

const sections = [
  { id: 'aceitacao', title: '1. Aceitação dos Termos' },
  { id: 'descricao', title: '2. Descrição do Serviço' },
  { id: 'planos', title: '3. Planos e Taxas' },
  { id: 'responsabilidades', title: '4. Responsabilidades do Usuário' },
  { id: 'limites', title: '5. Limites e Restrições' },
  { id: 'privacidade', title: '6. Privacidade e Segurança' },
  { id: 'prevencao', title: '7. Prevenção à Lavagem de Dinheiro' },
  { id: 'modificacoes', title: '8. Modificações do Serviço' },
  { id: 'limitacao', title: '9. Limitação de Responsabilidade' },
  { id: 'disposicoes', title: '10. Disposições Finais' },
]

export default function Terms() {
  const [activeSection, setActiveSection] = useState('aceitacao')

  useEffect(() => {
    const handleScroll = () => {
      const sectionElements = sections.map(s => document.getElementById(s.id))
      const scrollPosition = window.scrollY + 150

      // Check if at bottom of page - if so, activate last section
      const scrollHeight = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)
      const isAtBottom = window.innerHeight + window.scrollY >= scrollHeight - 200
      if (isAtBottom) {
        setActiveSection(sections[sections.length - 1].id)
        return
      }

      for (let i = sectionElements.length - 1; i >= 0; i--) {
        const section = sectionElements[i]
        if (section && section.offsetTop <= scrollPosition) {
          setActiveSection(sections[i].id)
          break
        }
      }
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id)
    if (element) {
      const offset = 100
      const elementPosition = element.getBoundingClientRect().top + window.pageYOffset
      window.scrollTo({ top: elementPosition - offset, behavior: 'smooth' })
    }
  }

  return (
    <main className="min-h-screen">
      <div className="max-w-7xl mx-auto py-12 px-4">
        {/* Header */}
        <div className="text-center mb-12">
          <p className="text-foreground/50 text-xs mb-2">
            Atualizado em {new Date().toLocaleDateString('pt-BR')}
          </p>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">Termos de Serviço</h1>
          <p className="text-foreground/60 text-base max-w-3xl mx-auto">
            Estes Termos regem o uso da plataforma Amethys Wallet. Ao utilizar nossos serviços,
            você concorda com as condições aqui descritas.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-12">
          {/* Sidebar Navigation - sticky */}
          <aside className="lg:w-72 shrink-0">
            <div className="lg:sticky lg:top-24">
              <p className="text-xs font-medium uppercase tracking-wider text-foreground/40 mb-4">
                Navegação
              </p>
              <nav className="space-y-1">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => scrollToSection(section.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all flex items-center justify-between group ${activeSection === section.id
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'text-foreground/60 hover:bg-foreground/5 hover:text-foreground'
                      }`}
                  >
                    <span className="truncate">{section.title}</span>
                    <FontAwesomeIcon
                      icon={faChevronRight}
                      className={`text-[10px] transition-transform ${activeSection === section.id ? 'text-primary' : 'text-foreground/30 group-hover:translate-x-0.5'
                        }`}
                    />
                  </button>
                ))}
              </nav>
            </div>
          </aside>

          {/* Content */}
          <div className="flex-1 max-w-4xl">
            <div className="space-y-20">

              <section id="aceitacao" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">1. Aceitação dos Termos</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[1.a]</span> Ao acessar e usar a Amethys Wallet, você concorda em cumprir e estar vinculado aos seguintes termos e condições de uso.</p>
                  <p><span className="text-foreground/50">[1.b]</span> Se você não concorda com alguma parte destes termos, não deve usar nosso serviço.</p>
                  <p><span className="text-foreground/50">[1.c]</span> A Amethys Wallet reserva o direito de suspender ou encerrar o acesso aos serviços apenas mediante ordem judicial ou determinação legal expressa, respeitando o princípio da presunção de inocência.</p>
                </div>
              </section>

              <section id="descricao" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">2. Descrição do Serviço</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[2.a]</span> A Amethys Wallet é uma gateway de pagamentos que oferece soluções completas para processamento de transações financeiras, permitindo que empresas e desenvolvedores integrem pagamentos via PIX, Cartão de Crédito/Débito e Criptomoedas em suas aplicações.</p>
                  <p><span className="text-foreground/50">[2.b]</span> Como gateway de pagamentos, fornecemos infraestrutura tecnológica segura para recebimento, processamento e gestão de transações financeiras, incluindo APIs, webhooks e ferramentas de gestão.</p>
                  <p><span className="text-foreground/50">[2.c]</span> Oferecemos diferentes planos de serviço com taxas e limites variados conforme descrito em nossa página de preços.</p>
                  <p><span className="text-foreground/50">[2.d]</span> Os serviços são fornecidos exclusivamente através da plataforma Amethys Wallet e seus sistemas integrados.</p>
                </div>
              </section>

              <section id="planos" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">3. Planos e Taxas</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[3.a]</span> Nossos planos são baseados em volume de transações mensais: FREE (até 300 transações/mês - R$ 0,70), CARBON (300-800 - R$ 0,65 - Mensalidade R$ 19,97), DIAMOND (800-2.000 - R$ 0,60 - Mensalidade R$ 49,97), RICH (3.000-6.000 - R$ 0,55 - Mensalidade R$ 149,97), ENTERPRISE (6.000+ - R$ 0,50 - Mensalidade R$ 999,97).</p>
                  <p><span className="text-foreground/50">[3.b]</span> Os planos são renovados automaticamente a cada 30 dias. Upgrades e downgrades são aplicados automaticamente com base no volume.</p>
                  <p><span className="text-foreground/50">[3.c]</span> As taxas e mensalidades podem ser alteradas mediante aviso prévio de 30 dias.</p>
                </div>
              </section>

              <section id="responsabilidades" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">4. Responsabilidades do Usuário</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[4.a]</span> Você é responsável por manter a segurança de sua conta e API Key, não compartilhando credenciais de acesso.</p>
                  <p><span className="text-foreground/50">[4.b]</span> Você se compromete a usar o serviço APENAS para fins legais e lícitos, sendo PROIBIDO utilizar a plataforma para qualquer atividade ilegal, fraudulenta ou criminosa.</p>
                  <p><span className="text-foreground/50">[4.c]</span> Você é responsável por manter saldo suficiente para cobrir taxas e mensalidades.</p>
                </div>
              </section>

              <section id="limites" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">5. Limites e Restrições</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[5.a]</span> Cada plano possui limites de transações mensais. Exceder pode resultar em upgrade automático ou restrições temporárias.</p>
                  <p><span className="text-foreground/50">[5.b]</span> Valores mínimos e máximos por transação podem ser aplicados conforme a política de cada método de pagamento.</p>
                  <p><span className="text-foreground/50">[5.c]</span> A Amethys Wallet reserva o direito de impor limites adicionais para segurança e estabilidade.</p>
                </div>
              </section>

              <section id="privacidade" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">6. Privacidade e Segurança</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[6.a]</span> A Amethys Wallet utiliza criptografia de ponta (SSL/TLS) e segue as melhores práticas de segurança e conformidade com a LGPD.</p>
                  <p><span className="text-foreground/50">[6.b]</span> Coletamos apenas dados necessários para a prestação dos serviços. Respeitamos o anonimato dos usuários e não solicitamos documentos de identificação pessoal.</p>
                  <p><span className="text-foreground/50">[6.c]</span> Não compartilhamos suas informações com terceiros, exceto quando necessário para processar transações ou quando exigido por ordem judicial.</p>
                  <p><span className="text-foreground/50">[6.d]</span> Mantemos registros de transações conforme exigido pela legislação brasileira.</p>
                  <p><span className="text-foreground/50">[6.e]</span> Você possui direitos garantidos pela LGPD, incluindo acesso, correção, exclusão e portabilidade de dados.</p>
                  <p><span className="text-foreground/50">[6.f]</span> Consulte nossa Política de Privacidade para mais detalhes.</p>
                  <p><span className="text-foreground/50">[6.g]</span> Você é responsável por manter a confidencialidade de suas credenciais de acesso.</p>
                </div>
              </section>

              <section id="prevencao" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">7. Prevenção à Lavagem de Dinheiro</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[7.a]</span> A Amethys Wallet está em conformidade com a Lei nº 9.613/1998 (prevenção à lavagem de dinheiro) e regulamentações do Banco Central.</p>
                  <p><span className="text-foreground/50">[7.b]</span> Você é responsável por garantir que todas as transações sejam legítimas e relacionadas a atividades lícitas.</p>
                  <p><span className="text-foreground/50">[7.c]</span> A Amethys Wallet NÃO bloqueia contas de usuários, exceto mediante ordem judicial ou determinação legal expressa.</p>
                  <p><span className="text-foreground/50">[7.d]</span> Em caso de ordem judicial, cumpriremos integralmente a determinação.</p>
                  <p><span className="text-foreground/50">[7.e]</span> Transações acima de valores estabelecidos pela legislação serão reportadas aos órgãos competentes.</p>
                  <p><span className="text-foreground/50">[7.f]</span> Não nos responsabilizamos por bloqueios impostos por instituições financeiras parceiras ou autoridades reguladoras.</p>
                </div>
              </section>

              <section id="modificacoes" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">8. Modificações do Serviço</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[8.a]</span> Reservamos o direito de modificar, suspender ou descontinuar qualquer aspecto do serviço a qualquer momento.</p>
                  <p><span className="text-foreground/50">[8.b]</span> Alterações significativas serão comunicadas com antecedência razoável.</p>
                  <p><span className="text-foreground/50">[8.c]</span> O uso continuado do serviço após modificações implica aceitação das novas condições.</p>
                </div>
              </section>

              <section id="limitacao" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">9. Limitação de Responsabilidade</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[9.a]</span> A Amethys Wallet não se responsabiliza por perdas ou danos decorrentes do uso ou impossibilidade de uso do serviço.</p>
                  <p><span className="text-foreground/50">[9.b]</span> Não nos responsabilizamos por falhas técnicas, interrupções ou indisponibilidade temporária.</p>
                  <p><span className="text-foreground/50">[9.c]</span> Não nos responsabilizamos por transações que violem estes termos ou a legislação aplicável.</p>
                </div>
              </section>

              <section id="disposicoes" className="scroll-mt-28">
                <h2 className="text-2xl font-bold mb-4 text-foreground">10. Disposições Finais</h2>
                <div className="space-y-3 text-foreground/80 text-[15px] leading-relaxed">
                  <p><span className="text-foreground/50">[10.a]</span> Estes termos podem ser atualizados periodicamente. O uso continuado implica aceitação das novas condições.</p>
                  <p><span className="text-foreground/50">[10.b]</span> Para questões sobre estes termos, entre em contato através do nosso suporte.</p>
                  <p><span className="text-foreground/50">[10.c]</span> Em caso de litígio, as partes elegem o foro da cidade de Peixoto de Azevedo, Mato Grosso, Brasil.</p>
                </div>
              </section>

            </div>

            {/* Spacer to allow scrolling last sections to top */}
            <div className="h-[50vh]" />
          </div>
        </div>
      </div>
    </main>
  )
}

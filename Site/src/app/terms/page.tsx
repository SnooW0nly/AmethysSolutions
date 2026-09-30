"use client";

import Link from "next/link";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCalendar, faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { faShield, faCookie, faMoneyBillWave, faDatabase, faClipboardCheck } from "@fortawesome/free-solid-svg-icons";

const legalDocs = [
  {
    href: "/terms/legais/privacy",
    badge: "Privacidade",
    icon: faShield,
    title: "Política de Privacidade",
    description: "Como coletamos, usamos e protegemos seus dados pessoais.",
  },
  {
    href: "/terms/legais/cookies",
    badge: "Cookies",
    icon: faCookie,
    title: "Política de Cookies",
    description: "Quais cookies utilizamos e como você pode gerenciá-los.",
  },
  {
    href: "/terms/legais/reembolso",
    badge: "Reembolso",
    icon: faMoneyBillWave,
    title: "Política de Reembolso",
    description: "Condições e procedimentos para solicitação de reembolso.",
  },
  {
    href: "/terms/legais/dpa",
    badge: "DPA",
    icon: faDatabase,
    title: "Acordo de Tratamento de Dados",
    description: "Termos sobre o tratamento de dados pessoais de terceiros.",
  },
  {
    href: "/terms/legais/aup",
    badge: "AUP",
    icon: faClipboardCheck,
    title: "Política de Uso Aceitável",
    description: "Regras de uso permitido dos nossos bots e aplicações.",
  },
];

function Clause({ index, children }: { index: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3 group">
      <span className="text-[11px] font-mono text-foreground/30 shrink-0 mt-0.5 group-hover:text-primary/50 transition-colors select-none w-12">
        {index}
      </span>
      <p className="text-sm text-foreground/75 leading-relaxed">{children}</p>
    </div>
  );
}

function Section({ number, title, children }: { number: string; title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <div className="flex items-baseline gap-3 border-b border-foreground/8 pb-2">
        <span className="text-[11px] font-mono text-primary/60 shrink-0">{number}</span>
        <h2 className="text-base font-bold text-foreground/95 uppercase tracking-wider">{title}</h2>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

export default function Terms() {
  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8 space-y-2 text-center">
        <p className="text-[11px] font-mono text-foreground/40 uppercase tracking-widest">Amethys Solutions</p>
        <h1 className="text-4xl font-bold tracking-tight">Termos de Serviço</h1>
        <p className="text-foreground/60 text-sm max-w-xl mx-auto leading-relaxed">
          Estes Termos regem o uso de todos os bots e aplicações da Amethys Solutions. Ao contratar ou utilizar qualquer serviço, você concorda integralmente com as condições descritas.
        </p>
        <div className="flex items-center justify-center gap-1.5 text-foreground/35 text-[11px] font-mono pt-1">
          <FontAwesomeIcon icon={faCalendar} className="text-[10px]" />
          <span>Última atualização: 04/08/2025 — Versão 2.0</span>
        </div>
      </div>

      <hr className="border-foreground/10 mb-10" />

      {/* Legal Docs quick-links */}
      <div className="mb-12">
        <p className="text-[11px] font-mono text-foreground/40 uppercase tracking-widest mb-4">Documentos Legais Relacionados</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {legalDocs.map((doc) => (
            <Link
              key={doc.href}
              href={doc.href}
              className="group flex items-start gap-3 p-3.5 rounded-lg border border-foreground/10 hover:border-primary/30 hover:bg-primary/3 transition-all duration-150"
            >
              <FontAwesomeIcon icon={doc.icon} className="text-primary/50 text-[14px] mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground/85 group-hover:text-foreground transition-colors">{doc.title}</p>
                <p className="text-[11px] text-foreground/45 mt-0.5 leading-snug">{doc.description}</p>
              </div>
              <FontAwesomeIcon icon={faArrowRight} className="text-foreground/25 text-[11px] mt-1 shrink-0 group-hover:text-primary/50 group-hover:translate-x-0.5 transition-all" />
            </Link>
          ))}
        </div>
      </div>

      <div className="space-y-10">

        <Section number="1." title="Objeto e Âmbito dos Serviços">
          <Clause index="1.1.">
            A Amethys Solutions, pessoa jurídica de direito privado, oferece exclusivamente o aluguel de bots e aplicações digitais prontos para implantação em servidores Discord, doravante denominados "Serviços".
          </Clause>
          <Clause index="1.2.">
            Estes Termos de Serviço ("Termos") regulam a relação contratual entre a Amethys Solutions ("Fornecedora") e qualquer pessoa física ou jurídica que acesse, contrate ou utilize os Serviços ("Usuário").
          </Clause>
          <Clause index="1.3.">
            Ao acessar ou utilizar quaisquer dos Serviços, o Usuário declara ter lido, compreendido e aceitado integralmente estes Termos, assim como todos os documentos a eles vinculados, incluindo a Política de Privacidade, Política de Cookies, Política de Reembolso, DPA e AUP.
          </Clause>
          <Clause index="1.4.">
            Caso o Usuário não concorde com qualquer disposição destes Termos, deverá abster-se de utilizar os Serviços.
          </Clause>
        </Section>

        <Section number="2." title="Cadastro, Conta e Autenticação">
          <Clause index="2.1.">
            Para utilizar os Serviços, é obrigatório o cadastro de uma conta. Durante o cadastro, poderão ser coletadas as seguintes informações: nome completo ou apelido, endereço de e-mail, Discord ID, país de origem e endereço IP.
          </Clause>
          <Clause index="2.2.">
            O Usuário é o único e exclusivo responsável pela guarda, sigilo e integridade de suas credenciais de acesso, respondendo por todas as ações realizadas em sua conta.
          </Clause>
          <Clause index="2.3.">
            Em caso de suspeita de uso não autorizado, acesso indevido ou comprometimento das credenciais, o Usuário deve comunicar imediatamente a equipe da Amethys Solutions pelos canais oficiais de suporte.
          </Clause>
          <Clause index="2.4.">
            A Amethys Solutions não armazena nem tem acesso às credenciais de login do Discord do Usuário. A autenticação é realizada exclusivamente por meio do protocolo OAuth2 oficial do Discord.
          </Clause>
          <Clause index="2.5.">
            O uso de VPNs, proxies ou qualquer ferramenta de mascaramento de endereço IP é expressamente proibido, salvo mediante autorização prévia e por escrito da Amethys Solutions.
          </Clause>
          <Clause index="2.6.">
            É vedado o compartilhamento, venda, transferência ou cessão de contas a terceiros sem autorização formal prévia da Amethys Solutions.
          </Clause>
          <Clause index="2.7.">
            A Amethys Solutions reserva-se o direito de recusar, suspender ou encerrar contas a seu exclusivo critério, especialmente em casos de violação destes Termos.
          </Clause>
        </Section>

        <Section number="3." title="Obrigações e Responsabilidades do Usuário">
          <Clause index="3.1.">
            O Usuário compromete-se a utilizar os Serviços em estrita conformidade com a legislação brasileira vigente e aplicável, incluindo, sem limitação, a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018), o Marco Civil da Internet (Lei nº 12.965/2014), o Código de Defesa do Consumidor e a legislação de direitos autorais.
          </Clause>
          <Clause index="3.2.">
            O Usuário é integralmente responsável pelo conteúdo inserido, transmitido ou gerado por meio dos bots e aplicações contratados, incluindo comandos, automações, mensagens e dados.
          </Clause>
          <Clause index="3.3.">
            São expressamente proibidas as seguintes condutas:
          </Clause>
          <Clause index="3.3.a.">
            Tentativa de acesso não autorizado às áreas administrativas, painéis internos ou infraestrutura dos Serviços por qualquer meio, incluindo engenharia reversa, decompilação, desmontagem ou exploração de vulnerabilidades.
          </Clause>
          <Clause index="3.3.b.">
            Uso de scripts externos, automações de terceiros, bots de automação ou quaisquer ferramentas não expressamente autorizadas que interajam com os Serviços.
          </Clause>
          <Clause index="3.3.c.">
            Venda, sublicenciamento, redistribuição ou revenda dos Serviços ou do acesso a eles sem autorização expressa.
          </Clause>
          <Clause index="3.4.">
            O Usuário compromete-se a manter-se atualizado sobre as regras e diretrizes das plataformas integradas, especialmente o Discord Terms of Service e o Discord Developer Policy.
          </Clause>
        </Section>

        <Section number="4." title="Uso dos Bots e Aplicações">
          <Clause index="4.1.">
            Os bots e aplicações fornecidos pela Amethys Solutions são licenciados para uso restrito pelo Usuário contratante, de forma não exclusiva, intransferível e para uso exclusivo no(s) servidor(es) Discord indicados no momento da contratação.
          </Clause>
          <Clause index="4.2.">
            É expressamente vedado utilizar os bots ou aplicações para quaisquer das seguintes finalidades:
          </Clause>
          <Clause index="4.2.a.">
            Atividades ilegais ou que violem qualquer lei ou regulamento aplicável, incluindo, sem limitação, fraudes, lavagem de dinheiro e crimes cibernéticos.
          </Clause>
          <Clause index="4.2.b.">
            Envio de spam, mensagens em massa não solicitadas, conteúdo enganoso ou phishing.
          </Clause>
          <Clause index="4.2.c.">
            Veiculação, armazenamento ou transmissão de conteúdo adulto (+18), material sexualmente explícito ou conteúdo que envolva menores de idade de forma inapropriada.
          </Clause>
          <Clause index="4.2.d.">
            Disseminação de malware, vírus, worms, trojans ou qualquer código malicioso.
          </Clause>
          <Clause index="4.2.e.">
            Ataques de negação de serviço (DoS/DDoS), flood ou qualquer prática que comprometa a estabilidade das plataformas.
          </Clause>
          <Clause index="4.2.f.">
            Coleta não autorizada de dados pessoais de terceiros por meio dos bots.
          </Clause>
          <Clause index="4.3.">
            A Amethys Solutions pode suspender ou revogar o acesso ao bot/aplicação em caso de suspeita fundamentada de uso indevido, sem necessidade de aviso prévio, preservado o direito de contraditório em momento posterior.
          </Clause>
          <Clause index="4.4.">
            O Usuário é responsável pela configuração adequada do bot em seu servidor, incluindo a definição de permissões, canais e integrações, de acordo com as boas práticas e as diretrizes disponibilizadas pela Amethys Solutions.
          </Clause>
        </Section>

        <Section number="5." title="Disponibilidade, SLA e Limitações">
          <Clause index="5.1.">
            A Amethys Solutions envidará seus melhores esforços para manter os Serviços disponíveis 24 (vinte e quatro) horas por dia, 7 (sete) dias por semana, de acordo com o plano contratado.
          </Clause>
          <Clause index="5.2.">
            A disponibilidade dos Serviços poderá ser interrompida nas seguintes situações, sem que isso configure descumprimento contratual:
          </Clause>
          <Clause index="5.2.a.">
            Manutenções programadas, com aviso prévio mínimo de 24 horas pelos canais oficiais da Amethys Solutions, sempre que possível.
          </Clause>
          <Clause index="5.2.b.">
            Falhas técnicas de terceiros, incluindo interrupções na plataforma Discord, provedores de hospedagem ou serviços de infraestrutura.
          </Clause>
          <Clause index="5.2.c.">
            Eventos de força maior, incluindo desastres naturais, ataques cibernéticos externos, falhas de energia ou quaisquer circunstâncias fora do controle razoável da Amethys Solutions.
          </Clause>
          <Clause index="5.3.">
            A Amethys Solutions não se responsabiliza por perdas de dados gerados por meio dos Serviços, como logs, históricos ou configurações, exceto quando haja previsão contratual específica de backup.
          </Clause>
          <Clause index="5.4.">
            Em nenhuma hipótese a Amethys Solutions será responsável por danos indiretos, lucros cessantes, perda de oportunidade de negócio, danos morais, danos à reputação ou qualquer prejuízo decorrente do uso ou da indisponibilidade dos Serviços.
          </Clause>
          <Clause index="5.5.">
            A responsabilidade total da Amethys Solutions perante o Usuário, em qualquer hipótese, ficará limitada ao valor efetivamente pago pelo Usuário pelos Serviços no mês em que ocorreu o dano.
          </Clause>
        </Section>

        <Section number="6." title="Propriedade Intelectual">
          <Clause index="6.1.">
            O código-fonte, design, interfaces, funcionalidades, marcas, logotipos, nome comercial e demais elementos intelectuais dos bots e aplicações são de propriedade exclusiva da Amethys Solutions, protegidos pela legislação brasileira e internacional de direitos autorais, marcas e propriedade intelectual.
          </Clause>
          <Clause index="6.2.">
            O contrato de prestação de serviços não transfere ao Usuário qualquer direito de propriedade intelectual sobre os Serviços, sendo vedado ao Usuário:
          </Clause>
          <Clause index="6.2.a.">
            Reproduzir, copiar, modificar, adaptar, traduzir ou criar obras derivadas dos bots/aplicações, total ou parcialmente.
          </Clause>
          <Clause index="6.2.b.">
            Remover ou alterar avisos de propriedade intelectual, marcas d'água ou créditos presentes nos Serviços.
          </Clause>
          <Clause index="6.2.c.">
            Utilizar o nome, marca ou logotipo da Amethys Solutions sem autorização prévia e expressa.
          </Clause>
          <Clause index="6.3.">
            Qualquer violação de propriedade intelectual ensejará a suspensão imediata do acesso aos Serviços, sem prejuízo das medidas legais cabíveis.
          </Clause>
        </Section>

        <Section number="7." title="Pagamentos, Planos e Renovação">
          <Clause index="7.1.">
            Os Serviços são oferecidos mediante pagamento conforme os planos e valores vigentes divulgados na plataforma, sujeitos a alteração nos termos da Cláusula 9.
          </Clause>
          <Clause index="7.2.">
            Os pagamentos são processados por meio de plataformas de pagamento de terceiros, sendo realizados prioritariamente via PIX. O Usuário é responsável por manter dados de pagamento válidos e atualizados.
          </Clause>
          <Clause index="7.3.">
            A falta de pagamento na data de vencimento poderá acarretar a suspensão imediata do acesso aos Serviços, sem necessidade de notificação prévia.
          </Clause>
          <Clause index="7.4.">
            Reembolsos seguem exclusivamente as regras estabelecidas na Política de Reembolso, disponível em <span className="font-mono text-primary/70 text-[11px]">/terms/legais/reembolso</span>.
          </Clause>
          <Clause index="7.5.">
            A Amethys Solutions não se responsabiliza por cobranças duplicadas, erros de processamento ou quaisquer falhas imputáveis a plataformas de pagamento de terceiros.
          </Clause>
        </Section>

        <Section number="8." title="Marketing, Comunicações e Feedbacks">
          <Clause index="8.1.">
            A Amethys Solutions poderá divulgar funcionalidades, benefícios e cases de uso dos Serviços para fins de marketing e comunicação institucional, sem identificar ou expor dados pessoais dos Usuários.
          </Clause>
          <Clause index="8.2.">
            Feedbacks, depoimentos e avaliações fornecidos pelo Usuário poderão ser utilizados pela Amethys Solutions para aprimoramento e divulgação dos Serviços, mediante consentimento prévio e expresso do Usuário.
          </Clause>
          <Clause index="8.3.">
            O Usuário poderá solicitar, a qualquer momento, a exclusão de seu depoimento ou avaliação, mediante comunicação formal aos canais de suporte.
          </Clause>
          <Clause index="8.4.">
            A Amethys Solutions poderá enviar comunicados, avisos de manutenção, atualizações de política e notificações operacionais por e-mail ou mensagem direta no Discord. O Usuário não poderá optar por não receber comunicações de natureza operacional essencial.
          </Clause>
        </Section>

        <Section number="9." title="Atualizações dos Termos, Planos e Serviços">
          <Clause index="9.1.">
            A Amethys Solutions reserva-se o direito de revisar, modificar ou atualizar estes Termos a qualquer momento, mediante notificação aos Usuários pelos canais oficiais com antecedência mínima de 7 (sete) dias, salvo em casos de urgência legal ou regulatória.
          </Clause>
          <Clause index="9.2.">
            O uso continuado dos Serviços após a vigência das alterações implica aceitação tácita e integral das novas condições.
          </Clause>
          <Clause index="9.3.">
            Os planos, valores, recursos, funcionalidades e condições dos Serviços poderão ser alterados, atualizados, suspensos ou descontinuados a qualquer tempo, sem que isso implique direito à indenização, salvo no que diz respeito ao período já pago e não utilizado.
          </Clause>
          <Clause index="9.4.">
            É responsabilidade exclusiva do Usuário revisar periodicamente os Termos vigentes, disponíveis permanentemente em <span className="font-mono text-primary/70 text-[11px]">/terms</span>.
          </Clause>
        </Section>

        <Section number="10." title="Rescisão e Suspensão">
          <Clause index="10.1.">
            O Usuário poderá encerrar sua conta e rescindir o contrato a qualquer momento, observando os procedimentos previstos no painel de controle ou mediante contato com o suporte.
          </Clause>
          <Clause index="10.2.">
            A Amethys Solutions poderá rescindir o contrato ou suspender o acesso do Usuário, com ou sem aviso prévio, nas seguintes hipóteses:
          </Clause>
          <Clause index="10.2.a.">
            Violação de qualquer cláusula destes Termos ou dos documentos a eles vinculados.
          </Clause>
          <Clause index="10.2.b.">
            Inadimplência superior a 3 (três) dias após a data de vencimento.
          </Clause>
          <Clause index="10.2.c.">
            Conduta fraudulenta, abusiva ou que cause danos à Amethys Solutions, a outros Usuários ou a terceiros.
          </Clause>
          <Clause index="10.2.d.">
            Determinação de autoridade judicial, administrativa ou regulatória competente.
          </Clause>
          <Clause index="10.3.">
            A rescisão por qualquer motivo não gera direito a reembolso, exceto nos casos expressamente previstos na Política de Reembolso.
          </Clause>
        </Section>

        <Section number="11." title="Disposições Finais">
          <Clause index="11.1.">
            Estes Termos constituem o acordo integral entre as partes quanto ao objeto aqui descrito e substituem quaisquer acordos anteriores, verbais ou escritos, sobre o mesmo tema.
          </Clause>
          <Clause index="11.2.">
            A eventual nulidade ou ineficácia de qualquer cláusula destes Termos não afetará a validade das demais disposições, que permanecerão em pleno vigor.
          </Clause>
          <Clause index="11.3.">
            A omissão ou tolerância de qualquer das partes quanto ao descumprimento de qualquer obrigação não constituirá novação, renúncia ou precedente para infrações futuras.
          </Clause>
          <Clause index="11.4.">
            Terceiros só poderão utilizar o nome, marca ou logotipo da Amethys Solutions mediante autorização prévia e por escrito.
          </Clause>
          <Clause index="11.5.">
            Em caso de litígio decorrente destes Termos, as partes elegem o Foro da Comarca de Peixoto de Azevedo, Estado de Mato Grosso, Brasil, com renúncia expressa a qualquer outro, por mais privilegiado que seja, para dirimir quaisquer controvérsias.
          </Clause>
          <Clause index="11.6.">
            Estes Termos são regidos pelas leis da República Federativa do Brasil.
          </Clause>
        </Section>

      </div>
    </div>
  );
}
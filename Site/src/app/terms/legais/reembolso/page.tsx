"use client";

import LegalLayout, { LegalSection, LegalClause, LegalNote } from "@/components/LegalLayout";

export default function Reembolso() {
  return (
    <LegalLayout
      badge="Reembolso"
      title="Política de Reembolso"
      subtitle="Estabelece as condições, prazos e procedimentos aplicáveis a solicitações de reembolso pelos Serviços prestados pela Amethys Solutions."
      updatedAt="04/08/2025"
    >

      <LegalSection number="1." title="Disposições Gerais">
        <LegalClause index="1.1.">
          Esta Política de Reembolso rege as condições sob as quais a Amethys Solutions poderá restituir, total ou parcialmente, valores pagos pelo Usuário pelos Serviços contratados.
        </LegalClause>
        <LegalClause index="1.2.">
          Ao contratar qualquer Serviço da Amethys Solutions, o Usuário declara ter lido e aceito integralmente esta Política, que faz parte integrante dos Termos de Serviço.
        </LegalClause>
        <LegalClause index="1.3.">
          Salvo disposição expressa em contrário nesta Política, os pagamentos realizados pelo Usuário são não reembolsáveis.
        </LegalClause>
      </LegalSection>

      <LegalSection number="2." title="Direito de Arrependimento (Art. 49 CDC)">
        <LegalClause index="2.1.">
          Nos termos do art. 49 do Código de Defesa do Consumidor (Lei nº 8.078/1990), o Usuário que contratar os Serviços por meio eletrônico tem o direito de se arrepender no prazo de 7 (sete) dias corridos, contados a partir da data da contratação.
        </LegalClause>
        <LegalClause index="2.2.">
          Para exercer o direito de arrependimento, o Usuário deve:
        </LegalClause>
        <LegalClause index="2.2.a.">
          Entrar em contato com o suporte da Amethys Solutions pelos canais oficiais dentro do prazo de 7 (sete) dias.
        </LegalClause>
        <LegalClause index="2.2.b.">
          Informar o número do pedido ou ID da transação, o motivo do arrependimento e os dados bancários ou chave PIX para devolução.
        </LegalClause>
        <LegalClause index="2.3.">
          O exercício do direito de arrependimento implica o cancelamento imediato do acesso aos Serviços e a restituição integral do valor pago, processada em até 10 (dez) dias úteis.
        </LegalClause>
        <LegalNote>
          O direito de arrependimento aplica-se apenas à primeira contratação de cada Serviço. Renovações, upgrades de plano e contratações adicionais não são elegíveis a este benefício.
        </LegalNote>
      </LegalSection>

      <LegalSection number="3." title="Reembolso por Falha na Prestação do Serviço">
        <LegalClause index="3.1.">
          O Usuário poderá solicitar reembolso parcial ou total em casos de falha comprovada e imputável exclusivamente à Amethys Solutions na prestação dos Serviços, observadas as seguintes condições:
        </LegalClause>
        <LegalClause index="3.1.a.">
          Indisponibilidade total e ininterrupta dos Serviços por período superior a 72 (setenta e duas) horas consecutivas, não decorrente de manutenção programada, força maior ou falha de terceiros (ex.: Discord, provedores de hospedagem).
        </LegalClause>
        <LegalClause index="3.1.b.">
          Cobrança duplicada ou indevida decorrente de erro exclusivo da Amethys Solutions, comprovada mediante apresentação do comprovante de pagamento.
        </LegalClause>
        <LegalClause index="3.2.">
          O valor do reembolso por indisponibilidade será calculado de forma proporcional ao período efetivamente afetado em relação ao ciclo de faturamento mensal.
        </LegalClause>
        <LegalClause index="3.3.">
          Falhas de desempenho parcial, lentidão, instabilidade intermitente ou funcionalidades temporariamente indisponíveis não configuram hipótese de reembolso, desde que não comprometam o uso primário do Serviço.
        </LegalClause>
      </LegalSection>

      <LegalSection number="4." title="Hipóteses de Não Reembolso">
        <LegalClause index="4.1.">
          Não serão elegíveis a reembolso, sob qualquer hipótese, os pagamentos realizados nas seguintes circunstâncias:
        </LegalClause>
        <LegalClause index="4.1.a.">
          Cancelamento ou rescisão por vontade unilateral do Usuário após o período de arrependimento de 7 dias.
        </LegalClause>
        <LegalClause index="4.1.b.">
          Suspensão ou encerramento do acesso por violação dos Termos de Serviço, AUP ou qualquer documento vinculado.
        </LegalClause>
        <LegalClause index="4.1.c.">
          Insatisfação subjetiva com funcionalidades já disponíveis e descritas no plano contratado.
        </LegalClause>
        <LegalClause index="4.1.d.">
          Indisponibilidade decorrente de manutenção programada, falhas na plataforma Discord, falhas de provedores terceiros ou eventos de força maior.
        </LegalClause>
        <LegalClause index="4.1.e.">
          Erros de configuração, uso inadequado ou imperícia do Usuário na operação dos bots e aplicações.
        </LegalClause>
        <LegalClause index="4.1.f.">
          Período já utilizado do ciclo de faturamento, salvo nos casos das Cláusulas 2 e 3 desta Política.
        </LegalClause>
        <LegalClause index="4.1.g.">
          Compras realizadas por terceiros com as credenciais do Usuário, sem comunicação imediata de uso não autorizado.
        </LegalClause>
      </LegalSection>

      <LegalSection number="5." title="Procedimento para Solicitação de Reembolso">
        <LegalClause index="5.1.">
          Para solicitar reembolso, o Usuário deve seguir o procedimento abaixo:
        </LegalClause>
        <LegalClause index="5.1.a.">
          <strong>Passo 1:</strong> Acessar o painel de suporte da Amethys Solutions ou entrar em contato pelos canais oficiais (Discord ou e-mail institucional).
        </LegalClause>
        <LegalClause index="5.1.b.">
          <strong>Passo 2:</strong> Apresentar as seguintes informações: Discord ID, ID da transação ou número do pedido, valor pago, data do pagamento, descrição detalhada do motivo da solicitação e, quando aplicável, evidências que comprovem a falha na prestação do serviço.
        </LegalClause>
        <LegalClause index="5.1.c.">
          <strong>Passo 3:</strong> Informar a chave PIX ou dados bancários para processamento da restituição.
        </LegalClause>
        <LegalClause index="5.2.">
          A Amethys Solutions analisará a solicitação em até 5 (cinco) dias úteis e comunicará a decisão fundamentada ao Usuário.
        </LegalClause>
        <LegalClause index="5.3.">
          Em caso de aprovação, o reembolso será processado em até 10 (dez) dias úteis contados da data de aprovação, por meio de transferência PIX ou pelo mesmo meio de pagamento utilizado na compra.
        </LegalClause>
        <LegalClause index="5.4.">
          Em caso de indeferimento, o Usuário poderá apresentar recurso no prazo de 5 (cinco) dias úteis, com novas evidências ou argumentação, para nova análise.
        </LegalClause>
      </LegalSection>

      <LegalSection number="6." title="Disposições Finais">
        <LegalClause index="6.1.">
          Esta Política é regida pela legislação brasileira, especialmente pelo Código de Defesa do Consumidor e demais normas aplicáveis.
        </LegalClause>
        <LegalClause index="6.2.">
          A Amethys Solutions reserva-se o direito de atualizar esta Política periodicamente. Alterações serão comunicadas pelos canais oficiais.
        </LegalClause>
      </LegalSection>

    </LegalLayout>
  );
}
"use client";

import LegalLayout, { LegalSection, LegalClause, LegalSubSection, LegalNote } from "@/components/LegalLayout";

export default function Privacy() {
  return (
    <LegalLayout
      badge="Privacidade"
      title="Política de Privacidade"
      subtitle="Explica como a Amethys Solutions coleta, utiliza, armazena e protege os dados pessoais dos Usuários, em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018)."
      updatedAt="04/08/2025"
    >

      <LegalSection number="1." title="Controlador dos Dados">
        <LegalClause index="1.1.">
          O controlador dos dados pessoais tratados no âmbito dos Serviços é a Amethys Solutions, pessoa jurídica de direito privado, com sede em Peixoto de Azevedo, Estado de Mato Grosso, Brasil.
        </LegalClause>
        <LegalClause index="1.2.">
          Para fins desta Política, aplicam-se as definições previstas na LGPD, em especial: "dado pessoal", "tratamento", "titular", "controlador", "operador" e "encarregado".
        </LegalClause>
        <LegalClause index="1.3.">
          Dúvidas, solicitações e requisições referentes ao tratamento de dados pessoais podem ser enviadas ao canal oficial de suporte da Amethys Solutions no Discord ou por e-mail institucional.
        </LegalClause>
      </LegalSection>

      <LegalSection number="2." title="Dados Coletados">
        <LegalClause index="2.1.">
          Durante o cadastro e uso dos Serviços, a Amethys Solutions poderá coletar os seguintes dados:
        </LegalClause>
        <LegalSubSection number="2.1.a." title="Dados fornecidos diretamente pelo Usuário">
          <LegalClause index="2.1.a.i.">Nome completo ou apelido, endereço de e-mail e país de origem informados no momento do cadastro.</LegalClause>
          <LegalClause index="2.1.a.ii.">Discord ID (identificador único do usuário na plataforma Discord), obtido via autenticação OAuth2.</LegalClause>
          <LegalClause index="2.1.a.iii.">Informações de pagamento, como dados de transação PIX, processados por plataformas de pagamento terceiras.</LegalClause>
        </LegalSubSection>
        <LegalSubSection number="2.1.b." title="Dados coletados automaticamente">
          <LegalClause index="2.1.b.i.">Endereço IP e metadados de rede no momento do acesso à plataforma.</LegalClause>
          <LegalClause index="2.1.b.ii.">Logs de acesso e de uso dos Serviços, incluindo data, hora, ações realizadas e erros registrados.</LegalClause>
          <LegalClause index="2.1.b.iii.">Informações de dispositivo, navegador e sistema operacional, quando aplicável.</LegalClause>
        </LegalSubSection>
        <LegalClause index="2.2.">
          A Amethys Solutions não coleta dados sensíveis conforme definidos pelo art. 5º, II da LGPD, tais como dados de saúde, biométricos, raciais, religiosos ou de orientação sexual.
        </LegalClause>
      </LegalSection>

      <LegalSection number="3." title="Finalidade e Base Legal do Tratamento">
        <LegalClause index="3.1.">
          O tratamento dos dados pessoais coletados é realizado com base nas seguintes hipóteses legais previstas na LGPD:
        </LegalClause>
        <LegalClause index="3.1.a.">
          <strong>Execução de contrato</strong> (art. 7º, V): para prestação dos Serviços contratados, gerenciamento de conta, suporte técnico e processamento de pagamentos.
        </LegalClause>
        <LegalClause index="3.1.b.">
          <strong>Legítimo interesse</strong> (art. 7º, IX): para prevenção de fraudes, segurança da plataforma, melhoria dos Serviços e comunicações operacionais essenciais.
        </LegalClause>
        <LegalClause index="3.1.c.">
          <strong>Cumprimento de obrigação legal</strong> (art. 7º, II): para atendimento a requisições de autoridades competentes e cumprimento de obrigações fiscais e regulatórias.
        </LegalClause>
        <LegalClause index="3.1.d.">
          <strong>Consentimento</strong> (art. 7º, I): para envio de comunicações de marketing e utilização de feedbacks, quando aplicável.
        </LegalClause>
      </LegalSection>

      <LegalSection number="4." title="Compartilhamento de Dados">
        <LegalClause index="4.1.">
          A Amethys Solutions não vende, aluga ou comercializa dados pessoais de Usuários a terceiros sob nenhuma hipótese.
        </LegalClause>
        <LegalClause index="4.2.">
          Os dados poderão ser compartilhados com terceiros exclusivamente nas seguintes situações:
        </LegalClause>
        <LegalClause index="4.2.a.">
          Provedores de serviços que atuam como operadores de dados (ex.: plataformas de pagamento, provedores de hospedagem, serviços de monitoramento), com os quais a Amethys Solutions mantém acordos de processamento de dados adequados.
        </LegalClause>
        <LegalClause index="4.2.b.">
          Autoridades públicas, judiciais ou regulatórias, quando exigido por lei, ordem judicial ou processo legal válido.
        </LegalClause>
        <LegalClause index="4.2.c.">
          Terceiros em caso de fusão, aquisição ou reestruturação societária, desde que o cessionário assuma as obrigações desta Política.
        </LegalClause>
        <LegalClause index="4.3.">
          Todo compartilhamento de dados com operadores é regido por cláusulas contratuais que garantem nível de proteção equivalente ao desta Política.
        </LegalClause>
      </LegalSection>

      <LegalSection number="5." title="Retenção e Exclusão de Dados">
        <LegalClause index="5.1.">
          Os dados pessoais serão retidos pelo tempo necessário ao cumprimento das finalidades descritas nesta Política ou por períodos superiores quando exigidos por lei.
        </LegalClause>
        <LegalClause index="5.2.">
          Após o encerramento da conta ou término da relação contratual, os dados serão retidos por até 5 (cinco) anos para fins de cumprimento de obrigações legais, contábeis e fiscais, findo o qual serão anonimizados ou excluídos de forma segura.
        </LegalClause>
        <LegalClause index="5.3.">
          Logs de acesso são retidos por, no mínimo, 6 (seis) meses, conforme previsto no art. 15 do Marco Civil da Internet.
        </LegalClause>
      </LegalSection>

      <LegalSection number="6." title="Direitos do Titular">
        <LegalClause index="6.1.">
          Nos termos dos arts. 17 a 22 da LGPD, o Usuário, na qualidade de titular dos dados, poderá exercer os seguintes direitos mediante solicitação formal ao suporte:
        </LegalClause>
        <LegalClause index="6.1.a.">Confirmação da existência de tratamento e acesso aos dados pessoais.</LegalClause>
        <LegalClause index="6.1.b.">Correção de dados incompletos, inexatos ou desatualizados.</LegalClause>
        <LegalClause index="6.1.c.">Anonimização, bloqueio ou eliminação de dados desnecessários, excessivos ou tratados em desconformidade com a LGPD.</LegalClause>
        <LegalClause index="6.1.d.">Portabilidade dos dados a outro fornecedor de serviço, conforme regulamentação da ANPD.</LegalClause>
        <LegalClause index="6.1.e.">Revogação do consentimento, quando o tratamento for baseado nessa hipótese legal.</LegalClause>
        <LegalClause index="6.1.f.">Informação sobre entidades públicas e privadas com as quais os dados foram compartilhados.</LegalClause>
        <LegalClause index="6.1.g.">Revisão de decisões tomadas unicamente com base em tratamento automatizado.</LegalClause>
        <LegalClause index="6.2.">
          As solicitações serão respondidas no prazo de até 15 (quinze) dias úteis, podendo ser prorrogado mediante justificativa fundamentada.
        </LegalClause>
        <LegalNote>
          A Amethys Solutions poderá solicitar documentos de identificação para verificar a autenticidade das solicitações, garantindo a segurança dos dados do titular.
        </LegalNote>
      </LegalSection>

      <LegalSection number="7." title="Segurança dos Dados">
        <LegalClause index="7.1.">
          A Amethys Solutions adota medidas técnicas e organizacionais adequadas para proteger os dados pessoais contra acesso não autorizado, perda, alteração, divulgação ou destruição.
        </LegalClause>
        <LegalClause index="7.2.">
          Entre as medidas adotadas, incluem-se: criptografia de dados em trânsito (TLS/HTTPS), controle de acesso baseado em funções, logs de auditoria e treinamento de equipe.
        </LegalClause>
        <LegalClause index="7.3.">
          Em caso de incidente de segurança que possa acarretar risco ou dano relevante aos titulares, a Amethys Solutions notificará a Autoridade Nacional de Proteção de Dados (ANPD) e os titulares afetados no prazo razoável, conforme previsto no art. 48 da LGPD.
        </LegalClause>
      </LegalSection>

      <LegalSection number="8." title="Transferência Internacional de Dados">
        <LegalClause index="8.1.">
          Caso dados pessoais sejam transferidos para países ou organismos internacionais que não proporcionem grau de proteção adequado, a Amethys Solutions adotará as salvaguardas previstas no art. 33 da LGPD, incluindo cláusulas contratuais padrão ou garantias equivalentes.
        </LegalClause>
      </LegalSection>

      <LegalSection number="9." title="Alterações nesta Política">
        <LegalClause index="9.1.">
          Esta Política poderá ser atualizada periodicamente. O Usuário será notificado sobre alterações relevantes pelos canais oficiais. O uso continuado dos Serviços após a notificação implica aceitação das novas condições.
        </LegalClause>
      </LegalSection>

    </LegalLayout>
  );
}
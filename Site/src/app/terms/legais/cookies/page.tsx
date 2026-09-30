"use client";

import LegalLayout, { LegalSection, LegalClause, LegalSubSection, LegalNote } from "@/components/LegalLayout";

export default function Cookies() {
  return (
    <LegalLayout
      badge="Cookies"
      title="Política de Cookies"
      subtitle="Descreve como a Amethys Solutions utiliza cookies e tecnologias similares em sua plataforma, bem como as opções de gerenciamento disponíveis ao Usuário."
      updatedAt="04/08/2025"
    >

      <LegalSection number="1." title="O que são Cookies">
        <LegalClause index="1.1.">
          Cookies são pequenos arquivos de texto armazenados no dispositivo do Usuário (computador, smartphone, tablet) quando este acessa uma plataforma web. Eles permitem que a plataforma reconheça o dispositivo do Usuário em visitas subsequentes e armazene preferências e informações de sessão.
        </LegalClause>
        <LegalClause index="1.2.">
          Além dos cookies tradicionais, a Amethys Solutions pode utilizar tecnologias similares, como web beacons, pixels de rastreamento, armazenamento local (localStorage/sessionStorage) e identificadores de sessão, todas coletivamente referidas nesta Política como "cookies".
        </LegalClause>
      </LegalSection>

      <LegalSection number="2." title="Tipos de Cookies Utilizados">
        <LegalSubSection number="2.1." title="Cookies Estritamente Necessários">
          <LegalClause index="2.1.a.">
            Indispensáveis para o funcionamento básico da plataforma. Permitem autenticação, manutenção de sessão, segurança e navegação. Não podem ser desativados sem comprometer o funcionamento dos Serviços.
          </LegalClause>
          <LegalClause index="2.1.b.">
            Exemplos: cookie de sessão de autenticação, token CSRF (proteção contra falsificação de requisição), preferências de idioma.
          </LegalClause>
        </LegalSubSection>
        <LegalSubSection number="2.2." title="Cookies de Desempenho e Análise">
          <LegalClause index="2.2.a.">
            Permitem coletar informações sobre como os Usuários interagem com a plataforma, quais páginas são mais acessadas e identificar erros. Os dados são agregados e anonimizados.
          </LegalClause>
          <LegalClause index="2.2.b.">
            Exemplos: ferramentas de análise de tráfego web, monitoramento de desempenho e métricas de uso da plataforma.
          </LegalClause>
        </LegalSubSection>
        <LegalSubSection number="2.3." title="Cookies de Funcionalidade">
          <LegalClause index="2.3.a.">
            Permitem que a plataforma lembre escolhas feitas pelo Usuário (como preferências de tema, idioma ou layout) para oferecer uma experiência personalizada.
          </LegalClause>
        </LegalSubSection>
        <LegalSubSection number="2.4." title="Cookies de Terceiros">
          <LegalClause index="2.4.a.">
            Serviços integrados de terceiros (como plataformas de pagamento ou autenticação via Discord OAuth2) podem definir seus próprios cookies, cujo tratamento é regido pelas respectivas políticas de privacidade desses terceiros.
          </LegalClause>
          <LegalClause index="2.4.b.">
            A Amethys Solutions não tem controle sobre os cookies de terceiros e recomenda a leitura das políticas de privacidade dessas plataformas.
          </LegalClause>
        </LegalSubSection>
        <LegalNote>
          A Amethys Solutions não utiliza cookies para fins de publicidade comportamental ou rastreamento entre sites de terceiros.
        </LegalNote>
      </LegalSection>

      <LegalSection number="3." title="Base Legal para Uso de Cookies">
        <LegalClause index="3.1.">
          O uso de cookies estritamente necessários fundamenta-se no legítimo interesse e na execução contratual, sendo inerentes ao funcionamento dos Serviços.
        </LegalClause>
        <LegalClause index="3.2.">
          O uso de cookies de desempenho, funcionalidade e terceiros, quando não estritamente necessários, é realizado mediante consentimento do Usuário, obtido por meio do banner de consentimento de cookies exibido no primeiro acesso.
        </LegalClause>
      </LegalSection>

      <LegalSection number="4." title="Duração dos Cookies">
        <LegalClause index="4.1.">
          Os cookies utilizados pela Amethys Solutions podem ser classificados quanto à duração em:
        </LegalClause>
        <LegalClause index="4.1.a.">
          <strong>Cookies de sessão:</strong> Temporários, são excluídos automaticamente ao fechar o navegador. Utilizados principalmente para autenticação e segurança.
        </LegalClause>
        <LegalClause index="4.1.b.">
          <strong>Cookies persistentes:</strong> Permanecem no dispositivo por um período determinado, até a data de expiração definida ou até que o Usuário os exclua manualmente. Utilizados para preferências e análise.
        </LegalClause>
        <LegalClause index="4.2.">
          Os cookies persistentes da Amethys Solutions têm prazo de expiração máximo de 12 (doze) meses, salvo disposição diversa indicada no banner de consentimento.
        </LegalClause>
      </LegalSection>

      <LegalSection number="5." title="Gerenciamento e Controle de Cookies">
        <LegalClause index="5.1.">
          O Usuário pode gerenciar, restringir ou excluir cookies a qualquer momento por meio das configurações do navegador utilizado.
        </LegalClause>
        <LegalClause index="5.2.">
          A desativação de cookies estritamente necessários pode impedir o acesso a funcionalidades essenciais dos Serviços, incluindo autenticação e navegação no painel de controle.
        </LegalClause>
        <LegalClause index="5.3.">
          Para gerenciar cookies nos principais navegadores, o Usuário pode seguir as instruções oficiais de:
        </LegalClause>
        <LegalClause index="5.3.a.">Google Chrome: Configurações → Privacidade e Segurança → Cookies e outros dados do site.</LegalClause>
        <LegalClause index="5.3.b.">Mozilla Firefox: Configurações → Privacidade e Segurança → Cookies e dados do site.</LegalClause>
        <LegalClause index="5.3.c.">Microsoft Edge: Configurações → Privacidade, pesquisa e serviços → Cookies.</LegalClause>
        <LegalClause index="5.3.d.">Safari: Preferências → Privacidade → Gerenciar dados do site.</LegalClause>
        <LegalClause index="5.4.">
          O consentimento para cookies não essenciais pode ser revogado a qualquer momento pelo Usuário, por meio do painel de preferências de cookies disponível na plataforma ou pelas configurações do navegador.
        </LegalClause>
      </LegalSection>

      <LegalSection number="6." title="Atualizações desta Política">
        <LegalClause index="6.1.">
          Esta Política de Cookies poderá ser atualizada periodicamente para refletir alterações nos cookies utilizados ou em razão de exigências legais. O Usuário será notificado por meio de banner de consentimento atualizado ou pelos canais oficiais de comunicação.
        </LegalClause>
      </LegalSection>

    </LegalLayout>
  );
}
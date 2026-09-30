"use client";

import LegalLayout, { LegalSection, LegalClause, LegalSubSection, LegalNote } from "@/components/LegalLayout";

export default function DPA() {
  return (
    <LegalLayout
      badge="DPA"
      title="Acordo de Tratamento de Dados"
      subtitle="Data Processing Agreement (DPA) — Estabelece as responsabilidades e obrigações da Amethys Solutions enquanto operadora de dados pessoais de titulares cujos dados são tratados por meio dos Serviços contratados, em conformidade com a LGPD."
      updatedAt="04/08/2025"
    >

      <LegalSection number="1." title="Definições e Partes">
        <LegalClause index="1.1.">
          Para fins deste Acordo de Tratamento de Dados ("DPA"), aplicam-se as seguintes definições, além daquelas previstas na LGPD (Lei nº 13.709/2018):
        </LegalClause>
        <LegalClause index="1.1.a.">
          <strong>"Controlador":</strong> O Usuário contratante dos Serviços da Amethys Solutions, que determina as finalidades e os meios do tratamento dos dados pessoais de membros de seu servidor Discord.
        </LegalClause>
        <LegalClause index="1.1.b.">
          <strong>"Operador":</strong> A Amethys Solutions, que realiza o tratamento de dados pessoais em nome do Controlador, conforme as instruções por este definidas.
        </LegalClause>
        <LegalClause index="1.1.c.">
          <strong>"Dados Pessoais do Usuário Final":</strong> Dados de membros dos servidores Discord do Controlador que são coletados, armazenados ou processados pelos bots e aplicações da Amethys Solutions durante a prestação dos Serviços.
        </LegalClause>
        <LegalClause index="1.1.d.">
          <strong>"Suboperador":</strong> Terceiro contratado pela Amethys Solutions para auxiliar na prestação dos Serviços, que também realiza tratamento de dados em nome do Controlador.
        </LegalClause>
        <LegalClause index="1.2.">
          Este DPA integra-se aos Termos de Serviço e demais documentos contratuais da Amethys Solutions, prevalecendo sobre disposições genéricas em matéria de proteção de dados.
        </LegalClause>
      </LegalSection>

      <LegalSection number="2." title="Objeto e Instrução de Tratamento">
        <LegalClause index="2.1.">
          Este DPA regula o tratamento de Dados Pessoais do Usuário Final realizado pela Amethys Solutions (Operadora) em nome do Usuário contratante (Controlador), no âmbito da prestação dos Serviços descritos nos Termos de Serviço.
        </LegalClause>
        <LegalClause index="2.2.">
          A Amethys Solutions tratará os Dados Pessoais do Usuário Final exclusivamente conforme as instruções documentadas do Controlador e as configurações realizadas por este no painel de controle dos Serviços.
        </LegalClause>
        <LegalClause index="2.3.">
          A Amethys Solutions notificará o Controlador caso receba instrução que, a seu juízo, viole a LGPD ou demais normas aplicáveis de proteção de dados, sem que isso implique obrigação de descumprir a instrução até manifestação do Controlador.
        </LegalClause>
        <LegalClause index="2.4.">
          O Controlador é o único responsável por assegurar a existência de base legal adequada para o tratamento dos Dados Pessoais do Usuário Final que instrui a Amethys Solutions a realizar.
        </LegalClause>
      </LegalSection>

      <LegalSection number="3." title="Categorias de Dados e Finalidades">
        <LegalClause index="3.1.">
          Os dados tratados pela Amethys Solutions na qualidade de Operadora podem incluir, conforme a configuração do Serviço pelo Controlador:
        </LegalClause>
        <LegalSubSection number="3.1.a." title="Dados de identificação">
          <LegalClause index="3.1.a.i.">Discord ID (identificador único de usuário na plataforma Discord).</LegalClause>
          <LegalClause index="3.1.a.ii.">Nome de usuário (username) e apelido (nickname) no servidor.</LegalClause>
          <LegalClause index="3.1.a.iii.">Avatar e dados de perfil público disponibilizados pela API do Discord.</LegalClause>
        </LegalSubSection>
        <LegalSubSection number="3.1.b." title="Dados de comportamento e interação">
          <LegalClause index="3.1.b.i.">Histórico de comandos executados nos bots.</LegalClause>
          <LegalClause index="3.1.b.ii.">Logs de atividade, punições, advertências e registros de moderação gerados pelas ferramentas contratadas.</LegalClause>
          <LegalClause index="3.1.b.iii.">Pontuações, rankings, moedas virtuais e demais dados gerados por sistemas de gamificação, quando contratados.</LegalClause>
        </LegalSubSection>
        <LegalClause index="3.2.">
          A Amethys Solutions não tratará dados sensíveis de Usuários Finais, conforme definidos na LGPD, exceto quando expressamente configurado e autorizado pelo Controlador e com fundamento em base legal adequada.
        </LegalClause>
        <LegalClause index="3.3.">
          As finalidades do tratamento são determinadas pelo Controlador e limitadas à operação das funcionalidades dos Serviços contratados.
        </LegalClause>
      </LegalSection>

      <LegalSection number="4." title="Obrigações da Amethys Solutions (Operadora)">
        <LegalClause index="4.1.">
          A Amethys Solutions, na qualidade de Operadora, compromete-se a:
        </LegalClause>
        <LegalClause index="4.1.a.">
          Tratar os Dados Pessoais do Usuário Final exclusivamente conforme as instruções do Controlador e as finalidades descritas nos Termos de Serviço, salvo obrigação legal em contrário.
        </LegalClause>
        <LegalClause index="4.1.b.">
          Implementar medidas técnicas e organizacionais adequadas para garantir a segurança, confidencialidade e integridade dos dados tratados, conforme a Cláusula 6 deste DPA.
        </LegalClause>
        <LegalClause index="4.1.c.">
          Não divulgar, vender, compartilhar ou utilizar os Dados Pessoais do Usuário Final para finalidades próprias da Amethys Solutions, exceto quando necessário para a prestação dos Serviços.
        </LegalClause>
        <LegalClause index="4.1.d.">
          Garantir que os colaboradores e prestadores de serviços com acesso aos dados estejam vinculados a obrigações de confidencialidade.
        </LegalClause>
        <LegalClause index="4.1.e.">
          Notificar o Controlador em até 48 (quarenta e oito) horas sobre qualquer incidente de segurança que afete os Dados Pessoais do Usuário Final, fornecendo informações suficientes para que o Controlador cumpra suas obrigações legais.
        </LegalClause>
        <LegalClause index="4.1.f.">
          Auxiliar o Controlador no atendimento de solicitações de exercício de direitos pelos titulares dos dados, nos limites do tecnicamente possível.
        </LegalClause>
        <LegalClause index="4.1.g.">
          Excluir ou devolver os Dados Pessoais do Usuário Final ao término da prestação dos Serviços, salvo obrigação legal de retenção, mediante solicitação do Controlador.
        </LegalClause>
        <LegalClause index="4.1.h.">
          Disponibilizar ao Controlador as informações necessárias para demonstrar o cumprimento das obrigações previstas neste DPA e permitir e contribuir para auditorias razoáveis, mediante notificação prévia.
        </LegalClause>
      </LegalSection>

      <LegalSection number="5." title="Obrigações do Controlador (Usuário Contratante)">
        <LegalClause index="5.1.">
          O Controlador, ao utilizar os Serviços da Amethys Solutions, compromete-se a:
        </LegalClause>
        <LegalClause index="5.1.a.">
          Assegurar que os membros de seu servidor Discord cujos dados são tratados foram informados e, quando necessário, consentiram com o tratamento de seus dados pelos bots e aplicações contratados.
        </LegalClause>
        <LegalClause index="5.1.b.">
          Configurar os Serviços de forma adequada, respeitando os princípios da finalidade, necessidade e proporcionalidade previstos na LGPD.
        </LegalClause>
        <LegalClause index="5.1.c.">
          Disponibilizar aos membros de seu servidor política de privacidade própria que informe sobre o uso de bots de terceiros e o tratamento de dados decorrente.
        </LegalClause>
        <LegalClause index="5.1.d.">
          Atender prontamente às solicitações de exercício de direitos apresentadas pelos titulares dos dados, utilizando os mecanismos disponibilizados pela Amethys Solutions quando aplicável.
        </LegalClause>
      </LegalSection>

      <LegalSection number="6." title="Medidas de Segurança">
        <LegalClause index="6.1.">
          A Amethys Solutions implementa as seguintes medidas técnicas e organizacionais para proteção dos dados:
        </LegalClause>
        <LegalClause index="6.1.a.">Criptografia de dados em trânsito mediante protocolos TLS 1.2 ou superior.</LegalClause>
        <LegalClause index="6.1.b.">Controle de acesso baseado em funções (RBAC), com princípio do menor privilégio.</LegalClause>
        <LegalClause index="6.1.c.">Autenticação segura para sistemas internos.</LegalClause>
        <LegalClause index="6.1.d.">Logs de auditoria de acesso e alterações em dados sensíveis.</LegalClause>
        <LegalClause index="6.1.e.">Procedimentos de resposta a incidentes documentados.</LegalClause>
        <LegalClause index="6.1.f.">Revisões periódicas de segurança da infraestrutura.</LegalClause>
        <LegalNote>
          As medidas de segurança poderão ser atualizadas pela Amethys Solutions para refletir o estado da arte e as melhores práticas do setor, sem necessidade de notificação prévia, desde que o nível de proteção não seja reduzido.
        </LegalNote>
      </LegalSection>

      <LegalSection number="7." title="Suboperadores">
        <LegalClause index="7.1.">
          O Controlador autoriza, de forma geral, o uso de suboperadores pela Amethys Solutions para a prestação dos Serviços, incluindo provedores de hospedagem, infraestrutura de banco de dados e monitoramento.
        </LegalClause>
        <LegalClause index="7.2.">
          A Amethys Solutions compromete-se a:
        </LegalClause>
        <LegalClause index="7.2.a.">
          Impor aos suboperadores obrigações de proteção de dados equivalentes às previstas neste DPA, por meio de contratos escritos.
        </LegalClause>
        <LegalClause index="7.2.b.">
          Permanecer responsável perante o Controlador pelas ações dos suboperadores em relação ao tratamento de dados.
        </LegalClause>
        <LegalClause index="7.3.">
          A lista atualizada de suboperadores poderá ser solicitada pelo Controlador a qualquer momento pelos canais de suporte.
        </LegalClause>
      </LegalSection>

      <LegalSection number="8." title="Duração e Encerramento">
        <LegalClause index="8.1.">
          Este DPA vigorará enquanto a Amethys Solutions tratar Dados Pessoais do Usuário Final em nome do Controlador, ou seja, enquanto os Serviços contratados estiverem ativos.
        </LegalClause>
        <LegalClause index="8.2.">
          Com o encerramento dos Serviços, a Amethys Solutions excluirá os Dados Pessoais do Usuário Final de seus sistemas no prazo de até 30 (trinta) dias, salvo obrigação legal de retenção, mediante solicitação do Controlador.
        </LegalClause>
      </LegalSection>

    </LegalLayout>
  );
}
# Amethys Solutions

Este repositório reúne o código do projeto **Amethys Solutions** que foi vazado. Ele fica disponível como registro desse projeto e **não representa a Amethys atual**.

> **Esclarecimento:** a **Amethys atual é uma versão melhorada da Vision Applications**. O projeto atual da Amethys não tem relação com a Amethys Solutions apresentada neste repositório. O dono oficial da Amethys é **@souhyped**. Para informações e contato sobre a Amethys atual, acesse o [servidor oficial no Discord](https://discord.gg/2yWthJH33W).

## O que existe neste repositório

| Diretório | Conteúdo | Tecnologias principais |
| --- | --- | --- |
| [`Bot/`](Bot/) | Bot para Discord com loja, vendas, tickets, moderação, proteção, sorteios, automações e integrações, incluindo Telegram. | Python, disnake, MongoDB |
| [`Site/`](Site/) | Site institucional e painel com páginas de aplicações, faturas, configurações, serviços e administração. | Next.js, React, TypeScript |
| [`Api/`](Api/) | API para autenticação, aplicações, pagamentos, faturas, integrações e rotinas de cobrança. | Node.js, Express, MongoDB |
| [`Api-Cloud/`](Api-Cloud/) | Serviço HTTP e WebSocket para comunicação com bots, OAuth, recuperação de membros e presentes. | Go |
| [`Wallet/FrontEnd/`](Wallet/FrontEnd/) | Interface da carteira com conta, transações, transferências, depósitos, metas e área administrativa. | Next.js, React, TypeScript |
| [`Wallet/BackEnd/`](Wallet/BackEnd/) | API da carteira para usuários, pagamentos, transferências, webhooks e administração. | Node.js, Express, MongoDB, Redis |

## Funcionalidades presentes no código

- **Discord:** comandos e painéis para vendas, produtos, carrinho, tickets, proteção, moderação, sorteios e automações de comunidade.
- **Gestão:** site e API com autenticação, aplicações, faturas, serviços e painéis administrativos.
- **Comunicação em tempo real:** serviço WebSocket em Go para eventos e operações ligadas aos bots.
- **Carteira:** frontend e backend próprios para saldo, pagamentos, transferências e histórico.

As pastas mostram funcionalidades implementadas ou iniciadas nesta cópia; sua presença não garante que estejam completas ou funcionando isoladamente.

## Sobre esta cópia

O código contém configurações e referências da época da Amethys Solutions. Links, nomes e integrações encontrados nos arquivos podem estar desatualizados e **não devem ser usados como canais oficiais da Amethys atual**. O canal atual é o [Discord informado acima](https://discord.gg/2yWthJH33W).

Antes de publicar, executar ou reutilizar esta cópia, revise os arquivos de ambiente, configurações, backups e credenciais incorporadas ao código. Remova dados privados e substitua ou revogue chaves, tokens e webhooks expostos. Não há instruções únicas de instalação para todo o repositório: cada componente possui dependências e configuração próprias.

Este repositório não inclui uma licença geral na raiz. A disponibilização do código, por si só, não concede permissão de uso, modificação ou redistribuição além do que a legislação aplicável permitir.

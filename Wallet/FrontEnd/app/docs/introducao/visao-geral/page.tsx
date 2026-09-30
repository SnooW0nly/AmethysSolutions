'use client'

import { DocPageHeader, QuickRefCard, Callout, CodeBlock } from '@/components/docs/doc-components'

const quickRef = [
  { method: 'POST', path: '/user/register', description: 'Criar nova conta', href: '/docs/usuario/registrar' },
  { method: 'POST', path: '/payment/create', description: 'Gerar cobrança PIX', href: '/docs/pagamentos/criar' },
  { method: 'POST', path: '/withdraw/create', description: 'Sacar via PIX', href: '/docs/saques/pix' },
  { method: 'POST', path: '/transfer/internal', description: 'Transferência interna', href: '/docs/transferencias/interna' },
  { method: 'GET',  path: '/user/balance', description: 'Consultar saldo', href: '/docs/usuario/saldo' },
  { method: 'GET',  path: '/payment/list', description: 'Listar cobranças', href: '/docs/pagamentos/listar' },
  { method: 'GET',  path: '/public-stats', description: 'Estatísticas públicas', href: '/docs/publico/estatisticas' },
  { method: 'POST', path: '/withdraw/crypto', description: 'Sacar em USDT BEP20', href: '/docs/saques/crypto' },
]

export default function VisaoGeralPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Introdução"
        title="Visão Geral"
        description="A API Amethys Wallet permite que desenvolvedores integrem funcionalidades financeiras completas em suas aplicações — desde a emissão de cobranças PIX até saques automáticos e transferências entre contas."
      />

      <Callout type="info">
        Todos os valores monetários são expressados em <strong>centavos (inteiros)</strong>, exceto quando indicado o contrário.{' '}
        Exemplo: <code className="font-mono text-[12px] text-primary">R$ 10,00 = 1000</code>.
      </Callout>

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-4">Base URL</h2>
        <CodeBlock lang="http" copyable>{'https://api.amethys.lat/api/v1'}</CodeBlock>
      </div>

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-2">Como funciona</h2>
        <p className="text-[14px] text-foreground/50 mb-5 leading-relaxed">
          A API segue os princípios REST. Todas as requisições e respostas usam JSON. A autenticação é feita via API Key no header <code className="font-mono text-[12px] text-primary">X-API-Key</code>.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
          {[
            { label: 'Protocolo', value: 'HTTPS' },
            { label: 'Formato', value: 'application/json' },
            { label: 'Versão', value: 'v1' },
          ].map(item => (
            <div key={item.label} className="bg-foreground/[0.03] border border-foreground/10 rounded-xl px-4 py-3.5">
              <div className="text-[10px] font-semibold text-foreground/30 uppercase tracking-wider mb-1.5">{item.label}</div>
              <code className="font-mono text-[12px] text-primary">{item.value}</code>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-2">Referência rápida de endpoints</h2>
        <p className="text-[13.5px] text-foreground/50 mb-5">Todos os endpoints disponíveis de um relance:</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {quickRef.map(item => (
            <QuickRefCard key={item.path} {...item} />
          ))}
        </div>
      </div>
    </div>
  )
}

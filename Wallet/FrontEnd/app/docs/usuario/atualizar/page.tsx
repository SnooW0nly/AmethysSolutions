'use client'

import { DocPageHeader, EndpointBar, ParamsTable } from '@/components/docs/doc-components'

export default function UsuarioAtualizarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Usuário"
        title="Atualizar usuário"
        description="Atualiza os dados da conta autenticada. Todos os campos são opcionais."
      />

      <EndpointBar method="PUT" path="/user/update" auth />

      <ParamsTable
        columns={['Campo', 'Tipo', 'Descrição']}
        params={[
          { name: 'name', type: 'string', description: 'Nome do titular' },
          { name: 'email', type: 'string', description: 'Novo e-mail da conta' },
          { name: 'phone', type: 'string', description: 'Telefone com DDD' },
          { name: 'pixKey', type: 'string', description: <>Nova chave PIX (requer <code className="font-mono text-[11px] text-primary">pixKeyType</code>)</> },
          { name: 'pixKeyType', type: 'string', description: <><code className="font-mono text-[11px] text-primary">CPF</code>, <code className="font-mono text-[11px] text-primary">CNPJ</code>, <code className="font-mono text-[11px] text-primary">EMAIL</code>, <code className="font-mono text-[11px] text-primary">PHONE</code>, <code className="font-mono text-[11px] text-primary">RANDOM</code></> },
          { name: 'webhookUrl', type: 'string', description: 'URL HTTPS para receber eventos' },
          { name: 'planAutoRenew', type: 'boolean', description: 'Renovar plano automaticamente' },
        ]}
      />
    </div>
  )
}

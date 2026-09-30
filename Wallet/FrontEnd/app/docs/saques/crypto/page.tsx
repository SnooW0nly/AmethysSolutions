'use client'

import { DocPageHeader, EndpointBar, ParamsTable, Callout } from '@/components/docs/doc-components'

export default function SaquesCryptoPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Saques"
        title="Sacar em Criptomoeda (USDT BEP20)"
        description="Converte saldo em reais para USDT e envia para uma wallet BEP20. Mínimo R$ 20,00, máximo R$ 3.000,00 por saque. Taxa: 6% + R$ 2,00 fixo."
      />

      <EndpointBar method="POST" path="/withdraw/crypto" auth />

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Parâmetros do body</h3>
        <ParamsTable params={[
          { name: 'amount', type: 'number', required: true, description: 'Valor em reais. Entre R$ 20,00 e R$ 3.000,00' },
          { name: 'wallet', type: 'string', required: true, description: <>Endereço BEP20 válido (começa com <code className="font-mono text-[11px] text-primary">0x</code>, 42 caracteres)</> },
          { name: 'description', type: 'string', required: false, description: 'Descrição interna' },
        ]} />
      </div>

      <Callout type="warn">
        Endereços inválidos resultam em <strong>perda permanente de fundos</strong>. Valide o endereço BEP20 antes de enviar.
        Apenas redes <strong>BNB Smart Chain (BEP20)</strong> são suportadas.
      </Callout>
    </div>
  )
}

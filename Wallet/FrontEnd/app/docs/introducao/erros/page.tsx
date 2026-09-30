'use client'

import { DocPageHeader, StatusBadge, CodeBlock } from '@/components/docs/doc-components'

const codes = [
  { code: '200', meaning: 'OK', desc: 'Requisição bem-sucedida' },
  { code: '201', meaning: 'Created', desc: 'Recurso criado com sucesso' },
  { code: '400', meaning: 'Bad Request', desc: 'Parâmetros inválidos ou faltando' },
  { code: '401', meaning: 'Unauthorized', desc: 'API Key ausente ou inválida' },
  { code: '403', meaning: 'Forbidden', desc: 'Sem permissão para o recurso' },
  { code: '404', meaning: 'Not Found', desc: 'Recurso não encontrado' },
  { code: '429', meaning: 'Too Many Requests', desc: 'Rate limit atingido' },
  { code: '500', meaning: 'Server Error', desc: 'Erro interno — tente novamente' },
]

export default function ErrosPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Introdução"
        title="Tratamento de Erros"
        description="A API usa códigos HTTP padrão. Todos os erros retornam JSON com os campos error e message."
      />

      <div className="overflow-x-auto mb-8">
        <table className="w-full text-[13px] border-collapse">
          <thead>
            <tr className="border-b border-foreground/10">
              {['Código', 'Significado', 'Descrição'].map(col => (
                <th key={col} className="text-left py-2.5 px-3 text-[10px] font-semibold text-foreground/30 uppercase tracking-wider font-mono">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {codes.map(({ code, meaning, desc }) => (
              <tr key={code} className="border-b border-foreground/[0.06] last:border-0 hover:bg-foreground/[0.02] transition-colors">
                <td className="py-3 px-3"><StatusBadge code={code} /></td>
                <td className="py-3 px-3 font-mono text-[12px] text-foreground/70">{meaning}</td>
                <td className="py-3 px-3 text-foreground/50">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-4">Estrutura de erro</h2>
        <CodeBlock lang="json — Exemplo de erro" copyable={false}>{`{
  <span style="color:#93c5fd">"error"</span>: <span style="color:#86efac">"Saldo insuficiente"</span>,
  <span style="color:#93c5fd">"message"</span>: <span style="color:#86efac">"O valor deve ser maior que a taxa de R$ 0.50"</span>
}`}</CodeBlock>
      </div>
    </div>
  )
}

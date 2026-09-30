'use client'

import { DocPageHeader, CodeBlock, Callout, Tabs } from '@/components/docs/doc-components'

export default function AutenticacaoPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Introdução"
        title="Autenticação"
        description="A API utiliza API Keys no formato vp_... Após registrar um usuário, uma API Key é gerada automaticamente. Guarde-a em local seguro — ela não pode ser recuperada."
      />

      <Callout type="warn">
        <strong>Nunca exponha sua API Key</strong> no client-side (browser). Use sempre no servidor.
        O endpoint <code className="font-mono text-[12px]">POST /payment/send</code> aceita <strong>somente</strong> API Key (não JWT).
      </Callout>

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-2">Header de autenticação</h2>
        <p className="text-[14px] text-foreground/50 mb-5 leading-relaxed">
          Envie a API Key via header em qualquer requisição autenticada:
        </p>

        <Tabs tabs={['X-API-Key', 'Authorization Bearer']}>
          {(active) => (
            <div className="bg-[#0c0d0e] p-5">
              <pre className="font-mono text-[12.5px] leading-relaxed text-foreground/70 whitespace-pre">
                {active === 'X-API-Key'
                  ? `<span style="color:#86efac">X-API-Key:</span> vp_sua_api_key_aqui\n<span style="color:#86efac">Content-Type:</span> application/json`
                  : `<span style="color:#86efac">Authorization:</span> Bearer vp_sua_api_key_aqui\n<span style="color:#86efac">Content-Type:</span> application/json`
                }
              </pre>
            </div>
          )}
        </Tabs>
      </div>

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-2">Exemplo com cURL</h2>
        <CodeBlock lang="bash">{`<span style="color:#71717a"># Usando X-API-Key</span>
curl -X GET https://api.amethys.lat/api/v1/user/get \\
  -H <span style="color:#86efac">"X-API-Key: vp_sua_api_key"</span> \\
  -H <span style="color:#86efac">"Content-Type: application/json"</span>`}</CodeBlock>
      </div>

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-2">Onde obter a API Key</h2>
        <p className="text-[14px] text-foreground/50 mb-4 leading-relaxed">
          Sua API Key é gerada no momento do registro da conta via <code className="font-mono text-[12px] text-primary">POST /user/register</code>.
          Ela aparece apenas uma vez na resposta. Se perdida, não é possível recuperá-la — será necessário criar uma nova conta.
        </p>
        <div className="bg-foreground/[0.03] border border-foreground/10 rounded-xl p-5">
          <p className="text-[11px] font-mono text-foreground/30 uppercase tracking-wider mb-3">Formato da API Key</p>
          <code className="font-mono text-[14px] text-primary">vp_<span className="text-foreground/40">xxxxxxxxxxxxxxxxxxx</span></code>
          <p className="text-[12px] text-foreground/40 mt-2">Prefixo <code className="font-mono">vp_</code> seguido de 19+ caracteres alfanuméricos.</p>
        </div>
      </div>
    </div>
  )
}

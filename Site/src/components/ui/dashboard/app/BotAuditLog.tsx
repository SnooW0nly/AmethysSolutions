import { Hammer } from "lucide-react";

export function BotAuditLog() {
  return (
    <div className="flex flex-col">
      <div className="flex flex-col">
        <p className="font-semibold flex items-center gap-2">Registro de Auditoria</p>
        <p className="text-xs text-foreground/60">
          Veja um registro de alterações realizadas no bot pelos usuários autorizados
        </p>
        <hr className="border-foreground/5 mt-2" />
      </div>
      <div className="mt-6 p-10 flex flex-col items-center text-center">
        <div className="">
          <Hammer className="w-12 h-12 text-primary" />
        </div>
        <h3 className="mt-4 text-xl font-semibold text-foreground">Em desenvolvimento</h3>
        <p className="mt-2 text-sm text-foreground/60 max-w-md">
          Em breve você poderá visualizar um histórico detalhado de ações do seu bot,
          incluindo mudanças de configurações, permissões e integrações.
        </p>
      </div>
    </div>
  );
}
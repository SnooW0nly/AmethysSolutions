"use client";

export function AuditTable({ logs, loading }: { logs: any[]; loading: boolean }) {
  if (loading) return <div className="text-sm text-foreground/60">Carregando...</div>;
  if (!logs.length) return <div className="text-sm text-foreground/60">Sem registros</div>;
  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[720px] flex flex-col gap-2 max-h-72 overflow-auto">
        {logs.map((l, idx) => (
          <div key={idx} className="text-xs text-foreground/80 flex items-center justify-between">
            <span>{new Date(l.createdAt).toLocaleString()}</span>
            <span className={`font-semibold ${l.action === 'redeem' ? 'text-success' : l.action === 'archive' ? 'text-warning' : l.action === 'restore' ? 'text-primary' : 'text-foreground'}`}>{l.action}</span>
            <span>{l.targetId}</span>
            <span className="text-foreground/60">actor: {l.actorId || '-'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}



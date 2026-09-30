import { CheckCircle, Gift, Loader2 } from "lucide-react";
import { ExistingApp } from "../types";
import { formatDateSafe, buildDurationLabel } from "../utils";

interface AppSelectionProps {
  apps: ExistingApp[];
  monthsToAdd?: number;
  daysToAdd?: number;
  loading: boolean;
  onRedeem: (appId: string | null) => void;
  onCancel: () => void;
}

export function AppSelection({
  apps,
  monthsToAdd,
  daysToAdd,
  loading,
  onRedeem,
  onCancel,
}: AppSelectionProps) {
  return (
    <div className="p-4 bg-foreground/10 rounded-lg border border-foreground/20">
      <p className="text-sm font-medium text-foreground/80 mb-3">
        {apps.length > 0
          ? "Você já possui bots. Escolha uma opção:"
          : "Como deseja usar este gift?"}
      </p>
      <div className="space-y-2">
        {/* Opção: Criar novo bot */}
        <button
          onClick={() => onRedeem(null)}
          disabled={loading}
          className="w-full px-4 py-3 cursor-pointer bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors text-left flex items-center gap-3"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 flex-shrink-0 animate-spin" />
              <div>
                <div className="font-semibold">Criando...</div>
                <div className="text-xs opacity-80">Aguarde, estamos preparando seu bot</div>
              </div>
            </>
          ) : (
            <>
              <Gift className="w-5 h-5 flex-shrink-0" />
              <div>
                <div className="font-semibold">Criar novo bot</div>
                <div className="text-xs opacity-80">Criar uma nova aplicação com este gift</div>
              </div>
            </>
          )}
        </button>

        {/* Opções: Adicionar aos bots existentes */}
        {apps.map((app) => (
          <button
            key={app._id}
            onClick={() => onRedeem(app._id)}
            disabled={loading}
            className="w-full px-4 py-3 bg-foreground/10 hover:bg-foreground/20 disabled:opacity-50 text-foreground text-sm font-medium rounded-lg transition-colors text-left flex items-center gap-3 border border-foreground/20"
          >
            <CheckCircle className="w-5 h-5 flex-shrink-0 text-green-500" />
            <div>
              <div className="font-semibold">{app.name}</div>
              <div className="text-xs opacity-60">
                Adicionar {buildDurationLabel(monthsToAdd ?? 0, daysToAdd ?? 0)} • Expira em{" "}
                {formatDateSafe(app.expiresAt)}
              </div>
            </div>
          </button>
        ))}

        {/* Botão cancelar */}
        <button
          onClick={onCancel}
          disabled={loading}
          className="w-full px-4 py-2 bg-foreground/5 hover:bg-foreground/10 disabled:opacity-50 text-foreground/70 text-sm font-medium rounded-lg transition-colors"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}



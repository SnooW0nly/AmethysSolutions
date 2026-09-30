import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlay, faRotateRight, faPowerOff } from "@fortawesome/free-solid-svg-icons";

type Action = "start" | "stop" | "restart";

type ActionButtonsProps = {
  isRunning: boolean;
  isOffline: boolean;
  actionLoading: Action | null;
  onAction: (action: Action) => void;
  onAfterAction?: () => void;
  botConfigured?: boolean;
  serverConfigured?: boolean;
};

export function ActionButtons({ isRunning, isOffline, actionLoading, onAction, onAfterAction, botConfigured, serverConfigured }: ActionButtonsProps) {
  const handle = (action: Action) => {
    onAction(action);
    onAfterAction?.();
  };

  // Desabilita start/restart se bot ou server não estiverem configurados
  const canStartOrRestart = botConfigured && serverConfigured;
  const isRestarting = actionLoading === "restart";
  const startDisabled = isRunning || actionLoading !== null || !canStartOrRestart;
  const restartDisabled = actionLoading !== null || !canStartOrRestart;
  const stopDisabled = isOffline || actionLoading !== null;

  const getTitle = (action: Action) => {
    if (actionLoading !== null) return "Aguarde...";
    if (action === "start" || action === "restart") {
      if (!botConfigured) return "Configure o token primeiro";
      if (!serverConfigured) return "Configure o servidor primeiro";
    }
    return action === "start" ? "Ligar" : action === "restart" ? "Reiniciar" : "Desligar";
  };

  return (
    <div className="flex flex-row items-center gap-2 justify-between w-full">
      <button
        aria-label="Ligar"
        title={getTitle("start")}
        className={`p-2 w-1/3 rounded-md cursor-pointer bg-green-500/5 border border-green-500/10 hover:bg-green-500/10 disabled:opacity-50 disabled:bg-foreground/5 disabled:cursor-not-allowed disabled:border-foreground/10 disabled:text-foreground/50 transition-all duration-200 text-sm text-green-500 flex items-center justify-center`}
        onClick={() => handle("start")}
        disabled={startDisabled}
      >
        <FontAwesomeIcon icon={faPlay} />
      </button>

      <button
        aria-label="Reiniciar"
        title={getTitle("restart")}
        className={`p-2 w-1/3 rounded-md cursor-pointer bg-yellow-500/5 border border-yellow-500/10 hover:bg-yellow-500/10 disabled:opacity-50 disabled:bg-foreground/5 disabled:cursor-not-allowed disabled:border-foreground/10 disabled:text-foreground/50 transition-all duration-200 text-sm text-yellow-500 flex items-center justify-center`}
        onClick={() => handle("restart")}
        disabled={restartDisabled}
      >
        <FontAwesomeIcon icon={faRotateRight} className={isRestarting ? "animate-spin" : ""} />
      </button>

      <button
        aria-label="Desligar"
        title={getTitle("stop")}
        className={`p-2 w-1/3 rounded-md cursor-pointer bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 disabled:opacity-50 disabled:bg-foreground/5 disabled:cursor-not-allowed disabled:border-foreground/10 disabled:text-foreground/50 transition-all duration-200 text-sm text-red-500 flex items-center justify-center`}
        onClick={() => handle("stop")}
        disabled={stopDisabled}
      >
        <FontAwesomeIcon icon={faPowerOff} />
      </button>
    </div>
  );
}



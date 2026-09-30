import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faCheck, faChevronDown, faCircleExclamation } from "@fortawesome/free-solid-svg-icons";
import { Tooltip } from "@heroui/react";

type AppHeaderProps = {
  name?: string | null;
  fallbackName?: string | null;
  appId?: string | null;
  copied: boolean;
  onCopy?: () => void;
  onOpenPicker?: () => void;
  copyAsSpan?: boolean;
  asDiv?: boolean;
  botConfigured?: boolean;
};

export function AppHeader({ name, fallbackName, appId, copied, onCopy, onOpenPicker, copyAsSpan, asDiv, botConfigured }: AppHeaderProps) {
  const Root: any = asDiv ? "div" : "button";
  const rootProps: any = asDiv
    ? { role: "button", tabIndex: 0, onClick: onOpenPicker }
    : { type: "button", onClick: onOpenPicker };

  console.log(botConfigured);
  return (
    <Root
      {...rootProps}
      className="w-full flex flex-row items-center gap-2 text-left cursor-pointer p-0.5"
      aria-label="Selecionar aplicação"
      title="Selecionar aplicação"
    >
      <div className="flex-1">
        <div className="text-sm font-medium leading-tight flex flex-row items-center gap-1">{name || fallbackName || "Aplicação"}

        {botConfigured === false ? (
          <div className="relative">
            <Tooltip content="Bot não configurado" showArrow color="danger" placement="left">
              <span className="inline-flex items-center justify-center rounded-full text-red-500">
                <FontAwesomeIcon icon={faCircleExclamation} className="text-[10px]" />
              </span>
            </Tooltip>
          </div>
        ) : null}
        </div>
        <p className="text-[10px] text-foreground/50 leading-tight flex flex-row gap-1 items-center">
          {appId || "ID não encontrado"}
          {appId && (
            copyAsSpan ? (
              <span
                className="relative text-[10px] text-foreground/50 leading-tight cursor-pointer hover:text-foreground/80"
                onClick={(e) => {
                  e.stopPropagation();
                  onCopy?.();
                }}
                aria-label="Copiar ID"
                title="Copiar ID"
              >
                <FontAwesomeIcon icon={copied ? faCheck : faCopy} size="sm" className={copied ? "text-green-500" : ""} />
              </span>
            ) : (
              <button
                type="button"
                className="relative text-[10px] text-foreground/50 leading-tight cursor-pointer hover:text-foreground/80"
                onClick={(e) => {
                  e.stopPropagation();
                  onCopy?.();
                }}
                aria-label="Copiar ID"
                title="Copiar ID"
              >
                <FontAwesomeIcon icon={copied ? faCheck : faCopy} size="sm" className={copied ? "text-green-500" : ""} />
              </button>
            )
          )}
        </p>
      </div>
      <FontAwesomeIcon icon={faChevronDown} className="text-foreground/50 text-xs" />
    </Root>
  );
}



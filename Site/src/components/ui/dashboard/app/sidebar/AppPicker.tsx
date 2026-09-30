import { Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Spinner, Button, Tooltip, DropdownSection } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircleExclamation } from "@fortawesome/free-solid-svg-icons";
import { AppHeader } from "./AppHeader";

type AppPickerProps = {
  name?: string | null;
  fallbackName?: string | null;
  appId?: string | null;
  copied: boolean;
  onCopy?: () => void;
  apps?: any[] | null;
  appsLoading?: boolean;
  onSelectApp?: (id: string) => void;
  placement?: any;
  className?: string;
  menuClassName?: string;
  sectionTitle?: string;
  botConfigured?: boolean;
};

export function AppPicker({ name, fallbackName, appId, copied, onCopy, apps, appsLoading, onSelectApp, placement = "bottom-start", className, menuClassName, sectionTitle, botConfigured }: AppPickerProps) {
  console.log(botConfigured);
  return (
    <Dropdown placement={placement} className={["min-w-[280px] bg-background border border-foreground/10  ", className].filter(Boolean).join(" ")}> 
      <DropdownTrigger>
        <Button
          disableRipple
          variant="light"
          className="w-full p-0 h-auto bg-transparent text-left relative z-20 hover:bg-transparent data-[hover=true]:bg-transparent focus:bg-transparent active:bg-transparent outline-none"
          radius="sm"
        >
          <AppHeader name={name} fallbackName={fallbackName} appId={appId} copied={copied} onCopy={onCopy} copyAsSpan asDiv botConfigured={botConfigured} />
        </Button>
      </DropdownTrigger>
      <DropdownMenu aria-label="Selecionar aplicação" className={["max-h-36 overflow-auto outline-none", menuClassName].filter(Boolean).join(" ")} onAction={(key) => onSelectApp && onSelectApp(String(key))}>
        {sectionTitle ? (
          <DropdownSection title={sectionTitle}>
            {appsLoading ? (
              <DropdownItem key="loading" isDisabled startContent={<Spinner size="sm" />}>Carregando...</DropdownItem>
            ) : (
              <>
                {(apps || []).map((a) => {
                  const notConfigured = a?.bot?.configured === false;
                  return (
                    <DropdownItem
                      key={a._id}
                      description={a?._id}
                      className="py-2 h-12 outline-none data-[hover=true]:bg-foreground/5"
                      endContent={notConfigured ? (
                        <Tooltip content="Bot não configurado" color="danger">
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-500/10 border border-red-500/20 p-1 text-red-500">
                            <FontAwesomeIcon icon={faCircleExclamation} className="text-[10px]" />
                          </span>
                        </Tooltip>
                      ) : undefined}
                    >
                      {a?.name || a?.appId || "Aplicação"}
                    </DropdownItem>
                  );
                })}
                {apps && apps.length === 0 && (
                  <DropdownItem key="empty" isDisabled>Nenhuma aplicação encontrada</DropdownItem>
                )}
              </>
            )}
          </DropdownSection>
        ) : (
          <>
            {appsLoading ? (
              <DropdownItem key="loading" isDisabled startContent={<Spinner size="sm" />}>Carregando...</DropdownItem>
            ) : (
              <>
                {(apps || []).map((a) => {
                  const notConfigured = a?.bot?.configured === false;
                  return (
                    <DropdownItem
                      key={a._id}
                      description={a?._id}
                      className="py-2 h-12 outline-none data-[hover=true]:bg-foreground/5"
                      endContent={notConfigured ? (
                        <Tooltip content="Bot não configurado" color="danger">
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-500/10 border border-red-500/20 p-1 text-red-500">
                            <FontAwesomeIcon icon={faCircleExclamation} className="text-[10px]" />
                          </span>
                        </Tooltip>
                      ) : undefined}
                    >
                      {a?.name || a?.appId || "Aplicação"}
                    </DropdownItem>
                  );
                })}
                {apps && apps.length === 0 && (
                  <DropdownItem key="empty" isDisabled>Nenhuma aplicação encontrada</DropdownItem>
                )}
              </>
            )}
          </>
        )}
      </DropdownMenu>
    </Dropdown>
  );
}



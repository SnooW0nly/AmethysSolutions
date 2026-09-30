import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faXmark } from "@fortawesome/free-solid-svg-icons";
import { ScrollShadow } from "@heroui/react";
import { AppPicker } from "./AppPicker";
import { StatusBadges } from "./StatusBadges";
import { ActionButtons } from "./ActionButtons";
import { Logo } from "@/components/Icons";
import { SectionLinks } from "./SectionLinks";
import { ExpiryBanner } from "./ExpiryBanner";

type MobileDrawerProps = {
  isOpen: boolean;
  onClose?: () => void;
  name?: string | null;
  fallbackName?: string | null;
  appId?: string | null;
  copied: boolean;
  onCopy?: () => void;
  apps?: any[] | null;
  appsLoading?: boolean;
  onSelectApp?: (id: string) => void;
  statusDisplay: { label: string; dotClass: string };
  utilizedRam?: number | null;
  isRunning: boolean;
  isOffline: boolean;
  actionLoading: "start" | "stop" | "restart" | null;
  onAction: (action: "start" | "stop" | "restart") => void;
  botConfigured?: boolean;
  serverConfigured?: boolean;
  expiresAt?: string | null;
  planMonths?: number | null;
};

export function MobileDrawer({ isOpen, onClose, name, fallbackName, appId, copied, onCopy,  apps, appsLoading, onSelectApp, statusDisplay, utilizedRam, isRunning, isOffline, actionLoading, onAction, botConfigured, serverConfigured, expiresAt, planMonths }: MobileDrawerProps) {
  return (
    <div className={`md:hidden ${isOpen ? "fixed" : "hidden"} inset-0 z-100`}>
      <button aria-label="Fechar menu" onClick={onClose} className="absolute inset-0 bg-black/40" />
      <div className={`absolute left-0 top-0 h-full w-full bg-background border-r border-foreground/10 flex flex-col transform transition-transform duration-200 ${isOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="p-4 flex items-center justify-between sticky top-0 bg-background z-10">
          <div
              className="flex justify-start items-center gap-3 cursor-pointer select-none"
              onClick={() => {
                window.location.href = "/";
              }}
            >
              <Logo size={38} width={38} height={38} />
              <div className="flex flex-col leading-[15px]">
                <span className="text-foreground/90 font-normal font-sans text-[13px]">
                  Amethys
                </span>
                <span className="text-foreground/60 font-normal font-sans text-[12px]">
                  Applications
                </span>
              </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-md hover:bg-foreground/5" aria-label="Fechar">
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>
        <hr className="border-foreground/10 w-full sticky top-[56px] bg-background z-10" />
        {/* Header with app card + expiry pinned at top */}
        <div className="p-4 pt-3 sticky top-[57px] bg-background z-10">
          <div className="bg-foreground/2 border border-foreground/10 rounded-xl p-2 relative">
            <AppPicker
              name={name}
              fallbackName={fallbackName}
              appId={appId}
              copied={copied}
              onCopy={onCopy}
              apps={apps}
              appsLoading={appsLoading}
              onSelectApp={(id) => {
                onSelectApp?.(id);
                onClose?.();
              }}
              placement="bottom-start"
              className="min-w-[280px] outline-none"
              menuClassName="max-h-72 overflow-auto outline-none"
              sectionTitle="Selecionar aplicação"
              botConfigured={botConfigured}
            />
            <StatusBadges statusDisplay={statusDisplay} utilizedRam={utilizedRam} />
            <hr className="border-foreground/10 w-full my-2" />
            <ActionButtons isRunning={isRunning} isOffline={isOffline} actionLoading={actionLoading} onAction={onAction} onAfterAction={onClose} botConfigured={botConfigured} serverConfigured={serverConfigured} />
          </div>
          {/*<div className="mt-2">
            <ExpiryBanner expiresAt={expiresAt} months={planMonths ?? undefined} />
          </div>*/}
        </div>

        {/* Scrollable links only */}
        <ScrollShadow className="flex-1 overflow-y-auto p-4 pt-0 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
          <SectionLinks onNavigate={onClose} />
        </ScrollShadow>
      </div>
    </div>
  );
}



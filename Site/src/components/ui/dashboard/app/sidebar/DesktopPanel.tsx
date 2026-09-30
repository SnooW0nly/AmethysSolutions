import { ScrollShadow, Tooltip } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircleExclamation } from "@fortawesome/free-solid-svg-icons";
import { AppPicker } from "./AppPicker";
import { StatusBadges } from "./StatusBadges";
import { ActionButtons } from "./ActionButtons";
import { SectionLinks } from "./SectionLinks";
import { ExpiryBanner } from "./ExpiryBanner";

type DesktopPanelProps = {
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

export function DesktopPanel({ name, fallbackName, appId, copied, onCopy, apps, appsLoading, onSelectApp, statusDisplay, utilizedRam, isRunning, isOffline, actionLoading, onAction, botConfigured, serverConfigured, expiresAt, planMonths }: DesktopPanelProps) {
  console.log(botConfigured);
  return (
    <aside className="hidden md:flex w-70 bg-background border-r border-foreground/10 flex-col px-3">
      {/* Fixed header with app card and expiry banner */}
      <div className="sticky top-0 z-10 bg-background pt-4 pb-2">
        <div className="border border-foreground/10 rounded-lg p-2 relative">
          <AppPicker
            name={name}
            fallbackName={fallbackName}
            appId={appId}
            copied={copied}
            onCopy={onCopy}
            apps={apps}
            appsLoading={appsLoading}
            onSelectApp={onSelectApp}
            placement="bottom-start"
            className="min-w-[280px] outline-none"
            menuClassName="max-h-72 overflow-auto outline-none"
            sectionTitle="Selecionar aplicação"
            botConfigured={botConfigured}
          />
          <StatusBadges statusDisplay={statusDisplay} utilizedRam={utilizedRam} />
          <hr className="border-foreground/10 w-full my-2" />
          <ActionButtons isRunning={isRunning} isOffline={isOffline} actionLoading={actionLoading} onAction={onAction} botConfigured={botConfigured} serverConfigured={serverConfigured} />
        </div>
        {/*<div className="mt-2">
          <ExpiryBanner expiresAt={expiresAt} months={planMonths ?? undefined} />
        </div>*/}
      </div>

      {/* Scrollable sections and links area only */}
      <ScrollShadow className="flex-1 pr-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
        <div className="py-3">
          <SectionLinks />
        </div>
      </ScrollShadow>
    </aside>
  );
}


